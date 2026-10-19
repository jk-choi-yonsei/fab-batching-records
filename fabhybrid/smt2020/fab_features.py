"""The 29 global fab-state features, sampled from the instance alone.

These describe the whole fab at a moment -- risk, capacity, flow and control
aggregates -- and are what the critic reads; the actor sees only its
candidates. They are pure functions of the simulator state: no policy, no
network, no fitted model is consulted, so they carry no assumption about who
is dispatching.

Extracted from the old phi_probe module, whose fitted potential failed its
pre-registered trials twice; the features outlived the potential.
"""
import math
from collections import defaultdict

import numpy as np

from rl_env import SECONDS_PER_DAY as SPD

import math
from collections import defaultdict

import numpy as np


WARMUP = 365

RISK = ["risk_sat", "w_hopeless", "w_risk_1d", "w_risk_2d", "w_risk_5d",
        "mean_slack_d", "p10_slack_d", "committed_lateness",
        # v1 debt features (2026-08-06): the exploit test showed a triage burst
        # cleans the sub-5-day head while its cost -- mid-slack lots quietly
        # aging -- was invisible above that band. These carry the middle mass.
        "band_0_5", "band_5_10", "band_10_20", "band_20_40", "band_40p",
        "soft_debt_10d", "aging_pressure"]
CAP = ["idle_frac", "batch_fill_potential", "batch_under_min_frac", "batch_wip_share",
       "setup_step_share", "mean_load_per_machine", "max_family_load",
       "p90_family_load"]
FLOW = ["wip", "wip_entropy", "wip_imbalance", "top3_queue_share", "mean_progress"]
CTRL = ["t_days"]
FEATURES = RISK + CAP + FLOW + CTRL
GROUPS = {"risk": RISK, "capacity": CAP, "flow": FLOW, "control": CTRL}


def snapshot(inst, now, t_days, fam_machines):
    """All Φ candidate components, from the current state only."""
    f = {"t_days": t_days}
    lots = inst.active_lots

    # --- risk -------------------------------------------------------------
    slacks, w_sat = [], 0.0
    w_hop = w1 = w2 = w5 = 0.0
    committed = 0.0
    b05 = b510 = b1020 = b2040 = b40 = 0.0
    soft_debt = aging = 0.0
    prog = []
    for l in lots:
        s = (l.deadline_at - now - l.remaining_time) / SPD
        w = l.priority
        slacks.append(s)
        w_sat += w * math.tanh(s / 3.0)          # saturating: only near-0 slack moves it
        if s < 0:
            w_hop += w
            committed += w * (-s)
        else:
            if s < 1:
                w1 += w
            if s < 2:
                w2 += w
            if s < 5:
                w5 += w
            if s < 5:
                b05 += w
            elif s < 10:
                b510 += w
            elif s < 20:
                b1020 += w
            elif s < 40:
                b2040 += w
            else:
                b40 += w
            if s < 10:
                soft_debt += w * (10.0 - s)
            if s < 0.5 * (l.remaining_time / SPD):
                aging += w
        if l.full_time:
            prog.append((l.full_time - l.remaining_time) / l.full_time)
    n = max(1, len(slacks))
    ss = sorted(slacks)
    f.update(risk_sat=w_sat, w_hopeless=w_hop, w_risk_1d=w1, w_risk_2d=w2,
             w_risk_5d=w5, mean_slack_d=sum(slacks) / n,
             p10_slack_d=ss[int(0.10 * (n - 1))] if ss else 0.0,
             committed_lateness=committed,
             band_0_5=b05, band_5_10=b510, band_10_20=b1020,
             band_20_40=b2040, band_40p=b40,
             soft_debt_10d=soft_debt, aging_pressure=aging)

    # --- capacity ---------------------------------------------------------
    # NB: this simulator has essentially no standing queue -- a lot is dispatched in
    # the same instant it becomes free, so `lot.waiting_machines` is empty whenever we
    # sample and any queue-length feature built on it reads zero. Attribute lots by
    # the step they are currently AT instead; that is the fab's real standing load.
    load = defaultdict(int)
    setup_steps = 0
    bcount, bmax, bmin = defaultdict(int), {}, {}
    batch_wip = 0
    for l in lots:
        st = l.actual_step
        if st is None:
            continue
        load[st.family] += 1
        if st.setup_needed:
            setup_steps += 1
        if st.batch_max > 1:
            # a batch can only combine lots at the SAME step, not merely the same
            # family -- that distinction is why Tassel fires furnaces at 3.47/5
            bcount[(st.family, st.step_name)] += 1
            bmax[(st.family, st.step_name)] = st.batch_max
            bmin[(st.family, st.step_name)] = st.batch_min
            batch_wip += 1
    fills = [min(n, bmax[k]) / bmax[k] for k, n in bcount.items()]
    under = sum(1 for k, n in bcount.items() if n < bmin[k])

    n_mach = max(1, len(inst.machines))
    idle = sum(1 for m in inst.machines if inst.free_machines[m.idx])
    loads = sorted(load[fam] / max(1, len(ms)) for fam, ms in fam_machines.items())
    f.update(idle_frac=idle / n_mach,
             batch_fill_potential=sum(fills) / len(fills) if fills else 1.0,
             batch_under_min_frac=under / max(1, len(bcount)),
             batch_wip_share=batch_wip / max(1, len(lots)),
             setup_step_share=setup_steps / max(1, len(lots)),
             mean_load_per_machine=sum(load.values()) / n_mach,
             max_family_load=loads[-1] if loads else 0.0,
             p90_family_load=loads[int(0.9 * (len(loads) - 1))] if loads else 0.0)
    queue = load

    # --- flow -------------------------------------------------------------
    hist = [0] * 10
    for p in prog:
        hist[min(9, int(p * 10))] += 1
    tot = max(1, sum(hist))
    frac = [h / tot for h in hist]
    ent = -sum(p * math.log(p) for p in frac if p > 0)
    qs = sorted(queue.values(), reverse=True)
    f.update(wip=len(lots), wip_entropy=ent,
             wip_imbalance=math.sqrt(sum((p - 0.1) ** 2 for p in frac)),
             top3_queue_share=sum(qs[:3]) / max(1, sum(qs)),
             mean_progress=sum(prog) / max(1, len(prog)))
    return f


