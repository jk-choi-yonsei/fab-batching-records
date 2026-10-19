"""Table 1's testbed rows and the run cost kappa of Appendix A.3, computed from the SMT2020 data files in the
simulator submodule (external/PySCFabSim-release/datasets/SMT2020_{HVLM,LVHM}). Fitting and simulation free.

  python -B testbed_facts.py          -> prints the rows and writes testbed_facts.json next to this file

Rows: tools and tool families (the Delay_* placeholder family of 400 slots is not a tool), furnaces (the
per-batch families) and their tools, the capacity of a furnace load in lots (BATCHMX wafers / 25), the run
duration (PTIME of the per-batch steps), lots released per day at 0.98 of the testbed's rate (1440 min / REPEAT
per order, summed), the queue-time constraints on the routes, how many end at a furnace step (STEP_CQT names
the target step), their limits, and kappa = beta B S / (1 + beta S) at beta = 0.003 over the constrained
furnace steps.
"""
import csv
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "external", "PySCFabSim-release", "datasets"))
WAFERS_PER_LOT = 25
SCALE = 0.98
BETA = 0.003


def rows(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        r = list(csv.reader(f, delimiter="\t"))
    head = r[0]
    return [dict(zip(head, x)) for x in r[1:] if x and any(x)]


def hours(value, unit):
    v = float(value)
    return {"sec": v / 3600, "min": v / 60, "hr": v, "hour": v, "day": 24 * v}[unit.strip().lower()]


def facts(fab):
    d = os.path.join(DATA, f"SMT2020_{fab}")
    tools = rows(os.path.join(d, "tool.txt.1l"))
    qty = {}
    for t in tools:
        qty[t["STNFAM"]] = qty.get(t["STNFAM"], 0) + int(float(t["STNQTY"] or 0))
    real = {f: q for f, q in qty.items() if not f.startswith("Delay")}
    orders = rows(os.path.join(d, "order.txt"))
    released = sum(1440.0 / float(o["REPEAT"]) for o in orders if o["RUNITS"].strip().lower() == "min")
    furnace_fams, caps, runs = set(), set(), []
    n_cqt = n_cqt_furnace = 0
    limits_furnace, kappas = set(), []
    for rp in sorted(glob.glob(os.path.join(d, "route_*.txt"))):
        R = rows(rp)
        steps = {int(x["STEP"]): x for x in R}
        for x in R:
            if x.get("PTPER") == "per_batch":
                furnace_fams.add(x["STNFAM"])
                caps.add(int(float(x["BATCHMX"])) // WAFERS_PER_LOT)
                runs.append(hours(x["PTIME"], x["PTUNITS"]))
            if x.get("STEP_CQT", "").strip():
                n_cqt += 1
                target = steps[int(float(x["STEP_CQT"]))]
                if target.get("PTPER") == "per_batch":
                    n_cqt_furnace += 1
                    limits_furnace.add(round(hours(x["CQT"], x["CQTUNITS"]), 3))
                    B = int(float(target["BATCHMX"])) // WAFERS_PER_LOT
                    S = hours(target["PTIME"], target["PTUNITS"])
                    kappas.append(BETA * B * S / (1 + BETA * S))
    return {
        "tools": sum(real.values()), "tool_families": len(real),
        "furnaces": sum(qty[f] for f in furnace_fams), "furnace_families": len(furnace_fams),
        "load_capacity_lots": [min(caps), max(caps)],
        "run_hours": [round(min(runs), 2), round(max(runs), 2)],
        "released_per_day_nominal": round(released, 3), "released_per_day_at_scale": round(SCALE * released, 3),
        "queue_time_constraints": n_cqt, "ending_at_a_furnace_step": n_cqt_furnace,
        "furnace_limits_h": sorted(limits_furnace),
        "kappa_at_beta": {"beta": BETA, "min": round(min(kappas), 4), "max": round(max(kappas), 4)},
    }


def main():
    out = {fab: facts(fab) for fab in ("HVLM", "LVHM")}
    for fab, f in out.items():
        print(f"== {fab}")
        for k, v in f.items():
            print(f"  {k}: {v}")
    with open(os.path.join(HERE, "testbed_facts.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("wrote", os.path.join(HERE, "testbed_facts.json"))


if __name__ == "__main__":
    main()
