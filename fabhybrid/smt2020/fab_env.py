"""Layer-1 environment: PySCFabSim's own dispatch loop with the ordering
decision handed to a policy.

The previous version reimplemented the loop, and lost 37% of the fab's
throughput doing it: 35.7 lots/day against the 57.2 released, WIP climbing
from 2,228 to 6,109 over 180 days, 61% of it past due. Upstream's own loop on
the same dataset, same seed, same t=0 state settles at 57-58 lots/day with
Lot_3 at 52.0 days and Lot_4 at 28.7 -- which is the benchmark's shipped
reference (51.21 / 28.38) to within a day. The fab was never the problem.

What the reimplementation left out is exactly what
`get_lots_to_dispatch_by_machine` does after it sorts:

  - group a machine's waiting lots by step and rank groups by batch FILL, not
    by the head lot alone;
  - refuse a batch that cannot be filled to batch_max, leaving the machine
    idle rather than burning a furnace slot on a half load;
  - if the chosen lots need a different setup, hand them to a sibling machine
    in the family that already has that setup;
  - honour min_runs_left, up to five deferrals.

So this module does not reimplement any of it. It runs upstream's loop and
upstream's selection code verbatim, and replaces one thing: which candidate
group goes on the machine. That is the only place a dispatching policy has
any business acting, and it keeps every hard constraint on upstream's side
where it cannot be quietly dropped.

The action space follows from that. At a decision point the environment
offers the machine's candidate groups, ordered by upstream's constraint
prefix, plus a defer action -- which is upstream's own `lots = None`, the
thing its rules do automatically whenever a batch is under-full. A rule can
only ever defer for that one reason; a policy can decide when a partial load
is worth running. That is the batching lever the static capacity check points
at, expressed as a choice rather than a threshold.

Reward: total weighted tardiness, accrued continuously. A lot pays
priority/10 per day for every day it sits unfinished past its deadline and
stops the moment it completes. Nothing is paid for being on time. Accrual
rather than a one-shot charge, because under a one-shot charge neglect is
free the instant after it is billed.
"""
import heapq
import os
import random
from collections import defaultdict
from typing import List

import numpy as np
import torch

import rl_env
from rl_env import (SECONDS_PER_DAY as SPD, compute_features, new_instance,
                    tool_groups, Dispatchers)
from cqt import CQTMonitor
import kopp
from simulation.plugins.interface import IPlugin

REGULAR = 10
MAX_DISPATCH_FAILED = 5          # upstream's min-runs deferral budget
N_EXTRA = 18                     # per-group columns appended to the 12 lot features


class _OutageTap(IPlugin):
    """Remembers until when each machine is out. Only an outage that hits a
    busy machine takes it out of service (the simulator shifts its pending
    events; an idle machine is left available), so only those are recorded."""

    def __init__(self):
        self.down_until = {}
        self._last_br, self._last_pm = {}, {}

    def reset(self, instance):
        self.down_until = {}
        self._last_br = {m.idx: m.bred_time for m in instance.machines}
        self._last_pm = {m.idx: m.pmed_time for m in instance.machines}

    def _mark(self, instance, m, length):
        if m.events and length > 0:
            self.down_until[m.idx] = max(self.down_until.get(m.idx, 0.0),
                                         instance.current_time + length)

    def on_breakdown(self, instance, ev):
        m = ev.machine
        self._mark(instance, m, m.bred_time - self._last_br.get(m.idx, 0.0))
        self._last_br[m.idx] = m.bred_time

    def on_preventive_maintenance(self, instance, ev):
        m = ev.machine
        self._mark(instance, m, m.pmed_time - self._last_pm.get(m.idx, 0.0))
        self._last_pm[m.idx] = m.pmed_time


def candidate_groups(instance, machine, ptuple_fcn, cqt=None, top_k=6):
    """Upstream's per-machine candidates, enumerated instead of decided.

    Mirrors `get_lots_to_dispatch_by_machine` up to the point where it takes
    `lot_l[0]`: score the machine's waiting lots, group batch steps by step
    name, and order the groups by the constraint prefix (cqt, min-run setup,
    batch fill, min-batch) before the rule's own priority terms. Returns the
    ordered groups; picking among them is the policy's job.
    """
    time = instance.current_time
    for lot in machine.waiting_lots:
        lot.ptuple = ptuple_fcn(lot, time, machine, instance.setups)
    wl = sorted(machine.waiting_lots, key=lambda k: k.ptuple)
    if not wl:
        return []
    if wl[0].actual_step.batch_max > 1:
        lot_m = defaultdict(list)
        for w in wl:
            lot_m[w.actual_step.step_name].append(w)
        return sorted(lot_m.values(), key=lambda l: (
            l[0].ptuple[0],
            l[0].ptuple[1],
            -min(1, len(l) / l[0].actual_step.batch_max),
            0 if len(l) >= l[0].actual_step.batch_min else 1,
            *(l[0].ptuple[2:]),
        ))
    # A non-batch step normally offers the rule's pick and nothing else, which
    # is why the policy never saw a queue-time decision: every clock start is a
    # singleton dispatch. When a constraint is in play, offer the alternatives
    # too, so declining to start a clock is an action the policy can take.
    if cqt is not None:
        involved = False
        for l in wl[:top_k]:
            if cqt.starts_clock(l.actual_step) is not None:
                involved = True
                break
            rec = cqt.open.get(id(l))
            if rec is not None and l.actual_step.order == rec[0]:
                involved = True
                break
        if involved and len(wl) > 1:
            return [[l] for l in wl[:top_k]]
    return [[wl[0]]]


def finalize_choice(instance, machine, lots, break_lock=False):
    """Upstream's post-selection handling, verbatim: truncate to batch_max,
    move to a sibling machine that already holds the setup, and honour
    min_runs_left. Returns (machine, lots) with lots None if it must defer.

    `break_lock` is the law's second deferral: a min-run lock is a load-building
    deferral like an under-full batch, and a lot whose clock is about to run
    out is worth more than the setup it saves. With break_lock the lock is
    ignored for this dispatch; nothing else changes."""
    lots = list(lots)
    if len(lots) > lots[0].actual_step.batch_max:
        lots = lots[:lots[0].actual_step.batch_max]
    if machine.current_setup != lots[0].actual_step.setup_needed:
        for m in instance.family_machines[machine.family]:
            if (m in instance.usable_machines
                    and m.current_setup == lots[0].actual_step.setup_needed):
                machine = m
                break
    if (not break_lock
            and machine.dispatch_failed < MAX_DISPATCH_FAILED
            and machine.min_runs_left is not None
            and machine.min_runs_setup != lots[0].actual_step.setup_needed):
        machine.dispatch_failed += 1
        return machine, None
    machine.dispatch_failed = 0
    return machine, lots


def group_is_full(group):
    return len(group) >= group[0].actual_step.batch_max


class FabEnv:
    """One decision = which candidate group runs on the freed machine, or
    defer. `ptuple_fcn` supplies the constraint prefix and a default ordering;
    the policy reorders within what it allows."""

    def __init__(self, dataset="HVLM", seed=0, episode_days=30,
                 horizon_days=None, rule="cr", plugins=None,
                 ptuple_fcn=None, cqt_weight=0.0, fam_feats=True, scrap=False,
                 cqt_rule="none", stopping="none", minrun_break_h=0.0,
                 minrun_net_setup=False, batch_only=False, reward="tardiness",
                 source_gate=None):
        self.dataset = dataset
        # the law's second deferral (hours); 0 leaves upstream's min-run lock alone
        self.minrun_break_h = float(minrun_break_h)
        # Read the residual NET of the setup the break would incur. At a batch
        # tool breaking the deferral starts service now, so residual and
        # time-to-start-of-service are the same number; at a setup lock they are
        # not -- the machine changes setup first (60-80 min on the implant
        # families) and the lot's clock runs through it. The law's statistic is
        # the time until service can BEGIN, which is this.
        self.minrun_net_setup = bool(minrun_net_setup)
        # batch_only: the policy sees batch decision points only; every other
        # decision is upstream's. reward "yield": +w per completion, -w per
        # scrapped lot (w = priority/10) -- the scrap game's own objective.
        self.batch_only = bool(batch_only)
        # env -> candidate group -> bool (True = refuse). None disables the hook
        # entirely, which is the default, so every earlier run reproduces.
        self.source_gate = source_gate
        if reward not in ("tardiness", "yield"):
            raise ValueError(f"reward must be 'tardiness' or 'yield', not {reward!r}")
        self.reward = reward
        self.seed = seed
        self.episode_days = episode_days
        self.horizon_days = horizon_days or rl_env.BENCH_DAYS
        self.ptuple_fcn = self._base_ptuple = ptuple_fcn or {
            "cr": Dispatchers.cr_ptuple_for_lot,
            "fifo": Dispatchers.fifo_ptuple_for_lot,
            "kopp": kopp.base_ptuple}[rule]
        # the simulator raises on_cqt_violated on its plugins; nothing in this
        # project ever listened, so queue-time breaks were invisible
        # A queue-time break is a point charge on one lot that the other 499
        # steps cannot offset -- the only quantity in this fab that does not
        # average. The monitor is always attached so the policy can see the
        # clocks; cqt_weight decides whether breaking one costs anything.
        self.cqt = CQTMonitor(scrap=scrap)
        self.cqt_weight = cqt_weight
        # the benchmark authors' own control, so anything built on top is
        # measured against them rather than against this project's inventions
        self.cqt_rule = cqt_rule
        # Kopp's lot stopping: a named scenario ("none"/"high"/"medium"/"small")
        # or a {family: (t1, t2)} dict. One entry point -- the scalar t1/t2 pair
        # it replaces set the same threshold on all 106 families, which is not
        # what they do and never fired here anyway.
        self.stop_scenario = stopping
        self.stopping = None
        # The ablation is the information, not the architecture: the three
        # target-family columns are emitted either way and the network is the
        # same size, so a difference between the two runs cannot be a
        # difference in capacity.
        # read from the environment as well, because training spawns worker
        # and eval subprocesses -- a flag threaded through call sites is one
        # missed argument away from an ablation that silently is not one
        self.fam_feats = fam_feats and os.environ.get("FAB_NO_FAM_FEATS") != "1"
        # which tools are out (an outage only bites a busy machine; an idle one
        # is never made unavailable, instance.py:219-227), for the features
        self._outage = _OutageTap()
        self.plugins = list(plugins or []) + [self.cqt, self._outage]
        inst0 = new_instance(dataset, seed=0, days=1, lot_for_machine=True)
        self.tools_type = tool_groups(inst0)
        self.tg_index = {g: i for i, g in enumerate(self.tools_type)}
        del inst0
        self.instance = None

    # ---- lifecycle -------------------------------------------------------
    def reset(self, seed=None, snapshot=None):
        """A fresh benchmark instance at t=0, or -- with `snapshot` (a path
        from scrap_snap.py) -- the warmed fab it holds, with the simulator's
        RNG restored so two candidates from the same snapshot see the same
        future (CRN), then reseeded per `seed` if one is given."""
        s = self.seed if seed is None else seed
        random.seed(s); np.random.seed(s); torch.manual_seed(s)
        if snapshot is None:
            self.instance = new_instance(self.dataset, seed=s,
                                         days=self.horizon_days,
                                         lot_for_machine=True,
                                         plugins=self.plugins)
        else:
            self.instance = self._restore(snapshot)
        inst = self.instance
        self.fam_machines = defaultdict(list)
        for m in inst.machines:
            self.fam_machines[m.family].append(m)
        self.t0 = inst.current_time
        self.t_end = self.t0 + self.episode_days * SPD
        self._sim_done = False
        self.stats = defaultdict(int)
        # Optional per-(family, step) load ledger. Off by default: when it is
        # None `_commit` does one boolean test and nothing else, so the default
        # path is unchanged. It exists because the fab-wide fill batch_fire
        # accumulates in its own loop cannot see the loads `_advance_to_decision`
        # auto-commits, and those are full by construction.
        self.load_ledger = None
        self.ledger_from = 0.0
        self._done_seen = len(inst.done_lots)
        self._lot_ix, self._lot_ref = {}, []
        self._tardy, self._tardy_w = {}, 0.0
        self.tardy_by_family = {}
        self._cqt_seen = 0
        self.cqt_charges = []          # (lot index, sim time, weight)
        self._acc_t, self.tardiness = self.t0, 0.0
        self._ddl = []
        for pool in (inst.active_lots, inst.dispatchable_lots):
            for l in pool:
                if l.deadline_at > inst.current_time:
                    heapq.heappush(self._ddl, (l.deadline_at, id(l), l))
                elif getattr(l, "done_at", None) is None:
                    self._open_tardy(l, inst.current_time)
        self._fam_ema, self._fam_state = {}, {}
        self._fam_lost = {m.idx: m.bred_time + m.pmed_time for m in inst.machines}
        self._fam_t, self._fam_next = self.t0, self.t0
        self._refresh_fam()
        self.cqt.on_scrap = self._on_scrap
        if self.cqt_rule == "qtcr":
            self.ptuple_fcn = kopp.qtcr_ptuple(self._base_ptuple, self.cqt)
        elif self.cqt_rule == "cqt_first":
            self.ptuple_fcn = kopp.cqt_first_ptuple(self._base_ptuple, self.cqt)
        per = (self.stop_scenario if isinstance(self.stop_scenario, dict)
               else kopp.Stopping.SCENARIOS.get(self.stop_scenario, {}))
        if per:
            self.stopping = kopp.Stopping(self.cqt, inst, per_family=per)
        self.scrapped = 0
        self._machine, self._groups = None, None
        # yield reward: point charges per lot, (lot id, sim time, value)
        self._yield = []
        self._yield_pending = 0.0
        self._outage.reset(inst)
        # earliest future arrival per (family, step_name): a heap of
        # (arrival time, lot id) fed at dispatch, so a look-ahead rule reads
        # "when does the next lot for this load get here" in O(1) instead of
        # sweeping the active lots at every batch decision
        self._next_arr = defaultdict(list)
        if snapshot is not None:
            self._refill_next_arrivals()
        self._advance_to_decision()
        return self._obs()

    def _restore(self, path):
        """Load a scrap_snap.py snapshot: install this env's plugins on the
        instance, rebuild the queue-time monitor's tables (they are keyed by
        object identity, which the pickle round-trip changed) from the marks
        the snapshot left on the lots, and refill the next-arrival index from
        the machines' pending lot-done events."""
        import gzip
        import cloudpickle
        from simulation.randomizer import Randomizer
        with gzip.open(path, "rb") as f:
            snap = cloudpickle.load(f)
        inst = snap["inst"]
        Randomizer().random.setstate(snap["rng"])
        inst.plugins = list(self.plugins)
        mon = self.cqt
        mon.on_sim_init(inst)
        mon.open = {}
        mon._expiry = []
        mon._seq = 0
        for lot in list(inst.active_lots) + list(inst.dispatchable_lots):
            rec = getattr(lot, "_cqt_open", None)
            if rec is not None:
                mon.open[id(lot)] = rec
                if mon.scrap:
                    mon._seq += 1
                    heapq.heappush(mon._expiry, (rec[1], mon._seq, lot))
        mon.events, mon.scrapped, mon.slack = [], [], []
        mon.n_started = mon.n_violated = 0
        mon.by_family.clear(); mon.viol_by_family.clear()
        mon.t0 = inst.current_time
        self._snapshot_meta = snap.get("meta", {})
        return inst

    def _refill_next_arrivals(self):
        """Lots in process whose next step is a batch step, from the machines'
        pending lot-done events (used after a snapshot restore)."""
        for m in self.instance.machines:
            for ev in m.events:
                for lot in getattr(ev, "lots", ()) or ():
                    nxt = lot.remaining_steps[0] if lot.remaining_steps else None
                    if nxt is not None and nxt.batch_max > 1:
                        heapq.heappush(self._next_arr[(nxt.family, nxt.step_name)],
                                       (ev.timestamp, id(lot)))

    def next_arrival(self, family, step_name):
        """Absolute time of the earliest lot now in process whose next step is
        (family, step_name); None if nothing is on its way. Entries that have
        already arrived are dropped on read."""
        h = self._next_arr.get((family, step_name))
        if not h:
            return None
        now = self.instance.current_time
        while h and h[0][0] <= now:
            heapq.heappop(h)
        return h[0][0] if h else None

    def _on_scrap(self, lot):
        """A scrapped lot leaves the fab without completing. It must stop
        accruing tardiness -- otherwise it is charged forever, since the charge
        only ends at completion and completion never comes."""
        self.scrapped += 1
        self._close_tardy(lot, self.instance.current_time)
        w = lot.priority / REGULAR
        self._yield.append((self.lot_id(lot), self.instance.current_time, -w))
        self._yield_pending -= w

    FAM_REFRESH_S = 3600.0             # family state is a slow variable
    # ~10 days at that cadence. Two days was wrong: the validated signal is the
    # queue against the family's long-run typical level, and a two-day baseline
    # catches up to a three-day excursion and erases exactly the case worth
    # seeing. Long enough to be a level, short enough to be this fab's level.
    FAM_EMA = 1.0 / 240.0

    def _refresh_fam(self):
        """Per family: how loaded it is now, how that compares with its own
        recent level, and how much tool time it has just lost.

        Recomputed on a clock rather than per decision -- a sweep of the active
        lots costs about as much as 2,300 dispatches, and a family's queue is a
        slow variable. The comparison is against the family's OWN recent level
        because families differ by an order of magnitude in baseline queue, so
        an absolute count would mostly say which family this is.
        """
        inst = self.instance
        now = inst.current_time
        q = defaultdict(int)
        for l in inst.active_lots:
            st = getattr(l, "actual_step", None)
            f = getattr(st, "family", None) if st is not None else None
            if f is not None:
                q[f] += 1
        dt = max(60.0, now - self._fam_t)
        lost = defaultdict(float)
        for m in inst.machines:
            cur = m.bred_time + m.pmed_time
            lost[m.family] += cur - self._fam_lost.get(m.idx, 0.0)
            self._fam_lost[m.idx] = cur
        for f, ms in self.fam_machines.items():
            n = max(1, len(ms))
            per_tool = q.get(f, 0) / n
            ema = self._fam_ema.get(f)
            # ratio first, then update: the comparison must be against the past,
            # not against a mean that already contains the present
            rel = per_tool / ema if ema else 1.0
            self._fam_ema[f] = per_tool if ema is None else \
                ema + self.FAM_EMA * (per_tool - ema)
            self._fam_state[f] = (min(20.0, per_tool),
                                  min(5.0, rel),
                                  min(1.0, lost[f] / (n * dt)))
        self._fam_q = dict(q)
        self._fam_t = now
        self._fam_next = now + self.FAM_REFRESH_S

    def rebuild_deadlines(self):
        """Rebuild the deadline heap from the lots' CURRENT deadlines.

        Anything that edits deadline_at after reset -- release rescaling, for
        one -- leaves the heap holding the values it was built with, so lots
        are charged tardy against dates they no longer have. Call this after
        any such edit. Symptom if you do not: tardiness that rises as the fab
        gets EASIER, 8,125 lot-days per day at 100% on-time.
        """
        inst = self.instance
        now = inst.current_time
        self._ddl = []
        self._tardy, self._tardy_w = {}, 0.0
        self.tardy_by_family = {}
        self._cqt_seen = 0
        self.cqt_charges = []          # (lot index, sim time, weight)
        self._acc_t, self.tardiness = now, 0.0
        for pool in (inst.active_lots, inst.dispatchable_lots):
            for l in pool:
                if l.deadline_at > now:
                    heapq.heappush(self._ddl, (l.deadline_at, id(l), l))
                elif getattr(l, "done_at", None) is None:
                    self._open_tardy(l, now)

    # ---- lot identity ----------------------------------------------------
    def lot_id(self, lot):
        k = id(lot)
        i = self._lot_ix.get(k)
        if i is None:
            i = len(self._lot_ref)
            self._lot_ix[k] = i
            self._lot_ref.append(lot)
        return i

    def cand_ids(self):
        """Every lot this decision arbitrates, flat, with the sizes needed to
        map them back to the candidate groups the observation describes.

        A batch group moves as a unit, so the decision's scope is all of its
        lots, not just the head the features were computed from. Returns
        (lot ids, lots per group) with sum(sizes) == len(ids)."""
        sizes = np.fromiter((len(g) for g in self._groups), np.int32,
                            len(self._groups))
        ids = np.fromiter((self.lot_id(l) for g in self._groups for l in g),
                          np.int32, int(sizes.sum()))
        return ids, sizes

    def tardy_intervals(self):
        n = len(self._tardy)
        ix = np.zeros(n, np.int32); a = np.zeros(n, np.float64)
        b = np.zeros(n, np.float64); w = np.zeros(n, np.float32)
        now = self.instance.current_time
        for k, (lid, (s, e, ww)) in enumerate(self._tardy.items()):
            ix[k] = lid; a[k] = s; b[k] = now if e is None else e; w[k] = ww
        return ix, a, b, w

    # ---- tardiness accrual ----------------------------------------------
    def _accrue_to(self, t):
        if t > self._acc_t:
            self.tardiness += self._tardy_w * (t - self._acc_t) / SPD
            self._acc_t = t

    def _open_tardy(self, lot, when):
        lid = self.lot_id(lot)
        if lid in self._tardy:
            return
        w = lot.priority / REGULAR
        self._tardy[lid] = [when, None, w]
        self._tardy_w += w
        self.stats["went_tardy"] += 1
        # where the lot was standing when it went late. The directive
        # vocabulary is family-scoped, so this is the unit a prediction has to
        # name if it is going to be settled against what a directive did.
        st = getattr(lot, "actual_step", None)
        fam = getattr(st, "family", None) if st is not None else None
        if fam is not None:
            self.tardy_by_family[fam] = self.tardy_by_family.get(fam, 0.0) + w

    def _close_tardy(self, lot, when):
        lid = self._lot_ix.get(id(lot))
        rec = self._tardy.get(lid) if lid is not None else None
        if rec is None or rec[1] is not None:
            return
        rec[1] = when
        self._tardy_w -= rec[2]

    def _due_events(self, now):
        out = []
        while self._ddl and self._ddl[0][0] <= now:
            _, _, l = heapq.heappop(self._ddl)
            # a scrapped lot is gone; it neither completes nor keeps accruing.
            # Left in, it would be charged from its due date to the end of the
            # run, because the charge only stops at a completion that never
            # comes -- which is what made scrapping look 36x worse than it is.
            if getattr(l, "scrapped_at", None) is not None:
                continue
            if getattr(l, "done_at", None) is None or l.done_at > l.deadline_at:
                out.append((l.deadline_at, l))
        return out

    def _settle(self, now):
        """Charge the tardiness that accrued up to `now`, event by event."""
        events = self._due_events(now)
        dl = self.instance.done_lots
        for l in dl[self._done_seen:]:
            if l.done_at <= l.deadline_at:
                self.stats["ontime"] += 1
            else:
                self.stats["late"] += 1
                events.append((l.done_at, l))
            w = l.priority / REGULAR
            self._yield.append((self.lot_id(l), l.done_at, w))
            self._yield_pending += w
        self._done_seen = len(dl)
        before = self.tardiness
        for t_ev, lot in sorted(events, key=lambda e: e[0]):
            self._accrue_to(min(t_ev, now))
            if getattr(lot, "done_at", None) is not None and lot.done_at <= t_ev:
                self._close_tardy(lot, lot.done_at)
            else:
                self._open_tardy(lot, lot.deadline_at)
        self._accrue_to(now)
        charged = 0.0
        for ev in self.cqt.events[self._cqt_seen:]:
            if ev["late"]:
                charged += 1.0
                self.cqt_charges.append((ev["day"], 1.0))
        self._cqt_seen = len(self.cqt.events)
        self.cqt_violations = getattr(self, "cqt_violations", 0) + int(charged)
        if self.reward == "yield":
            # step() negates the return value (a cost); yield is a gain
            r, self._yield_pending = self._yield_pending, 0.0
            return -r
        return (self.tardiness - before) + self.cqt_weight * charged

    def yield_events(self):
        """Every point charge since reset: (lot ids, sim times, values), values
        +w for a completion and -w for a scrap. The material for lot-scoped
        credit under the yield reward."""
        n = len(self._yield)
        ids = np.zeros(n, np.int32); t = np.zeros(n, np.float64); v = np.zeros(n, np.float32)
        for k, (lid, tt, vv) in enumerate(self._yield):
            ids[k], t[k], v[k] = lid, tt, vv
        return ids, t, v

    # ---- upstream's loop -------------------------------------------------
    def _advance_to_decision(self):
        """Upstream's l4m loop, stopping when a machine has a real choice."""
        inst = self.instance
        for _ in range(5_000_000):
            if inst.done or inst.current_time > self.t_end:
                self._sim_done = True
                return
            self.cqt.sweep(inst)
            if inst.next_decision_point():
                self._sim_done = True
                return
            machine = next(iter(inst.usable_machines), None)
            if machine is None:
                self._sim_done = True
                return
            groups = candidate_groups(inst, machine, self.ptuple_fcn,
                                      cqt=self.cqt)
            if groups and self.stopping is not None:
                self.stopping.refresh(inst)
                keep = [g for g in groups if not self.stopping.holds(g[0])]
                if keep:
                    groups = keep
            if not groups:
                inst.usable_machines.remove(machine)
                continue
            # A SOURCE GATE, if armed, filters candidates before anything else.
            # US 6,647,307 (TSMC, filed 2002, granted 2003) puts the decision at
            # the tool that STARTS a queue-time clock: read the target tool's
            # loading and refuse to start a clock that cannot be met. It has to
            # sit HERE, above the auto-commit branches, because `group_is_full`
            # is trivially true for a non-batch step (batch_max = 1), so a
            # single-candidate non-batch dispatch is taken as dynamics and never
            # reaches the batch_only branch -- with the hook there it saw zero
            # clock-source decisions in a 20-day run. Filtering rather than
            # deferring also gives the comparator its best shot: gating a LOT
            # should not idle a tool that has other work. None by default, so
            # every earlier run reproduces bit for bit.
            if self.source_gate is not None:
                keep = [g for g in groups if not self.source_gate(self, g)]
                if not keep:
                    self._defer(machine)
                    self.stats["source_gated"] += 1
                    continue
                if len(keep) != len(groups):
                    self.stats["source_filtered"] += 1
                groups = keep
            # A single full group with nothing to weigh it against is dynamics,
            # not a decision: upstream would take it and so do we.
            if len(groups) == 1 and group_is_full(groups[0]):
                self._commit(machine, groups[0])
                self.stats["auto"] += 1
                continue
            # batch_only: a non-batch step is upstream's decision (its first
            # group); the policy only ever sees a batch tool's choice
            if self.batch_only and groups[0][0].actual_step.batch_max <= 1:
                self._commit(machine, groups[0])
                self.stats["auto_nonbatch"] += 1
                continue
            self._machine, self._groups = machine, groups
            return
        raise RuntimeError("advance stuck")

    def _setup_cost(self, machine, lot):
        """Seconds of setup this dispatch would incur on this machine, read the
        way the simulator reads it in `Instance.get_times`."""
        step = lot.actual_step
        ns = getattr(step, "setup_needed", "")
        if ns == "" or machine.current_setup == ns:
            return 0.0
        if getattr(step, "setup_time", None) is not None:
            return float(step.setup_time)
        s = self.instance.setups
        if (machine.current_setup, ns) in s:
            return float(s[(machine.current_setup, ns)])
        return float(s.get(("", ns), 0.0))

    def _commit(self, machine, group):
        inst = self.instance
        brk = False
        if self.minrun_break_h > 0.0:
            # any open clock counts, whatever its target: a lot held here by a
            # setup lock spends the margin of a clock that stops downstream
            now = inst.current_time
            st = self._setup_cost(machine, group[0]) if self.minrun_net_setup else 0.0
            for l in group:
                rec = self.cqt.open.get(id(l))
                if rec is not None and 0.0 <= rec[1] - now - st < self.minrun_break_h * 3600.0:
                    brk = True
                    break
            if brk:
                g0 = group[0]
                locked = (machine.dispatch_failed < MAX_DISPATCH_FAILED
                          and machine.min_runs_left is not None
                          and machine.min_runs_setup != g0.actual_step.setup_needed)
                if locked:
                    self.stats["minrun_broken"] += 1
        machine, lots = finalize_choice(inst, machine, group, break_lock=brk)
        if lots is None:
            if machine in inst.usable_machines:
                inst.usable_machines.remove(machine)
            self.stats["defer_minruns"] += 1
            return False
        if self.load_ledger is not None and inst.current_time >= self.ledger_from:
            # every load, whoever decided it: this is the only funnel both the
            # auto-commit path and step() pass through
            st0 = lots[0].actual_step
            rec = self.load_ledger.setdefault(
                (machine.family, st0.step_name),
                {"batch_max": st0.batch_max, "loads": 0, "lots": 0, "partial": 0})
            rec["loads"] += 1
            rec["lots"] += len(lots)
            if st0.batch_max > 1 and len(lots) < st0.batch_max:
                rec["partial"] += 1
        _, l_done = inst.dispatch(machine, lots)
        # l_done already includes the transport to the next step, so it is the
        # arrival time there; only batch steps are indexed, nothing else reads it
        nxt = lots[0].remaining_steps[0] if lots[0].remaining_steps else None
        if nxt is not None and nxt.batch_max > 1:
            heapq.heappush(self._next_arr[(nxt.family, nxt.step_name)],
                           (l_done, id(lots[0])))
        self.stats["dispatch"] += 1
        self.stats["lots_dispatched"] += len(lots)
        return True

    def _defer(self, machine):
        if machine in self.instance.usable_machines:
            self.instance.usable_machines.remove(machine)
        self.stats["defer"] += 1

    # ---- gym-ish API -----------------------------------------------------
    def n_actions(self):
        return len(self._groups) + 1        # groups + defer

    def _obs(self):
        if self._sim_done:
            return None
        heads: List = [g[0] for g in self._groups]
        feats, tg = compute_features(heads, self.instance,
                                     self.instance.current_time, self.tg_index)
        # two things the per-lot features cannot see: how full this group is,
        # and how many lots it holds. They are what a defer decision turns on.
        now = self.instance.current_time
        if now >= self._fam_next:
            self._refresh_fam()
        extra = np.zeros((len(self._groups), N_EXTRA), np.float32)
        # station-level columns are the same for every group at this tool:
        # what is on its way to this load, and how much of the family is up
        fam = self._machine.family
        fam_ms = self.fam_machines.get(fam, ())
        free = getattr(self.instance, "free_machines", None)
        idle = sum(1 for m in fam_ms if free is not None and free[m.idx]) if fam_ms else 0
        down = sum(1 for m in fam_ms if self._outage.down_until.get(m.idx, 0.0) > now)
        for i, g in enumerate(self._groups):
            extra[i, 0] = len(g) / max(1, g[0].actual_step.batch_max)
            extra[i, 1] = len(g)
            st_g = g[0].actual_step
            if st_g.batch_max > 1:
                nxt = self.next_arrival(st_g.family, st_g.step_name)
                extra[i, 11] = min(24.0, (nxt - now) / 3600.0) if nxt is not None else -1.0
                heap = self._next_arr.get((st_g.family, st_g.step_name), ())
                extra[i, 12] = sum(1 for t, _ in heap if now < t <= now + 3600.0)
                extra[i, 13] = sum(1 for t, _ in heap if now < t <= now + 4 * 3600.0)
            else:
                extra[i, 11] = -1.0
            extra[i, 14] = idle
            extra[i, 15] = down
            extra[i, 16] = st_g.batch_max
            # the group's tightest live queue-time clock, if any
            best = None
            for l in g:
                rec = self.cqt.open.get(id(l))
                if rec is not None and l.actual_step.order == rec[0]:
                    left = (rec[1] - now) / 3600.0
                    if best is None or left < best:
                        best = left
            if best is not None:
                extra[i, 2] = 1.0
                extra[i, 3] = max(-48.0, min(48.0, best))
            # the same margin with "no clock" read as a wide margin, so that a
            # minimum over groups is the tool's tightest clock -- the quantity
            # the law thresholds (column 3 keeps its legacy zero default)
            extra[i, 17] = max(-48.0, min(48.0, best)) if best is not None else 48.0
            # and whether running this group would START a clock: the only
            # move that avoids the trade instead of making it
            st = self.cqt.starts_clock(g[0].actual_step)
            if st is not None:
                extra[i, 4] = 1.0
                extra[i, 5] = st[1] / 3600.0
                # ...and the state of the family the clock will have to reach.
                # This is what separates a clock that will be met from one that
                # will not: breaks concentrate in small families whose queue was
                # already elevated a day earlier, and nothing about the source
                # step says where the target step sits or how backed up it is.
                tf = self.cqt.target_family(g[0].actual_step)
                cs = self._fam_state.get(tf) if (tf and self.fam_feats) else None
                if cs is not None:
                    extra[i, 7] = cs[1]                       # queue vs its own typical level
                    extra[i, 8] = cs[0]                       # and the level itself, per tool
                    extra[i, 9] = cs[2] * 100.0               # tool time just lost
                    extra[i, 10] = min(30.0, len(self.fam_machines.get(tf, ())))
            # where the rule would rank this group. Without it the policy has
            # to re-derive the rule's ordering from raw features before it can
            # even imitate it, which is why cloning fell to 88%; with it, the
            # policy's job is the interesting one -- when to deviate.
            extra[i, 6] = i
        return feats, tg, torch.from_numpy(extra), True

    def step(self, action):
        machine, groups = self._machine, self._groups
        if action == len(groups):
            self._defer(machine)
        else:
            self._commit(machine, groups[action])
        self._advance_to_decision()
        r = -self._settle(self.instance.current_time)
        done = self._sim_done
        return (None if done else self._obs()), r, done, {}

    def rule_action(self):
        """What the underlying rule would do: take the first group if it is
        full, otherwise defer -- upstream's exact behaviour."""
        return 0 if group_is_full(self._groups[0]) else len(self._groups)
