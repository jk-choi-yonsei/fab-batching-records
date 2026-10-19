"""The numbers of the shift block, computed from its run files: the release rate moved from 0.98 to 0.90,
0.80 and (if the line stays stable) 1.05 (experiments/smt2020/final/shift/PROTOCOL_shift.md).

  python -B shift_report.py                 # final/shift -> final/shift/results.json once the block has
                                            # finished, before that final/shift_report_dev/results_partial.json
  python -B shift_report.py --out X.json    # any results file (refused, exit 2, under final/shift while the
                                            # block runs)
  python -B shift_report.py --tex           # also paper/tables/shift.tex (only from the finished block;
                                            # otherwise name the file with --tex-out)

It only reads. It never calls the parts of make_shift_jobs.py that write (stage_b, check_step0, gate_high,
prelaunch, write_all) and imports no simulator module. Run it with -B: the block's chain imports from this
folder, and stale bytecode in a synced folder once changed a trajectory.

Every file name comes from make_shift_jobs.py. A run that is missing is left out, never an error; a run that
is unreadable or not the block's configuration (dataset, seed, 360 days, the rate, qtcr, scrap, the 87-day
warm-up, the arm and, for a table, the deployed artefact by name and by its start map) is listed in
meta.problems and left out. Every paired statistic is computed on the seeds both policies have, with n against
the 32 seeds. The tests are those of confirm_report.py: completed lots per day paired by seed, the 95%
paired-t interval with the exact Student quantile, the exact two-sided sign test with ties dropped.
PROTOCOL_shift.md declares no families, so no p-value is adjusted, and no thresholds for its predictions: the
"checks" of each reading are this script's operationalisation, labelled as such in the results file.

Layout of the results file: "meta"; "reference_0p98", the confirmatory block's numbers at 0.98 (from
final/confirm/results.json); "rates": {"0.9" | "0.8" | "1.05": status, stage, the queue markers, the
selection file, the probe (1.05) and, per scenario,
  policies     every policy run at that rate in the layout of the policies table (Table 3): n, completed,
               scrapped at furnaces and elsewhere, under-full loads per day, cycle time, per_seed{...}
  comparisons  {"A-B": n, mean, lo, hi, wins, losses, ties, p_sign, pct, per_seed[...], secondary{...},
               reading, declared, n_expected, complete}, A minus B in completed lots per day
  selection    the threshold grid on seeds 108-115 and the retuned threshold h*
  tables       the facts of the stale (0.98) and refitted tables (confirm_report.table_facts)
  records      per rule: the new records, and how the refitted table differs from the 0.98 one
  readings     R1-R6 and cells, as PROTOCOL_shift.md declares them}.
"""
import sys

sys.dont_write_bytecode = True      # the block's chain imports from this folder: leave no bytecode beside it

import argparse                     # noqa: E402
import json                         # noqa: E402
import os                           # noqa: E402
import re                           # noqa: E402
import time                         # noqa: E402

import numpy as np                  # noqa: E402

from make_shift_jobs import (FABS, RULES, REPORT_SEEDS, SELECT_SEEDS, RECORD_SEEDS, THETAS, RATES, HIGH,  # noqa: E402
                             SLOPE_MAX, STEP0_SEED, S as SHIFT_REL, rname, rtag, rule_run, table_run, out_of,
                             stale, refit, dump, local)
from make_confirm_jobs import PINNED, strip                                                             # noqa: E402
from confirm_report import (paired, summary, table_facts, agreement, clean, rel, git_head,             # noqa: E402
                            WINDOW_DAYS, RUN_DAYS, WARMUP_DAYS, MARGIN, ALPHA)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
FINAL = os.path.join(ROOT, "experiments", "smt2020", "final")
SHIFT = os.path.join(FINAL, "shift")
FAMILY = os.path.join(FINAL, "betarx", "family")
JOBS = os.path.join(ROOT, "experiments", "smt2020", "jobs")
REFERENCE = os.path.join(FINAL, "confirm", "results.json")
TEX = os.path.join(ROOT, "paper", "tables", "shift.tex")
ALL_RATES = list(RATES) + [HIGH]
NOMINAL = 0.98                      # the rate at which every table and parameter of the paper was fitted
KEY = {"timeout": "timeout", "mbs3": "mbs", "nach": "nach"}         # a rule's file tag -> its policy key
RK = tuple(KEY[t] for t, _ in RULES)                                  # ("timeout", "mbs", "nach")
LABEL = {"timeout": "timeout", "mbs": "minimum batch size", "nach": "NACH"}
OWN = {"timeout": "the timeout rule's records", "mbs": "the minimum-batch-size rule's records",
       "nach": "NACH's records"}
GROUPS = (("Rules", ("timeout", "mbs", "nach")),
          ("Threshold tuned in the simulator (at 0.98)", ("clock",)),
          ("Threshold retuned at the rate", ("clock_rt",)),
          ("Table fitted at 0.98", ("tbl_timeout", "tbl_mbs", "tbl_nach")),
          ("Table refitted at the rate", ("rft_timeout", "rft_mbs", "rft_nach")))
SECONDARY = ("scrapped", "scrapped_furnace", "scrapped_other", "underfull_per_day", "cycle_p50_days")
STATS = ("n", "n_expected", "complete", "mean", "sd", "lo", "hi", "wins", "losses", "ties", "p_sign", "pct")
PIN = {os.path.basename(k): v for k, v in PINNED.items()}          # artefact name -> first 16 hex of its SHA-256
EQUAL = "retuned threshold is 1.5 h"
PENDING = "no selection yet"
CHANGE = ("cells_differ", "fire_gained", "fire_lost", "direction", "level_new", "level_old", "level_shift",
          "agree_old_on_new_records", "agree_new_on_old_records")
PREDICTION = {
    "R1": "Positive on most seeds at 0.90 and 0.80, since the rule's parameter is as stale as the table, but by "
          "less than at 0.98.",
    "R2": "Positive on every seed, by at least the 0.98 margin.",
    "R3": "Positive where R1 fell short of the 0.98 margin.",
    "R4": "The timeout and minimum-batch-size tables at least as good as the retuned control limit, as at 0.98.",
    "R5": "At the lower rates the threshold rises (an under-full run costs less capacity, and a load takes longer "
          "to fill), and the refitted tables start earlier in the same way; the direction of the change is read "
          "off the tables' entries.",
    "R6": "Control limits on the residual whose thresholds do not fall with the time to the next arrival, and the "
          "number of entries that differ from the 0.98 tables.",
    "cells": "Cells with both actions at least n0 times in the new records, per rule."}
OPERATIONALISED = {
    "R1": "this script's reading: positive_on_most_seeds = wins > n/2; smaller_than_0p98_mean (_pct) = the mean "
          "(the % of the rule) below that of tbl_X-X at 0.98 in final/confirm/results.json",
    "R2": "this script's reading: positive_on_every_seed = wins == n > 0; at_least_0p98_mean (_pct) = the mean "
          "(the %) at least that of tbl_X-X at 0.98",
    "R3": "this script's reading: r1_short_of_0p98_pct = R1's % below the 0.98 %, the condition under which the "
          "prediction applies; positive_mean = mean > 0; positive_sign_0p05 = exact sign test p <= 0.05 with "
          "more wins than losses",
    "R4": "this script's reading: 'at least as good' three ways, none chosen: mean_nonnegative (mean >= 0), "
          "noninferior_0p25 (lower end of the 95% interval above -0.25, the C2 margin of PROTOCOL_confirm.md), "
          "superior_sign_0p05 (sign test p <= 0.05, more wins than losses); timeout and mbs only, against the "
          "retuned control limit (the control limit at 1.5 h when the retuned threshold is 1.5 h)",
    "R5": "this script's reading: threshold_direction = h* against 1.5 h; a table starts earlier when it starts in "
          "cells where the 0.98 table waits and waits in none where that one starts; checks at rates below 0.98 "
          "only: threshold_rises, tables_start_earlier (all three rules), same_direction (higher with earlier, "
          "lower with later, same with same)",
    "R6": "control_limit_form = no adjacent pair of cells at which the start region is not closed downward in the "
          "residual or shrinks as the arrival moves later (confirm_report.table_facts); cells_differ_0p98 = "
          "entries of the start map that differ from the 0.98 table of the same rule",
    "cells": "cells_both = of the cells, those in which the new records hold each action at least n0 (K0) times "
             "(confirm_report.table_facts)"}


# ---------------------------------------------------------------- where things are

def same_path(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def under(p, d):
    """whether path p lies in directory d"""
    p, d = (os.path.normcase(os.path.realpath(x)) for x in (p, d))
    try:
        return os.path.commonpath([p, d]) == d
    except ValueError:                  # another drive
        return False


def paths(shift_dir=None, family_dir=None, jobs_dir=None, reference=None):
    sd = os.path.abspath(shift_dir or SHIFT)
    return {"shift": sd, **{k: os.path.join(sd, k) for k in ("report", "select", "records", "tables", "probe", "step0")},
            "family": os.path.abspath(family_dir or FAMILY), "jobs": os.path.abspath(jobs_dir or JOBS),
            "reference": os.path.abspath(reference or REFERENCE),
            "dev": os.path.join(os.path.dirname(sd), "shift_report_dev"), "block": same_path(sd, SHIFT)}


def run_name(fab, arm, rate, seed):
    return os.path.basename(out_of(rule_run(fab, arm, rate, seed, "x")))


def table_run_name(fab, theta_rel, rate, seed):
    return os.path.basename(out_of(table_run(fab, theta_rel, rate, seed, "x")))


def _tag(name, seed):
    return name.split(f"_s{seed}_", 1)[1][:-len("_qtcr_scrap.json")]


def policy_spec(rate, fab, P, selected_h, seeds=REPORT_SEEDS):
    """{key: arm, tag, theta (the artefact's path), group, role, label, files{seed: path}} for every policy run at
    this rate; clock_rt only when the retuned threshold is known and is not 1.5 h"""
    spec = {}

    def add(key, arm, theta_rel, theta, group, role, label):
        names = {s: (run_name(fab, arm, rate, s) if theta_rel is None else table_run_name(fab, theta_rel, rate, s))
                 for s in seeds}
        s0 = seeds[0]
        spec[key] = {"arm": arm, "tag": _tag(names[s0], s0), "theta": theta, "group": group, "role": role,
                     "label": label, "files": {s: os.path.join(P["report"], n) for s, n in names.items()}}

    for tag, arm in RULES:
        add(KEY[tag], arm, None, None, GROUPS[0][0], "rule", LABEL[KEY[tag]])
    add("clock", "clock:1.5", None, None, GROUPS[1][0], "tuned", "control limit, $h = 1.5$ h")
    if selected_h not in (None, "1.5"):
        add("clock_rt", f"clock:{selected_h}", None, None, GROUPS[2][0], "retuned",
            f"control limit, $h = {selected_h}$ h, retuned at {rname(rate)}")
    for tag, _ in RULES:
        k = KEY[tag]
        add(f"tbl_{k}", "level:1", stale(fab, tag), os.path.join(P["family"], os.path.basename(stale(fab, tag))),
            GROUPS[3][0], "stale", f"table from {OWN[k]}, fitted at 0.98")
    for tag, _ in RULES:
        k = KEY[tag]
        rp = refit(fab, tag, rate)
        add(f"rft_{k}", "level:1", rp, os.path.join(P["tables"], os.path.basename(rp)),
            GROUPS[4][0], "refit", f"table from {OWN[k]}, refitted at {rname(rate)}")
    return spec


def select_spec(rate, fab, P):
    return {th: {s: os.path.join(P["select"], run_name(fab, f"clock:{th}", rate, s)) for s in SELECT_SEEDS}
            for th in THETAS}


def dump_paths(fab, tag, rate, P):
    return {s: os.path.join(P["records"], os.path.basename(dump(fab, tag, rate, s))) for s in RECORD_SEEDS}


# ---------------------------------------------------------------- the run files

def load(files, fab, rate, arm, theta_name, fire, problems):
    """{seed: the run's numbers} for the files that exist and are the block's configuration (confirm_report.load
    for any rate, with the arm, the deployed table's name and its start map checked as well)"""
    out = {}
    for seed, p in files.items():
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                j = json.load(f)
            k = j["scrap_kpi"]
            th = j.get("theta")
            checks = (("dataset", j["dataset"] == fab), ("seed", int(j["seed"]) == seed),
                      ("days", int(j["days"]) == RUN_DAYS),
                      ("scale", abs(float(j["scale"]) - float(rate)) < 1e-9),
                      ("cqt_rule", j.get("cqt_rule") == "qtcr"), ("scrap", bool(j.get("scrap"))),
                      ("warmup_days", abs(float(j["warmup_days"]) - WARMUP_DAYS) < 0.05),
                      ("arm", j.get("arm") == arm),
                      ("theta", th is None if theta_name is None else
                       (th is not None and os.path.basename(th) == theta_name)),
                      ("level.fire", fire is None or (j.get("level") or {}).get("fire") == fire))
            bad = [name for name, ok in checks if not ok]
            pw, pr = j.get("batches_partial_all"), j.get("batches_partial")
            blk = j.get("blocking") or {}
            df, do = blk.get("batch_deaths"), blk.get("nonbatch_deaths")
            row = {"completed": float(k["completed_per_day"]), "scrapped": k["scrapped_per_day"],
                   # lots scrapped in days 87-360 while waiting for a batch tool, and for any other tool, per day
                   "scrapped_furnace": None if df is None else df / WINDOW_DAYS,
                   "scrapped_other": None if do is None else do / WINDOW_DAYS,
                   "cycle_p50_days": k.get("cycle_p50_days"),
                   # under-full loads started in days 87-360 per day of that window (the protocol's measure), and
                   # the decision loop's count over the whole run per day of the run
                   "underfull_per_day": None if pw is None else pw / WINDOW_DAYS,
                   "underfull_per_day_run": None if pr is None else pr / RUN_DAYS,
                   "released_per_day": j.get("released_per_day"),
                   "wip_slope_back_half": j.get("wip_slope_back_half"), "wip_end": j.get("wip_end")}
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as e:     # e.g. caught while written
            problems.append(f"unreadable, treated as missing: {rel(p)} ({type(e).__name__})")
            continue
        if bad:
            problems.append(f"not the block's configuration ({', '.join(bad)}), left out: {rel(p)}")
            continue
        out[seed] = row
    return out


def started_no_output(files):
    """seeds whose run was launched (its .err exists) and has not written its file yet"""
    return [s for s, p in files.items() if not os.path.exists(p) and os.path.exists(p + ".err")]


def crn_check(data, problems, where=""):
    """common random numbers: every policy of a seed releases the same lots"""
    by_seed = {}
    for k, v in data.items():
        for s, r in v.items():
            if r.get("released_per_day") is not None:
                by_seed.setdefault(s, {})[k] = float(r["released_per_day"])
    bad = []
    for s in sorted(by_seed):
        x = by_seed[s]
        if max(x.values()) - min(x.values()) > 1e-9:
            bad.append(s)
            problems.append(f"common random numbers broken: {where} seed {s}: released per day differs across "
                            f"policies ({', '.join(f'{k} {v:.6f}' for k, v in x.items())})")
    return bad


def _avg(v, key):
    x = [r[key] for r in v.values() if r.get(key) is not None]
    return float(np.mean(x)) if x else None


def artefact_fire(path):
    """the start map as the artefact stores it (what batch_fire.py copies into level.fire), or None"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)["fire"]
    except (ValueError, KeyError, TypeError, OSError):
        return None


# ---------------------------------------------------------------- the threshold grid

def pick(means):
    """make_shift_jobs.stage_b's rule: the highest mean, ties to the first threshold in grid order"""
    if len(means) != len(THETAS) or any(m is None for m in means):
        return None
    return THETAS[max(range(len(THETAS)), key=lambda i: (means[i], -i))]


def selection_block(rate, fab, P, problems):
    files = select_spec(rate, fab, P)
    data = {th: load(files[th], fab, rate, f"clock:{th}", None, None, problems) for th in THETAS}
    crn_check(data, problems, f"rate {rname(rate)} {fab} selection")
    grid = {}
    for th in THETAS:
        c = [data[th][s]["completed"] for s in SELECT_SEEDS if s in data[th]]
        grid[th] = {"n": len(c), "mean": sum(c) / len(c) if c else None,      # summed in seed order, as stage_b
                    "sd": float(np.std(c, ddof=1)) if len(c) > 1 else None,
                    "per_seed": [data[th][s]["completed"] if s in data[th] else None for s in SELECT_SEEDS]}
    full = all(grid[th]["n"] == len(SELECT_SEEDS) for th in THETAS)
    from_files = pick([grid[th]["mean"] for th in THETAS]) if full else None
    sel_path = os.path.join(P["select"], f"selection_{rtag(rate)}.json")
    entry = None
    if os.path.exists(sel_path):
        try:
            with open(sel_path, encoding="utf-8") as f:
                js = json.load(f)
            entry = next((e for e in js if e.get("fab") == fab and str(e.get("rate")) == rname(rate)), None)
        except (ValueError, TypeError, AttributeError, OSError) as e:
            problems.append(f"unreadable selection file: {rel(sel_path)} ({type(e).__name__})")
    sj = None if entry is None else str(entry.get("selected"))
    selected, source = ((sj, os.path.basename(sel_path)) if sj is not None else
                        (from_files, "files (provisional)") if from_files is not None else (None, None))
    agree = None if sj is None or from_files is None else sj == from_files
    grid_agree = (None if entry is None or not full else
                  all(round(grid[th]["mean"], 3) == (entry.get("grid") or {}).get(th) for th in THETAS))
    if agree is False:
        problems.append(f"rate {rname(rate)} {fab}: {os.path.basename(sel_path)} selects {sj} h, the selection runs "
                        f"select {from_files} h")
    if grid_agree is False:
        problems.append(f"rate {rname(rate)} {fab}: the grid means of {os.path.basename(sel_path)} differ from the "
                        f"selection runs")
    return {"seeds": list(SELECT_SEEDS), "grid": grid, "n_present": sum(g["n"] for g in grid.values()),
            "n_expected": len(THETAS) * len(SELECT_SEEDS),
            "started_no_output": sum(len(started_no_output(files[th])) for th in THETAS),
            "complete": full, "selected_from_files": from_files,
            "selection_json": None if entry is None else dict(entry, path=rel(sel_path)),
            "selected_h": selected, "selected_source": source, "agree": agree, "grid_agree": grid_agree}


# ---------------------------------------------------------------- the tables

def monotone_split(fire):
    """(residual, arrival): the two counts table_facts adds into monotone_violations"""
    f = np.asarray(fire, int)
    nT, nN = f.shape
    res = sum(int(f[i, j] < f[i + 1, j]) for i in range(nT - 1) for j in range(nN))
    arr = sum(int(f[i, j + 1] < f[i, j]) for i in range(nT) for j in range(nN - 1))
    return res, arr


def facts(path, problems, pinned=False, sources=None):
    """confirm_report.table_facts, None if the artefact is absent or unreadable; pinned_ok for a stale table
    (SHA-256 against PROTOCOL_confirm.md) and source_ok for a refit (fitted from the two expected dumps)"""
    if not path or not os.path.exists(path):
        return None
    try:
        f = table_facts(path)
    except (SystemExit, ValueError, KeyError, TypeError, IndexError, OSError) as e:
        problems.append(f"table not readable, left out: {rel(path)} ({type(e).__name__}: {e})")
        return None
    f["violations_residual"], f["violations_arrival"] = monotone_split(f["fire"])
    if pinned:
        want = PIN.get(os.path.basename(path))
        f["pinned_ok"] = None if want is None else f["sha256_16"] == want
        if f["pinned_ok"] is not True:
            problems.append(f"stale table {rel(path)}: sha256 {f['sha256_16']}, PROTOCOL_confirm.md records {want}")
    if sources is not None:
        f["source_ok"] = sorted(f["source"]) == sorted(sources)
        if not f["source_ok"]:
            problems.append(f"refitted table {rel(path)}: fitted from {f['source']}, expected {sorted(sources)}")
    return f


def table_change(new, old):
    """how a refitted table differs from the 0.98 table of the same rule"""
    if new is None or old is None:
        return None
    a, b = np.asarray(new["fire"], int), np.asarray(old["fire"], int)
    if a.shape != b.shape:
        return {"comparable": False}
    gained, lost = int(((a == 1) & (b == 0)).sum()), int(((a == 0) & (b == 1)).sum())
    direction = ("same" if not gained and not lost else "earlier" if not lost else "later" if not gained
                 else "mixed")
    ln, lo = new["level_h_by_arrival_bin"], old["level_h_by_arrival_bin"]
    return {"cells_differ": gained + lost, "fire_gained": gained, "fire_lost": lost, "direction": direction,
            "level_new": ln, "level_old": lo,
            "level_shift": [None if x is None or y is None else x - y for x, y in zip(ln, lo)],
            # of the free decisions in the new records, the share at which the 0.98 table takes the refit's action
            "agree_old_on_new_records": agreement(old, new)[0],
            "agree_new_on_old_records": agreement(new, old)[0]}


def reference(path, problems):
    """the 0.98 numbers of the confirmatory block, per scenario; None if the file is absent"""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            R = json.load(f)
        out = {"path": rel(path), "generated": R["meta"].get("generated"), "finished": R["meta"].get("finished")}
        for fab in FABS:
            C, Pp, T = R[fab]["comparisons"], R[fab]["policies"], R[fab].get("tables", {})
            keys = [f"tbl_{k}-{k}" for k in RK] + [f"tbl_{k}-clock" for k in RK]
            out[fab] = {
                "comparisons": {key: {f: C[key].get(f) for f in ("n", "mean", "lo", "hi", "wins", "losses", "ties",
                                                                 "pct")} for key in keys if key in C},
                "policies": {k: {f: Pp[k].get(f) for f in ("n", "completed", "scrapped_furnace", "scrapped_other",
                                                           "underfull_per_day", "cycle_p50_days")}
                             for k in RK + ("clock",) + tuple(f"tbl_{x}" for x in RK) if k in Pp},
                "cells_both": {k: T[k].get("cells_both") for k in (f"tbl_{x}" for x in RK) if k in T},
                "monotone_violations": {k: T[k].get("monotone_violations") for k in (f"tbl_{x}" for x in RK) if k in T}}
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as e:
        problems.append(f"0.98 reference not readable: {rel(path)} ({type(e).__name__})")
        return None
    return out


# ---------------------------------------------------------------- comparisons and readings

def comparisons(data, seeds, selected_h):
    """A - B in completed lots per day on the seeds both have, in the order of the readings"""
    def one(a, b, reading, declared):
        A, B = data.get(a) or {}, data.get(b) or {}
        c = paired(A, B, seeds)
        c["secondary"] = {k: paired(A, B, seeds, k, per_seed=False) for k in SECONDARY}
        c.update(reading=reading, declared=declared, n_expected=len(seeds), n_a=sum(s in A for s in seeds),
                 n_b=sum(s in B for s in seeds), complete=c["n"] == len(seeds))
        return c

    def retuned(a, b, reading, declared, same):
        if selected_h is None:
            return {"pending": PENDING, "reading": reading, "declared": declared}
        if selected_h == "1.5":
            return ({"same_as": same, "reason": EQUAL} if same else {"same_policy": True, "reason": EQUAL}) | \
                {"reading": reading, "declared": declared}
        return one(a, b, reading, declared)

    out = {}
    for k in RK:
        out[f"tbl_{k}-{k}"] = one(f"tbl_{k}", k, "R1", True)
    for k in RK:
        out[f"rft_{k}-{k}"] = one(f"rft_{k}", k, "R2", True)
    for k in RK:
        out[f"rft_{k}-tbl_{k}"] = one(f"rft_{k}", f"tbl_{k}", "R3", True)
    for k in RK:
        out[f"rft_{k}-clock"] = one(f"rft_{k}", "clock", "R4", True)
        out[f"rft_{k}-clock_rt"] = retuned(f"rft_{k}", "clock_rt", "R4", True, f"rft_{k}-clock")
    for k in RK:
        out[f"tbl_{k}-clock"] = one(f"tbl_{k}", "clock", "not declared (the 0.98 records-table analogue)", False)
    out["clock_rt-clock"] = retuned("clock_rt", "clock", "not declared (supplement to R5)", False, None)
    return out


def _st(c):
    """a comparison's statistics, or its same_as / pending note as it stands"""
    if c is None:
        return None
    return {k: c.get(k) for k in STATS} if "n" in c else dict(c)


def _cmp(x, y, op):
    return None if x is None or y is None else bool(op(x, y))


def _sup(c):
    """superiority by the exact sign test at 0.05, the policy named first ahead"""
    return None if not c or not c.get("n") or c.get("p_sign") is None else bool(c["p_sign"] <= ALPHA
                                                                                 and c["wins"] > c["losses"])


def readings(cmp, recs, sel, ref, fab, rate, tables=None):
    """R1-R6 and cells of PROTOCOL_shift.md for one scenario at one rate, each restating its statistics; every
    check is null where an input is missing"""
    lt, ge = (lambda a, b: a < b), (lambda a, b: a >= b)
    reff = (ref or {}).get(fab) or {}
    rc = reff.get("comparisons") or {}
    tables = tables or {}

    def stats(key, why):
        c = cmp[key]
        e = {"comparison": key, **_st(c)}
        if "n" in c and not c["n"]:
            e["pending"] = why
        return e

    def why_rft(k):
        return "no refitted table yet" if tables.get(f"rft_{k}") is None else "no runs yet"

    out = {r: {"prediction": PREDICTION[r], "operationalised": OPERATIONALISED[r], "by_rule": {}}
           for r in ("R1", "R2", "R3", "R4", "R6", "cells")}
    for k in RK:
        r0 = rc.get(f"tbl_{k}-{k}") or {}
        c1 = cmp[f"tbl_{k}-{k}"]
        e = stats(f"tbl_{k}-{k}", "no runs yet")
        e["ref_0p98"] = rc.get(f"tbl_{k}-{k}")
        e["checks"] = {"positive_on_most_seeds": bool(c1["wins"] > c1["n"] / 2) if c1["n"] else None,
                       "smaller_than_0p98_mean": _cmp(c1["mean"], r0.get("mean"), lt),
                       "smaller_than_0p98_pct": _cmp(c1["pct"], r0.get("pct"), lt)}
        out["R1"]["by_rule"][k] = e

        c2 = cmp[f"rft_{k}-{k}"]
        e = stats(f"rft_{k}-{k}", why_rft(k))
        e["ref_0p98"] = rc.get(f"tbl_{k}-{k}")
        e["checks"] = {"positive_on_every_seed": bool(c2["wins"] == c2["n"]) if c2["n"] else None,
                       "at_least_0p98_mean": _cmp(c2["mean"], r0.get("mean"), ge),
                       "at_least_0p98_pct": _cmp(c2["pct"], r0.get("pct"), ge)}
        out["R2"]["by_rule"][k] = e

        c3 = cmp[f"rft_{k}-tbl_{k}"]
        e = stats(f"rft_{k}-tbl_{k}", why_rft(k))
        e["checks"] = {"r1_short_of_0p98_pct": _cmp(c1["pct"], r0.get("pct"), lt),
                       "positive_mean": None if c3["mean"] is None else bool(c3["mean"] > 0),
                       "positive_sign_0p05": _sup(c3)}
        out["R3"]["by_rule"][k] = e

        vc, vr = cmp[f"rft_{k}-clock"], cmp[f"rft_{k}-clock_rt"]
        use = vc if "same_as" in vr else vr if "n" in vr else None        # the comparison "retuned" resolves to
        e = {"vs_clock": stats(f"rft_{k}-clock", why_rft(k)),
             "vs_retuned": stats(f"rft_{k}-clock_rt", why_rft(k)) if "n" in vr else {"comparison": f"rft_{k}-clock_rt",
                                                                                     **_st(vr)},
             "ref_0p98": rc.get(f"tbl_{k}-clock")}
        if k in ("timeout", "mbs"):
            ok = use is not None and use["n"] > 0
            e["checks"] = {"mean_nonnegative_vs_retuned": _cmp(use["mean"], 0.0, ge) if ok else None,
                           "noninferior_0p25_vs_retuned": (None if not ok or use["lo"] is None
                                                           else bool(use["lo"] > -MARGIN)),
                           "superior_sign_0p05_vs_retuned": _sup(use) if ok else None}
        out["R4"]["by_rule"][k] = e

        rf, st = tables.get(f"rft_{k}"), tables.get(f"tbl_{k}")
        ch = table_change(rf, st) or {}
        zero = {"monotone_violations_0p98": None if st is None else st["monotone_violations"],
                "level_by_arrival_bin_0p98": None if st is None else st["level_h_by_arrival_bin"],
                "fire_0p98": None if st is None else st["fire"]}
        if rf is None:
            out["R6"]["by_rule"][k] = {"pending": "no refitted table yet", **zero}
        else:
            out["R6"]["by_rule"][k] = {
                "violations_residual": rf["violations_residual"], "violations_arrival": rf["violations_arrival"],
                "monotone_violations": rf["monotone_violations"], "adjacent_pairs": rf["adjacent_pairs"],
                "control_limit_form": rf["monotone_violations"] == 0, "cells_differ_0p98": ch.get("cells_differ"),
                "fire_gained": ch.get("fire_gained"), "fire_lost": ch.get("fire_lost"),
                "direction": ch.get("direction"), "level_by_arrival_bin": rf["level_h_by_arrival_bin"],
                "level_shift": ch.get("level_shift"), "fire": rf["fire"], **zero}
        rec = recs.get(k) or {}
        cells = {"dumps_present": sum(d["present"] for d in (rec.get("dumps") or {}).values()),
                 "dumps_expected": len(RECORD_SEEDS), "cells_both_0p98": None if st is None else st["cells_both"]}
        if rf is None:
            out["cells"]["by_rule"][k] = {"pending": "no refitted table yet", **cells}
        else:
            out["cells"]["by_rule"][k] = {"cells_both": rf["cells_both"], "cells": rf["cells"],
                                          "share_decisions_own": rf["share_decisions_own"],
                                          "n_transitions": rf["n_transitions"], **cells}
    h = sel.get("selected_h")
    out["R4"]["retuned"] = {"selected_h": h, "selected_source": sel.get("selected_source"),
                            "note": EQUAL if h == "1.5" else PENDING if h is None else None}

    direction = None if h is None else ("higher" if float(h) > 1.5 else "lower" if float(h) < 1.5 else "same")
    dirs = {k: (out["R6"]["by_rule"][k].get("direction")) for k in RK}
    below = float(rate) < NOMINAL
    want = {"higher": "earlier", "lower": "later", "same": "same"}
    gone = any(d is None for d in dirs.values())
    out["R5"] = {"prediction": PREDICTION["R5"], "operationalised": OPERATIONALISED["R5"],
                 "selected_h": h, "selected_source": sel.get("selected_source"), "agree_files_json": sel.get("agree"),
                 "grid": {th: {"n": g["n"], "mean": g["mean"]} for th, g in sel["grid"].items()},
                 "threshold_direction": direction,
                 "tables": {k: {"direction": dirs[k], "level_shift": out["R6"]["by_rule"][k].get("level_shift"),
                                "cells_differ_0p98": out["R6"]["by_rule"][k].get("cells_differ_0p98")} for k in RK},
                 "checks": {"threshold_rises": None if not below or direction is None else direction == "higher",
                            "tables_start_earlier": None if not below or gone else all(d == "earlier"
                                                                                         for d in dirs.values()),
                            "same_direction": None if not below or gone or direction is None
                            else all(d == want[direction] for d in dirs.values())},
                 "note": None if below else "the protocol predicts a direction at the rates below 0.98 only"}
    if h is None:
        out["R5"]["pending"] = PENDING
    return {k: out[k] for k in ("R1", "R2", "R3", "R4", "R5", "R6", "cells")}


# ---------------------------------------------------------------- one scenario at one rate

def scenario(rate, fab, P, seeds, ref, problems):
    """(the block of the results file, the policy spec) for one scenario at one rate"""
    where = f"rate {rname(rate)} {fab}"
    sel = selection_block(rate, fab, P, problems)
    h = sel["selected_h"]
    spec = policy_spec(rate, fab, P, h, seeds)
    tables, records = {}, {}
    for tag, _ in RULES:
        k = KEY[tag]
        dumps = dump_paths(fab, tag, rate, P)
        st = facts(spec[f"tbl_{k}"]["theta"], problems, pinned=True)
        rf = facts(spec[f"rft_{k}"]["theta"], problems, sources=[os.path.basename(p) for p in dumps.values()])
        tables[f"tbl_{k}"], tables[f"rft_{k}"] = st, rf
        ch = table_change(rf, st) or {}
        records[k] = {"rule": k, "stale": rel(spec[f"tbl_{k}"]["theta"]), "refit": rel(spec[f"rft_{k}"]["theta"]),
                      "dumps": {str(s): {"path": rel(p), "present": os.path.exists(p)} for s, p in dumps.items()},
                      **{c: ch.get(c) for c in CHANGE},
                      "cells_both": None if rf is None else rf["cells_both"], "cells": None if rf is None else rf["cells"],
                      "share_decisions_own": None if rf is None else rf["share_decisions_own"],
                      "cells_both_0p98": None if st is None else st["cells_both"]}
    data = {}
    for key, e in spec.items():
        fire = artefact_fire(e["theta"]) if e["theta"] else None
        if e["theta"] and fire is None and any(os.path.exists(p) for p in e["files"].values()):
            problems.append(f"{where} {key}: run files exist but the table {rel(e['theta'])} is missing or unreadable; "
                            f"their start map is not checked")
        data[key] = load(e["files"], fab, rate, e["arm"], os.path.basename(e["theta"]) if e["theta"] else None,
                         fire, problems)
    crn_check(data, problems, where)
    pol = {}
    for key, e in spec.items():
        s = summary(data[key], seeds, e["role"], e["label"], e["tag"])
        s.pop("underfull_per_day_dev", None)
        s.update(arm=e["arm"], group=e["group"], theta=rel(e["theta"]) if e["theta"] else None,
                 line={f: _avg(data[key], f) for f in ("released_per_day", "wip_slope_back_half", "wip_end")},
                 started_no_output=started_no_output(e["files"]))
        pol[key] = s
    cmp = comparisons(data, seeds, h)
    exp = {"report": len(spec) * len(seeds), "report_pending": len(seeds) if h is None else 0,
           "select": sel["n_expected"], "records": len(RULES) * len(RECORD_SEEDS), "tables": len(RULES)}
    have = {"report": sum(len(v) for v in data.values()), "select": sel["n_present"],
            "records": sum(d["present"] for r in records.values() for d in r["dumps"].values()),
            "tables": sum(tables[f"rft_{k}"] is not None for k in RK)}
    block = {"seeds": list(seeds),
             "status": {"runs_expected": exp, "runs_present": have,
                        "started_no_output": sum(len(p["started_no_output"]) for p in pol.values())
                        + sel["started_no_output"],
                        "complete": all(have[k] == exp[k] for k in have) and not exp["report_pending"]},
             "policies": pol, "comparisons": cmp, "selection": sel, "tables": tables, "records": records,
             "readings": readings(cmp, records, sel, ref, fab, rate, tables)}
    return block, spec


# ---------------------------------------------------------------- the block's state

def _marker(p):
    m = {"present": os.path.exists(p), "failed": None, "text": None}
    if m["present"]:
        try:
            with open(p, encoding="utf-8") as f:
                m["text"] = f.read().strip()
            g = re.search(r"failed=(\d+)", m["text"])
            m["failed"] = int(g.group(1)) if g else None
        except OSError:
            pass
    return m


def _rate_files(rate, P):
    """whether any output of this rate is on disk (run files, launched runs, dumps, refits)"""
    pats = ((P["report"], f"_r{rname(rate)}_d360_"), (P["select"], f"_r{rname(rate)}_d360_"),
            (P["records"], f"_{rtag(rate)}_p1_"), (P["tables"], f"_{rtag(rate)}_b0p003"))
    for d, pat in pats:
        if os.path.isdir(d) and any(pat in n for n in os.listdir(d)):
            return True
    return False


def rate_status(rate, P):
    t = rtag(rate)
    markers = {st: _marker(os.path.join(P["jobs"], f"shift_{t}_{st}.done")) for st in ("a", "fit", "b")}
    high = abs(float(rate) - HIGH) < 1e-9
    skip = os.path.join(P["shift"], "HIGH_SKIPPED.txt")
    out = {"status": None, "stage": None, "markers": markers, "high_skipped": None}
    if high and os.path.exists(skip):
        with open(skip, encoding="utf-8") as f:
            out.update(status="skipped", high_skipped=f.read().strip())
    elif high and not os.path.exists(os.path.join(P["jobs"], f"shift_{t}_a.txt")):
        out["status"] = "not_gated"
    elif markers["b"]["present"]:
        out["status"] = "finished"
    elif not _rate_files(rate, P) and not any(m["present"] for m in markers.values()):
        out["status"] = "not_started"
    else:
        out["status"] = "partial"
        out["stage"] = ("B" if markers["fit"]["present"] or os.path.exists(os.path.join(P["jobs"], f"shift_{t}_b.txt"))
                        else "fit" if markers["a"]["present"] else "A")
    return out


def probe_block(P, problems):
    """the four probe runs at 1.05 and make_shift_jobs.gate_high's rule: every |back-half WIP slope| < 1 lot/day"""
    runs = {}
    for fab in FABS:
        files = {s: os.path.join(P["probe"], run_name(fab, "clock:1.5", HIGH, s)) for s in (64, 65)}
        v = load(files, fab, HIGH, "clock:1.5", None, None, problems)
        for s in (64, 65):
            r = v.get(s) or {}
            runs[f"{fab} s{s}"] = {"present": s in v, "slope": r.get("wip_slope_back_half"), "wip_end": r.get("wip_end")}
    present = sum(r["present"] for r in runs.values())
    slopes = [r["slope"] for r in runs.values()]
    stable = (None if present < len(runs) or any(x is None for x in slopes)
              else all(abs(float(x)) < SLOPE_MAX for x in slopes))
    return {"runs": runs, "n_present": present, "n_expected": len(runs), "stable": stable,
            "rule": f"all |back-half WIP slope| < {SLOPE_MAX:g} lot/day (make_shift_jobs.gate_high)"}


def step0_block(P):
    """the step-0 pair and the block's own seed-64 run, compared in every field but wall_s"""
    name = run_name("HVLM", "timeout:1", RATES[0], STEP0_SEED)
    a, b = os.path.join(P["step0"], "a", name), os.path.join(P["step0"], "b", name)
    blk = os.path.join(P["report"], name)

    def same(p, q):
        if not (os.path.exists(p) and os.path.exists(q)):
            return None
        try:
            return strip(p) == strip(q)
        except (ValueError, OSError):
            return None

    pf = os.path.join(P["jobs"], "shift_step0.pass")
    lines = []
    if os.path.exists(pf):
        with open(pf, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    return {"a_vs_b": same(a, b), "a_vs_block": same(a, blk), "pass_lines": lines}


def check_job_files(rate, specs, P, problems, skipped=False):
    """the outputs the job files of this rate name against the names this script expects (paths taken relative to
    the shift directory, so a test tree checks the same way)"""
    t = rtag(rate)
    root = local(SHIFT_REL)

    def key(p):
        return os.path.relpath(p, P["shift"]).replace("\\", "/")

    exp = {"a": set(), "fit": set(), "b": set()}
    if not skipped:
        for fab, spec in specs.items():
            for tag, _ in RULES:
                exp["a"] |= {key(p) for p in dump_paths(fab, tag, rate, P).values()}
                exp["fit"].add(key(spec[f"rft_{KEY[tag]}"]["theta"]))
            for k, e in spec.items():
                exp["b" if k.startswith("rft_") or k == "clock_rt" else "a"] |= {key(p) for p in e["files"].values()}
            for files in select_spec(rate, fab, P).values():
                exp["a"] |= {key(p) for p in files.values()}
    out = {}
    for st in ("a", "fit", "b"):
        jf = os.path.join(P["jobs"], f"shift_{t}_{st}.txt")
        if not os.path.exists(jf):
            out[st] = None
            continue
        got = set()
        with open(jf, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "  ->  " in line:
                    got.add(os.path.relpath(local(out_of(line)), root).replace("\\", "/"))
        extra, miss = sorted(got - exp[st]), sorted(exp[st] - got)
        if extra or miss:
            problems.append(f"jobs/shift_{t}_{st}.txt and this script disagree on the outputs: "
                            f"{len(extra)} only in the job file (e.g. {extra[:2]}), {len(miss)} only here "
                            f"(e.g. {miss[:2]})")
        out[st] = {"jobs": len(got), "expected": len(exp[st]), "agree": not extra and not miss}
    return out


def default_out(finished, P):
    """final/shift/results.json only once the block has finished; before that a file beside it, never in it"""
    return os.path.join(P["shift"], "results.json") if finished else os.path.join(P["dev"], "results_partial.json")


# ---------------------------------------------------------------- markdown

def _f(x, spec="{:.2f}"):
    return "--" if x is None else spec.format(x)


def _p(p):
    return "--" if p is None else ("<0.001" if p < 0.001 else f"{p:.3f}")


def _yn(x):
    return "--" if x is None else ("yes" if x else "no")


SHORT = {"positive_on_most_seeds": "w>n/2", "smaller_than_0p98_mean": "mean<0.98", "smaller_than_0p98_pct": "%<0.98",
         "positive_on_every_seed": "w=n", "at_least_0p98_mean": "mean>=0.98", "at_least_0p98_pct": "%>=0.98",
         "r1_short_of_0p98_pct": "R1 short", "positive_mean": "mean>0", "positive_sign_0p05": "sign<=0.05",
         "mean_nonnegative_vs_retuned": "mean>=0", "noninferior_0p25_vs_retuned": "lo>-0.25",
         "superior_sign_0p05_vs_retuned": "sign<=0.05"}


def _checks(ch):
    return "; ".join(f"{SHORT.get(k, k)} {_yn(v)}" for k, v in (ch or {}).items()) or "--"


def _row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _pair(c, N):
    if c is None:
        return ["--"] * 6
    if "same_as" in c or "same_policy" in c:
        return [f"= {c.get('same_as') or 'identical'} ({c['reason']})"] + [""] * 5
    if "pending" in c and "n" not in c:
        return [f"pending ({c['pending']})"] + [""] * 5
    if not c["n"]:
        return [f"0/{N}*", "pending" + (f" ({c['pending']})" if c.get("pending") else "")] + [""] * 4
    ci = "--" if c.get("lo") is None else f"[{c['lo']:+.2f}, {c['hi']:+.2f}]"
    return [f"{c['n']}/{N}" + ("*" if c["n"] < N else ""), _f(c["mean"], "{:+.2f}"), ci,
            f"{c['wins']}/{c['losses']}/{c['ties']}", _p(c["p_sign"]), _f(c["pct"], "{:+.1f}")]


def _ref(r):
    return "--" if not r else f"{_f(r.get('mean'), '{:+.2f}')} / {_f(r.get('pct'), '{:+.1f}')}%"


def markdown(res):
    m = res["meta"]
    N = m["report_seeds"][1] - m["report_seeds"][0] + 1
    L = [f"# Shift block (PROTOCOL_shift.md): read {m['generated']}, git {m['git_head']}"
         + ("" if m["finished"] else "  **NOT FINISHED**"), ""]
    e, p = m["runs_expected"], m["runs_present"]
    L.append(f"Runs present of expected: report {p['report']}/{e['report']}"
             + (f" (+{e['report_pending']} if a retuned threshold is not 1.5 h)" if e.get("report_pending") else "")
             + f", selection {p['select']}/{e['select']}, record dumps {p['records']}/{e['records']}, refitted "
               f"tables {p['tables']}/{e['tables']}; launched without output yet: {m['started_no_output']}.")
    L.append("Rates: " + "; ".join(f"{k} {R['status']}" + (f" (stage {R['stage']})" if R.get("stage") else "")
                                   for k, R in res["rates"].items()) + ".")
    s0 = m["step0"]
    L.append(f"Step 0: a = b {_yn(s0['a_vs_b'])}; a = the block's seed-64 run {_yn(s0['a_vs_block'])}; "
             f"{len(s0['pass_lines'])} line(s) in shift_step0.pass.")
    L.append(f"0.98 reference: {m['reference']['path']} ({m['reference']['generated']})" if m.get("reference")
             else "0.98 reference: absent (every check against 0.98 is --)")
    ref = res.get("reference_0p98") or {}
    rates = list(res["rates"])

    L += ["", f"## Table minus its rule: % of the rule's completions per day (paired seeds of {N})", ""]
    head = ["scenario", "rule", "0.98"] + [f"{w} {r}" for r in rates for w in ("stale", "refit")]
    L += [_row(head), "|" + "---|" * len(head)]
    for fab in FABS:
        for k in RK:
            r = ((ref.get(fab) or {}).get("comparisons") or {}).get(f"tbl_{k}-{k}")
            cells = [fab, k, "--" if not r else f"{_f(r.get('pct'), '{:+.1f}')} ({r.get('n')})"]
            for rk in rates:
                B = res["rates"][rk].get(fab)
                for a in ("tbl", "rft"):
                    c = (B or {}).get("comparisons", {}).get(f"{a}_{k}-{k}")
                    cells.append(res["rates"][rk]["status"] if B is None else
                                 f"{_f(c['pct'], '{:+.1f}')} ({c['n']}/{N})")
            L.append(_row(cells))

    for rk, R in res["rates"].items():
        if R.get("probe"):
            pr = R["probe"]
            L += ["", f"Probe at {rk}: {pr['n_present']}/{pr['n_expected']} runs, stable {_yn(pr['stable'])}: "
                  + ", ".join(f"{k} slope {_f(v['slope'], '{:+.3f}')} WIP {v['wip_end'] if v['wip_end'] is not None else '--'}"
                              for k, v in pr["runs"].items())]
        if R["status"] == "skipped":
            L += ["", f"## Rate {rk}: skipped", "", R.get("high_skipped") or ""]
            continue
        jf = R.get("job_files") or {}
        L += ["", "Job files at " + rk + ": " + ", ".join(
            f"{st} {'--' if v is None else ('agree' if v['agree'] else 'DISAGREE')} "
            f"({'-' if v is None else v['jobs']} jobs)" for st, v in jf.items())]
        for fab in FABS:
            B = R.get(fab)
            if B is None:
                continue
            st = B["status"]
            ex, hv = st["runs_expected"], st["runs_present"]
            L += ["", f"## Rate {rk}, {fab}: {R['status']}" + (f" (stage {R['stage']})" if R.get("stage") else ""),
                  "", f"report {hv['report']}/{ex['report']}" + (f" (+{ex['report_pending']} pending)" if ex["report_pending"] else "")
                  + f", selection {hv['select']}/{ex['select']}, dumps {hv['records']}/{ex['records']}, refits "
                    f"{hv['tables']}/{ex['tables']}, launched without output {st['started_no_output']}", ""]
            if not (hv["report"] or hv["select"] or hv["tables"] or st["started_no_output"]):
                L.append("No run file yet: the tables are left out here (every policy n = 0, every reading pending; "
                         "the results file lists them).")
                continue
            L += [_row(["policy", "n", "completed/day", "scrapped at furnaces", "elsewhere", "under-full/day",
                        "cycle (d)"]), "|---|---|---|---|---|---|---|"]
            P = B["policies"]
            for heading, names in GROUPS:
                names = [x for x in names if x in P]
                if not names:
                    continue
                L.append(_row([f"*{heading}*", "", "", "", "", "", ""]))
                for x in names:
                    q = P[x]
                    L.append(_row([q["label"].replace("$", ""), f"{q['n']}/{N}" + ("*" if q["n"] < N else ""),
                                   _f(q["completed"]), _f(q["scrapped_furnace"], "{:.1f}"),
                                   _f(q["scrapped_other"], "{:.1f}"), _f(q["underfull_per_day"], "{:.1f}"),
                                   _f(q["cycle_p50_days"], "{:.1f}")]))
            C = B["comparisons"]
            rc = ((ref.get(fab) or {}).get("comparisons") or {})
            RD = B["readings"]
            L += ["", f"Readings, A - B in completed lots per day (* = fewer than {N} paired seeds; 0.98 = the same "
                      f"comparison in the confirmatory block, mean / %):", ""]
            L += [_row(["reading", "A - B", "n", "mean", "95% CI", "w/l/t", "sign p", "%", "0.98", "checks"]),
                  "|---|---|---|---|---|---|---|---|---|---|"]
            for key, c in C.items():
                a, b = key.split("-")
                k = a.split("_", 1)[1] if "_" in a and a != "clock_rt" else None
                reading = c.get("reading", "")
                if reading == "R1":
                    r0, ch = rc.get(key), RD["R1"]["by_rule"][k]["checks"]
                elif reading == "R2":
                    r0, ch = rc.get(f"tbl_{k}-{k}"), RD["R2"]["by_rule"][k]["checks"]
                elif reading == "R3":
                    r0, ch = None, RD["R3"]["by_rule"][k]["checks"]
                elif reading == "R4":
                    r0 = rc.get(f"tbl_{k}-clock")
                    ch = RD["R4"]["by_rule"][k].get("checks") if b == "clock_rt" else None
                else:
                    r0, ch = (rc.get(key) if a.startswith("tbl_") else None), None
                L.append(_row([reading if c.get("declared") else "--", f"{a} - {b}"] + _pair(c, N)
                              + [_ref(r0), _checks(ch) if ch else ""]))
            r5 = RD["R5"]
            L += ["", f"R5: h* = {r5['selected_h'] or '--'} h ({r5['selected_source'] or 'no selection yet'}; files and "
                      f"selection file agree {_yn(r5['agree_files_json'])}); direction against 1.5 h "
                      f"{r5['threshold_direction'] or '--'}; tables "
                  + ", ".join(f"{k} {v['direction'] or '--'}" for k, v in r5["tables"].items())
                  + f"; checks {_checks(r5['checks'])}",
                  "grid (mean completed/day over seeds 108-115, n of 8): "
                  + ", ".join(f"{th} h {_f(g['mean'])} ({g['n']})" for th, g in r5["grid"].items())]
            L += ["", _row(["rule", "cells both (0.98)", "dumps", "violations res/arr (0.98 total)",
                            "control-limit form", "cells differ from 0.98", "gained/lost", "direction",
                            "level by arrival bin, h (0.98)", "0.98 table on new records"]),
                  "|---|---|---|---|---|---|---|---|---|---|"]
            for k in RK:
                r6, ce = RD["R6"]["by_rule"][k], RD["cells"]["by_rule"][k]
                rec = B["records"][k]
                lv = lambda xs: "--" if xs is None else "/".join("-" if x is None else f"{x:g}" for x in xs)
                if "pending" in r6:
                    L.append(_row([k, f"-- ({_f(ce['cells_both_0p98'], '{}')})", f"{ce['dumps_present']}/{ce['dumps_expected']}",
                                   f"-- ({_f(r6['monotone_violations_0p98'], '{}')})", "pending", "", "", "",
                                   f"-- ({lv(r6['level_by_arrival_bin_0p98'])})", ""]))
                else:
                    ag = rec.get("agree_old_on_new_records")
                    L.append(_row([k, f"{ce['cells_both']}/{ce['cells']} ({_f(ce['cells_both_0p98'], '{}')})",
                                   f"{ce['dumps_present']}/{ce['dumps_expected']}",
                                   f"{r6['violations_residual']}/{r6['violations_arrival']} "
                                   f"({_f(r6['monotone_violations_0p98'], '{}')})", _yn(r6["control_limit_form"]),
                                   _f(r6["cells_differ_0p98"], "{}"), f"{r6['fire_gained']}/{r6['fire_lost']}",
                                   r6["direction"] or "--",
                                   f"{lv(r6['level_by_arrival_bin'])} ({lv(r6['level_by_arrival_bin_0p98'])})",
                                   "--" if ag is None else f"{100 * ag:.1f}%"]))
    for title, items in (("Deviations", m["deviations"]), ("Problems", m["problems"]), ("Notes", m["notes"])):
        L += ["", f"## {title} ({len(items)})", ""] + ([f"- {x}" for x in items] or ["none"])
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- LaTeX (paper/tables/shift.tex)

def shift_tex(res, src):
    """records.tex's layout: one emph group per scenario, rows rate x rule; holes print as \\textbf{??}"""
    import confirm_tables as ct
    m = res["meta"]
    lo, hi = m["report_seeds"]
    N = hi - lo + 1
    notes, rows = ct.Notes(), []

    def mark(c):
        return notes.mark(f"Paired on {c['n']} of the {N} seeds.") if c["n"] < N else ""

    def pct(c):
        if not c or "n" not in c or not c["n"] or c["pct"] is None:
            return ct.HOLE
        return ct.num(c["pct"], 1) + mark(c)

    ncell = 24
    for fab in FABS:
        rows.append(rf"\multicolumn{{7}}{{@{{}}l}}{{\emph{{{fab}}}}} \\")
        first = True
        for rk, R in res["rates"].items():
            B = R.get(fab)
            if B is None:
                continue
            if not first:
                rows.append(r"\addlinespace[3pt]")
            first = False
            C = B["comparisons"]
            for i, k in enumerate(RK):
                rt = C[f"rft_{k}-clock_rt"]
                rt = C[rt["same_as"]] if "same_as" in rt else rt if "n" in rt else None
                have = rt is not None and rt["n"] and rt["mean"] is not None
                rec = B["records"][k]
                ncell = rec["cells"] or ncell
                rows.append(" & ".join([
                    f"{float(rk):.2f}" if i == 0 else "", ct.tex(LABEL[k]),
                    ct.HOLE if rec["cells_both"] is None else str(rec["cells_both"]),
                    pct(C[f"tbl_{k}-{k}"]), pct(C[f"rft_{k}-{k}"]),
                    (ct.sgn(rt["mean"]) + mark(rt)) if have else ct.HOLE,
                    ((ct.ci(rt["lo"], rt["hi"]) if rt["lo"] is not None else "--") if have else ct.HOLE)]) + r" \\")
        rows.append(r"\midrule")
    rows.pop()

    def h_of(R, fab):
        s = (R.get(fab) or {}).get("selection") or {}
        if s.get("selected_h") is None:
            return ct.HOLE
        return f"{s['selected_h']}~h" + ("" if s.get("selected_source") != "files (provisional)" else
                                         notes.mark("Chosen from the selection runs before make_shift_jobs.py "
                                                    "recorded it."))

    parts = []
    for fab in FABS:
        xs = [f"{h_of(R, fab)} at {float(rk):.2f}" for rk, R in res["rates"].items() if R.get(fab) is not None]
        if xs:
            parts.append(" and ".join(xs) + f" on {fab}")
    general = (rf"Cells: the number of the {ncell} cells in which the new records hold each action at least $n_0$ "
               rf"times. Diff.: the paired difference in completed lots per day. The values of $\theta$ retuned at each rate are " + ", and ".join(parts)
               + r", against 1.5~h at 0.98.")
    skipped = [f"{float(rk):.2f}" for rk, R in res["rates"].items() if R["status"] == "skipped"]
    body = "\n".join("    " + r for r in rows)
    head = r"""    & & & Fitted at 0.98 $-$ rule & Refitted $-$ rule & \multicolumn{2}{c}{Refitted $-$ retuned threshold} \\
    \cmidrule(lr){4-4} \cmidrule(lr){5-5} \cmidrule(l){6-7}
    Rate & Records of & Cells & (\%) & (\%) & Diff. & 95\% CI \\"""
    cap_ = r"Results at the release rates of 0.90 and 0.80."
    e, p = m["runs_expected"], m["runs_present"]
    comment = "\n".join(["% generated by fabhybrid/smt2020/shift_report.py from " + rel(src),
                         f"% shift results of {m['generated']}, seeds {lo}-{hi}, {p['report']} of {e['report']} "
                         f"report runs; do not edit by hand"]
                        + ([] if m["finished"] else
                           ["% PARTIAL: the block had not finished when these numbers were computed"])) + "\n"
    return ct.interact_table(cap_, "tab:shift", r"@{}l l c c c rc@{}", head, body, "3pt", notes.render(general),
                             comment)


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--rates", default=",".join(rname(r) for r in ALL_RATES), help="e.g. 0.9,0.8,1.05")
    ap.add_argument("--seeds", default=f"{REPORT_SEEDS[0]}-{REPORT_SEEDS[-1]}", help="report seeds, first-last")
    ap.add_argument("--shift-dir", default=None, help="default: experiments/smt2020/final/shift")
    ap.add_argument("--family-dir", default=None, help="the 0.98 tables (default: final/betarx/family)")
    ap.add_argument("--jobs-dir", default=None, help="job files and queue markers (default: experiments/smt2020/jobs)")
    ap.add_argument("--reference", default=None, help="the 0.98 results (default: final/confirm/results.json)")
    ap.add_argument("--out", default=None, help="results file (default: final/shift/results.json once the block has "
                                                "finished, else final/shift_report_dev/results_partial.json)")
    ap.add_argument("--tex", action="store_true", help="also write the LaTeX table")
    ap.add_argument("--tex-out", default=None, help="where (default paper/tables/shift.tex, finished block only)")
    ap.add_argument("--quiet", action="store_true", help="no markdown on stdout")
    ap.add_argument("--no-log", action="store_true", help="do not note an interim read in interim_looks.log")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

    rates = [float(x) for x in a.rates.split(",") if x.strip()]
    for r in rates:
        if not any(abs(r - x) < 1e-9 for x in ALL_RATES):
            raise SystemExit(f"--rates: {r:g} is not a rate of the block ({', '.join(rname(x) for x in ALL_RATES)})")
    lo, hi = (int(x) for x in a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    P = paths(a.shift_dir, a.family_dir, a.jobs_dir, a.reference)
    every = {rname(r): rate_status(r, P) for r in ALL_RATES}
    finished = all(s["status"] in ("finished", "skipped") for s in every.values())
    full = finished and set(rname(r) for r in rates) == set(every)
    out_path = os.path.abspath(a.out) if a.out else default_out(full, P)
    if not finished and under(out_path, P["shift"]):
        print(f"refused: {out_path} lies under {P['shift']}, and the block has not finished (the chain writes there); "
              f"name a results file elsewhere", file=sys.stderr)
        raise SystemExit(2)
    if a.tex and not a.tex_out and not full:
        print("refused: paper/tables/shift.tex is written only from the finished block; name the file with --tex-out",
              file=sys.stderr)
        raise SystemExit(2)

    problems, deviations, notes = [], [], []
    generated = time.strftime("%Y-%m-%d %H:%M:%S")
    log = os.path.join(P["dev"], "interim_looks.log")
    if P["block"] and not finished and not a.no_log:
        os.makedirs(P["dev"], exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{generated} read before the block finished: "
                    + ", ".join(f"{k} {v['status']}" + (f" ({v['stage']})" if v["stage"] else "") for k, v in every.items())
                    + "\n")
    if P["block"] and os.path.exists(log):
        with open(log, encoding="utf-8") as f:
            looks = [ln.strip() for ln in f if ln.strip()]
        if looks:
            notes.append(f"the run files were read {len(looks)} time(s) before the block finished (first {looks[0][:19]}, "
                         f"last {looks[-1][:19]}; {rel(log)}); PROTOCOL_shift.md declares no ban on interim looks")
    notes.append("p_holm is null throughout: PROTOCOL_shift.md declares no families of comparisons")
    notes.append("the checks of each reading are this script's operationalisation of the protocol's predictions "
                 "(see each reading's 'operationalised'); the protocol fixes no thresholds")
    if seeds != list(REPORT_SEEDS):
        notes.append(f"report seeds {lo}-{hi}, not the protocol's {REPORT_SEEDS[0]}-{REPORT_SEEDS[-1]}; the job files "
                     f"are not checked")

    ref = reference(P["reference"], problems)
    step0 = step0_block(P)
    if step0["a_vs_b"] is False:
        deviations.append("step 0: the two step-0 runs differ")
    if step0["a_vs_block"] is False:
        deviations.append("step 0: the block's own seed-64 run differs from step 0")
    res = {"meta": None, "reference_0p98": None if ref is None else {fab: ref[fab] for fab in FABS}, "rates": {}}
    stale_pins = {}
    for fab in FABS:
        for tag, _ in RULES:
            p = os.path.join(P["family"], os.path.basename(stale(fab, tag)))
            f = facts(p, problems, pinned=True)
            stale_pins[os.path.basename(p)] = None if f is None else f["pinned_ok"]
            if f is None:
                problems.append(f"stale table missing: {rel(p)}")
    sum_exp = {k: 0 for k in ("report", "report_pending", "select", "records", "tables")}
    sum_have = {k: 0 for k in ("report", "select", "records", "tables")}
    started, complete, missing = 0, True, {}
    for r in rates:
        rk = rname(r)
        st = every[rk]
        sel_path = os.path.join(P["select"], f"selection_{rtag(r)}.json")
        R = {"rate": r, "rtag": rtag(r), "status": st["status"], "stage": st["stage"],
             "markers": {k: {"present": v["present"], "failed": v["failed"]} for k, v in st["markers"].items()},
             "selection_file": rel(sel_path) if os.path.exists(sel_path) else None,
             "high_skipped": st["high_skipped"],
             "probe": probe_block(P, problems) if abs(r - HIGH) < 1e-9 else None}
        for k, v in st["markers"].items():
            if v["present"] and v["failed"]:
                deviations.append(f"rate {rk}: jobs/shift_{rtag(r)}_{k}.done records {v['failed']} failed job(s) after "
                                  f"the queue's second pass; those runs stay missing")
        if st["status"] != "skipped":
            specs = {}
            for fab in FABS:
                R[fab], specs[fab] = scenario(r, fab, P, seeds, ref, problems)
                s = R[fab]["status"]
                for k in sum_exp:
                    sum_exp[k] += s["runs_expected"][k]
                for k in sum_have:
                    sum_have[k] += s["runs_present"][k]
                started += s["started_no_output"]
                complete = complete and s["complete"]
                miss = {k: q["seeds_missing"] for k, q in R[fab]["policies"].items() if q["seeds_missing"]}
                if miss:
                    missing.setdefault(rk, {})[fab] = miss
            R["job_files"] = (check_job_files(r, specs, P, problems) if seeds == list(REPORT_SEEDS) else None)
        else:
            R["job_files"] = check_job_files(r, {}, P, problems, skipped=True)
        res["rates"][rk] = R

    res["meta"] = {
        "mode": "shift", "generated": generated, "git_head": git_head(),
        "protocol": "experiments/smt2020/final/shift/PROTOCOL_shift.md", "shift_dir": rel(P["shift"]),
        "family_dir": rel(P["family"]), "block": bool(P["block"]),
        "reference": None if ref is None else {"path": ref["path"], "generated": ref["generated"]},
        "report_seeds": [lo, hi], "select_seeds": [SELECT_SEEDS[0], SELECT_SEEDS[-1]],
        "record_seeds": list(RECORD_SEEDS), "rates": [rname(r) for r in rates],
        "window_days": WINDOW_DAYS, "run_days": RUN_DAYS,
        "interval": "95% paired t, exact Student quantile for the n of each comparison",
        "sign_test": "exact, two-sided, ties dropped", "multiplicity": "none declared in PROTOCOL_shift.md",
        "runs_expected": sum_exp, "runs_present": sum_have, "started_no_output": started,
        "finished": bool(finished), "complete": bool(complete and finished),
        "statuses": {k: v["status"] for k, v in every.items()},
        "step0": step0, "stale_tables_pinned": stale_pins,
        "problems": list(dict.fromkeys(problems)), "deviations": list(dict.fromkeys(deviations)), "notes": notes,
        "missing": missing}

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(clean(res), f, indent=1, allow_nan=False)
    if not a.quiet:
        print(markdown(clean(res)))
    print(("" if finished else "[NOT FINISHED] ") + f"wrote {out_path}")
    if a.tex:
        tp = os.path.abspath(a.tex_out) if a.tex_out else TEX
        if not finished and under(tp, P["shift"]):
            print(f"refused: {tp} lies under {P['shift']}", file=sys.stderr)
            raise SystemExit(2)
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        with open(tp, "w", encoding="utf-8", newline="\n") as f:
            f.write(shift_tex(clean(res), out_path))
        print(f"wrote {tp}")
    return res


if __name__ == "__main__":
    main()
