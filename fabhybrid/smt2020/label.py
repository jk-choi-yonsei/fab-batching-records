"""Per-decision labels from OBSERVED footprints, for the decision-level learner.

No rule enters here. For every under-full decision with a live clock in an exploration
dump (readout.py --dump-lots under the `explore:p` arm, which fires at random with
probability p and otherwise behaves as the shipped dispatcher), record the state phi,
the action taken, and what then happened within a horizon H:

  D_pres_H   lots that stood at this tool with a live clock AT the decision and were
             scrapped at this step within H       (directly attributable to the decision)
  D_arr_H    lots NOT present at the decision that were scrapped at this step within H
             (arrived to a busy tool: the delayed cost of firing, or the saving of waiting)
  C          capacity spent if fired: (B - k) empty slots x recipe hours R, where R is
             observed as the time to this machine's next decision. 0 if waited.
  fill       k / B of the fired load (nan if waited)

Because the exploration arm chooses fire/wait at random, the difference in outcomes
between fired and waited decisions in similar states is a causal effect, not a
correlation with whatever a rule would have done.

  python label.py "../../experiments/smt2020/fit/explore/HVLM_explore0p02_s*.json" \\
      --out ../../experiments/smt2020/fit/explore/HVLM_labels.npz
"""
import argparse
import glob
import json
from collections import Counter, defaultdict

import numpy as np

HORIZONS = (6.0, 12.0, 24.0)          # hours



BATCH_MAX = [None]     # optional step -> batch_max fallback, set from --batch-max

def batch_max_per_step(dec, scr, fallback=None):
    """batch_max (lots) per step from size / phi[0], cross-checked against the scrapped records.

    Dumps written before the record carried `phi` (HVLM round-1 seeds 100-101) have no votes;
    for those, `fallback` (a step -> batch_max dict, e.g. --batch-max JSON) fills in. A step
    that is neither voted nor covered raises -- never skip a step silently.
    """
    votes = defaultdict(Counter)
    for d in dec:
        if d["size"] > 0 and d.get("phi") and d["phi"][0] > 0:
            votes[d["step"]][int(round(d["size"] / d["phi"][0]))] += 1
    B = {}
    for step, c in votes.items():
        bm, n = c.most_common(1)[0]
        assert n >= 0.99 * sum(c.values()), (step, dict(c))
        B[step] = bm
    for s in scr:
        if s["step"] in B and s["batch_max"] > 1:
            assert B[s["step"]] == s["batch_max"], (s["step"], B[s["step"]], s["batch_max"])
    steps = {d["step"] for d in dec}
    for step in steps - set(B):
        if fallback and step in fallback:
            B[step] = int(fallback[step])
        else:
            raise KeyError(f"no batch_max for {step}: the dump has no phi and no --batch-max table covers it")
    return B

def label_one(path):
    D = json.load(open(path))
    dec, scr = D["decisions"], D["scrapped"]
    days = D["days"]
    # deaths at each step, as (day, id), sorted
    deaths = defaultdict(list)
    for s in scr:
        if s["batch_max"] > 1:
            deaths[s["step"]].append((s["day"], s["id"]))
    for k in deaths:
        deaths[k].sort()
    # B per step = the step's batch_max in lots. `size` is the head GROUP (every waiting lot
    # of that recipe), not the load, so its maximum is a queue length; phi[0] = size / batch_max
    # by construction in level.phi, which gives batch_max back exactly (2026-09-16 fix).
    B = batch_max_per_step(dec, scr, BATCH_MAX[0])
    # decision days per machine, for the recipe length of a fire
    by_m = defaultdict(list)
    for d in dec:
        by_m[d["mach"]].append(d["day"])
    for m in by_m:
        by_m[m].sort()

    rows = []
    for d in dec:
        if d["full"] or not d["clocks"]:
            continue
        t = d["day"]
        fired = d["act"] < d["n_groups"]
        present = {c[0] for c in d["clocks"]}
        step_deaths = deaths.get(d["step"], [])
        out = {}
        for H in HORIZONS:
            hd = H / 24.0
            win = [lid for (dd, lid) in step_deaths if t < dd <= t + hd]
            out[f"D_pres_{H:g}"] = sum(1 for lid in win if lid in present)
            out[f"D_arr_{H:g}"] = sum(1 for lid in win if lid not in present)
        later = [x for x in by_m[d["mach"]] if x > t + 1e-9]
        R = (later[0] - t) * 24.0 if later else np.nan
        b = B.get(d["step"], np.nan)
        k = d["size"] if fired and d["act"] == 0 else np.nan
        C = ((b - k) * R) if (fired and d["act"] == 0 and np.isfinite(b) and np.isfinite(R)) else (0.0 if not fired else np.nan)
        rows.append({
            "phi": np.array(d["phi"], float) if "phi" in d else np.full(11, np.nan),   # all 11 features when the dump has them
            "fired": int(fired), "act": d["act"], "n_groups": d["n_groups"],
            "size": d["size"], "B": b, "R": R, "C": C, "fill": (k / b) if np.isfinite(k) and np.isfinite(b) else np.nan,
            "tightest": min(c[1] for c in d["clocks"]), "n_clocks": len(d["clocks"]),
            "own_res_h": d["own_res_h"], "nxt_h": d["nxt_h"], "step": d["step"], "mach": d["mach"],
            "day": t, "seed": D["seed"], **out,
        })
    return rows, D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern")
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-max", default=None, help="JSON step -> batch_max, for dumps written without phi")
    a = ap.parse_args()
    if a.batch_max:
        BATCH_MAX[0] = json.load(open(a.batch_max))
    files = sorted(glob.glob(a.pattern))
    if not files:
        raise SystemExit(f"no dumps match {a.pattern}")
    allrows = []
    for f in files:
        rows, D = label_one(f)
        allrows += rows
        nf = sum(r["fired"] for r in rows)
        print(f"{f.split('/')[-1]}: {len(rows):,} under-full live-clock decisions, fired {nf:,} "
              f"({100 * nf / max(1, len(rows)):.1f}%), scrapped {len(D['scrapped']):,}")
    keys = [k for k in allrows[0] if k not in ("phi", "step")]
    arr = {k: np.array([r[k] for r in allrows], float) for k in keys}
    arr["step"] = np.array([r["step"] for r in allrows])
    arr["phi"] = np.stack([r["phi"] for r in allrows])
    n_phi = int(np.isfinite(arr["phi"][:, 0]).sum())
    np.savez_compressed(a.out, **arr)
    n = len(allrows); f = arr["fired"].astype(bool)
    print(f"\n{n:,} decisions -> {a.out}   (full 11-feature phi on {n_phi:,} rows)")
    for H in HORIZONS:
        dp, da = arr[f"D_pres_{H:g}"], arr[f"D_arr_{H:g}"]
        print(f"  H={H:>4g} h  deaths of PRESENT lots: fired {dp[f].mean():.3f}  waited {dp[~f].mean():.3f}   |   "
              f"deaths of ARRIVING lots: fired {da[f].mean():.3f}  waited {da[~f].mean():.3f}")
    Cf = arr["C"][f]
    print(f"  capacity spent when fired: med {np.nanmedian(Cf):.1f} slot-hours (B-k med {np.nanmedian(arr['B'][f]-arr['size'][f]):.1f}, R med {np.nanmedian(arr['R'][f]):.1f} h)")


if __name__ == "__main__":
    main()
