"""The tables fitted from the unaltered records of the timeout and minimum-batch-size rules (and NACH), refitted
over the price, the discount and n0, and the facts of each set of records. Fitting only: no simulation.

  python -B rule_tables.py FAB KIND      # one (scenario, records) pair; writes rule_tables/<FAB>_<KIND>.json
  python -B rule_tables.py --summary     # collects them into rule_tables_summary.json

KIND: timeout (records <FAB>_norev_p1), mbs3, nach, full (the full-batch rule with 2% of the free decisions
started, records <FAB>_p1). Estimator as the block's tables: --chain family --backoff --from-day 90 --fold fill.
"""
import glob
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "fabhybrid", "smt2020")))
C = os.path.join(HERE, "..", "collect")
OUT = os.path.join(HERE, "rule_tables")
SRC = {"timeout": "{fab}_norev_p1", "mbs3": "{fab}_mbs3_p1", "nach": "{fab}_nach_p1", "full": "{fab}_p1"}
PRICES = (0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.003, 0.004, 0.005, 0.0075, 0.01, 0.015, 0.02)
GAMMAS = (0.8, 0.95, 0.99)
N0S = (1, 3, 30)


def one(fab, kind):
    import fit_q
    edges0 = {k: list(v) for k, v in fit_q.EDGES.items()}
    dumps = [os.path.join(C, SRC[kind].format(fab=fab) + f"_s{s}.json") for s in (100, 101)]

    def fit(lam=0.003, gamma=0.9, n0=10):
        fit_q.EDGES.clear(); fit_q.EDGES.update({k: list(v) for k, v in edges0.items()})
        fit_q.K0 = float(n0)
        tmp = os.path.join(tempfile.gettempdir(), f"rt_{fab}_{kind}_{os.getpid()}.json")
        sys.argv = ["fit_q.py", *dumps, "--chain", "family", "--lam", str(lam), "--gamma-h", str(gamma), "--backoff",
                    "--from-day", "90", "--fold", "fill", "--out", tmp]
        with redirect_stdout(io.StringIO()):
            fit_q.main()
        T = json.load(open(tmp))
        os.remove(tmp)
        fire = [[c[0] for c in r] for r in T["fire"]]
        nf = [[c[0] for c in r] for r in T["n_fired"]]
        nw = [[c[0] for c in r] for r in T["n_waited"]]
        own = [[c[0] for c in r] for r in T["own_entry"]]
        return {"map": "|".join("".join(map(str, r)) for r in fire), "fire": fire, "n_fired": nf, "n_waited": nw, "own": own}

    ref = fit()
    tot = sum(map(sum, ref["n_fired"])) + sum(map(sum, ref["n_waited"]))

    def against(t):
        d = [(i, j) for i in range(len(ref["fire"])) for j in range(len(ref["fire"][0])) if t["fire"][i][j] != ref["fire"][i][j]]
        share = sum(ref["n_fired"][i][j] + ref["n_waited"][i][j] for i, j in d) / tot
        return {"map": t["map"], "cells_differ": len(d), "share_decisions": share}

    def monotone(fire):
        nT, nN = len(fire), len(fire[0])
        down = sum(int(fire[i][j] < fire[i + 1][j]) for i in range(nT - 1) for j in range(nN))
        later = sum(int(fire[i][j + 1] < fire[i][j]) for i in range(nT) for j in range(nN - 1))
        return down + later

    # facts of the records (free decisions from the fit's first day on)
    n_free = n_start = soon = none = inhead = 0
    for p in dumps:
        for d in json.load(open(p))["decisions"]:
            if d["day"] < 90.0 or d["full"] or not d["clocks"]:
                continue
            c = min(d["clocks"], key=lambda x: x[1])
            if c[1] < 0.0:
                continue
            n_free += 1
            n_start += d["act"] < d["n_groups"]
            soon += d["nxt_h"] < 0.25
            none += d["nxt_h"] >= 24.0
            inhead += bool(c[2])
    res = {"fab": fab, "kind": kind, "reference": ref["map"], "monotone_violations": monotone(ref["fire"]),
           "cells_both": sum(map(sum, ref["own"])), "free_decisions_fit": tot,
           "records": {"free": n_free, "started_pct": 100 * n_start / n_free, "next_within_15min_pct": 100 * soon / n_free,
                       "none_announced_pct": 100 * none / n_free, "tightest_in_load_pct": 100 * inhead / n_free},
           "price": {f"{b:g}": against(fit(lam=b)) for b in PRICES},
           "gamma": {f"{g:g}": against(fit(gamma=g)) for g in GAMMAS},
           "n0": {f"{n:g}": against(fit(n0=n)) for n in N0S}}
    for k in ("price", "gamma", "n0"):
        for v in res[k].values():
            pass
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, f"{fab}_{kind}.json"), "w"), indent=1)
    print(fab, kind, "reference", ref["map"], "| monotone violations", res["monotone_violations"], "| cells with both", res["cells_both"])
    for k in ("price", "gamma", "n0"):
        print("  ", k, {a: (v["cells_differ"], round(100 * v["share_decisions"], 2)) for a, v in res[k].items()})


def summary():
    out = {}
    for p in sorted(glob.glob(os.path.join(OUT, "*.json"))):
        r = json.load(open(p))
        out.setdefault(r["fab"], {})[r["kind"]] = r
        print(f"{r['fab']} {r['kind']:8s} {r['reference']}  cells {r['cells_both']:2d}  monotone violations {r['monotone_violations']}  "
              f"free {r['records']['free']:,} started {r['records']['started_pct']:.1f}%  soon {r['records']['next_within_15min_pct']:.0f}%  "
              f"none {r['records']['none_announced_pct']:.0f}%  in load {r['records']['tightest_in_load_pct']:.0f}%")
        for k in ("price", "gamma", "n0"):
            print("     ", k, " ".join(f"{a}:{v['cells_differ']}" for a, v in r[k].items()))
    json.dump(out, open(os.path.join(HERE, "rule_tables_summary.json"), "w"), indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "--summary":
        summary()
    else:
        one(sys.argv[1], sys.argv[2])
