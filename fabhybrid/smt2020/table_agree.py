"""Decision-level agreement of fitted tables on logged decisions, without simulation.

Every free decision of the given dumps (a live queue-time clock, load not full, from --from-day on)
is looked up in each table through the table's own edges, exactly as level.py deploys it; the
output is, for each table, the share of those decisions on which it takes the reference table's
action, and the share it fires.

  python table_agree.py --ref A.json --tables B.json C.json --dumps d1.json d2.json [--from-day 90]
"""
import argparse
import json
import os

import numpy as np


def cell(x, edges):
    return int(np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2))


def free_states(paths, from_day):
    out = []
    for p in paths:
        D = json.load(open(p))
        for d in D["decisions"]:
            if d["day"] < from_day or d["full"] or not d["clocks"]:
                continue
            tight = min(c[1] for c in d["clocks"])
            if tight < 0.0:
                continue
            out.append((tight, d["nxt_h"]))
    return np.array(out)


def actions(table, X):
    e, f = table["edges"], np.asarray(table["fire"])
    return np.array([f[cell(m, e["tightest"]), cell(u, e["nxt"]), 0] for m, u in X], dtype=int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--tables", nargs="+", required=True)
    ap.add_argument("--dumps", nargs="+", required=True)
    ap.add_argument("--from-day", type=float, default=90.0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    X = free_states(a.dumps, a.from_day)
    ref = json.load(open(a.ref))
    r = actions(ref, X)
    rows = {"ref": os.path.basename(a.ref), "n_free_decisions": int(len(X)), "ref_fire_share": float(r.mean()), "tables": {}}
    for t in a.tables:
        T = json.load(open(t))
        x = actions(T, X)
        rows["tables"][os.path.basename(t)] = {"agree": float((x == r).mean()), "fire_share": float(x.mean()),
                                               "edges": T["edges"], "lam": T.get("lam")}
        print(f"{os.path.basename(t):48s} agree {100 * (x == r).mean():6.2f}%  fires {100 * x.mean():5.2f}%  "
              f"(ref fires {100 * r.mean():5.2f}%, n {len(X)})")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
