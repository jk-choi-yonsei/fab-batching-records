"""The isolated station of announced_station.py at the per-run cost that the learner's price implies.

At beta = 0.003 lots per empty slot-hour, eq. (kappa) of the paper gives kappa = 0.08-0.14 for the four
constrained furnace steps, below the grid {0.25, 0.5, 1} of announced_station.py --grid. This script solves
the same grid of (B, p, eta) for chosen R, L and kappa and stores the same analysis per instance, so that the
two sets can be read together.

  python announced_lowkappa.py 8 2,4 0.1 ../../../experiments/smt2020/theory/announced_kappa0p1_R8.json
  python announced_lowkappa.py 12 4 0.1 ../../../experiments/smt2020/theory/announced_kappa0p1_R12_L4.json
"""
import itertools
import json
import sys
import time

from announced_station import analyse, solve


def main():
    Rs = [int(x) for x in sys.argv[1].split(",")]
    Ls = [int(x) for x in sys.argv[2].split(",")]
    kappas = [float(x) for x in sys.argv[3].split(",")]
    out_path = sys.argv[4]
    grid = list(itertools.product([2, 3, 4], Rs, Ls, [0.1, 0.25, 0.5], kappas, [0.0, 0.02, 0.05, 0.1, 0.2]))
    out = []
    for B, R, L, p, kappa, c in grid:
        t0 = time.time()
        an = analyse(solve(B, R, L, p, kappa, c, 0.99))
        umax = 0                                    # the furthest announced arrival the station waits for
        for u, row in an["actions_by_u"].items():
            if u == "none":
                continue
            for m in range(1, R + 1):
                if m > int(u) and row[m - 1] in "W?":
                    umax = max(umax, int(u))
        an.update(B=B, R=R, L=L, p=p, kappa=kappa, c=c, gamma=0.99, u_max_waited=umax)
        out.append(an)
        print(f"B{B} R{R} L{L} p{p} k{kappa} c{c}: {time.time() - t0:.1f}s non-thr {an['non_threshold']} "
              f"nj-viol {an['nothing_joins_violations']} mono {an['mono_violations']}/{an['mono_pairs']} "
              f"mixed {an['um_mixed']}/{an['um_cells']} partial {an['partial_runs']} umax {umax}", flush=True)
        with open(out_path, "w") as f:
            json.dump(out, f, indent=1)
    priced = [i for i in out if i["c"] > 0]
    print("instances", len(out), "| non-threshold", sum(i["non_threshold"] for i in out),
          "| nothing-joins violations", sum(i["nothing_joins_violations"] for i in out),
          "| monotonicity", sum(i["mono_violations"] for i in out), "/", sum(i["mono_pairs"] for i in out),
          "| partial runs", sum(i["partial_runs"] for i in out),
          "| mixed cells", sum(i["um_mixed"] for i in out), "/", sum(i["um_cells"] for i in out),
          "| priced", len(priced), "waits within kappa/eta in",
          sum(1 for i in priced if i["u_max_waited"] <= i["kappa"] / i["c"] + 1e-12))


if __name__ == "__main__":
    main()
