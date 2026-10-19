"""Where does the rest of the state enter the priced station's optimal policy?

For every (u, m) cell in which the optimal action is not a function of (u, m) alone,
classify the configurations by the count k, whether k = B - 1 (one slot left), and
whether a second announced arrival can also share the run (u2 <= m - 1). Also record,
per instance, the largest u at which waiting for an announced arrival is ever optimal,
against kappa / c. Runs the R = 8 instances of the grid (the R = 12 ones give the same
picture on the cases tried); writes announced_cells.json.

  python theory/announced_cells.py
"""
import itertools
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from announced_station import solve, first_bit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "..", "experiments", "smt2020", "theory", "announced_cells.json")


def cells(sol, margin=1e-9):
    res, w, k, Qf, Qw, B, R, L = sol["res"], sol["w"], sol["k"], sol["Qf"], sol["Qw"], sol["B"], sol["R"], sol["L"]
    fires = Qf.max(axis=0) > Qw + margin
    ties = np.abs(Qf.max(axis=0) - Qw) <= margin
    by = {}
    for s in np.nonzero((k >= 1) & (k < B))[0]:
        rm, wm = int(res[s]), int(w[s])
        m, u = first_bit(rm), first_bit(wm)
        later = wm & (wm - 1)
        u2 = first_bit(later)
        a = "T" if ties[s] else ("F" if fires[s] else "W")
        by.setdefault((u, m), []).append((int(k[s]), u2, a))
    return by


def main():
    grid = list(itertools.product([2, 3, 4], [8], [2, 4], [0.1, 0.25, 0.5], [0.25, 0.5, 1.0], [0.0, 0.02, 0.05, 0.1, 0.2]))
    out = []
    tot_mixed = 0; mixed_with_full_slot = 0; mixed_with_second_joining = 0; mixed_explained = 0
    for B, R, L, p, kappa, c in grid:
        sol = solve(B, R, L, p, kappa, c, 0.99)
        by = cells(sol)
        inst = {"B": B, "R": R, "L": L, "p": p, "kappa": kappa, "c": c, "mixed_cells": [], "u_max_waited": 0,
                "kappa_over_c": (kappa / c) if c > 0 else None}
        for (u, m), rows in by.items():
            acts = {a for _, _, a in rows if a != "T"}
            if u is not None and any(a == "W" for _, _, a in rows) and m > u:
                inst["u_max_waited"] = max(inst["u_max_waited"], u)
            if len(acts) < 2:
                continue
            tot_mixed += 1
            # which configurations fire: is it always k = B-1 with a second arrival that can join?
            firing = [(kk, u2) for kk, u2, a in rows if a == "F"]
            waiting = [(kk, u2) for kk, u2, a in rows if a == "W"]
            f_full_slot = all(kk == B - 1 for kk, _ in firing)
            f_second = all(u2 is not None and u2 <= m - 1 for _, u2 in firing)
            explained = all(kk == B - 1 and u2 is not None and u2 <= m - 1 for kk, u2 in firing) and \
                not any(kk == B - 1 and u2 is not None and u2 <= m - 1 for kk, u2 in waiting)
            mixed_with_full_slot += f_full_slot; mixed_with_second_joining += f_second; mixed_explained += explained
            inst["mixed_cells"].append({"u": u, "m": m, "fire_configs": sorted(set(firing), key=str), "wait_configs": sorted(set(waiting), key=str),
                                        "fires_only_at_one_slot_left": f_full_slot, "fires_only_with_second_arrival_joining": f_second,
                                        "explained_by_both": explained})
        out.append(inst)
        print(f"B{B} L{L} p{p} k{kappa} c{c}: mixed {len(inst['mixed_cells'])}, u_max waited {inst['u_max_waited']}, kappa/c {inst['kappa_over_c']}", flush=True)
    print(f"mixed cells {tot_mixed}: firing configs all at one slot left {mixed_with_full_slot}, all with a second joining arrival {mixed_with_second_joining}, "
          f"exactly (one slot left AND second joining) {mixed_explained}")
    # the cap: u_max_waited vs kappa/c
    caps = [(i["u_max_waited"], i["kappa_over_c"], i["L"]) for i in out if i["kappa_over_c"] is not None]
    within = sum(1 for um, kc, L in caps if um <= kc)
    print(f"u_max waited <= kappa/c in {within} of {len(caps)} priced instances; "
          f"u_max = min(L, floor(kappa/c)) in {sum(1 for um, kc, L in caps if um == min(L, int(kc)))}")
    json.dump({"instances": out, "mixed_cells": tot_mixed, "mixed_all_one_slot_left": mixed_with_full_slot,
               "mixed_all_second_joining": mixed_with_second_joining, "mixed_explained_by_both": mixed_explained,
               "u_max_within_kappa_over_c": within, "priced_instances": len(caps)}, open(OUT, "w"), indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
