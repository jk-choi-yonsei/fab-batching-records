"""Queue-time constraints, implemented here because the simulator's are inert.

SMT2020 ships the constraints in the route files -- 66 across the two HVLM
routes, 264 across LVHM's ten, at 1, 2, 4, 8 and 10 hours. PySCFabSim reads
them and has the checking code. Neither works, for two reasons in sequence:

  classes.py: `cqt_for_step = d['STEP_CQT'] if 'STEP_CQT' in d else None`
    The column is present on every row, so this is never None -- it is the
    empty string for the ~93% of steps that have no constraint. Every step
    therefore looks constrained.

  instance.py: `if lot.actual_step.order == lot.cqt_waiting`
    order is an int, cqt_waiting is that raw string, so the comparison is
    always False and on_cqt_violated never fires. Measured: 0 violations and
    0 constrained arrivals over 20 simulated days.

  instance.py: `lot.cqt_deadline = lot.actual_step.cqt_time` then
  `if lot.cqt_deadline < self.current_time`
    A duration compared against an absolute timestamp. Latent behind the
    first bug; fixing the parse alone would flag every arrival instead.

So rather than patch three places in vendored code, the constraint is
implemented against the plugin interface, where the definition is explicit and
ours: the clock starts when the source step COMPLETES -- that is what a queue
time is, the wafer sitting exposed after an operation -- and stops when the
target step starts. Late means the lot broke the constraint.

This matters beyond bookkeeping. Every other quantity in this fab averages
away: a cycle time is a sum over 500+ steps and concentrates, so no lot is
ever especially unlucky. A queue-time break does not average. It is one
event, at one step, with a discrete consequence for that lot, and the other
499 steps cannot compensate.
"""
import heapq
from collections import Counter, defaultdict

from rl_env import SECONDS_PER_DAY as SPD


def constraints(instance):
    """Step object -> (target step order, limit in seconds), parsed the way the
    data means it. Keyed by identity so a lookup is O(1): the monitor is called
    on every step completion and every dispatch."""
    out = {}
    for rname, route in instance.routes.items():
        for s in route.steps:
            raw = getattr(s, "cqt_for_step", None)
            if raw is None or str(raw).strip() == "":
                continue
            try:
                tgt = int(str(raw).strip())
            except ValueError:
                continue
            lim = getattr(s, "cqt_time", None)
            if not isinstance(lim, (int, float)) or lim <= 0:
                continue
            out[id(s)] = (tgt, float(lim))
    return out


class CQTMonitor:
    """Starts a clock when a constrained step finishes, stops it when the
    target step starts, and records whether the lot made it."""

    def __init__(self, scrap=False):
        # Kopp, Hassoun, Kalir and Mönch state that lots breaking a CQT
        # constraint "have to be scrapped"; the RL papers on the same problem
        # (Altenmüller 2020, and Applied Materials' queue-time work) follow the
        # opposite convention and let the lot finish its route. The choice is
        # not cosmetic: under scrapping a break costs a finished lot, so
        # violations and throughput stop being independent axes and the
        # intervention trade-off becomes a single one. Default off so every
        # earlier measurement still reproduces.
        self.scrap = scrap
        self.scrapped = []
        self.on_scrap = None            # env callback: it owns the tardiness books
        self._expiry = []               # heap of (deadline, seq, lot)
        self._seq = 0
        self.rules = None
        self.tfam = {}                  # id(source step) -> family of the TARGET step
        self.open = {}                  # lot id -> (target, deadline, source, limit)
        self.events = []                # every resolved constraint
        self.n_started = 0
        self.n_violated = 0
        self.by_family = Counter()
        self.viol_by_family = Counter()
        self.slack = []                 # seconds to spare at the target step
        self.t0 = 0.0

    def on_sim_init(self, instance):
        self.t0 = instance.current_time
        self.rules = constraints(instance)
        self._map_targets(instance)

    def _map_targets(self, instance):
        """Which family will the lot have to reach before the clock runs out.
        Breaks concentrate in family-day cells rather than in families or in
        days -- the worst decile of cells carries 56% of them against 41% for
        an equal-rate null -- and the cells that go bad are in SMALL families
        whose queue was already elevated the day before. So the congestion of
        the family at the far end of the clock is the thing worth knowing
        before starting one, and it is not derivable from the source step."""
        for route in instance.routes.values():
            fam = {s.order: getattr(s, "family", None) for s in route.steps}
            for s in route.steps:
                rec = self.rules.get(id(s))
                if rec is not None:
                    self.tfam[id(s)] = fam.get(rec[0])

    def target_family(self, step):
        if not self.tfam and self.rules:
            return None
        return self.tfam.get(id(step))

    def _route(self, lot):
        return getattr(lot, "part_name", None) or getattr(lot, "name", None)

    def on_step_done(self, instance, lot, step):
        if self.rules is None:
            self.rules = constraints(instance)
            self._map_targets(instance)
        rec = self.rules.get(id(step))
        if rec is None:
            return
        tgt, lim = rec
        deadline = instance.current_time + lim
        self.open[id(lot)] = (tgt, deadline, step.order, lim)
        self.n_started += 1
        if self.scrap:
            self._seq += 1
            heapq.heappush(self._expiry, (deadline, self._seq, lot))

    def on_dispatch(self, instance, machine, lots, machine_end_time, lot_end_time):
        now = instance.current_time
        for l in lots:
            rec = self.open.get(id(l))
            if rec is None:
                continue
            tgt, deadline, src, lim = rec
            if l.actual_step.order != tgt:
                continue
            late = now > deadline
            fam = l.actual_step.family
            self.by_family[fam] += 1
            self.slack.append(deadline - now)
            if late:
                self.n_violated += 1
                self.viol_by_family[fam] += 1
            self.events.append({"day": (now - self.t0) / SPD, "lot": l.name,
                                "src": src, "tgt": tgt, "limit_h": lim / 3600.0,
                                "family": fam, "late": bool(late),
                                "slack_h": (deadline - now) / 3600.0})
            del self.open[id(l)]

    # -- unused hooks the simulator may call ------------------------------
    def on_sim_done(self, instance): pass
    def on_lots_release(self, instance, lots): pass
    def on_lot_done(self, instance, lot): pass
    def on_machine_free(self, instance, machine): pass
    def on_lot_free(self, instance, lot):
        if self.scrap:
            self._maybe_scrap(instance, lot)
    def on_breakdown(self, machine, ev): pass
    def on_preventive_maintenance(self, machine, ev): pass
    def on_cqt_violated(self, instance, machine, lot): pass
    def get_output_name(self): return None

    def sweep(self, instance):
        """Scrap the lots whose clock has run out while they waited.

        Cheap enough to call at every decision point: the heap only surfaces
        lots whose deadline has actually passed. A lot that is mid-process when
        its clock expires is left alone -- a running furnace is not aborted --
        and is caught by on_lot_free when the step finishes.
        """
        if not self.scrap:
            return 0
        now, n = instance.current_time, 0
        while self._expiry and self._expiry[0][0] <= now:
            _, _, lot = heapq.heappop(self._expiry)
            n += self._maybe_scrap(instance, lot)
        return n

    def _maybe_scrap(self, instance, lot):
        rec = self.open.get(id(lot))
        if rec is None or instance.current_time <= rec[1]:
            return 0
        if not getattr(lot, "waiting_machines", None):
            return 0                    # on a machine; on_lot_free will catch it
        tgt, deadline, src, lim = rec
        # the same bookkeeping a resolved constraint gets, so rates stay
        # comparable whichever convention is in force
        fam = getattr(lot.actual_step, "family", None)
        self.by_family[fam] += 1
        self.viol_by_family[fam] += 1
        self.n_violated += 1
        self.slack.append(deadline - instance.current_time)
        self.events.append({"day": (instance.current_time - self.t0) / SPD,
                            "lot": lot.name, "src": src, "tgt": tgt,
                            "limit_h": lim / 3600.0, "family": fam,
                            "late": True, "scrapped": True,
                            "slack_h": (deadline - instance.current_time) / 3600.0})
        del self.open[id(lot)]
        self._remove(instance, lot)
        self.scrapped.append(lot)
        if self.on_scrap is not None:
            self.on_scrap(lot)
        return 1

    @staticmethod
    def _remove(instance, lot):
        """Take the lot out of the fab, mirroring what the dispatch manager does
        when a lot is reserved -- minus the machine, which stays free."""
        for m in list(getattr(lot, "waiting_machines", ())):
            if lot in m.waiting_lots:
                m.waiting_lots.remove(lot)
            if not m.waiting_lots and m in instance.usable_machines:
                instance.usable_machines.remove(m)
        lot.waiting_machines.clear()
        if lot in instance.active_lots:
            instance.active_lots.remove(lot)
        lot.scrapped_at = instance.current_time

    def starts_clock(self, step):
        """Would dispatching a lot AT this step start a queue-time clock?
        The policy needs this to have the avoidance move at all: yielding once
        a clock is running is a fixed-rate trade, but not starting one is not.
        """
        if self.rules is None:
            return None
        return self.rules.get(id(step))

    def summary(self, days):
        n, v = self.n_started, self.n_violated
        resolved = len(self.events)
        return {"clocks_started": n, "resolved": resolved, "violations": v,
                "scrapped": len(self.scrapped),
                "violation_rate": (v / resolved) if resolved else None,
                "violations_per_day": v / days if days else None,
                "still_open_at_end": len(self.open),
                "worst_families": self.viol_by_family.most_common(8)}


def cqt_aware(base_fcn, monitor, threshold_h=None):
    """The rules already reserve a slot for queue-time urgency -- position 1 of
    the priority tuple, `0 if lot.cqt_waiting is not None else 1`. That term is
    0 for every lot because of the parse bug, so it orders nothing. This
    rebuilds the same tuple with the slot filled from the monitor, which knows
    which lots are on a live clock and when it runs out.

    Nothing else moves: position 0 stays the min-runs constraint, and the
    rule's own ordering (critical ratio, or FIFO) still breaks ties. The only
    change is that a lot standing at the step its clock is counting down to
    now goes first.
    """
    def f(lot, time, machine=None, setups=None):
        t = list(base_fcn(lot, time, machine, setups))
        rec = monitor.open.get(id(lot))
        urgent = 1
        if rec is not None and lot.actual_step.order == rec[0]:
            # threshold_h None means always yield to a clock, which is what the
            # rule intended; a finite value yields only once the clock is that
            # close, which is what traces the curve between the two extremes
            if threshold_h is None or (rec[1] - time) / 3600.0 <= threshold_h:
                urgent = 0
        if len(t) > 1:
            t[1] = urgent
        else:
            t = [urgent] + t
        return tuple(t)
    return f
