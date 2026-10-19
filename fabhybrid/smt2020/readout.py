"""What did the learner learn? Read the policy out, decision by decision.

The paper's claim is that PART of the learned policy is a rule -- a cut on one
number -- and that the rest is what a rule cannot say. That has to be measured,
not asserted, and measured on the decisions the policy actually faced. This
runs an arm (a fitted artefact, or a rule for calibration) for `--days`,
records the feature vector and the action at every batch decision, and then
asks three questions of the record:

  1. Under-full decisions -- the decision the law speaks to. For every single
     feature, the best one-sided cut (fire iff x < t, or x > t) and the
     fraction of the policy's own fire/wait decisions it reproduces. If the
     cut on the tightest residual explains ~all of them, the learner found the
     control limit; the theory then says why that is right.
  2. Full-load decisions. How often the policy HOLDS a full head group, and how
     often it fires a different group instead -- the two dimensions upstream
     never uses, which the chain model prices at "sometimes" and "never".
  3. Which group, when several are full or under-full: agreement with
     upstream's own ordering.

Calibration: `--arm clock:1` must read out as a 100% cut on own_res (the
tightest residual) by construction; a random policy artefact should read out
as nothing in particular. Both are run before any learned artefact is.

  python readout.py --dataset HVLM --arm level:1 --theta <best.json> --days 30
  python readout.py --dataset HVLM --arm clock:1 --days 30          # calibration
"""
import argparse
import json
import os

import numpy as np

import batch_fire
import level as L
from fab_env import group_is_full

REC = {"phi": [], "full": [], "act": [], "n_groups": [], "n_full": [], "t": [], "mach": [], "step": [], "size": [],
       "head": [], "clocks": []}
REC_ENV = [None]     # the env, kept alive past run() so the event ledger can be dumped


def _tap_factory(orig):
    def tap(env, kind, coef):
        groups = env._groups
        g0 = groups[0]
        if g0[0].actual_step.batch_max > 1:
            now = env.instance.current_time
            x = L.phi(env, g0, now)
            a = orig(env, kind, coef)
            REC["phi"].append(x)
            REC["full"].append(group_is_full(g0))
            REC["act"].append(a)
            REC["n_groups"].append(len(groups))
            REC["n_full"].append(sum(1 for g in groups if group_is_full(g)))
            # identity and time, so a held load can be followed until it fires
            REC["t"].append(now / 3600.0)
            REC["mach"].append(env._machine.idx)
            REC["step"].append(f"{g0[0].actual_step.family}|{g0[0].actual_step.step_name}")
            REC["size"].append(len(g0))
            # lot identity, for the rule's confusion matrix: who stood in the head
            # group, and every live clock the rule's `tightest` is computed over.
            # SAME test as choose() and phi() -- the clock must STOP at this step --
            # so the recorded set is exactly what the rule thresholds.
            # id(l), NOT l.name: lot.name is the PRODUCT name (4 distinct values on HVLM,
            # 15 on LVHM), so it cannot key a lot. id() is stable within the run.
            REC["head"].append([id(l) for l in g0])
            cl = []
            for l in env._machine.waiting_lots:
                rec = env.cqt.open.get(id(l))
                if rec is not None and l.actual_step.order == rec[0]:
                    cl.append((id(l), (rec[1] - now) / 3600.0, l in g0))
            REC["clocks"].append(cl)
            REC_ENV[0] = env
            return a
        return orig(env, kind, coef)
    return tap


def best_cut(x, fire):
    """Best one-sided threshold on x reproducing the fire/wait labels."""
    order = np.argsort(x)
    xs, fs = x[order], fire[order].astype(int)
    n = len(xs)
    # fire iff x < t : for a cut after position i, predicted fire = positions <= i
    cum = np.cumsum(fs)
    tot = cum[-1]
    best = (0.0, None, None)
    for i in range(-1, n):
        fire_below = cum[i] if i >= 0 else 0
        k = i + 1
        acc_lt = (fire_below + (n - k) - (tot - fire_below)) / n        # fire iff below
        acc_gt = ((tot - fire_below) + k - fire_below) / n              # fire iff above
        t = xs[i] if i >= 0 else -np.inf
        if acc_lt > best[0]:
            best = (acc_lt, "<", t)
        if acc_gt > best[0]:
            best = (acc_gt, ">", t)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="HVLM")
    ap.add_argument("--arm", default="clock:1")
    ap.add_argument("--theta", default=None)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--scale", type=float, default=0.98)
    ap.add_argument("--cqt-rule", default="qtcr")
    ap.add_argument("--out", default=None)
    ap.add_argument("--eps", type=float, default=0.0, help="round-2 exploration around a table artefact (see batch_fire --eps)")
    ap.add_argument("--eps-fw", type=float, default=0.0)
    ap.add_argument("--eps-wf", type=float, default=0.0)
    ap.add_argument("--dump", default=None, help="save the raw (phi, full, action, n_groups) record as .npz")
    ap.add_argument("--dump-from", type=float, default=0.0,
                    help="keep only records from this simulated day on (a logging window after the warm-up)")
    ap.add_argument("--slim", action="store_true",
                    help="write only what fit_q.py reads: no lot identities, no clock-event ledger, phi cut to the fill")
    ap.add_argument("--dump-lots", default=None,
                    help="save per-decision lot identities + live clocks, and the whole queue-time event "
                         "ledger (who died, when, where), as .json -- the input to fit_q.py and table_agree.py "
                         "(first written for confusion.py, now in archive/2026-09-batch-line-closed/)")
    a = ap.parse_args()

    class A:
        pass
    cfg = A()
    cfg.dataset, cfg.scale, cfg.days, cfg.measure_from, cfg.seed = a.dataset, a.scale, a.days, 0.5, a.seed
    cfg.arm, cfg.base, cfg.cqt_rule, cfg.scrap = a.arm, "cr", a.cqt_rule, True
    cfg.minrun_break, cfg.minrun_net_setup, cfg.variant = 0.0, False, "none"
    cfg.theta, cfg.source_gate = a.theta, None
    cfg.eps = a.eps
    cfg.eps_fw, cfg.eps_wf = a.eps_fw, a.eps_wf
    batch_fire.choose = _tap_factory(batch_fire.choose)
    r = batch_fire.run(cfg)

    X = np.array(REC["phi"])
    full = np.array(REC["full"])
    act = np.array(REC["act"])
    ng = np.array(REC["n_groups"])
    nfull = np.array(REC["n_full"])
    fired = act < ng
    fired_head = act == 0
    out = {"arm": a.arm, "theta": a.theta, "days": a.days, "decisions": int(len(act)),
           "completed_per_day": r["scrap_kpi"]["completed_per_day"],
           "scrapped_per_day": r["scrap_kpi"]["scrapped_per_day"],
           "wip_end": r.get("wip_end"), "wip_slope_back_half": r.get("wip_slope_back_half"),
           "batch_fill": r.get("batch_fill"), "batches_fired": r.get("batches_fired")}
    print(f"run: completed/day {out['completed_per_day']}  scrapped/day {out['scrapped_per_day']}  "
          f"wip_end {out['wip_end']}  wip slope {out['wip_slope_back_half']}  fill {out['batch_fill']}  "
          f"batches {out['batches_fired']}")
    if a.dump:
        np.savez_compressed(a.dump, phi=X, full=full, act=act, n_groups=ng, n_full=nfull,
                            t=np.array(REC["t"]), mach=np.array(REC["mach"]),
                            step=np.array(REC["step"]), size=np.array(REC["size"]))
    if a.dump_lots:
        env = REC_ENV[0]
        t0_h = env.cqt.t0 / 3600.0
        dec = [{"i": i, "day": (REC["t"][i] - t0_h) / 24.0, "mach": int(REC["mach"][i]),
                "step": REC["step"][i], "act": int(REC["act"][i]), "n_groups": int(REC["n_groups"][i]),
                "full": bool(REC["full"][i]), "size": int(REC["size"][i]),
                "own_res_h": float(REC["phi"][i][10] * 24.0), "nxt_h": float(REC["phi"][i][3] * 24.0),
                "phi": [float(v) for v in REC["phi"][i]],          # all 11 features, the learner's input
                "head": REC["head"][i],
                "clocks": [[n, float(r), bool(h)] for n, r, h in REC["clocks"][i]]}
               for i in range(len(REC["act"]))]
        ev = [{"lot": e["lot"], "day": float(e["day"]), "late": bool(e["late"]),
               "scrapped": bool(e.get("scrapped", False)), "family": e["family"],
               "slack_h": float(e["slack_h"])} for e in env.cqt.events]
        if a.dump_from > 0.0:
            dec = [d for d in dec if d["day"] >= a.dump_from]
            ev = [e for e in ev if e["day"] >= a.dump_from]
        if a.slim:
            ev = []
            for d in dec:
                d["phi"] = d["phi"][:1]                    # the fill; label.batch_max_per_step reads size / phi[0]
                d.pop("head", None)
                d["clocks"] = [[0, c[1], c[2]] for c in d["clocks"]]
        json.dump({"arm": a.arm, "theta": a.theta, "dataset": a.dataset, "days": a.days,
                   "dump_from": a.dump_from, "eps": a.eps, "eps_fw": a.eps_fw, "eps_wf": a.eps_wf,
                   "seed": a.seed, "decisions": dec, "events": ev,
                   # every scrapped lot with WHERE it died: _remove() stamps scrapped_at and
                   # leaves actual_step at the step the lot was waiting for, so the death
                   # site survives. batch_max > 1 there means it died at a batch tool.
                   "scrapped": [{"id": id(l), "name": l.name,
                                 "day": (getattr(l, "scrapped_at", float("nan")) - env.cqt.t0) / 86400.0,
                                 "step": f"{l.actual_step.family}|{l.actual_step.step_name}",
                                 "batch_max": int(l.actual_step.batch_max)}
                                for l in env.cqt.scrapped]},
                  open(a.dump_lots, "w"), separators=(",", ":"))
        print(f"wrote {a.dump_lots}: {len(dec)} decisions, {len(ev)} clock events, "
              f"{len(env.cqt.scrapped)} scrapped lots")

    # 1. the under-full decision
    uf = ~full
    if uf.sum():
        fire = fired[uf]
        rows = []
        for j, name in enumerate(L.FEATURES):
            acc, side, t = best_cut(X[uf, j], fire)
            rows.append((acc, name, side, t))
        rows.sort(reverse=True)
        base = max(fire.mean(), 1 - fire.mean())
        out["underfull"] = {"n": int(uf.sum()), "fire_rate": float(fire.mean()),
                            "majority_baseline": float(base),
                            "cuts": [{"feature": n, "agreement": float(acc), "rule": f"fire iff {n} {s} {t:.4f}"}
                                     for acc, n, s, t in rows]}
        print(f"UNDER-FULL decisions: {uf.sum()}  fire rate {fire.mean():.3f}  "
              f"(majority baseline {base:.3f})")
        for acc, n, s, t in rows[:5]:
            print(f"   {acc:6.1%}  fire iff {n} {s} {t:+.4f}"
                  f"   ({t * 24:+.2f} h)" if n in ("own_res", "headroom", "slack2", "budget") else
                  f"   {acc:6.1%}  fire iff {n} {s} {t:+.4f}")
        # the fire class is rare (0.5% under clock:1), so overall agreement sits
        # on a ~99% majority baseline and says little; report how the best cut
        # does ON THE FIRES -- recall (fires it reproduces) and precision
        acc, name, side, t = rows[0]
        j = L.FEATURES.index(name)
        pred = (X[uf, j] < t) if side == "<" else (X[uf, j] > t)
        tp = float((pred & fire).sum()); fp = float((pred & ~fire).sum()); fn = float((~pred & fire).sum())
        out["underfull"]["best_cut_recall"] = tp / max(1.0, tp + fn)
        out["underfull"]["best_cut_precision"] = tp / max(1.0, tp + fp)
        print(f"   best cut on the FIRES: recall {tp / max(1.0, tp + fn):.1%}  precision {tp / max(1.0, tp + fp):.1%}"
              f"  ({int(fire.sum())} fires among {int(uf.sum())} under-full decisions)")
        # fired a NON-head under-full group
        nonhead = fire & ~fired_head[uf]
        out["underfull"]["fired_nonhead_rate"] = float(nonhead.mean())
        print(f"   fired a group other than the head: {nonhead.mean():.3%}")

    # 2. the full-load decision
    if full.sum():
        held = (~fired)[full]
        other = (fired & ~fired_head)[full]
        out["full"] = {"n": int(full.sum()), "held_rate": float(held.mean()),
                       "fired_other_group_rate": float(other.mean())}
        print(f"FULL head-group decisions: {full.sum()}  held {held.mean():.3%}  "
              f"fired another group {other.mean():.3%}")
        if held.sum():
            hx = X[full]
            hl = held
            rows = []
            for j, name in enumerate(L.FEATURES):
                acc, side, t = best_cut(hx[:, j], hl)
                rows.append((acc, name, side, t))
            rows.sort(reverse=True)
            out["full"]["hold_cuts"] = [{"feature": n, "agreement": float(acc),
                                         "rule": f"hold iff {n} {s} {t:.4f}"} for acc, n, s, t in rows[:5]]
            print("   what a hold looks like:")
            for acc, n, s, t in rows[:3]:
                print(f"     {acc:6.1%}  hold iff {n} {s} {t:+.4f}")

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(out, open(a.out, "w"), indent=1, default=float)
        print("wrote", a.out)


if __name__ == "__main__":
    main()
