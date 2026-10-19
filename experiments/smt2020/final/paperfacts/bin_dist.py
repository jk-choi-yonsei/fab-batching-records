"""Distribution of the two state quantities in the dispatching records, against the table's bin edges.

No simulation. For each of the eight record sets (HVLM/LVHM x timeout, mbs3, nach, full-batch 2%),
over the FREE decisions (day >= 90, load not full, at least one live clock, tightest residual >= 0)
of seeds 100 and 101:

  m_min  the tightest residual (hours) over the live clocks at the decision
  u      hours to the next announced arrival (24.0 = none announced)
  started  iff act < n_groups

Reference edges (fit_q.py): m_min 0.25/0.5/1/2/4 h, u 0.25/1/3 h; bins are [a, b) as cell() reads them.
The joint 6 x 4 counts are compared with n_fired / n_waited / own_entry of the paper's artefacts
(betarx/family/{FAB}_{KIND}_b0p003_t1.json).

  python bin_dist.py        (from fabhybrid/smt2020, or anywhere: paths are absolute from this file)
writes bin_dist.json, bin_dist.md, bin_dist.png, bin_dist_u.png beside this script.
"""
import json
import os
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.abspath(os.path.join(HERE, ".."))
COLLECT = os.path.join(FINAL, "collect")
ARTE = os.path.join(FINAL, "betarx", "family")

FABS = ("HVLM", "LVHM")
KINDS = (("timeout", "norev_p1"), ("mbs3", "mbs3_p1"), ("nach", "nach_p1"), ("learner", "p1"))
SEEDS = (100, 101)
FROM_DAY = 90.0

T_EDGES = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, np.inf]
U_EDGES = [0.0, 0.25, 1.0, 3.0, np.inf]
FINE_T = np.arange(0.0, 10.0 + 1e-9, 0.25)          # 40 bins to 10 h, plus one bin beyond
FINE_U = np.arange(0.0, 3.0 + 1e-9, 0.125)          # 24 bins to 3 h
PCTS = (25, 50, 75, 90, 99)


def cell(x, edges):
    """fit_q.cell: index of the [a, b) bin, clipped to the last bin."""
    return int(np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2))


def load_free(fab, stem):
    rows = []
    files = []
    for s in SEEDS:
        p = os.path.join(COLLECT, f"{fab}_{stem}_s{s}.json")
        files.append(p)
        D = json.load(open(p))
        for d in D["decisions"]:
            if d["day"] < FROM_DAY or d["full"] or not d["clocks"]:
                continue
            m = min(c[1] for c in d["clocks"])
            if m < 0.0:
                continue
            rows.append((m, float(d["nxt_h"]), int(d["act"] < d["n_groups"]), int(d["size"]),
                         d["step"].split("|")[0], s))
    m = np.array([r[0] for r in rows]); u = np.array([r[1] for r in rows])
    st = np.array([r[2] for r in rows]); sz = np.array([r[3] for r in rows])
    fam = np.array([r[4] for r in rows]); seed = np.array([r[5] for r in rows])
    return dict(m=m, u=u, st=st, sz=sz, fam=fam, seed=seed, files=files)


def binned(x, st, edges):
    idx = np.array([cell(v, edges) for v in x])
    nb = len(edges) - 1
    cnt = np.bincount(idx, minlength=nb).astype(int)
    srt = np.bincount(idx, weights=st, minlength=nb).astype(int)
    return idx, cnt, srt


def rate(a, b):
    return [float(x) / y if y else None for x, y in zip(a, b)]


def fine_hist(x, st, grid):
    """counts on [grid[i], grid[i+1]) plus one bin for x >= grid[-1] (np.histogram closes its last bin, so
    the beyond bin is appended to the grid and every interior bin stays half-open)."""
    b = np.append(grid, np.inf)
    cnt, _ = np.histogram(x, bins=b)
    srt, _ = np.histogram(x[st == 1], bins=b)
    assert cnt.sum() == len(x) and srt.sum() == int(st.sum())
    return cnt.astype(int).tolist(), srt.astype(int).tolist()


def analyse(fab, kind, stem):
    R = load_free(fab, stem)
    m, u, st, sz, fam = R["m"], R["u"], R["st"], R["sz"], R["fam"]
    n = len(m); ns = int(st.sum())
    out = {"files": [os.path.relpath(f, FINAL).replace("\\", "/") for f in R["files"]],
           "n_free": n, "n_start": ns, "start_rate": ns / n,
           "by_family": {f: {"n_free": int((fam == f).sum()), "n_start": int(st[fam == f].sum())}
                         for f in sorted(set(fam))},
           "by_seed": {int(s): {"n_free": int((R["seed"] == s).sum()), "n_start": int(st[R["seed"] == s].sum())}
                       for s in SEEDS}}

    # ---- 1. m_min --------------------------------------------------------------------------
    ti, tc, ts = binned(m, st, T_EDGES)
    sext = np.quantile(m, [k / 6 for k in range(1, 6)])
    fc, fs = fine_hist(m, st, FINE_T)
    out["m_min"] = {
        "ref_edges": [e if np.isfinite(e) else "inf" for e in T_EDGES],
        "ref_bins": {"count": tc.tolist(), "start": ts.tolist(), "start_rate": rate(ts, tc),
                     "share_of_free": (tc / n).tolist(), "share_of_starts": (ts / max(ns, 1)).tolist()},
        "sextiles": sext.tolist(),
        "fine_grid_0p25h": {"edges": FINE_T.tolist() + ["inf"], "count": fc, "start": fs},
        "share_lt_2h": float((m < 2.0).mean()), "share_lt_4h": float((m < 4.0).mean()),
        "share_lt_1h": float((m < 1.0).mean()), "share_lt_0p5h": float((m < 0.5).mean()),
        "starts_share_lt_2h": float((m[st == 1] < 2.0).mean()), "starts_share_lt_4h": float((m[st == 1] < 4.0).mean()),
        "percentiles": {f"p{p}": float(np.percentile(m, p)) for p in PCTS},
        "min": float(m.min()), "max": float(m.max()), "mean": float(m.mean()),
        "starts_percentiles": {f"p{p}": float(np.percentile(m[st == 1], p)) for p in PCTS},
        "starts_median": float(np.median(m[st == 1])),
        # atoms at the constraint limits (a decision at the instant a lot's clock starts) and the bands between the modes
        "atoms": {f"eq_{v:g}": int((m == float(v)).sum()) for v in (4, 8, 10)},
        "share_ranges": {lab: float(((m >= a) & (m < b)).mean()) for lab, a, b in
                         (("[3,4)", 3, 4), ("[4,4.5)", 4, 4.5), ("[4.5,7)", 4.5, 7), ("[7,8)", 7, 8), ("[8,9)", 8, 9), ("[9,10]", 9, 10.0001))},
        "starts_share_ranges": {lab: float(((m[st == 1] >= a) & (m[st == 1] < b)).mean()) for lab, a, b in
                                (("[3,4)", 3, 4), ("[4,4.5)", 4, 4.5), ("[4.5,7)", 4.5, 7), ("[7,8)", 7, 8), ("[8,9)", 8, 9), ("[9,10]", 9, 10.0001))},
    }

    # ---- 2. u ----------------------------------------------------------------------------
    ui, uc, us = binned(u, st, U_EDGES)
    lt24 = u < 24.0
    gc, gs = fine_hist(u, st, FINE_U)
    out["u"] = {
        "ref_edges": [e if np.isfinite(e) else "inf" for e in U_EDGES],
        "ref_bins": {"count": uc.tolist(), "start": us.tolist(), "start_rate": rate(us, uc),
                     "share_of_free": (uc / n).tolist(), "share_of_starts": (us / max(ns, 1)).tolist()},
        "share_u_eq_24": float((u == 24.0).mean()), "n_u_eq_24": int((u == 24.0).sum()),
        "share_3_le_u_lt_24": float(((u >= 3.0) & lt24).mean()), "n_3_le_u_lt_24": int(((u >= 3.0) & lt24).sum()),
        "share_u_gt_24": float((u > 24.0).mean()),
        "n_lt24": int(lt24.sum()), "share_lt24": float(lt24.mean()),
        "quartiles_lt24": {f"p{p}": float(np.percentile(u[lt24], p)) for p in (25, 50, 75)},
        "max_lt24": float(u[lt24].max()) if lt24.any() else None,
        "p99_lt24": float(np.percentile(u[lt24], 99)) if lt24.any() else None,
        "share_u_eq_0": float((u == 0.0).mean()),
        "start_rate_u24": float(st[u == 24.0].mean()) if (u == 24.0).any() else None,
        "start_rate_lt24": float(st[lt24].mean()) if lt24.any() else None,
        "grid_0p125h_to_3h": {"edges": FINE_U.tolist() + ["inf"], "count": gc, "start": gs},
    }

    # ---- 3. joint 6 x 4 ------------------------------------------------------------------
    T, N = len(T_EDGES) - 1, len(U_EDGES) - 1
    jc = np.zeros((T, N), int); js = np.zeros((T, N), int)
    np.add.at(jc, (ti, ui), 1); np.add.at(js, (ti, ui), st)
    jw = jc - js
    own = (np.minimum(js, jw) >= 10)
    apath = os.path.join(ARTE, f"{fab}_{kind}_b0p003_t1.json")
    A = json.load(open(apath))
    a_nf = np.array(A["n_fired"])[:, :, 0]; a_nw = np.array(A["n_waited"])[:, :, 0]
    a_own = np.array(A["own_entry"])[:, :, 0].astype(bool); a_fire = np.array(A["fire"])[:, :, 0]
    assert A["edges"]["tightest"][1:-1] == T_EDGES[1:-1] and A["edges"]["nxt"][1:-1] == U_EDGES[1:-1], apath
    out["joint"] = {
        "rows_m_min": [f"[{T_EDGES[i]:g},{T_EDGES[i+1]:g})" for i in range(T)],
        "cols_u": [f"[{U_EDGES[j]:g},{U_EDGES[j+1]:g})" for j in range(N)],
        "count": jc.tolist(), "start": js.tolist(), "wait": jw.tolist(),
        "start_rate": [[(js[i, j] / jc[i, j]) if jc[i, j] else None for j in range(N)] for i in range(T)],
        "cells_ge10_each": own.astype(int).tolist(), "n_cells_ge10_each": int(own.sum()),
        "artefact": {"path": os.path.relpath(apath, FINAL).replace("\\", "/"),
                     "n_fired": a_nf.tolist(), "n_waited": a_nw.tolist(), "own_entry": a_own.astype(int).tolist(),
                     "n_own_entry": int(a_own.sum()), "fire": a_fire.tolist(),
                     "fire_residual_only": A["fire_residual_only"],
                     "sum_n_fired": int(a_nf.sum()), "sum_n_waited": int(a_nw.sum()),
                     "own_entry_matches": bool((own == a_own).all()),
                     "own_mismatch_cells": [[int(i), int(j)] for i in range(T) for j in range(N) if own[i, j] != a_own[i, j]],
                     "n_fired_diff": (js - a_nf).tolist(), "n_waited_diff": (jw - a_nw).tolist(),
                     "abs_diff_total": int(np.abs(js - a_nf).sum() + np.abs(jw - a_nw).sum())},
        "starts_in_fire_cells_share": float(js[a_fire == 1].sum() / max(ns, 1)),
        "free_in_fire_cells_share": float(jc[a_fire == 1].sum() / n),
    }

    # ---- 4. size (the load the rule sees) ------------------------------------------------
    sizes = sorted(set(sz.tolist()))
    sc = {int(s): int((sz == s).sum()) for s in sizes}
    ss = {int(s): int(st[sz == s].sum()) for s in sizes}
    by_bin = {}
    for i in range(T):
        sel = ti == i
        by_bin[f"[{T_EDGES[i]:g},{T_EDGES[i+1]:g})"] = {
            int(s): {"n": int((sel & (sz == s)).sum()), "start": int(st[sel & (sz == s)].sum())} for s in sizes}
    out["size"] = {"count": sc, "start": ss, "start_rate": {s: (ss[s] / sc[s]) if sc[s] else None for s in sc},
                   "share_size_ge3": float((sz >= 3).mean()), "start_rate_size_ge3": float(st[sz >= 3].mean()) if (sz >= 3).any() else None,
                   "start_rate_size_lt3": float(st[sz < 3].mean()) if (sz < 3).any() else None,
                   "by_m_min_bin": by_bin}
    return out, R


def fmt_bins(labels, cnt, srt, n, ns):
    lines = ["| bin | free | share | starts | start rate | share of starts |", "|---|---:|---:|---:|---:|---:|"]
    for lab, c, s in zip(labels, cnt, srt):
        lines.append(f"| {lab} | {c:,} | {100*c/n:.1f}% | {s:,} | {100*s/c if c else float('nan'):.1f}% | {100*s/max(ns,1):.1f}% |")
    return lines


def write_md(res, path):
    L = ["# Distribution of m_min and u in the records against the bin edges", "",
         "Free decisions of days >= 90, seeds 100 and 101, per record set (fab x rule). m_min = tightest live residual (h), "
         "u = hours to the next announced arrival (24.0 = none announced). Started iff act < n_groups. "
         "Bins are [a, b) as fit_q.cell reads them; the last u bin [3, inf) holds u = 24.0.", "",
         "Reference edges: m_min 0.25 / 0.5 / 1 / 2 / 4 h; u 0.25 / 1 / 3 h.", ""]
    for key, o in res.items():
        n, ns = o["n_free"], o["n_start"]
        L += [f"## {key}", "",
              f"Files: {', '.join(o['files'])}. Free decisions {n:,}, started {ns:,} ({100*ns/n:.2f}%). "
              + "; ".join(f"{f}: {v['n_free']:,}/{v['n_start']:,}" for f, v in o["by_family"].items()), ""]
        mm = o["m_min"]
        labs = [f"[{a:g},{b:g})" if np.isfinite(b) else f"[{a:g},inf)" for a, b in zip(T_EDGES[:-1], T_EDGES[1:])]
        L += ["### m_min (tightest residual)", ""] + fmt_bins(labs, mm["ref_bins"]["count"], mm["ref_bins"]["start"], n, ns)
        L += ["", f"Sextiles (edges a six-bin quantile binning would use): {', '.join(f'{x:.3f}' for x in mm['sextiles'])} h.",
              f"Percentiles of m_min: " + ", ".join(f"p{p} {mm['percentiles'][f'p{p}']:.3f}" for p in PCTS)
              + f"; min {mm['min']:.3f}, max {mm['max']:.3f}, mean {mm['mean']:.3f} h.",
              f"Share with m_min < 0.5 h {100*mm['share_lt_0p5h']:.1f}%, < 1 h {100*mm['share_lt_1h']:.1f}%, < 2 h {100*mm['share_lt_2h']:.1f}%, < 4 h {100*mm['share_lt_4h']:.1f}%.",
              f"Among starts: median m_min {mm['starts_median']:.3f} h; share of starts with m_min < 2 h {100*mm['starts_share_lt_2h']:.1f}%, < 4 h {100*mm['starts_share_lt_4h']:.1f}%.",
              "Atoms at the limits (m_min exactly 4, 8, 10 h): " + ", ".join(f"{k[3:]} h: {v:,}" for k, v in mm["atoms"].items())
              + ". Share of free decisions / of starts by band: " + "; ".join(f"{k} {100*v:.1f}% / {100*mm['starts_share_ranges'][k]:.1f}%" for k, v in mm["share_ranges"].items()) + ".", ""]
        fg = mm["fine_grid_0p25h"]
        L += ["Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts", "", "| from (h) | free | starts |", "|---:|---:|---:|"]
        for e, c, s in zip(fg["edges"][:-1], fg["count"], fg["start"]):
            L.append(f"| {e} | {c:,} | {s:,} |")
        L.append("")
        uu = o["u"]
        labs_u = [f"[{a:g},{b:g})" if np.isfinite(b) else f"[{a:g},inf)" for a, b in zip(U_EDGES[:-1], U_EDGES[1:])]
        L += ["### u (time to the next announced arrival)", ""] + fmt_bins(labs_u, uu["ref_bins"]["count"], uu["ref_bins"]["start"], n, ns)
        L += ["", f"u = 24.0 (none announced): {uu['n_u_eq_24']:,} ({100*uu['share_u_eq_24']:.1f}%), start rate there {100*(uu['start_rate_u24'] or 0):.2f}%; "
              f"3 <= u < 24: {uu['n_3_le_u_lt_24']:,} ({100*uu['share_3_le_u_lt_24']:.2f}%); u < 24: {uu['n_lt24']:,} ({100*uu['share_lt24']:.1f}%), start rate there {100*(uu['start_rate_lt24'] or 0):.2f}%.",
              f"Quartiles of u among u < 24: p25 {uu['quartiles_lt24']['p25']:.3f}, p50 {uu['quartiles_lt24']['p50']:.3f}, p75 {uu['quartiles_lt24']['p75']:.3f} h; p99 {uu['p99_lt24']:.3f}; max below 24: {uu['max_lt24']:.3f} h. Share with u = 0 exactly: {100*uu['share_u_eq_0']:.2f}%.", ""]
        g = uu["grid_0p125h_to_3h"]
        L += ["0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts", "", "| from (h) | free | starts |", "|---:|---:|---:|"]
        for e, c, s in zip(g["edges"][:-1], g["count"], g["start"]):
            L.append(f"| {e} | {c:,} | {s:,} |")
        L.append("")
        J = o["joint"]; A = J["artefact"]
        L += ["### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10", ""]
        L += ["| m_min \\ u | " + " | ".join(J["cols_u"]) + " |", "|---|" + "---:|" * len(J["cols_u"])]
        for i, r in enumerate(J["rows_m_min"]):
            L.append(f"| {r} | " + " | ".join(f"{J['count'][i][j]:,} / {J['start'][i][j]:,}" + ("" if J['cells_ge10_each'][i][j] else " (thin)") for j in range(len(J["cols_u"]))) + " |")
        L += ["", f"Cells with >= 10 of each action: {J['n_cells_ge10_each']} of 24; artefact own_entry: {A['n_own_entry']} of 24 "
              f"({'match' if A['own_entry_matches'] else 'MISMATCH at ' + str(A['own_mismatch_cells'])}). "
              f"Artefact {A['path']}: sum n_fired {A['sum_n_fired']:,}, n_waited {A['sum_n_waited']:,}; total absolute difference from the record counts {A['abs_diff_total']} decisions (chain ends dropped by fit_q.chains).",
              f"Artefact fire table (1 = start): " + str(A["fire"]) + f"; residual-only back-off {A['fire_residual_only']}. "
              f"Share of the rule's starts that lie in the table's start cells: {100*J['starts_in_fire_cells_share']:.1f}%; share of free decisions in those cells: {100*J['free_in_fire_cells_share']:.1f}%.", ""]
        S = o["size"]
        L += ["### Load size at free decisions", "", "| size | free | starts | start rate |", "|---:|---:|---:|---:|"]
        for s in sorted(S["count"], key=int):
            c, st_ = S["count"][s], S["start"][s]
            L.append(f"| {s} | {c:,} | {st_:,} | {100*st_/c if c else float('nan'):.1f}% |")
        L += ["", f"Share with size >= 3: {100*S['share_size_ge3']:.1f}%; start rate at size >= 3 {100*(S['start_rate_size_ge3'] or 0):.2f}%, at size < 3 {100*(S['start_rate_size_lt3'] or 0):.2f}%.", ""]
        L += ["Start rate by size within each m_min bin (n in parentheses):", "", "| m_min bin | " + " | ".join(f"size {s}" for s in sorted(S["count"], key=int)) + " |",
              "|---|" + "---:|" * len(S["count"])]
        for b, row in S["by_m_min_bin"].items():
            L.append(f"| {b} | " + " | ".join((f"{100*row[s]['start']/row[s]['n']:.0f}% ({row[s]['n']:,})" if row[s]["n"] else "-") for s in sorted(row, key=int)) + " |")
        L.append("")
    open(path, "w", encoding="utf-8").write("\n".join(L))


def plot_m(res, data, path):
    fig, axes = plt.subplots(2, 4, figsize=(18, 7.6), sharey=False)
    keys = list(res.keys())
    for ax, key in zip(axes.ravel(), keys):
        m, st = data[key]["m"], data[key]["st"]
        bins = np.append(FINE_T, 10.25)                       # 41 bins: the last holds m >= 10
        mm = np.minimum(m, 10.1)
        ax.hist(mm, bins=bins, color="#2a78d6", alpha=0.85, label="free decisions", linewidth=0)
        ax.hist(mm[st == 1], bins=bins, color="#eb6834", alpha=0.95, label="starts", linewidth=0)
        for e in T_EDGES[1:-1]:
            ax.axvline(e, color="#0b0b0b", lw=0.9)
        for q in res[key]["m_min"]["sextiles"]:
            ax.axvline(q, color="#52514e", lw=0.9, ls="--")
        ax.set_yscale("log"); ax.set_xlim(0, 10.25)
        n, ns = res[key]["n_free"], res[key]["n_start"]
        ax.set_title(f"{key.replace('_', ' ')}\n{n:,} free, {ns:,} started", fontsize=9)
        ax.set_xlabel("m_min, tightest residual (h)", fontsize=8); ax.tick_params(labelsize=8)
        ax.grid(axis="y", color="#e5e4df", lw=0.6); ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0, 0].set_ylabel("decisions per 0.25 h (log)", fontsize=8); axes[1, 0].set_ylabel("decisions per 0.25 h (log)", fontsize=8)
    axes[0, 0].legend(fontsize=7, loc="lower left", frameon=False)
    fig.suptitle("Tightest residual at free decisions, days 90-181, seeds 100-101. Solid lines: reference edges 0.25/0.5/1/2/4 h; "
                 "dashed: empirical sextiles. Last bar: m_min >= 10 h", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=150); plt.close(fig)


def plot_u(res, data, path):
    fig, axes = plt.subplots(2, 4, figsize=(18, 7.6))
    for ax, key in zip(axes.ravel(), res.keys()):
        u, st = data[key]["u"], data[key]["st"]
        sel = u < 3.0
        ax.hist(u[sel], bins=FINE_U, color="#2a78d6", alpha=0.85, label="free decisions", linewidth=0)
        ax.hist(u[sel & (st == 1)], bins=FINE_U, color="#eb6834", alpha=0.95, label="starts", linewidth=0)
        for e in U_EDGES[1:-1]:
            if e < 3.0:
                ax.axvline(e, color="#0b0b0b", lw=0.9)
        ax.set_yscale("log"); ax.set_xlim(0, 3.0)
        ax.set_title(key.replace("_", " "), fontsize=10)
        ax.set_xlabel("u, hours to the next announced arrival", fontsize=8); ax.tick_params(labelsize=8)
        ax.grid(axis="y", color="#e5e4df", lw=0.6); ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        uu = res[key]["u"]
        ax.text(0.98, 0.95, f"u = 24 (none): {100*uu['share_u_eq_24']:.1f}%\n3 <= u < 24: {100*uu['share_3_le_u_lt_24']:.2f}%\n"
                f"u < 3: {100*(1-uu['share_u_eq_24']-uu['share_3_le_u_lt_24']):.1f}%\nmax u < 24: {uu['max_lt24']:.2f} h",
                transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#52514e")
    axes[0, 0].set_ylabel("decisions per 0.125 h (log)", fontsize=8); axes[1, 0].set_ylabel("decisions per 0.125 h (log)", fontsize=8)
    axes[0, 0].legend(fontsize=7, loc="lower left", frameon=False)
    fig.suptitle("Time to the next announced arrival at free decisions, u < 3 h shown (edges 0.25 and 1 h; the bin [3, inf) holds 'none announced')", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=150); plt.close(fig)


def main():
    res, data = {}, {}
    for fab in FABS:
        for kind, stem in KINDS:
            key = f"{fab}_{kind}"
            out, R = analyse(fab, kind, stem)
            res[key] = out; data[key] = R
            J = out["joint"]["artefact"]
            print(f"{key:14s} free {out['n_free']:7,} started {out['n_start']:6,} ({100*out['start_rate']:.2f}%)  "
                  f"m_min p50 {out['m_min']['percentiles']['p50']:.2f} max {out['m_min']['max']:.2f}  sextiles {['%.2f' % x for x in out['m_min']['sextiles']]}  "
                  f"u=24 {100*out['u']['share_u_eq_24']:.1f}%  own cells {out['joint']['n_cells_ge10_each']} vs artefact {J['n_own_entry']} "
                  f"({'ok' if J['own_entry_matches'] else 'MISMATCH ' + str(J['own_mismatch_cells'])}), count diff {J['abs_diff_total']}")
    meta = {"definition": "free decision: day >= 90, not full, clocks non-empty, min residual >= 0; m_min = min residual over clocks; u = nxt_h; started iff act < n_groups",
            "ref_edges": {"m_min": [0.25, 0.5, 1.0, 2.0, 4.0], "u": [0.25, 1.0, 3.0]},
            "seeds": list(SEEDS), "from_day": FROM_DAY, "kind_to_stem": dict(KINDS), "artefacts": "betarx/family/{FAB}_{KIND}_b0p003_t1.json"}
    json.dump({"meta": meta, "sets": res}, open(os.path.join(HERE, "bin_dist.json"), "w"), indent=1)
    write_md(res, os.path.join(HERE, "bin_dist.md"))
    plot_m(res, data, os.path.join(HERE, "bin_dist.png"))
    plot_u(res, data, os.path.join(HERE, "bin_dist_u.png"))
    print("wrote bin_dist.json / .md / .png / _u.png in", HERE)


if __name__ == "__main__":
    main()
