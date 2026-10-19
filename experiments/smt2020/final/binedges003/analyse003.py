"""TASK A1 steps 2, 4, 5: check the ref fits against the paper artefacts, read every table's start
limits per u column and its monotonicity violations, locate where each variant's disagreement with
the reference arises, and write summary.json / summary.md.

  python analyse003.py   (run from anywhere; paths are resolved from this file's location)
"""
import json
import os
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.normpath(os.path.join(HERE, ".."))
REFDIR = os.path.join(FINAL, "betarx", "family")
COLLECT = os.path.join(FINAL, "collect")
FABS = ("HVLM", "LVHM")
KINDS = ("timeout", "mbs3", "nach", "learner")
STEM = {"timeout": "norev_p1", "mbs3": "mbs3_p1", "nach": "nach_p1", "learner": "p1"}
VARS = ("ref", "Rc", "Rf", "Rl", "Rh", "Ac", "Af", "Al", "Ah")
VAR_EDGES = {  # interior edges in hours (None = reference axis)
    "ref": (None, None),
    "Rc": ([0.5, 1, 2, 4], None),
    "Rf": ([0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4], None),
    "Rl": ([0.1875, 0.375, 0.75, 1.5, 3], None),
    "Rh": ([0.375, 0.75, 1.5, 3, 6], None),
    "Ac": (None, [0.5, 2]),
    "Af": (None, [0.25, 0.5, 1, 2, 3, 6]),
    "Al": (None, [0.125, 0.5, 1.5]),
    "Ah": (None, [0.5, 2, 6]),
}
FROM_DAY = 90.0


def cell(x, edges):
    return int(np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2))


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def free_states(fab, kind):
    """(m_min, u) of every free decision of the KIND's two record files, days >= 90, as table_agree.py."""
    out = []
    for seed in (100, 101):
        D = load(os.path.join(COLLECT, f"{fab}_{STEM[kind]}_s{seed}.json"))
        for d in D["decisions"]:
            if d["day"] < FROM_DAY or d["full"] or not d["clocks"]:
                continue
            tight = min(c[1] for c in d["clocks"])
            if tight < 0.0:
                continue
            out.append((tight, d["nxt_h"]))
    return np.array(out)


def actions(table, X):
    e, f = table["edges"], np.asarray(table["fire"])
    return np.array([f[cell(m, e["tightest"]), cell(u, e["nxt"]), 0] for m, u in X], dtype=int)


def fmt_edge(x):
    return "all" if x >= 24.0 else f"{x:g}"


def column_limits(table):
    """Per u bin: the pattern down the m axis (S = start, w = wait), whether it is an initial segment,
    and the m edges: 'limit' = largest m edge below which every bin starts (the first wait's lower edge),
    'last_start_edge' = the upper edge of the last start bin (equal to 'limit' when clean)."""
    e, f = table["edges"], np.asarray(table["fire"])[:, :, 0]
    tl = e["tightest"]
    cols = []
    for j in range(f.shape[1]):
        col = f[:, j].astype(int)
        pat = "".join("S" if v else "w" for v in col)
        starts = np.flatnonzero(col)
        if len(starts) == 0:
            limit, last, clean = 0.0, 0.0, True
        else:
            first_wait = int(np.flatnonzero(col == 0)[0]) if (col == 0).any() else len(col)
            limit = tl[first_wait]
            last = tl[int(starts[-1]) + 1]
            clean = bool(np.all(starts == np.arange(len(starts))))
        cols.append({"u_bin": f"[{e['nxt'][j]:g},{fmt_edge(e['nxt'][j + 1])})", "pattern": pat, "clean": clean,
                     "limit_h": float(limit), "last_start_edge_h": float(last)})
    return cols


def violations(table):
    """Pair counts: (m) a start at a larger m bin with a wait at a smaller m bin in the same u column;
    (u) a wait at a larger u bin with a start at a smaller u bin in the same m row."""
    f = np.asarray(table["fire"])[:, :, 0].astype(int)
    T, N = f.shape
    vm = sum(1 for j in range(N) for i in range(T) for i2 in range(i + 1, T) if f[i, j] == 0 and f[i2, j] == 1)
    vu = sum(1 for i in range(T) for j in range(N) for j2 in range(j + 1, N) if f[i, j] == 1 and f[i, j2] == 0)
    cols_bad = sum(1 for j in range(N) if any(f[i, j] == 0 and f[i2, j] == 1 for i in range(T) for i2 in range(i + 1, T)))
    rows_bad = sum(1 for i in range(T) if any(f[i, j] == 1 and f[i, j2] == 0 for j in range(N) for j2 in range(j + 1, N)))
    return {"m_pairs": vm, "u_pairs": vu, "columns_nonmonotone": cols_bad, "rows_nonmonotone": rows_bad}


def grid_text(table):
    e, f = table["edges"], np.asarray(table["fire"])[:, :, 0]
    own = np.asarray(table["own_entry"])[:, :, 0]
    tl, nl = e["tightest"], e["nxt"]
    head = "m \\ u".rjust(14) + " | " + " | ".join(f"[{nl[j]:g},{fmt_edge(nl[j+1])})".center(11) for j in range(f.shape[1]))
    lines = [head]
    for i in range(f.shape[0]):
        row = f"[{tl[i]:g},{fmt_edge(tl[i+1])})".rjust(14) + " | "
        row += " | ".join((("S" if f[i, j] else "w") + ("" if own[i, j] else "*")).center(11) for j in range(f.shape[1]))
        lines.append(row)
    return "\n".join(lines)


def disagreement_regions(ref, tab, X, r, x):
    """Where (in the REFERENCE table's cells) the variant's decisions differ: counts per ref cell, the
    direction, and the continuous ranges of m and u among the disagreeing decisions."""
    e = ref["edges"]
    dis = np.flatnonzero(x != r)
    if len(dis) == 0:
        return {"n": 0, "cells": []}
    cnt = Counter()
    for k in dis:
        m, u = X[k]
        cnt[(cell(m, e["tightest"]), cell(u, e["nxt"]), int(r[k]), int(x[k]))] += 1
    cells = []
    for (i, j, ra, xa), n in cnt.most_common():
        sel = [k for k in dis if cell(X[k][0], e["tightest"]) == i and cell(X[k][1], e["nxt"]) == j and r[k] == ra]
        ms = X[sel, 0]; us = X[sel, 1]
        cells.append({"ref_m_bin": f"[{e['tightest'][i]:g},{fmt_edge(e['tightest'][i+1])})",
                      "ref_u_bin": f"[{e['nxt'][j]:g},{fmt_edge(e['nxt'][j+1])})",
                      "ref_action": "start" if ra else "wait", "variant_action": "start" if xa else "wait",
                      "n": int(n), "share_of_free_pct": float(100 * n / len(X)),
                      "m_range_h": [float(ms.min()), float(ms.max())], "u_range_h": [float(us.min()), float(us.max())]})
    return {"n": int(len(dis)), "share_of_free_pct": float(100 * len(dis) / len(X)), "cells": cells}


def main():
    summary = {"price": 0.003, "estimator": "fit_q.py --chain family --lam 0.003 --backoff --from-day 90 --fold fill",
               "variants": {k: {"tightest": v[0], "nxt": v[1]} for k, v in VAR_EDGES.items()}, "ref_check": {},
               "per_fab_kind": {}, "walltime": {}}
    md = ["# Bin-edge variants at beta 0.003, four sets of records, both scenarios (TASK A1, 2026-10-09)", "",
          "Estimator: `fit_q.py --chain family --lam 0.003 --backoff --from-day 90 --fold fill` (n0 = K0 = 10, gamma 0.9/h),",
          "exactly as `betarx/family/{FAB}_{KIND}_b0p003_t1.json`; only `--edges-tightest` / `--edges-nxt` change.",
          "Records: `collect/{FAB}_{STEM}_s{100,101}.json`, days >= 90. Agreement = share of the KIND's own free decisions",
          "on which the variant takes the reference fit's action (`table_agree.py`, each table looked up through its own edges).",
          "Start limit per u column = the largest m edge below which every m bin starts (the lower edge of the first wait);",
          "`clean` = the starts form an initial segment of the m bins. Violations are pair counts: m = a start at a larger",
          "m bin above a wait in the same u column; u = a wait at a larger u bin beside a start in the same m row.",
          "Own = cells where both actions reached n0 = 10 (the others carry the residual-only decision).", "",
          "| variant | axis | interior edges (h) |", "|---|---|---|"]
    for v, (et, en) in VAR_EDGES.items():
        if v == "ref":
            desc = "m: 0.25,0.5,1,2,4 / u: 0.25,1,3"
        elif et:
            desc = "m: " + ",".join(f"{x:g}" for x in et)
        else:
            desc = "u: " + ",".join(f"{x:g}" for x in en)
        md.append(f"| {v} | {'m' if et else ('u' if en else '-')} | {desc} |")
    md.append("")
    # wall time
    wt_path = os.path.join(HERE, "walltime.txt")
    if os.path.exists(wt_path):
        wt = {}
        for line in open(wt_path, encoding="utf-8"):
            parts = line.split()
            if len(parts) >= 3:
                wt[parts[0]] = float(parts[1])
        summary["walltime"] = {"per_fit_s": wt, "n": len(wt), "min_s": min(wt.values()), "max_s": max(wt.values()),
                               "mean_s": float(np.mean(list(wt.values()))), "parallel": 4}
    all_agree = []
    worst_overall = None
    for fab in FABS:
        for kind in KINDS:
            key = f"{fab}_{kind}"
            paper = load(os.path.join(REFDIR, f"{fab}_{kind}_b0p003_t1.json"))
            tabs = {v: load(os.path.join(HERE, f"{fab}_{kind}_b0p003_{v}.json")) for v in VARS}
            ref = tabs["ref"]
            # step 2: ref fit vs paper artefact
            chk = {"fire_equal": ref["fire"] == paper["fire"], "edges_equal": ref["edges"] == paper["edges"],
                   "n_fired_equal": ref["n_fired"] == paper["n_fired"], "n_waited_equal": ref["n_waited"] == paper["n_waited"],
                   "own_entry_equal": ref["own_entry"] == paper["own_entry"],
                   "margin_max_abs_diff": float(np.max(np.abs(np.asarray(ref["margin"]) - np.asarray(paper["margin"])))),
                   "n_transitions": [ref["n_transitions"], paper["n_transitions"]]}
            if not chk["fire_equal"]:
                a, b = np.asarray(ref["fire"])[:, :, 0], np.asarray(paper["fire"])[:, :, 0]
                chk["fire_mismatch_cells"] = [[int(i), int(j), int(a[i, j]), int(b[i, j])] for i, j in zip(*np.nonzero(a != b))]
            summary["ref_check"][key] = chk
            # step 3 output (table_agree.py) + own recomputation for the regions
            ag_path = os.path.join(HERE, f"agree_{fab}_{kind}.json")
            ag = load(ag_path) if os.path.exists(ag_path) else None
            X = free_states(fab, kind)
            r = actions(ref, X)
            rows = {}
            for v in VARS:
                t = tabs[v]
                x = actions(t, X)
                agree = float((x == r).mean()); fire_share = float(x.mean())
                if ag is not None and v != "ref":
                    rec = ag["tables"][f"{fab}_{kind}_b0p003_{v}.json"]
                    assert abs(rec["agree"] - agree) < 1e-12 and abs(rec["fire_share"] - fire_share) < 1e-12, (key, v)
                own = np.asarray(t["own_entry"])[:, :, 0]
                cols = column_limits(t)
                rows[v] = {"agree_pct": 100 * agree, "start_share_pct": 100 * fire_share,
                           "n_free": int(len(X)), "n_cells": int(own.size), "own_cells": int(own.sum()),
                           "start_cells": int(np.asarray(t["fire"])[:, :, 0].sum()),
                           "columns": cols, "violations": violations(t),
                           "all_columns_clean": all(c["clean"] for c in cols),
                           "residual_only": t["fire_residual_only"], "grid": grid_text(t),
                           "disagreement": disagreement_regions(ref, t, X, r, x) if v != "ref" else None}
                if v != "ref":
                    all_agree.append((100 * agree, key, v))
            vals = [(rows[v]["agree_pct"], v) for v in VARS if v != "ref"]
            lo, hi = min(vals), max(vals)
            m_vals = [rows[v]["agree_pct"] for v in ("Rc", "Rf", "Rl", "Rh")]
            u_vals = [rows[v]["agree_pct"] for v in ("Ac", "Af", "Al", "Ah")]
            per = {"rows": rows, "min_agree": {"pct": lo[0], "variant": lo[1]}, "max_agree": {"pct": hi[0], "variant": hi[1]},
                   "mean_agree_m_axis": float(np.mean(m_vals)), "mean_agree_u_axis": float(np.mean(u_vals)),
                   "min_agree_m_axis": float(min(m_vals)), "min_agree_u_axis": float(min(u_vals)),
                   "worst_variant_top_cells": rows[lo[1]]["disagreement"]["cells"][:4]}
            summary["per_fab_kind"][key] = per
            if worst_overall is None or lo[0] < worst_overall[0]:
                worst_overall = (lo[0], key, lo[1])
            # markdown
            md += [f"## {fab} {kind} (records `{fab}_{STEM[kind]}_s100/101`, {len(X):,} free decisions; "
                   f"ref starts {100 * r.mean():.2f}%, ref fit == paper artefact: {chk['fire_equal']})", "",
                   "| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |",
                   "|---|---|---|---|---|---|---|---|"]
            for v in VARS:
                rw = rows[v]
                lim = "; ".join(f"{c['u_bin']}: {fmt_edge(c['limit_h'])}" + ("" if c["clean"] else f" ({c['pattern']})") for c in rw["columns"])
                md.append(f"| {v} | {rw['agree_pct']:.2f} | {rw['start_share_pct']:.2f} | {rw['start_cells']} | "
                          f"{rw['own_cells']}/{rw['n_cells']} | {'yes' if rw['all_columns_clean'] else 'NO'} | {lim} | "
                          f"{rw['violations']['m_pairs']} / {rw['violations']['u_pairs']} |")
            md += ["", f"Agreement over variants: min {lo[0]:.2f}% ({lo[1]}), max {hi[0]:.2f}% ({hi[1]}); "
                       f"m-axis variants mean {np.mean(m_vals):.2f}% (min {min(m_vals):.2f}%), "
                       f"u-axis variants mean {np.mean(u_vals):.2f}% (min {min(u_vals):.2f}%).", "",
                   f"Largest disagreement, {lo[1]} vs ref, by reference cell (ref action -> variant action, n, % of free decisions, "
                   f"m range, u range):", ""]
            for c in rows[lo[1]]["disagreement"]["cells"][:6]:
                md.append(f"- m {c['ref_m_bin']} x u {c['ref_u_bin']}: {c['ref_action']} -> {c['variant_action']}, n {c['n']:,} "
                          f"({c['share_of_free_pct']:.2f}%), m in [{c['m_range_h'][0]:.3f}, {c['m_range_h'][1]:.3f}] h, "
                          f"u in [{c['u_range_h'][0]:.3f}, {c['u_range_h'][1]:.3f}] h")
            md += ["", "Reference fire map (S = start, w = wait, * = residual-only entry):", "", "```", rows["ref"]["grid"], "```", ""]
            for v in VARS:
                if v != "ref" and (not rows[v]["all_columns_clean"] or rows[v]["violations"]["m_pairs"] or rows[v]["violations"]["u_pairs"]):
                    md += [f"{v} fire map (violations m {rows[v]['violations']['m_pairs']}, u {rows[v]['violations']['u_pairs']}):", "",
                           "```", rows[v]["grid"], "```", ""]
    all_agree.sort()
    summary["overall"] = {"min_agree": {"pct": all_agree[0][0], "fab_kind": all_agree[0][1], "variant": all_agree[0][2]},
                          "max_agree": {"pct": all_agree[-1][0], "fab_kind": all_agree[-1][1], "variant": all_agree[-1][2]},
                          "n_variant_tables": len(all_agree),
                          "below_99": [(a, k, v) for a, k, v in all_agree if a < 99.0],
                          "mean_agree_by_variant": {v: float(np.mean([a for a, k, vv in all_agree if vv == v])) for v in VARS if v != "ref"},
                          "min_agree_by_variant": {v: float(min(a for a, k, vv in all_agree if vv == v)) for v in VARS if v != "ref"},
                          "mean_agree_by_kind": {kd: float(np.mean([a for a, k, vv in all_agree if k.endswith("_" + kd)])) for kd in KINDS},
                          "min_agree_by_kind": {kd: float(min(a for a, k, vv in all_agree if k.endswith("_" + kd))) for kd in KINDS},
                          "mean_agree_by_fab": {fb: float(np.mean([a for a, k, vv in all_agree if k.startswith(fb)])) for fb in FABS},
                          "mean_agree_m_axis": float(np.mean([a for a, k, vv in all_agree if vv.startswith("R")])),
                          "mean_agree_u_axis": float(np.mean([a for a, k, vv in all_agree if vv.startswith("A")]))}
    ov = summary["overall"]
    md += ["## Overall", "",
           f"- agreement over the {ov['n_variant_tables']} variant tables: min {ov['min_agree']['pct']:.2f}% "
           f"({ov['min_agree']['fab_kind']} {ov['min_agree']['variant']}), max {ov['max_agree']['pct']:.2f}% "
           f"({ov['max_agree']['fab_kind']} {ov['max_agree']['variant']})",
           f"- below 99%: " + (", ".join(f"{k} {v} {a:.2f}%" for a, k, v in ov["below_99"]) if ov["below_99"] else "none"),
           f"- mean agreement, m-axis variants {ov['mean_agree_m_axis']:.2f}%, u-axis variants {ov['mean_agree_u_axis']:.2f}%",
           "- mean / min agreement by variant: " + ", ".join(f"{v} {ov['mean_agree_by_variant'][v]:.2f}/{ov['min_agree_by_variant'][v]:.2f}" for v in VARS if v != "ref"),
           "- mean / min agreement by records: " + ", ".join(f"{kd} {ov['mean_agree_by_kind'][kd]:.2f}/{ov['min_agree_by_kind'][kd]:.2f}" for kd in KINDS),
           "- mean agreement by scenario: " + ", ".join(f"{fb} {ov['mean_agree_by_fab'][fb]:.2f}" for fb in FABS),
           f"- ref fits equal to the paper artefacts (fire map): " + ", ".join(f"{k} {c['fire_equal']}" for k, c in summary["ref_check"].items()),
           ]
    if summary["walltime"]:
        w = summary["walltime"]
        md.append(f"- wall time per fit (4 in parallel, shared machine): {w['min_s']:.1f}-{w['max_s']:.1f} s, mean {w['mean_s']:.1f} s over {w['n']} fits")
    with open(os.path.join(HERE, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    with open(os.path.join(HERE, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
