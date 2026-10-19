"""Stage A of the final block: read the search-seed runs and apply the ONE selection rule
of experiments/smt2020/final/PROTOCOL.md -- within each arm family, the parameter with the
highest mean completions per day over the search seeds, per scenario.

Writes final/selection.json, which stage B's job file is built from. Reads nothing but
search seeds; the report seeds do not exist yet when this runs.

  python final_select.py
"""
import glob
import json
import os
import re
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(HERE, "..", "..", "experiments", "smt2020", "final")
FAMILIES = {                      # family -> regex over the arm tag
    "full": r"^full$",
    "mbs": r"^(mbs\d+|mbsmin)$",
    "nach": r"^nach$",
    "timeout": r"^timeout[\d.]+$",
    "clock": r"^clock[\d.]+$",
    "learner": r"^level1_.*_t3$",
}


def main():
    runs = defaultdict(dict)                      # (fab, tag) -> seed -> (completed, scrapped, fill, partial)
    for p in glob.glob(os.path.join(FINAL, "search", "batch_fire_*_qtcr_scrap.json")):
        m = re.match(r"batch_fire_(HVLM|LVHM)_r0\.98_d360_s(\d+)_(.+)_qtcr_scrap\.json", os.path.basename(p))
        if not m:
            continue
        j = json.load(open(p))
        k = j["scrap_kpi"]
        runs[(m.group(1), m.group(3))][int(m.group(2))] = (
            k["completed_per_day"], k["scrapped_per_day"], j.get("batch_fill"), j.get("batches_partial"))
    out = {}
    for fab in ("HVLM", "LVHM"):
        out[fab] = {}
        print(f"\n================ {fab}: search seeds, completions/day over days 87-360 ================")
        for fam, rx in FAMILIES.items():
            members = sorted(t for (f, t) in runs if f == fab and re.match(rx, t))
            if not members:
                continue
            rows = []
            for t in members:
                v = runs[(fab, t)]
                c = np.array([x[0] for x in v.values()])
                rows.append((t, len(c), float(c.mean()), float(c.std(ddof=1)) if len(c) > 1 else 0.0,
                             float(np.mean([x[1] for x in v.values()])),
                             float(np.mean([x[2] or 0 for x in v.values()])),
                             float(np.mean([x[3] or 0 for x in v.values()]))))
            best = max(rows, key=lambda r: r[2])
            out[fab][fam] = {"selected": best[0], "grid_size": len(rows),
                             "ladder": {r[0]: {"n": r[1], "completed": r[2], "sd": r[3], "scrapped": r[4],
                                               "fill": r[5], "partial_loads": r[6]} for r in rows}}
            print(f"  {fam} (grid {len(rows)})")
            for r in rows:
                mark = "  <- selected" if r[0] == best[0] and len(rows) > 1 else ""
                print(f"     {r[0]:28s} n={r[1]:2d}  {r[2]:7.3f} (sd {r[3]:.2f})  scrap {r[4]:6.2f}  fill {r[5]:.3f}  "
                      f"partial {r[6]:8.0f}{mark}")
    if not runs:
        raise SystemExit(f"no selection runs under {os.path.join(FINAL, 'search')}; selection.json left as it is")
    json.dump(out, open(os.path.join(FINAL, "selection.json"), "w"), indent=1)
    print("\nwrote", os.path.join(FINAL, "selection.json"))


if __name__ == "__main__":
    main()
