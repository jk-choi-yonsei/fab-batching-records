"""Should an under-full furnace run anyway, and should a queue-time clock decide it?

Measured 2026-09-04 (`batch_probe.py`, now archive/2026-09-closed-axes/, 180 d, measured
from day 90): upstream refuses any batch group short of `batch_max` (greedy.py:50) and
idles the tool. That refusal fires at **83-86% of all batch decision points** on both
datasets -- 142,261 times on HVLM and 125,976 on LVHM in a 90-day window. At a refusal the
fullest group already holds 3 of 5-6 lots a third of the time and 4 a quarter of
the time, and **45% (HVLM) / 42% (LVHM) of refusals have a waiting lot carrying a
live queue-time clock**, the tightest of them a median 2.4 h (HVLM) / 0.7 h
(LVHM) from violating.

So the batch rule and the residency constraint are in direct conflict, and
nothing in the literature arbitrates it: the classical batching rules (MBS,
Glassey & Weng 1991 look-ahead) cost a hold in cycle time only, because they do
not model tunnels; Kopp's queue-time rules are sequencing rules and never touch
batch formation. This measures the arbitration.

Three arms, one decision changed -- what to do when the best group is under-full:

  full      upstream: defer, idle the tool. The baseline.
  mbs:k     fire it if it holds at least k lots. The classical rule, and the
            baseline any reviewer will demand. k = batch_max reproduces `full`.
  clock:h   fire it if some lot waiting at this tool holds a live clock with
            less than h hours left. ONE coefficient, and provably inert at
            h = 0: the trigger set {0 <= margin < 0} is empty, so the arm is
            bit-identical to `full`. Asserted at launch, not assumed.

The guard is throughput and cycle time. Firing under-full loads wastes furnace
capacity, and the static capacity check says Diffusion has little to waste (72%
of available at full batches, 104% at the observed 69.4% fill). An arm that buys
violations with output is a loss, so both are reported on every run and the
comparison is at matched realised fill. This stack carries no cost plugin -- the
benchmark's published cost lives in `sota_repro` -- so throughput and ACT stand
in for it, and they are the right guard for this particular lever.

  python batch_fire.py --dataset LVHM --scale 0.98 --days 180 --arm clock:2 --seed 0
"""
import argparse
import json
import os
import time

import numpy as np

import bench_metrics
from fab_env import FabEnv, group_is_full
from rl_env import SECONDS_PER_DAY as SPD


def parse_arm(s):
    if s == "full":
        return ("full", 0.0)
    kind, _, val = s.partition(":")
    if kind not in ("mbs", "mbsmin", "clock", "clockany", "select", "level", "timeout", "nach", "nach_dl", "explore", "nxtrule"):
        raise SystemExit(f"unknown arm {s!r}")
    return (kind, float(val) if val else 0.0)


SLACK = {}          # (family, step) -> list of residuals at a lot's FIRST sighting
_SLACK_SEEN = set()
SLACK_FROM = [0.0]  # a one-element box so the decision loop can set the window
LEVEL = [None]
RNG = [None]    # seeded per run in run(); only the `explore` arm draws from it
# PER-STEP coefficients for the clock arm: {"<family>|<step_name>": hours}. Empty
# means the single global coefficient this project has always used. The rule reads
# ONE number for all 19 diffusion steps, and only 5 of them ever fire an under-full
# load, so whether one number is the right shape is a question the fab can answer.
HMAP = {}      # the fitted level artefact for the `level` arm, likewise


def _note_slack(env, now):
    """The entry-slack distribution the fire predicate actually reads.

    The reduction (timeout:T is clock:(c-T)) holds when a queue's ENTRY SLACK --
    the deadline minus the instant the lot joins that queue -- is single-valued.
    On this benchmark it need not be: a clock can start several steps upstream,
    so transit is random, and one family can host two constraint targets with
    different limits on the same machines. This records, once per lot per tool,
    the residual at the lot's first appearance in a decision there, which IS
    the quantity the predicate reads. Cheap: one set lookup per waiting lot.
    """
    if now < SLACK_FROM[0]:
        return
    m = env._machine
    for lot in m.waiting_lots:
        rec = env.cqt.open.get(id(lot))
        if rec is None or lot.actual_step.order != rec[0]:
            continue
        key = (id(lot), lot.actual_step.family, lot.actual_step.step_name)
        if key in _SLACK_SEEN:
            continue
        _SLACK_SEEN.add(key)
        SLACK.setdefault((lot.actual_step.family, lot.actual_step.step_name),
                         []).append((rec[1] - now) / 3600.0)


def choose(env, kind, coef):
    """Upstream's decision everywhere except one branch: the under-full batch."""
    groups = env._groups
    g0 = groups[0]
    step = g0[0].actual_step
    if step.batch_max > 1:
        _note_slack(env, env.instance.current_time)
    if step.batch_max <= 1:
        return 0                                  # upstream would run it
    now = env.instance.current_time
    if kind == "level" and LEVEL[0] is not None and LEVEL[0].is_policy:
        # THE LEARNER: the whole decision, argmax over every candidate and the
        # wait option. It starts as `full` and is told nothing else.
        return LEVEL[0].act(env, groups, now)
    if group_is_full(g0):
        # Upstream runs a full load unconditionally and so does every arm in
        # this family; the one-station theorem says that is right, since a full
        # load earns B - kappa > 0 for every kappa the regime admits and
        # `kappa_ladder` (archive/2026-10-closed-lines/theory) finds no exception in any cell. Only a GATED level arm
        # may hold one, and only because `chain_model` shows that is exactly
        # what the optimum does when the frame the cohort lands in cannot
        # absorb it -- 442 states on the calibrated cell, carrying most of a
        # gap worth 6.90% of throughput. Every other arm returns here bit for
        # bit as before.
        lv = LEVEL[0]
        if kind != "level" or lv is None or not lv.gated:
            return 0
        # Holding a load must not idle a tool that has other work. Try each FULL
        # candidate in the rule's own order and take the first the gate lets
        # through; the tool only idles when the gate blocks every one. Without
        # this the first fab reading of the gate lost 1.07 completions/day while
        # blocking 0.54% of full loads -- and the blocked loads were measured to
        # be ones it was SAFE to hold (own_res above 0.42, or no live clock at
        # all, which is 64.6% of full-load decisions), so the cost was the idle
        # tool rather than lots dying in the held load.
        for i, g in enumerate(groups):
            if group_is_full(g) and lv.decide(env, g, now, None, True):
                return i
        return len(groups)
    if kind == "full":
        return len(groups)                        # upstream defers
    if kind == "mbs":
        return 0 if len(g0) >= coef else len(groups)
    if kind == "mbsmin":
        # The minimum batch the DATASET specifies for this step, not a swept
        # coefficient: BATCHMN / wafers-per-lot, which is 3, 4 or 5 lots here
        # against a maximum of 4, 5 or 6. Nothing to tune.
        return 0 if len(g0) >= step.batch_min else len(groups)
    if kind == "timeout":
        # the industrial timeout: run once the oldest lot has waited T hours
        oldest = min(l.free_since for l in g0)
        return 0 if (now - oldest) >= coef * 3600.0 else len(groups)
    # the tightest live clock among the lots standing at this tool, seconds.
    # `clock` reads only clocks that stop at this step (the load IS the
    # target); `clockany` reads every open clock, including one that stops
    # further down the route and is spending its margin in this queue.
    tightest = None
    for lot in env._machine.waiting_lots:
        rec = env.cqt.open.get(id(lot))
        if rec is not None and (kind == "clockany" or lot.actual_step.order == rec[0]):
            left = rec[1] - now
            tightest = left if tightest is None else min(tightest, left)
    if kind == "explore":
        # EXPLORATION for the decision-level learner: at an under-full load with
        # a live clock, fire with probability coef, otherwise behave as the
        # shipped dispatcher does (`full`: wait). No hand rule anywhere in this
        # arm -- it exists to produce randomised fire/wait contrasts across the
        # whole state distribution, so a per-decision model can be fitted to
        # observed footprints instead of to a 180-day scalar. coef ~ the rule's
        # own firing RATE (1-2% of such decisions) keeps the fab in a regime
        # comparable to the one the policy will be evaluated in.
        if tightest is None:
            return len(groups)
        return 0 if RNG[0].random() < coef else len(groups)
    if kind == "select":
        # THE CEILING PROBE. Every other arm can only take groups[0] or defer,
        # and `candidate_groups` orders by the constraint prefix then by FILL --
        # upstream's queue-time slot is dead (instance.py compares an int order
        # against a raw string), so a starved constrained group is outranked by
        # a fuller unconstrained one at the same family. This arm keeps the same
        # trigger and changes only WHICH load runs: the group holding the most
        # endangered lot. It fires exactly as often as clock:h would; if it does
        # not beat clock:h then naming the load is worth nothing, and the ceiling
        # over the firing decision is closed by measurement rather than by model.
        # Inert at coef = 0 for the same reason clock:0 is.
        best_i, best_left = None, None
        for i, g in enumerate(groups):
            if g[0].actual_step.batch_max <= 1:
                continue
            for lot in g:
                rec = env.cqt.open.get(id(lot))
                if rec is None or lot.actual_step.order != rec[0]:
                    continue
                left = rec[1] - now
                if left < 0.0:
                    continue
                if best_left is None or left < best_left:
                    best_i, best_left = i, left
        if best_left is not None and best_left < coef * 3600.0:
            return best_i
        return len(groups)
    if kind == "nxtrule":
        # DIAGNOSTIC ONLY (2026-09-22), never a paper comparator: the isolated-station
        # optimum re-expressed at a dispatcher's decision epochs -- fire iff the tightest
        # clock would run out before the next lot for this step arrives (no arrival on the
        # way counts as never). Read off the learner's table; stays in the log.
        if tightest is None or tightest < 0.0:
            return len(groups)
        nxt_ = env.next_arrival(step.family, step.step_name)
        return 0 if (nxt_ is None or nxt_ - now >= tightest) else len(groups)
    if kind in ("clock", "clockany"):
        # run the partial load only to save a clock that is about to expire
        h = HMAP.get(f"{step.family}|{step.step_name}", coef) if HMAP else coef
        return 0 if (tightest is not None and 0.0 <= tightest < h * 3600.0) else len(groups)
    if kind == "level":
        # THE LEARNED ARM. Same predicate, same trigger set, same reading of the
        # tool's tightest clock -- the threshold moves with the state, and (for
        # a gated artefact) the full load can be held. The FORM is not free:
        # `kappa_ladder` counts 0 lower-set violations in 9,216-59,904 covering
        # pairs at every kappa, and `chain_model` puts the value of choosing
        # WHICH load to fire at -4.4e-16, so a policy allowed to change either
        # would be searching a space already known to be empty.
        lv = LEVEL[0]
        if lv is None:
            return 0 if (tightest is not None and 0.0 <= tightest < coef * 3600.0) else len(groups)
        return 0 if lv.decide(env, g0, now, tightest, False) else len(groups)
    # look-ahead rules: is the next lot for this load close enough to be worth
    # the wait? NACH (Fowler, Phillips & Hogg 1992) is DBH (Glassey & Weng 1991,
    # eqs. 2-4) restricted to the next arrival: waiting D = t1 - t0 for it costs
    # the q lots already here q*D and saves the arriving lot T - D (it would
    # otherwise queue until this run ends), so wait iff (T - D) - q*D > 0, i.e.
    # (q + 1)*D < T; ties start now. Verified against the printed equations
    # 2026-09-22; before that the code omitted the arriving lot's own D.
    nxt = env.next_arrival(step.family, step.step_name)
    S = step.processing_time.m
    if kind == "nach_dl" and tightest is not None and (nxt is None or nxt - now >= tightest):
        return 0                                 # a clock would run out first
    if nxt is None:
        return 0
    return len(groups) if (len(g0) + 1) * (nxt - now) < S else 0


def run(a):
    kind, coef = parse_arm(a.arm)
    t_wall = time.time()
    LEVEL[0] = None
    # the exploration arm's own stream, seeded from the run seed so it reproduces;
    # nothing else reads it, so every other arm stays bit-identical to before
    RNG[0] = np.random.default_rng(int(a.seed) * 7919 + 17)
    if kind == "level" and getattr(a, "theta", None):
        import level as level_mod
        LEVEL[0] = level_mod.Level.load(a.theta)
        assert LEVEL[0].h0 == coef, (
            f"artefact h0={LEVEL[0].h0} but the arm says level:{coef}; the arm names "
            "the base level and the two must agree or theta_0 is not the paper's arm")
        # hardening is applied to the LOADED artefact, never written back to it:
        # the file on disk stays the frozen policy and the run records the setting
        LEVEL[0].temp = float(getattr(a, "temp", 1.0))
        LEVEL[0].eps = float(getattr(a, "eps", 0.0))
        LEVEL[0].eps_fw = float(getattr(a, "eps_fw", 0.0))
        LEVEL[0].eps_wf = float(getattr(a, "eps_wf", 0.0))
        explore_on = LEVEL[0].eps > 0.0 or LEVEL[0].eps_fw > 0.0 or LEVEL[0].eps_wf > 0.0
        LEVEL[0].rng = np.random.default_rng(int(a.seed) * 7919 + 29) if explore_on else None
        sd_h, miss = float(getattr(a, "nxt_noise_min", 0.0)) / 60.0, float(getattr(a, "nxt_missing", 0.0))
        level_mod.NXT_NOISE.update(sd_h=sd_h, missing=miss,
                                   rng=np.random.default_rng(int(a.seed) * 7919 + 41) if (sd_h > 0.0 or miss > 0.0) else None)
    # releases are generated up to the horizon at the shipped rate; a
    # compressed stream (scale > 1) needs a longer horizon to stay fed
    horizon = int(a.days * max(1.0, a.scale)) + 2
    sgate = None
    if getattr(a, "source_gate", None) is not None:
        import level as level_mod
        sgate = level_mod.source_gate(a.source_gate)
    env = FabEnv(dataset=a.dataset, seed=a.seed, episode_days=a.days,
                 horizon_days=horizon, rule=a.base, cqt_rule=a.cqt_rule,
                 scrap=a.scrap, minrun_break_h=a.minrun_break,
                 minrun_net_setup=getattr(a, "minrun_net_setup", False),
                 source_gate=sgate)
    obs = env.reset(seed=a.seed)
    if a.scale != 1.0:
        import scenarios
        if a.scale < 1.0:
            scenarios.scale_release(env.instance, a.scale)
        else:
            scenarios.compress_release(env.instance, a.scale)
        env.rebuild_deadlines()

    vman = []                       # instance variants (variants.py) are archived; no run of the paper used one

    inst, t0 = env.instance, env.t0
    n_queued0 = len(inst.dispatchable_lots)
    wip_trace, nxt = [], t0 + 10 * SPD
    fired_sizes, fired_max, n_partial = [], [], 0
    check = (kind == "full") or (kind in ("clock", "select") and coef == 0.0)
    # an inert `level` arm is clock:h0, NOT `full`, so rule_action is the wrong
    # reference for it; it answers to the clock arm it is supposed to reproduce
    lvl_check = kind == "level" and (LEVEL[0] is None or LEVEL[0].inert)
    # an inert POLICY artefact is `full` and answers to rule_action like the
    # other inert arms; an inert level/gate artefact answers to clock:h0
    lvl_policy = LEVEL[0] is not None and LEVEL[0].is_policy
    # per-family ledger over the measurement window only, plus a snapshot of
    # the machines' cumulative counters at the window's start so utilisation
    # can be differenced over the window rather than over the whole run
    t_meas0 = t0 + a.measure_from * a.days * SPD
    env.load_ledger, env.ledger_from = {}, t_meas0
    SLACK.clear(); _SLACK_SEEN.clear(); SLACK_FROM[0] = t_meas0
    msnap = None
    # Was a server free when a lot died at a batch tool? This is the condition
    # the station theorems actually need -- not "many servers", but "a load
    # that wants to fire finds a machine". Under `full` a death with a free
    # server is a starvation death the control-limit can prevent; under
    # `clock:h` a death with NO free server is the ample-server premise
    # failing, and nothing at this decision could have saved the lot.
    blk = {"batch_deaths": 0, "batch_deaths_no_server": 0, "nonbatch_deaths": 0}
    _prev_on_scrap = env.cqt.on_scrap        # fab_env owns the tardiness books

    def _count_scrap(lot, _p=_prev_on_scrap, _e=env, _b=blk, _t=t_meas0):
        if _p is not None:
            _p(lot)
        if _e.instance.current_time < _t:
            return
        st = getattr(lot, "actual_step", None)
        fam = getattr(st, "family", "?")
        _b.setdefault("by_family", {})
        _b["by_family"][fam] = _b["by_family"].get(fam, 0) + 1
        if st is None or getattr(st, "batch_max", 1) <= 1:
            _b["nonbatch_deaths"] += 1
            return
        _b["batch_deaths"] += 1
        free = getattr(_e.instance, "free_machines", None)
        ms = _e.fam_machines.get(st.family, ())
        if free is None or not any(free[m.idx] for m in ms):
            _b["batch_deaths_no_server"] += 1

    env.cqt.on_scrap = _count_scrap

    while obs is not None:
        act = choose(env, kind, coef)
        if check:
            # inertness: these two arms must be upstream, decision for decision
            assert act == env.rule_action(), "arm is not inert"
        if lvl_check:
            ref = env.rule_action() if lvl_policy else choose(env, "clock", coef)
            assert act == ref, "inert level arm does not reproduce its reference"
        if act < len(env._groups):
            g = env._groups[act]
            bm = g[0].actual_step.batch_max
            if bm > 1:
                fired_sizes.append(min(len(g), bm))
                fired_max.append(bm)
                if len(g) < bm:
                    n_partial += 1
        obs, _, done, _ = env.step(act)
        if msnap is None and inst.current_time >= t_meas0:
            msnap = {m.idx: (m.utilized_time, m.pmed_time, m.bred_time,
                             m.setuped_time) for m in inst.machines}
            t_snap = inst.current_time
        if inst.current_time >= nxt or done:
            wip_trace.append({"day": round((inst.current_time - t0) / SPD, 1),
                              "wip": len(inst.active_lots),
                              "done": len(inst.done_lots)})
            nxt = inst.current_time + 10 * SPD
        if done:
            break

    ev = env.cqt.events
    d0 = a.measure_from * a.days
    s = bench_metrics.summary(inst, since_day=d0, dataset=a.dataset, t0=t0)
    seg = [e for e in ev if e["day"] >= d0]
    n, v = len(seg), sum(1 for e in seg if e["late"])
    d = np.array([r["day"] for r in wip_trace])
    w = np.array([r["wip"] for r in wip_trace], float)
    dn = np.array([r["done"] for r in wip_trace], float)
    half = d >= a.measure_from * a.days
    fill = (float(np.sum(fired_sizes) / np.sum(fired_max))
            if fired_sizes else None)
    # the scrap game's own ledger over the measurement window: a violation
    # there is a lost lot, so completions and deaths are the axes
    t_meas = t0 + d0 * SPD
    t_stop = min(inst.current_time, t0 + a.days * SPD)
    win = max(1e-9, (t_stop - t_meas) / SPD)
    in_win = lambda t: t is not None and t_meas <= t < t_stop
    done_w = [l for l in inst.done_lots if in_win(l.done_at)]
    scr_w = [l for l in env.cqt.scrapped if in_win(getattr(l, "scrapped_at", None))]
    ontime_w = [l for l in done_w if l.done_at <= l.deadline_at]
    cyc = sorted((l.done_at - l.release_at) / SPD for l in done_w)
    scrap_kpi = {
        "completed_per_day": round(len(done_w) / win, 2),
        "scrapped_per_day": round(len(scr_w) / win, 2),
        "on_time_pct_of_completed": round(100.0 * len(ontime_w) / max(1, len(done_w)), 2),
        "on_time_pct_of_completed_plus_scrapped": round(
            100.0 * len(ontime_w) / max(1, len(done_w) + len(scr_w)), 2),
        "cycle_p50_days": round(cyc[len(cyc) // 2], 2) if cyc else None,
        "scrapped_total": len(env.cqt.scrapped),
    }
    # per-family utilisation over the measurement window: the number that says
    # whether the furnaces are server-bound (the ample-server premise of the
    # station theorems) or idle-and-starving
    fam_util = {}
    if msnap:
        span = max(1e-9, inst.current_time - t_snap)
        agg = {}
        for m in inst.machines:
            u0, p0, b0, s0 = msnap[m.idx]
            r = agg.setdefault(m.family, [0.0, 0.0, 0.0, 0.0, 0])
            r[0] += m.utilized_time - u0
            r[1] += m.pmed_time - p0
            r[2] += m.bred_time - b0
            r[3] += m.setuped_time - s0
            r[4] += 1
        # NB: this loop variable used to be called `n`, which SHADOWED the
        # `n, v = len(seg), ...` bound above and reached the output as
        # "resolved" -- every batch_block artefact reports resolved = 2 (the
        # last family's machine count) and violation_rate_pct = 100*v/2 in the
        # tens of thousands. The KPI path was never affected; only these two
        # reported fields were. Renamed 2026-09-15.
        for fam, (u, p, b, stp, n_mach) in agg.items():
            avail = span * n_mach - p - b
            fam_util[fam] = {
                "n": n_mach,
                "util_pct": round(100.0 * u / avail, 2) if avail > 0 else None,
                "down_pct": round(100.0 * (p + b) / (span * n), 2),
                "setup_pct": round(100.0 * stp / (span * n), 2)}
    # every batch load of the window, including the full ones the auto-commit
    # path takes without a decision (which the fill above cannot see)
    ledger, t_lots, t_cap, t_part, t_loads = {}, 0, 0, 0, 0
    for (fam, step), r in sorted(env.load_ledger.items()):
        if r["batch_max"] <= 1:
            continue
        cap = r["loads"] * r["batch_max"]
        ledger["%s|%s" % (fam, step)] = {
            "batch_max": r["batch_max"], "loads": r["loads"], "lots": r["lots"],
            "partial": r["partial"],
            "fill": round(r["lots"] / cap, 4) if cap else None,
            "partial_pct": (round(100.0 * r["partial"] / r["loads"], 2)
                            if r["loads"] else None),
            "util_pct": (fam_util.get(fam) or {}).get("util_pct")}
        t_lots += r["lots"]; t_cap += cap
        t_part += r["partial"]; t_loads += r["loads"]
    return {
        "arm": a.arm, "dataset": a.dataset, "scale": a.scale, "seed": a.seed,
        "days": a.days, "base": a.base, "cqt_rule": a.cqt_rule, "scrap": a.scrap,
        "scrap_kpi": scrap_kpi,
        "warmup_days": round(d0, 1), "wall_s": round(time.time() - t_wall, 1),
        "on_time_regular_pct": s["on_time_regular_pct"],
        "act_regular_days": s["act_regular_days"],
        "resolved": n, "violations": v,
        "violation_rate_pct": round(100.0 * v / n, 3) if n else None,
        "clocks_started": env.cqt.n_started,
        "batch_fill": round(fill, 4) if fill else None,
        "batches_fired": len(fired_sizes), "batches_partial": n_partial,
        # the same three over EVERY load of the window, auto-committed included
        "batch_fill_all": round(t_lots / t_cap, 4) if t_cap else None,
        "batches_fired_all": t_loads, "batches_partial_all": t_part,
        "family_ledger": ledger, "fam_util": fam_util,
        "blocking": dict(blk),
        "entry_slack_h": {f"{k[0]}|{k[1]}": {
            "n": len(v), "min": round(min(v), 3), "max": round(max(v), 3),
            "mean": round(sum(v) / len(v), 3),
            "distinct_rounded": sorted({round(x, 1) for x in v})[:12],
            "n_distinct_rounded": len({round(x, 1) for x in v}),
            "p05": round(sorted(v)[int(0.05 * len(v))], 3),
            "p95": round(sorted(v)[int(0.95 * len(v))], 3)}
            for k, v in sorted(SLACK.items()) if v},
        "variant": getattr(a, "variant", "none"), "variant_manifest": vman,
        "throughput_back_half": (float((dn[-1] - dn[half][0])
                                       / (d[-1] - d[half][0]))
                                 if half.sum() > 1 else None),
        "wip_end": int(w[-1]),
        "wip_slope_back_half": (float(np.polyfit(d[half], w[half], 1)[0])
                                if half.sum() > 3 else None),
        "released_per_day": (n_queued0 - len(inst.dispatchable_lots)) / a.days,
        "env_stats": dict(env.stats),
        "trace": wip_trace,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="LVHM")
    ap.add_argument("--scale", type=float, default=0.98)
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--measure-from", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--arm", default="full")
    ap.add_argument("--base", default="cr")
    ap.add_argument("--cqt-rule", default="none")
    ap.add_argument("--scrap", action="store_true",
                    help="Kopp's convention: a lot that breaks a clock is scrapped")
    ap.add_argument("--minrun-break", type=float, default=0.0,
                    help="the law's second deferral: break a setup min-run lock for a "
                         "lot whose clock has under this many hours left (0 = off)")
    ap.add_argument("--minrun-net-setup", action="store_true",
                    help="read the residual net of the setup the break would incur")
    ap.add_argument("--source-gate", type=float, default=None,
                    help="the comparator from US 6,647,307 (TSMC, 2003): refuse to "
                         "start a queue-time clock the target family cannot meet with "
                         "this much of the budget (scaled) to spare. Composes with any "
                         "arm; absent leaves the hook off entirely. Very negative never "
                         "refuses, which is the inertness check.")
    ap.add_argument("--theta", default=None,
                    help="level.py artefact for the `level` arm (JSON); without it the "
                         "arm is exactly clock:h0")
    ap.add_argument("--eps", type=float, default=0.0,
                    help="ROUND-2 EXPLORATION for a `table` artefact: flip its fire/wait call with "
                         "this probability at under-full live-clock decisions (own seeded RNG). "
                         "0 = the table itself. Only meaningful with --theta.")
    ap.add_argument("--eps-fw", type=float, default=0.0, help="asymmetric exploration: P(flip a table FIRE to wait)")
    ap.add_argument("--eps-wf", type=float, default=0.0, help="asymmetric exploration: P(flip a table WAIT to fire)")
    ap.add_argument("--nxt-noise-min", type=float, default=0.0,
                    help="level arm: Gaussian error (SD, minutes) added to the time to the next arrival it reads "
                         "(deployment-time error option, off by default; not used in the final runs); own random stream")
    ap.add_argument("--nxt-missing", type=float, default=0.0,
                    help="level arm: probability that no arrival estimate is available at a decision (read as none due)")
    ap.add_argument("--temp", type=float, default=1.0,
                    help="HARDNESS of the artefact's decision boundary: multiplies the "
                         "argument of every tanh and nothing else. 1.0 is the fitted "
                         "artefact decision for decision; as it grows tanh -> sign and "
                         "the boundary stops being a ramp. Does not refit anything.")
    ap.add_argument("--hmap", default=None,
                    help="JSON {\"family|step\": hours} of per-step clock coefficients; unlisted steps keep --arm's")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    # a temperature with nothing to apply it to would be a silent no-op, and this
    # repository has paid for one of those already (the rescue patch that anchored
    # on a nonexistent line and let twelve runs execute at the module default)
    assert a.temp == 1.0 or a.theta, "--temp only means something with --theta"
    assert a.eps == 0.0 or a.theta, "--eps only means something with --theta"
    if a.hmap:
        HMAP.update({k: float(v) for k, v in json.load(open(a.hmap)).items()})
    r = run(a)
    r["minrun_break_h"] = a.minrun_break
    r["theta"] = a.theta
    r["temp"] = a.temp
    r["eps"] = a.eps
    r["eps_fw"], r["eps_wf"] = a.eps_fw, a.eps_wf
    r["nxt_noise_min"], r["nxt_missing"] = a.nxt_noise_min, a.nxt_missing
    r["hmap"] = getattr(a, "hmap", None)
    if HMAP:
        r["hmap_values"] = dict(HMAP)
    r["source_gate"] = a.source_gate
    if LEVEL[0] is not None:
        r["level"] = LEVEL[0].to_dict()
    r["minrun_net_setup"] = bool(a.minrun_net_setup)
    tag = a.arm.replace(":", "")
    if getattr(a, "theta", None):
        tag += "_" + os.path.splitext(os.path.basename(a.theta))[0]
    if getattr(a, "eps_fw", 0.0) > 0.0 or getattr(a, "eps_wf", 0.0) > 0.0:
        tag += "_" + f"efw{a.eps_fw:g}wf{a.eps_wf:g}".replace(".", "p")
    if getattr(a, "nxt_noise_min", 0.0) > 0.0:
        tag += "_" + f"eta{a.nxt_noise_min:g}m".replace(".", "p")    # must reach the filename (run_queue skips on existence)
    if getattr(a, "nxt_missing", 0.0) > 0.0:
        tag += "_" + f"etamiss{a.nxt_missing:g}".replace(".", "p")
    if getattr(a, "eps", 0.0) > 0.0:
        tag += "_" + f"eps{a.eps:g}".replace(".", "p")      # must reach the filename (run_queue skips on existence)
    if getattr(a, "temp", 1.0) != 1.0:
        # like the variant, the hardness MUST reach the filename: run_queue skips
        # on existence, so two temperatures sharing a name would be skipped
        tag += "_" + f"T{a.temp:g}".replace(".", "p")
    if getattr(a, "hmap", None):
        tag += "_" + os.path.splitext(os.path.basename(a.hmap))[0]
    if getattr(a, "source_gate", None) is not None:
        tag += f"_sg{a.source_gate:g}".replace(".", "").replace("-", "m")
    if a.cqt_rule != "none":
        tag += f"_{a.cqt_rule}"
    if a.minrun_break > 0:
        tag += f"_mr{a.minrun_break:g}"
        if a.minrun_net_setup:
            tag += "n"
    if a.scrap:
        tag += "_scrap"
    name = (f"batch_fire_{a.dataset}_r{a.scale}_d{a.days}_s{a.seed}_{tag}.json")
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, name)
    with open(path, "w") as f:
        json.dump(r, f, indent=1, default=float)
    print(json.dumps({k: v for k, v in r.items() if k != "trace"}))
    print("wrote", path)


if __name__ == "__main__":
    main()
