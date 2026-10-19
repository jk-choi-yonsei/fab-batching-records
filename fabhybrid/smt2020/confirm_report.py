"""The numbers of the confirmatory block, computed from the run files and written once.

Reads the run JSONs of experiments/smt2020/final/confirm/PROTOCOL_confirm.md (13 policies x 2
scenarios x 32 seeds, plus the HVLM records-price row) and writes one results JSON. Every number
the paper's tables, figures and text quote comes from that file; confirm_tables.py renders it.

  python confirm_report.py                    # the block: final/confirm/report, seeds 64-95, the file
                                              # tags of jobs/confirm_report.txt -> final/confirm/results.json
  python confirm_report.py --dev --out X.json # the development record: final/report, seeds 0-31, the
                                              # closest development tags (other prices: HVLM 0.02, LVHM 0.01)
  python confirm_report.py --dev --block-tables --out X.json
                                              # the same runs, but the facts of the fitted tables (records,
                                              # tables: maps, cells, agreement) read from the block's own
                                              # artefacts, which do not depend on any run
  python confirm_report.py --agree-dumps      # also recompute the agreement with the learner from the
                                              # logged decisions themselves (table_agree.py's way)

A run that is missing is left out, never an error: n is reported for every policy, and every paired
statistic is computed on the seeds both policies have. While the block is still running the default
mode reads what is on disk and writes final/confirm/results_partial.json ("finished": false) instead of
results.json; it notes the read in final/confirm/interim_looks.log, because the protocol declares no
interim looks and asks that deviations are kept with the results.

Tests are the protocol's: completed lots per day paired by seed, the 95% paired-t interval with the
exact Student quantile for the n of the comparison, the exact two-sided sign test with ties dropped,
Holm within the two declared families of three. The helpers follow final_report.py (archive/2026-10-closed-lines/stage-b-report; load, summary,
paired, sign_p); nothing is imported from it.

Layout of the results file: "meta", then one block per scenario ("HVLM", "LVHM") with
  seeds        the seeds of the block, in order
  policies     {name: n, completed, sd, scrapped, scrapped_furnace, scrapped_other, cycle_p50_days,
                underfull_per_day, role, label, tag, per_seed{completed, ...}} for learner (the learned
                table), resid, tbl_timeout, tbl_mbs, tbl_nach, logging, clock, mbs, timeout, nach, default,
                bc, ppo and, on HVLM, sens. underfull_per_day is the protocol's count over days 87-360;
                scrapped_furnace and scrapped_other are the lots scrapped per day of that window while
                waiting for a batch tool and for any other tool. BC and PPO have only
                underfull_per_day_run, the count over the whole run, and no scrap location, because
                eval_batch.py writes neither the window count nor where a lot is scrapped.
  comparisons  {"A-B": n, mean, lo, hi, wins, losses, ties, p_sign, p_holm, pct, per_seed[...],
                secondary{scrapped, cycle_p50_days, underfull_per_day}}, A minus B in completed lots per
                day; per_seed is aligned with seeds, null where either run is missing
  records      {timeout|mbs|nach|default: rule, table, comparison, cells_both, cells, share_decisions_own,
                agree_with_learner, fire (start = 1), own (1 = the cell's own estimate, 0 = the
                residual-only entry), fire_own, n_fired, n_waited, edges, ...}; default is the learner,
                fitted from the full-batch rule's records with 2% of the free decisions started
  tables       the same facts for every fitted table that is run (also resid and sens)
  claims       C1-C4 read as the protocol declares them
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from math import comb

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
FINAL = os.path.join(ROOT, "experiments", "smt2020", "final")
JOBS = os.path.join(ROOT, "experiments", "smt2020", "jobs")
CONFIRM = os.path.join(FINAL, "confirm")
JOBFILE = os.path.join(JOBS, "confirm_report.txt")
DONE = os.path.join(JOBS, "confirm_report.done")
FABS = ("HVLM", "LVHM")
RUN_DAYS, WARMUP_DAYS = 360, 87             # completions, scraps and loads are counted over days 87-360
WINDOW_DAYS = RUN_DAYS - WARMUP_DAYS        # 273
MARGIN = 0.25                               # non-inferiority margin of C2, completed lots per day
ALPHA = 0.05

POLICIES = ("learner", "resid", "tbl_timeout", "tbl_mbs", "tbl_nach", "logging", "clock",
            "mbs", "timeout", "nach", "default", "bc", "ppo", "sens")
SENS_FABS = ("HVLM",)                       # the records-price table is run on HVLM only
ROLE = {"default": "rule", "mbs": "rule", "nach": "rule", "timeout": "rule",     # the rules a fab runs
        "clock": "tuned",                   # control limit, its level tuned by simulation
        "bc": "trained", "ppo": "trained",  # trained in the simulator
        "learner": "learner",               # fitted from records
        "resid": "ablation", "tbl_timeout": "records", "tbl_mbs": "records", "tbl_nach": "records",
        "logging": "logging", "sens": "sensitivity"}
# every pair is "A-B" = A minus B; the first nineteen are the results schema, then the protocol's remaining
# secondary pairs (the last row of the records table, and the sensitivity row against the control limit)
# and one pair the text reads
COMPARISONS = (("learner", "mbs"), ("learner", "nach"), ("learner", "timeout"), ("learner", "clock"),
               ("learner", "resid"), ("learner", "bc"), ("learner", "ppo"), ("learner", "default"),
               ("tbl_timeout", "timeout"), ("tbl_mbs", "mbs"), ("tbl_nach", "nach"),
               ("tbl_timeout", "learner"), ("tbl_mbs", "learner"), ("tbl_nach", "learner"),
               ("tbl_timeout", "clock"), ("tbl_mbs", "clock"), ("tbl_nach", "clock"),
               ("logging", "default"), ("sens", "learner"),
               ("learner", "logging"), ("sens", "clock"),
               ("resid", "clock"))             # the same form, its level from the records against the tuned one
HOLM = {"C1": ("learner-mbs", "learner-nach", "learner-timeout"),
        "C3": ("tbl_timeout-timeout", "tbl_mbs-mbs", "tbl_nach-nach")}
# records block: key -> (the policy that made the records, the table fitted from them)
RECORDS = (("timeout", "timeout", "tbl_timeout"), ("mbs", "mbs", "tbl_mbs"), ("nach", "nach", "tbl_nach"),
           ("default", "logging", "learner"))
TABLE_POLICIES = ("learner", "resid", "tbl_timeout", "tbl_mbs", "tbl_nach", "sens")
SECONDARY = ("scrapped", "cycle_p50_days", "underfull_per_day", "scrapped_furnace")
RUN_RE = re.compile(r"^batch_fire_(HVLM|LVHM)_r[0-9.]+_d\d+_s(\d+)_(.+)_qtcr_scrap\.json$")


# ---------------------------------------------------------------- statistics

def sign_p(w, l):
    """exact two-sided sign test, ties dropped"""
    n = w + l
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)


def _betacf(a, b, x):
    """continued fraction of the incomplete beta function (modified Lentz)"""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 500):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h


def _betainc(a, b, x):
    """regularised incomplete beta function I_x(a, b)"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    p = 0.5 * _betainc(0.5 * df, 0.5, df / (df + t * t))
    return 1.0 - p if t >= 0 else p


def t_crit(n, level=0.95):
    """the exact two-sided Student quantile for n - 1 degrees of freedom (2.0395 at n = 32); scipy is not a
    dependency, so the CDF is inverted by bisection"""
    df = n - 1
    if df < 1:
        return None
    target = 1.0 - (1.0 - level) / 2.0
    lo, hi = 0.0, 1.0
    while t_cdf(hi, df) < target:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if t_cdf(mid, df) < target else (lo, mid)
    return 0.5 * (lo + hi)


def paired(a, b, seeds, key="completed", per_seed=True):
    """A - B on the seeds where both ran: mean, 95% paired-t interval, wins, losses and ties of A (A > B,
    A < B, A = B, whatever the preferred direction of the measure), sign test, and the mean as a percentage
    of B's mean on those seeds"""
    s = [x for x in seeds if x in a and x in b and a[x].get(key) is not None and b[x].get(key) is not None]
    d = np.array([a[x][key] - b[x][key] for x in s], float)
    n = len(s)
    out = {"n": n, "mean": None, "sd": None, "lo": None, "hi": None, "wins": 0, "losses": 0, "ties": 0,
           "p_sign": None, "p_holm": None, "pct": None, "t": None}
    if n:
        m = float(d.mean())
        w, l = int((d > 0).sum()), int((d < 0).sum())
        bm = float(np.mean([b[x][key] for x in s]))
        out.update(mean=m, wins=w, losses=l, ties=n - w - l, p_sign=sign_p(w, l),
                   pct=100.0 * m / bm if bm else None)
    if n > 1:
        sd = float(d.std(ddof=1))
        se = sd / math.sqrt(n)
        tc = t_crit(n)
        out.update(sd=sd, lo=m - tc * se, hi=m + tc * se, t=m / se if se > 0 else None)
    if per_seed:
        dd = dict(zip(s, d.tolist()))
        out["per_seed"] = [dd.get(x) for x in seeds]
    return out


def holm(ps, m=None):
    """Holm's adjusted p-values for one family: p~(k) = max over j <= k of min(1, (m - j + 1) p(j)) on the
    sorted p-values. A missing p-value keeps its place in the family (m stays the declared size)."""
    m = m or len(ps)
    order = sorted((i for i, p in enumerate(ps) if p is not None), key=lambda i: ps[i])
    adj, run = [None] * len(ps), 0.0
    for j, i in enumerate(order):
        run = max(run, min(1.0, (m - j) * ps[i]))
        adj[i] = run
    return adj


# ---------------------------------------------------------------- what is run, and where it is

def rel(p):
    """a path as the repository names it (absolute if it lies outside)"""
    try:
        r = os.path.relpath(p, ROOT)
    except ValueError:                      # another drive
        r = ".."
    return (os.path.abspath(p) if r.startswith("..") else r).replace("\\", "/")


def run_file(report, fab, seed, tag):
    return os.path.join(report, f"batch_fire_{fab}_r0.98_d360_s{seed}_{tag}_qtcr_scrap.json")


def _opt(cmd, name):
    m = re.search(rf"(?:^|\s){re.escape(name)}\s+(\S+)", cmd)
    return m.group(1) if m else None


def _classify(cmd, fab):
    """the policy a job line runs, read off its command"""
    if "eval_batch.py" in cmd:
        tag = _opt(cmd, "--tag")
        for kind in ("bc", "ppo"):
            if tag == f"{kind}{fab}":
                return kind, None
        raise SystemExit(f"job file: unknown network tag in: {cmd}")
    arm = _opt(cmd, "--arm") or ""
    if arm.startswith("level:"):
        theta = _opt(cmd, "--theta")
        stem = os.path.basename(theta)[:-len(".json")]
        m = re.match(rf"^{fab}_(resid|timeout|mbs\d*|nach)_b[0-9p]+_t\d+$", stem)
        if m:
            return {"resid": "resid", "timeout": "tbl_timeout", "nach": "tbl_nach"}.get(m.group(1), "tbl_mbs"), theta
        if re.match(rf"^{fab}_b[0-9p]+_t\d+rx$", stem):          # the learner is the file under collect/
            return ("learner" if os.path.basename(os.path.dirname(theta)) == "collect" else "sens"), theta
        raise SystemExit(f"job file: unknown table in: {cmd}")
    name = {"explore": "logging", "clock": "clock", "mbs": "mbs", "timeout": "timeout", "nach": "nach",
            "full": "default"}.get(arm.split(":")[0])
    if name is None:
        raise SystemExit(f"job file: unknown arm in: {cmd}")
    return name, None


def block_spec(jobfile, report, seeds):
    """The block as its job file declares it: {scenario: {policy: tag, theta, files{seed: path}}}. The file
    tags and the deployed tables are read from the job lines; the run files are looked for under `report`."""
    if not os.path.exists(jobfile):
        raise SystemExit(f"missing job file {jobfile}")
    spec = {fab: {} for fab in FABS}
    declared = {fab: {} for fab in FABS}
    for line in open(jobfile, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cmd, _, out = (x.strip() for x in line.partition("->"))
        m = RUN_RE.match(os.path.basename(out))
        if not m:
            raise SystemExit(f"job file: cannot read the output name of: {line}")
        fab, seed, tag = m.group(1), int(m.group(2)), m.group(3)
        if _opt(cmd, "--dataset") != fab or _opt(cmd, "--seed") != str(seed):
            raise SystemExit(f"job file: the command and its output name disagree: {line}")
        name, theta = _classify(cmd, fab)
        e = spec[fab].setdefault(name, {"tag": tag, "theta": None if theta is None else os.path.normpath(os.path.join(HERE, theta))})
        if e["tag"] != tag:
            raise SystemExit(f"job file: {fab} {name} has two file tags, {e['tag']} and {tag}")
        declared[fab].setdefault(name, {})[seed] = os.path.basename(out)
    for fab in FABS:
        want = set(POLICIES) - (set() if fab in SENS_FABS else {"sens"})
        if set(spec[fab]) != want:
            raise SystemExit(f"job file: {fab} runs {sorted(spec[fab])}, the block is {sorted(want)}")
        for name, e in spec[fab].items():
            if not set(seeds) <= set(declared[fab][name]):
                raise SystemExit(f"job file: {fab} {name} has no job for seeds {sorted(set(seeds) - set(declared[fab][name]))}")
            e["files"] = {s: os.path.join(report, declared[fab][name][s]) for s in seeds}
    return spec


def dev_spec(report, seeds):
    """The closest runs of the development record (seeds 0-31): the one-period tables at the prices of that
    record (HVLM 0.02, LVHM 0.01), the residual-only table of its three-period fit, the rules, the control
    limit, BC and PPO as in the block. The records-price row was not run on these seeds."""
    C = os.path.join(FINAL, "collect")
    spec = {}
    for fab, b in (("HVLM", "b0p02"), ("LVHM", "b0p01")):
        tables = {"learner": f"{fab}_{b}_t1rx", "resid": f"{fab}_{b}_t3rx_abl_residual",
                  "tbl_timeout": f"{fab}_norev_{b}_t1rx", "tbl_mbs": f"{fab}_mbs3_{b}_t1rx",
                  "tbl_nach": f"{fab}_nach_{b}_t1rx"}
        rules = {"logging": "explore0.02", "clock": "clock1.5", "mbs": "mbs3", "timeout": "timeout1",
                 "nach": "nach", "default": "full", "bc": f"rl-bc{fab}", "ppo": f"rl-ppo{fab}"}
        spec[fab] = {k: {"tag": f"level1_{v}", "theta": os.path.join(C, v + ".json")} for k, v in tables.items()}
        spec[fab].update({k: {"tag": v, "theta": None} for k, v in rules.items()})
        if fab in SENS_FABS:
            spec[fab]["sens"] = {"tag": None, "theta": None}
        for e in spec[fab].values():
            e["files"] = {} if e["tag"] is None else {s: run_file(report, fab, s, e["tag"]) for s in seeds}
    return spec


def load(files, fab, problems):
    """{seed: the run's numbers} for the run files that exist (as final_report.load, one policy)"""
    out = {}
    for seed, p in files.items():
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                j = json.load(f)
            k = j["scrap_kpi"]
            ok = (int(j["seed"]) == seed and j["dataset"] == fab and int(j["days"]) == RUN_DAYS
                  and abs(float(j["scale"]) - 0.98) < 1e-9 and j.get("cqt_rule") == "qtcr" and bool(j.get("scrap"))
                  and abs(float(j["warmup_days"]) - WARMUP_DAYS) < 0.05)
        except (ValueError, KeyError, TypeError, OSError) as e:      # e.g. a file caught while it is written
            problems.append(f"unreadable, treated as missing: {rel(p)} ({type(e).__name__})")
            continue
        if not ok:
            problems.append(f"not the block's configuration, left out: {rel(p)}")
            continue
        pw, pr = j.get("batches_partial_all"), j.get("batches_partial")
        blk = j.get("blocking") or {}
        df, do = blk.get("batch_deaths"), blk.get("nonbatch_deaths")
        out[seed] = {"completed": k["completed_per_day"], "scrapped": k["scrapped_per_day"],
                     # lots scrapped in days 87-360 while they waited for a batch tool, and for any other
                     # tool, per day of that window (batch_fire.py's own ledger; eval_batch.py has none)
                     "scrapped_furnace": None if df is None else df / WINDOW_DAYS,
                     "scrapped_other": None if do is None else do / WINDOW_DAYS,
                     "cycle_p50_days": k.get("cycle_p50_days"),
                     # under-full loads started in days 87-360 per day of that window (the protocol's measure;
                     # eval_batch.py, which runs BC and PPO, does not write the window count)
                     "underfull_per_day": None if pw is None else pw / WINDOW_DAYS,
                     # the decision loop's count over all 360 days: per day of the run, and over 273 as the
                     # development tables printed it
                     "underfull_per_day_run": None if pr is None else pr / RUN_DAYS,
                     "underfull_per_day_dev": None if pr is None else pr / WINDOW_DAYS}
    return out


def _mean(v, seeds, key):
    x = [v[s][key] for s in seeds if v[s].get(key) is not None]
    return float(np.mean(x)) if x else None


def summary(v, seeds, role, label, tag):
    """one policy over its seeds (as final_report.summary), with the per-seed values aligned with `seeds`"""
    s = [x for x in seeds if x in v]
    c = np.array([v[x]["completed"] for x in s], float)
    out = {"n": len(s), "completed": float(c.mean()) if len(s) else None,
           "sd": float(c.std(ddof=1)) if len(s) > 1 else None,
           "scrapped": _mean(v, s, "scrapped"), "scrapped_furnace": _mean(v, s, "scrapped_furnace"),
           "scrapped_other": _mean(v, s, "scrapped_other"), "cycle_p50_days": _mean(v, s, "cycle_p50_days"),
           "underfull_per_day": _mean(v, s, "underfull_per_day"),
           "underfull_per_day_run": _mean(v, s, "underfull_per_day_run"),
           "underfull_per_day_dev": _mean(v, s, "underfull_per_day_dev"),
           "role": role, "label": label, "tag": tag, "seeds_missing": [x for x in seeds if x not in v]}
    out["per_seed"] = {k: [v[x].get(k) if x in v else None for x in seeds]
                       for k in ("completed", "scrapped", "scrapped_furnace", "scrapped_other", "cycle_p50_days",
                                 "underfull_per_day", "underfull_per_day_run")}
    return out


def _num(tag, prefix):
    return tag[len(prefix):] if tag and tag.startswith(prefix) else "?"


def labels(spec_fab, lam):
    """display names (plain text with $...$ for symbols, readable by matplotlib and LaTeX alike); the
    parameters are read from the file tags and the price from the fitted tables"""
    eps = _num(spec_fab["logging"]["tag"], "explore")
    pct = f"{100 * float(eps):g}%" if eps != "?" else "?"
    return {"learner": f"table from the full-batch rule's records, {pct} started",
            "resid": "residual-only table from the same records",
            "tbl_timeout": "table from the timeout rule's records",
            "tbl_mbs": "table from the minimum-batch-size rule's records",
            "tbl_nach": "table from NACH's records",
            "logging": f"full batch, {pct} started",
            "clock": f"control limit, $h = {_num(spec_fab['clock']['tag'], 'clock')}$ h",
            "mbs": f"minimum batch size, $q = {_num(spec_fab['mbs']['tag'], 'mbs')}$",
            "timeout": f"timeout, $T = {_num(spec_fab['timeout']['tag'], 'timeout')}$ h",
            "nach": "NACH", "default": "full batch",
            "bc": "behaviour cloning", "ppo": "proximal policy optimisation",
            "sens": "table at the records' price" + (f", $\\beta = {lam.get('sens'):g}$" if lam.get("sens") else "")}


# ---------------------------------------------------------------- the fitted tables

def table_facts(path):
    """What a fitted table says, read off its artefact: the start map over (residual, arrival), which cells
    are the cell's own estimate, the level per arrival bin where a column is a control limit."""
    with open(path, "rb") as f:
        raw = f.read()
    T = json.loads(raw)
    fire = np.array(T["fire"], int)
    if fire.ndim != 3 or fire.shape[2] != 1:
        raise SystemExit(f"{rel(path)}: the table has a fill axis; the study's tables fold it")
    fire = fire[:, :, 0]
    nf, nw = np.array(T["n_fired"], float)[:, :, 0], np.array(T["n_waited"], float)[:, :, 0]
    k0 = float(T.get("K0", 10.0))
    both = (nf >= k0) & (nw >= k0)                        # each action logged at least n0 times in the cell
    own = np.array(T["own_entry"], int)[:, :, 0] if "own_entry" in T else np.ones_like(fire)
    fire_own = np.array(T["fire_own"], int)[:, :, 0] if "fire_own" in T else fire
    if T.get("backoff") and not np.array_equal(own.astype(bool), both):
        raise SystemExit(f"{rel(path)}: own_entry is not the cells with {k0:g} records of each action")
    te = T["edges"]["tightest"]

    def level(col):                                       # 1...1 0...0 over the residual bins is a control limit
        f = [int(x) for x in col]
        k = sum(f)
        return te[k] if f == [1] * k + [0] * (len(f) - k) else None

    nT, nN = fire.shape
    down = sum(int(fire[i, j] < fire[i + 1, j]) for i in range(nT - 1) for j in range(nN))    # closed downward in the residual
    later = sum(int(fire[i, j + 1] < fire[i, j]) for i in range(nT) for j in range(nN - 1))   # not shrinking as the arrival moves later
    return {"artefact": rel(path), "sha256_16": hashlib.sha256(raw).hexdigest()[:16],
            "lam": T.get("lam"), "K0": k0, "gamma_h": T.get("gamma_h"), "from_day": T.get("from_day"),
            "source": [os.path.basename(s) for s in T.get("source", [])], "n_transitions": T.get("n_transitions"),
            "edges": {"tightest": te, "nxt": T["edges"]["nxt"]},
            "cells": int(fire.size), "cells_both": int(both.sum()),
            "share_decisions_own": float((nf + nw)[both].sum() / (nf + nw).sum()),
            "fire": fire.tolist(), "own": own.tolist(), "fire_own": fire_own.tolist(),
            "n_fired": nf.astype(int).tolist(), "n_waited": nw.astype(int).tolist(),
            "margin": np.array(T["margin"], float)[:, :, 0].tolist() if "margin" in T else None,
            "level_h_by_arrival_bin": [level(fire[:, j]) for j in range(nN)],
            "adjacent_pairs": (nT - 1) * nN + nT * (nN - 1), "monotone_violations": down + later}


def agreement(facts, ref):
    """The share of the free decisions in the learner's records at which this table takes the learner's
    action, by the learner's cell counts (final_report.records' agree_reversals_table1), and the number of
    the learner's cells in which the action differs. A residual-only table is spread over the arrival bins."""
    f, r = np.array(facts["fire"]), np.array(ref["fire"])
    if facts["edges"]["tightest"] != ref["edges"]["tightest"]:
        return None, None
    if f.shape != r.shape:
        if f.shape[1] != 1:
            return None, None
        f = np.broadcast_to(f, r.shape)
    n = np.array(ref["n_fired"], float) + np.array(ref["n_waited"], float)
    same = f == r
    return float(n[same].sum() / n.sum()), int((~same).sum())


def _cells(x, edges):
    return np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2)


def agreement_from_dumps(tables, ref_path):
    """table_agree.py's computation: every free decision of the learner's dumps (a live queue-time clock,
    load not full, from the fit's first day on) looked up in each table through the table's own edges"""
    R = json.load(open(ref_path))
    X = []
    for src in R["source"]:
        p = src if os.path.isabs(src) else os.path.normpath(os.path.join(HERE, src))
        for d in json.load(open(p))["decisions"]:
            if d["day"] < R.get("from_day", 0.0) or d["full"] or not d["clocks"]:
                continue
            tight = min(c[1] for c in d["clocks"])
            if tight >= 0.0:
                X.append((tight, d["nxt_h"]))
    X = np.array(X, float)

    def actions(path):
        T = json.load(open(path))
        e, f = T["edges"], np.asarray(T["fire"], int)
        return f[_cells(X[:, 0], e["tightest"]), _cells(X[:, 1], e["nxt"]), 0]

    r = actions(ref_path)
    return {k: float((actions(p) == r).mean()) for k, p in tables.items()}, len(X)


# ---------------------------------------------------------------- the protocol's readings

def claims(cmp):
    """C1-C4 as PROTOCOL_confirm.md declares them, per scenario. Superiority: the sign test at 0.05 (after
    Holm in C1 and C3) with the policy named first ahead. C2: non-inferiority if the lower end of the 95%
    interval is above -0.25 lots a day; then, in fixed sequence, superiority by the unadjusted sign test."""
    def sup(key, pkey):
        c = cmp.get(key)
        if not c or not c["n"] or c[pkey] is None:
            return {"n": c["n"] if c else 0, "p": None, "holds": None, "opposite": None}
        rej = c[pkey] <= ALPHA
        return {"n": c["n"], "p": c[pkey], "holds": bool(rej and c["wins"] > c["losses"]),
                "opposite": bool(rej and c["losses"] > c["wins"])}

    out = {name: {k: sup(k, "p_holm") for k in fam} for name, fam in HOLM.items()}
    c = cmp.get("learner-clock")
    if c and c["n"] > 1:
        ni = c["lo"] > -MARGIN
        rej = c["p_sign"] <= ALPHA
        out["C2"] = {"n": c["n"], "margin": MARGIN, "lo": c["lo"], "noninferior": bool(ni),
                     "at_least_as_many": bool(c["lo"] >= 0.0),
                     "more": bool(ni and rej and c["wins"] > c["losses"]),
                     "control_limit_more": bool(rej and c["losses"] > c["wins"]), "p_sign": c["p_sign"]}
    else:
        out["C2"] = {"n": c["n"] if c else 0, "margin": MARGIN, "lo": None, "noninferior": None,
                     "at_least_as_many": None, "more": None, "control_limit_more": None, "p_sign": None}
    out["C4"] = {"learner-resid": sup("learner-resid", "p_sign")}
    return {k: out[k] for k in ("C1", "C2", "C3", "C4")}


# ---------------------------------------------------------------- one scenario

def scenario(fab, spec, seeds, agree_dumps, problems):
    sp = spec[fab]
    facts = {k: table_facts(sp[k]["theta"]) for k in TABLE_POLICIES
             if k in sp and sp[k]["theta"] and os.path.exists(sp[k]["theta"])}
    lab = labels(sp, {k: f["lam"] for k, f in facts.items()})
    data = {k: load(sp[k]["files"], fab, problems) for k in POLICIES if k in sp}
    res = {"seeds": list(seeds),
           "policies": {k: summary(data[k], seeds, ROLE[k], lab[k], sp[k]["tag"]) for k in POLICIES if k in sp}}

    cmp = {}
    for a, b in COMPARISONS:
        if a in data and b in data:
            c = paired(data[a], data[b], seeds)
            c["secondary"] = {k: paired(data[a], data[b], seeds, k, per_seed=False) for k in SECONDARY}
            cmp[f"{a}-{b}"] = c
    for fam in HOLM.values():
        for key, p in zip(fam, holm([cmp[k]["p_sign"] for k in fam], len(fam))):
            cmp[key]["p_holm"] = p
    res["comparisons"] = cmp

    ref = facts.get("learner")
    for k, f in facts.items():
        f["agree_with_learner"], f["cells_differ_learner"] = agreement(f, ref) if ref else (None, None)
    if agree_dumps and ref:
        got, n = agreement_from_dumps({k: sp[k]["theta"] for k in facts}, sp["learner"]["theta"])
        for k, v in got.items():
            facts[k]["agree_with_learner_dumps"], facts[k]["n_free_decisions_dumps"] = v, n
    res["records"] = {key: {"rule": rule, "table": table, "comparison": f"{table}-{rule}", **facts[table]}
                      for key, rule, table in RECORDS if table in facts}
    res["tables"] = facts
    res["claims"] = claims(cmp)
    return res


# ---------------------------------------------------------------- output

def clean(x):
    """plain JSON: numpy scalars to Python, NaN and infinities to null"""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if math.isfinite(x) else None
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def f2(x, spec="{:.2f}"):
    return "--" if x is None else spec.format(x)


def pv(p):
    return "--" if p is None else (f"{p:.3f}" if p >= 0.001 else f"{p:.1e}")


def show(res, fab):
    P, C = res["policies"], res["comparisons"]
    print(f"\n================ {fab}: completed lots per day over days 87-360, seeds "
          f"{res['seeds'][0]}-{res['seeds'][-1]} ================")
    print(f"  {'policy':12s} {'n':>3s} {'compl':>7s} {'sd':>5s} {'scrap':>6s} {'furn':>6s} {'other':>6s} {'under':>6s} {'cycle':>6s}  label")
    for k, p in P.items():
        uf = p["underfull_per_day"]
        run = p["underfull_per_day_run"]
        ufs = f2(uf, "{:.1f}") if uf is not None or run is None else f2(run, "{:.1f}") + "*"
        print(f"  {k:12s} {p['n']:3d} {f2(p['completed']):>7s} {f2(p['sd']):>5s} {f2(p['scrapped']):>6s} "
              f"{f2(p['scrapped_furnace']):>6s} {f2(p['scrapped_other']):>6s} "
              f"{ufs:>6s} {f2(p['cycle_p50_days']):>6s}  {p['label']}")
    print("  (* under-full loads per day over the whole run: the window count is not in the run file)")
    print(f"  {'A - B':24s} {'n':>3s} {'mean':>7s} {'95% CI':>17s} {'w/l/t':>9s} {'sign p':>8s} {'Holm p':>8s} {'%':>7s}")
    for k, c in C.items():
        ci = "--" if c["lo"] is None else f"[{c['lo']:+.2f}, {c['hi']:+.2f}]"
        print(f"  {k:24s} {c['n']:3d} {f2(c['mean'], '{:+.2f}'):>7s} {ci:>17s} "
              f"{c['wins']:3d}/{c['losses']}/{c['ties']:<2d} {pv(c['p_sign']):>8s} "
              f"{pv(c['p_holm']):>8s} {f2(c['pct'], '{:+.1f}'):>7s}")
    for key, r in res["records"].items():
        c = C.get(r["comparison"], {})
        ag = r["agree_with_learner"]
        print(f"  records of {key:8s} cells with both actions {r['cells_both']:2d}/{r['cells']}  "
              f"decisions in them {100 * r['share_decisions_own']:5.1f}%  same action as the learned table "
              f"{f2(None if ag is None else 100 * ag, '{:.1f}')}% ({r['cells_differ_learner']} cells differ)  "
              f"table - rule {f2(c.get('mean'), '{:+.2f}')}  start map {''.join('|' + ''.join(map(str, row)) for row in r['fire'])[1:]}")
    cl = res["claims"]
    print("  claims: " + "; ".join(
        [f"C1 {sum(bool(v['holds']) for v in cl['C1'].values())}/3 rules",
         f"C2 non-inferior {cl['C2']['noninferior']}, more {cl['C2']['more']}",
         f"C3 {sum(bool(v['holds']) for v in cl['C3'].values())}/3 tables",
         f"C4 {cl['C4']['learner-resid']['holds']}"]))


def step0_identity(spec):
    """PROTOCOL_confirm.md, step 0, after the block: the block's own seed-64 learner runs must equal the
    step-0 runs in every field but wall_s (make_confirm_jobs.check_step0, which compares and prints no metric)"""
    def strip(p):
        j = json.load(open(p))
        j.pop("wall_s", None)
        return {k: json.dumps(v, sort_keys=True) for k, v in j.items()}

    out = {}
    for fab in FABS:
        blk = spec[fab]["learner"]["files"].get(64)
        ref = os.path.join(CONFIRM, "step0", "a", os.path.basename(blk)) if blk else None
        try:
            out[fab] = strip(blk) == strip(ref) if blk and os.path.exists(blk) and os.path.exists(ref) else None
        except (ValueError, OSError):
            out[fab] = None
    return out


def git_head():
    try:
        r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip() or None
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dev", action="store_true", help="the development record (final/report, seeds 0-31)")
    ap.add_argument("--report-dir", default=None, help="where the run files are (default: the mode's own directory)")
    ap.add_argument("--seeds", default=None, help="first-last, e.g. 64-95 (default: the mode's own seeds)")
    ap.add_argument("--out", default=None, help="results file (default: final/confirm/results.json, or "
                                                "results_partial.json while the block runs; --dev: a file in the "
                                                "system's temporary directory)")
    ap.add_argument("--block-tables", action="store_true",
                    help="with --dev: read the facts of the fitted tables from the block's artefacts "
                         "(jobs/confirm_report.txt); the runs stay the development record's")
    ap.add_argument("--agree-dumps", action="store_true",
                    help="also compute the agreement with the learner from the logged decisions (reads the dumps)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    mode = "dev" if a.dev else "confirm"
    lo, hi = (int(x) for x in a.seeds.split("-")) if a.seeds else ((0, 31) if a.dev else (64, 95))
    seeds = list(range(lo, hi + 1))
    report = os.path.abspath(a.report_dir) if a.report_dir else os.path.join(FINAL, "report" if a.dev else os.path.join("confirm", "report"))
    spec = dev_spec(report, seeds) if a.dev else block_spec(JOBFILE, report, seeds)
    if a.block_tables:
        if not a.dev:
            raise SystemExit("--block-tables goes with --dev: the block reads its own tables anyway")
        blk = block_spec(JOBFILE, report, list(range(64, 96)))
        for fab in FABS:
            for k in TABLE_POLICIES:
                if k in spec[fab] and k in blk[fab] and blk[fab][k]["theta"]:
                    spec[fab][k]["theta"] = blk[fab][k]["theta"]
    the_block = (not a.dev) and os.path.normcase(os.path.realpath(report)) == os.path.normcase(os.path.realpath(os.path.join(CONFIRM, "report")))
    if not (a.dev or the_block or a.out):
        raise SystemExit("--report-dir is not the block's own directory: name the results file with --out")

    expected = [(fab, k, s, p) for fab in FABS for k, e in spec[fab].items() for s, p in e["files"].items()]
    present = sum(os.path.exists(p) for *_, p in expected)
    # the block has finished when its queue has written its marker (a run that failed twice stays missing)
    # or every run file is there; final/confirm/results.json is written only then
    finished = present == len(expected) or (the_block and os.path.exists(DONE)) or not the_block
    out_path = a.out or (os.path.join(tempfile.gettempdir(), "fab_confirm", "results_dev.json") if a.dev
                         else os.path.join(CONFIRM, "results.json" if finished else "results_partial.json"))
    meta = {"mode": mode, "generated": time.strftime("%Y-%m-%d %H:%M:%S"), "git_head": git_head(),
            "protocol": rel(os.path.join(CONFIRM, "PROTOCOL_confirm.md")), "report_dir": rel(report),
            "block": bool(the_block),               # true only for the block's own run files
            "seeds": [lo, hi], "window_days": WINDOW_DAYS, "run_days": RUN_DAYS,
            "interval": "95% paired t, exact Student quantile for the n of each comparison",
            "sign_test": "exact, two-sided, ties dropped", "holm_families": {k: list(v) for k, v in HOLM.items()},
            "noninferiority_margin": MARGIN,
            "runs_expected": len(expected), "runs_present": present, "finished": bool(finished),
            "complete": present == len(expected), "deviations": [], "problems": []}
    if a.dev:
        meta["notes"] = ["development record: seeds 0-31, tables fitted at the prices of that record "
                         "(HVLM 0.02, LVHM 0.01); resid is the residual-only table of the three-period fit; "
                         "the records-price row (sens) has no run on these seeds"]
        if a.block_tables:
            meta["notes"].append("the facts of the fitted tables (records, tables) are read from the block's "
                                 "artefacts; the runs are those of the development record's own tables")
    log = os.path.join(CONFIRM, "interim_looks.log")
    if the_block:
        if not finished:
            line = f"{meta['generated']} read with {present} of {len(expected)} run files on disk, before the queue finished"
            with open(log, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            print(f"NOTE: the block has not finished ({present} of {len(expected)} run files, no "
                  f"{rel(DONE)}): these are partial numbers, marked \"finished\": false.", file=sys.stderr)
        if os.path.exists(log):
            looks = [l.strip() for l in open(log, encoding="utf-8") if l.strip()]
            meta["deviations"].append(f"PROTOCOL_confirm.md declares no interim looks; the run files were read "
                                      f"{len(looks)} time(s) before the queue finished (first: {looks[0][:19]}, "
                                      f"last: {looks[-1][:19]}; {rel(log)})")
        ident = step0_identity(spec)
        meta["step0_identity"] = ident
        if any(v is False for v in ident.values()):
            meta["deviations"].append("the block's seed-64 learner run differs from step 0 on "
                                      + ", ".join(k for k, v in ident.items() if v is False)
                                      + ": the protocol reads nothing until the affected runs are redone")
            print("WARNING: " + meta["deviations"][-1], file=sys.stderr)

    out = {"meta": meta}
    for fab in FABS:
        out[fab] = scenario(fab, spec, seeds, a.agree_dumps, meta["problems"])
    meta["missing"] = {fab: {k: p["seeds_missing"] for k, p in out[fab]["policies"].items() if p["seeds_missing"]}
                       for fab in FABS}
    if finished and the_block:
        for fab in FABS:
            for k, miss in meta["missing"][fab].items():
                meta["deviations"].append(f"{fab} {k}: no run for seeds {miss}; they are dropped from every "
                                          f"comparison that involves this policy")
    for p in meta["problems"]:
        print("WARNING: " + p, file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(clean(out), f, indent=1, allow_nan=False)
    if not a.quiet:
        for fab in FABS:
            show(out[fab], fab)
    print(f"\n{mode}: {present} of {len(expected)} runs" + ("" if finished else "  [NOT FINISHED]"))
    print("wrote", out_path)
    stale = os.path.join(CONFIRM, "results_partial.json")
    if the_block and finished and os.path.exists(stale):
        print(f"note: {rel(stale)} is from before the block finished and can be deleted")


if __name__ == "__main__":
    main()
