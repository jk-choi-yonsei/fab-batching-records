"""The benchmark's own statistics, computed the way the simulator computes them.

This mirrors `simulation/stats.py::print_statistics` from PySCFabSim: per
product, the average cycle time (ACT), throughput, on-time percentage and
total tardiness over completed lots, plus per-family machine utilisation.
Those are the quantities SMT2020 ships reference values for, in
`datasets/lots_SMT2020_HVLM.txt`:

    Lot_3     th 18914.6   ACT 51.21 d   on-time 91.19 %
    Lot_4     th 19577.2   ACT 28.38 d   on-time 90.20 %
    HotLot_3  th   499.4   ACT 31.73 d   on-time 90.83 %
    HotLot_4  th   508.6   ACT 18.46 d   on-time 89.54 %

Two things are worth keeping in view when reading a result against those.
The due dates in the order file sit only 5-7% above the reference cycle time
(Lot_3 is due at 53.84 d against a 51.21 d reference), so on-time percentage
is close to a yes/no on whether the fab ran at its designed speed. And with
releases fixed and exogenous at ~57.2 lots/day, long-run throughput is pinned
by the release schedule -- a dispatcher moves cycle time and tardiness, not
output, so a throughput far below the reference means WIP is piling up rather
than that the fab is slow.

`since_day` exists for reporting on a measurement window; upstream uses none
(the 730-day horizon dilutes the start transient instead), so it defaults off.
"""
import statistics
from collections import defaultdict

from rl_env import SECONDS_PER_DAY as SPD, REFERENCE


def lot_stats(instance, since_day=0.0, dataset="HVLM"):
    """Per-product benchmark measures over lots completed after `since_day`."""
    cut = since_day * SPD
    per = defaultdict(lambda: {"act_sum": 0.0, "throughput": 0, "on_time": 0,
                               "tardiness": 0.0, "deadline_allowance": 0.0})
    for lot in instance.done_lots:
        if lot.done_at <= cut:
            continue
        p = per[lot.name]
        p["act_sum"] += lot.done_at - lot.release_at
        p["throughput"] += 1
        p["tardiness"] += max(0.0, lot.done_at - lot.deadline_at) / SPD
        p["deadline_allowance"] = (lot.deadline_at - lot.release_at) / SPD
        if lot.done_at <= lot.deadline_at:
            p["on_time"] += 1

    ref = REFERENCE.get(dataset, {})
    out = {}
    for name, p in per.items():
        n = p["throughput"]
        out[name] = {
            "act_days": p["act_sum"] / n / SPD,
            "throughput": n,
            "on_time_pct": 100.0 * p["on_time"] / n,
            "tardiness_lot_days": p["tardiness"],
            "mean_tardiness_days": p["tardiness"] / n,
            "deadline_allowance_days": p["deadline_allowance"],
            "ref_act_days": ref.get(name, (None, None, None))[1],
            "ref_on_time_pct": ref.get(name, (None, None, None))[2],
        }
    return out


def wip_stats(instance, t0=0.0):
    """What is still in the fab, and how much of it has already gone bad."""
    now = instance.current_time
    ages, late = [], []
    for lot in instance.active_lots:
        ages.append((now - lot.release_at) / SPD)
        if lot.deadline_at < now:
            late.append((now - lot.deadline_at) / SPD)
    n = len(ages)
    return {
        "wip": n,
        "past_due": len(late),
        "past_due_frac": (len(late) / n) if n else 0.0,
        "median_days_past_due": statistics.median(late) if late else 0.0,
        "mean_age_days": (sum(ages) / n) if n else 0.0,
        "days_simulated": (now - t0) / SPD,
    }


def machine_stats(instance):
    """Per-family availability and utilisation, as upstream reports them."""
    util, pm, br, setup = (defaultdict(list) for _ in range(4))
    for m in instance.machines:
        util[m.family].append(m.utilized_time)
        pm[m.family].append(m.pmed_time)
        br[m.family].append(m.bred_time)
        setup[m.family].append(m.setuped_time)
    now = instance.current_time
    out = {}
    for fam in util:
        avail = now - statistics.mean(pm[fam]) - statistics.mean(br[fam])
        out[fam] = {"n": len(util[fam]),
                    "avail_pct": 100.0 * avail / now if now else 0.0,
                    "util_pct": 100.0 * statistics.mean(util[fam]) / avail if avail else 0.0,
                    "setup_pct": 100.0 * statistics.mean(setup[fam]) / now if now else 0.0}
    return out


def summary(instance, since_day=0.0, dataset="HVLM", t0=0.0):
    lots = lot_stats(instance, since_day, dataset)
    reg = {k: v for k, v in lots.items() if not k.startswith(("HotLot", "SuperHot"))}
    tot = sum(v["throughput"] for v in lots.values())
    return {
        "per_lot": lots,
        "wip": wip_stats(instance, t0),
        "throughput_total": tot,
        "throughput_per_day": tot / max(1e-9, (instance.current_time - t0) / SPD),
        "act_regular_days": (sum(v["act_days"] * v["throughput"] for v in reg.values())
                             / max(1, sum(v["throughput"] for v in reg.values()))),
        "on_time_regular_pct": (100.0 * sum(v["on_time_pct"] / 100 * v["throughput"]
                                            for v in reg.values())
                                / max(1, sum(v["throughput"] for v in reg.values()))),
        "tardiness_total_lot_days": sum(v["tardiness_lot_days"] for v in lots.values()),
    }
