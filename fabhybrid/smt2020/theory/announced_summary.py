"""The numbers of Section 3.3.3 (Numerical solutions), from announced.json (the grid of 540 instances at
kappa in {0.25, 0.5, 1}), the three announced_kappa0p1_*.json files (180 instances at kappa = 0.1, which
complete the full factorial of 720 that the manuscript's \\stationInstances names) and announced_cells.json
(the cell classification on the R = 8 instances).

  python theory/announced_summary.py
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, "..", "..", "..", "experiments", "smt2020", "theory")


def main():
    g = json.load(open(os.path.join(T, "announced.json")))
    extra = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(T, "announced_kappa0p1_*.json")))]
    allg = g + [i for e in extra for i in e]
    um_all, mixed_all = sum(i["um_cells"] for i in allg), sum(i["um_mixed"] for i in allg)
    print(f"the manuscript's instances (\\stationInstances): {len(allg)} = {len(g)} + {' + '.join(str(len(e)) for e in extra)}")
    print(f"  (u, m) cells in which the rest of the state decides (\\stationMixedPct): {mixed_all} of {um_all} "
          f"= {100 * mixed_all / um_all:.2f}%")
    print(f"  cells in which m and u alone set the decision (\\stationPurePct): {um_all - mixed_all} of {um_all} "
          f"= {100 * (um_all - mixed_all) / um_all:.2f}%")
    print(f"  monotone-in-u violations / comparisons over all {len(allg)}: "
          f"{sum(i['mono_violations'] for i in allg)} / {sum(i['mono_pairs'] for i in allg)}")
    print(f"  non-threshold configurations over all {len(allg)}: {sum(i['non_threshold'] for i in allg)}")
    n = len(g)
    print(f"stations of announced.json: {n}")
    print("  non-threshold configurations:", sum(i["non_threshold"] for i in g))
    print("  nothing-joins violations:", sum(i["nothing_joins_violations"] for i in g))
    print("  monotone-in-u violations / comparisons:", sum(i["mono_violations"] for i in g), "/", sum(i["mono_pairs"] for i in g))
    print("  partial runs (optimum served fewer than all waiting):", sum(i["partial_runs"] for i in g))
    um, mixed = sum(i["um_cells"] for i in g), sum(i["um_mixed"] for i in g)
    print(f"  (u, m) cells: {um}, of which the rest of the state decides: {mixed} ({100 * mixed / um:.1f}%)")
    free = [i for i in g if i["c"] == 0]
    priced = [i for i in g if i["c"] > 0]
    print(f"  c = 0 stations: {len(free)}; cells where the rest decides: {sum(i['um_mixed'] for i in free)} of {sum(i['um_cells'] for i in free)}")
    for c in sorted({i["c"] for i in priced}):
        sub = [i for i in priced if i["c"] == c]
        print(f"  c = {c}: rest decides in {sum(i['um_mixed'] for i in sub)} of {sum(i['um_cells'] for i in sub)} cells")

    # the level equals the next possible arrival exactly: at c = 0, is every row F^{min(u,L+1)} W...?
    def exact(i):
        L = i["L"]
        for u, row in i["actions_by_u"].items():
            uu = L + 1 if u == "none" else int(u)
            want = "F" * uu + "W" * (len(row) - uu)
            if row.replace("T", "F") != want and row.replace("T", "W") != want:
                return False
        return True
    print(f"  level = next possible arrival at every u: {sum(exact(i) for i in free)} of {len(free)} at c = 0; "
          f"{sum(exact(i) for i in priced)} of {len(priced)} priced")
    cells = json.load(open(os.path.join(T, "announced_cells.json")))
    print(f"  R = 8 priced stations: u_max waited <= kappa/c in {cells['u_max_within_kappa_over_c']} of {cells['priced_instances']}")


if __name__ == "__main__":
    main()
