"""shift_report.py on hand-built trees and, where they exist, on the shift block's own files (read only).

Run from fabhybrid/smt2020:
  OMP_NUM_THREADS=1 python -B -m pytest tests/test_shift_report.py -q -p no:cacheprovider
"""
import sys

sys.dont_write_bytecode = True      # the shift block's chain imports from fabhybrid/smt2020

import json                         # noqa: E402
import os                           # noqa: E402
import re                           # noqa: E402

import numpy as np                  # noqa: E402
import pytest                       # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import confirm_report as cr         # noqa: E402
import make_shift_jobs as msj       # noqa: E402
import shift_report as sr           # noqa: E402

SEEDS = list(range(64, 96))
EDGES = {"tightest": [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 24.01], "nxt": [0.0, 0.25, 1.0, 3.0, 24.01], "fill": [0.0, 1.001]}
CL = [[1, 1, 1, 1], [1, 1, 1, 1], [0, 1, 1, 1], [0, 0, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]   # control limits 0.5/1/2/2 h


def table(fire2d, n=50, sources=()):
    """a 6 x 4 x 1 table artefact as fit_q.py writes one (the fields table_facts reads)"""
    cnt = [[[n] for _ in row] for row in fire2d]
    return {"h0": 1.0, "lam": 0.003, "K0": 10.0, "gamma_h": 0.9, "from_day": 90.0, "backoff": False, "edges": EDGES,
            "fire": [[[int(v)] for v in row] for row in fire2d], "n_fired": cnt, "n_waited": cnt,
            "source": list(sources), "n_transitions": 1000}


def write(path, obj):
    path = str(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return path


def run(fab, seed, rate, arm, completed, theta=None, fire=None, released=40.0):
    """a run file as batch_fire.py writes one (the fields shift_report reads)"""
    return {"dataset": fab, "seed": seed, "scale": rate, "days": 360, "cqt_rule": "qtcr", "scrap": True,
            "warmup_days": 87.0, "arm": arm, "theta": theta, "level": None if fire is None else {"fire": fire},
            "scrap_kpi": {"completed_per_day": completed, "scrapped_per_day": 19.0, "cycle_p50_days": 24.8},
            "batches_partial": 3600, "batches_partial_all": 2730,
            "blocking": {"batch_deaths": 1365, "nonbatch_deaths": 3822},
            "released_per_day": released, "wip_slope_back_half": 0.1, "wip_end": 1000, "wall_s": 1.0}


class Tree:
    """a fake block: final/shift, final/betarx/family with the six 0.98 tables, jobs/, no 0.98 reference"""

    def __init__(self, tmp):
        tmp = str(tmp)
        self.P = sr.paths(os.path.join(tmp, "final", "shift"), os.path.join(tmp, "final", "betarx", "family"),
                          os.path.join(tmp, "jobs"), os.path.join(tmp, "final", "confirm", "results.json"))
        for d in ("shift", "jobs"):
            os.makedirs(self.P[d], exist_ok=True)
        for fab in msj.FABS:
            for tag, _ in msj.RULES:
                write(os.path.join(self.P["family"], os.path.basename(msj.stale(fab, tag))), table(CL))

    def args(self, out, *more):
        return ["--shift-dir", self.P["shift"], "--family-dir", self.P["family"], "--jobs-dir", self.P["jobs"],
                "--reference", self.P["reference"]] + (["--out", str(out)] if out else []) + ["--no-log"] + list(more)

    def put(self, rate, fab, key, seeds, base=35.0, selected_h=None):
        e = sr.policy_spec(rate, fab, self.P, selected_h)[key]
        fire = sr.artefact_fire(e["theta"]) if e["theta"] else None
        theta = None if not e["theta"] else "../../experiments/smt2020/x/" + os.path.basename(e["theta"])
        for s in seeds:
            write(e["files"][s], run(fab, s, rate, e["arm"], base + 0.01 * (s - 64), theta, fire))
        return e

    def refit(self, rate, fab, tag, fire2d):
        return write(os.path.join(self.P["tables"], os.path.basename(msj.refit(fab, tag, rate))),
                     table(fire2d, sources=[msj.dump(fab, tag, rate, s) for s in msj.RECORD_SEEDS]))


def strict(path):
    def bad(x):
        raise ValueError(f"non-finite number in the results file: {x}")
    with open(path, encoding="utf-8") as f:
        return json.load(f, parse_constant=bad)


# ---------------------------------------------------------------- synthetic

def test_names_come_from_the_generator(tmp_path):
    assert sr.run_name("HVLM", "timeout:1", 0.9, 64) == "batch_fire_HVLM_r0.9_d360_s64_timeout1_qtcr_scrap.json"
    assert sr.run_name("LVHM", "clock:0.75", 0.8, 108) == "batch_fire_LVHM_r0.8_d360_s108_clock0.75_qtcr_scrap.json"
    assert sr.run_name("HVLM", "clock:1.5", 1.05, 65) == "batch_fire_HVLM_r1.05_d360_s65_clock1.5_qtcr_scrap.json"
    assert [msj.rname(r) for r in (0.9, 0.8, 1.05)] == ["0.9", "0.8", "1.05"]
    assert [msj.rtag(r) for r in (0.9, 0.8, 1.05)] == ["r0p90", "r0p80", "r1p05"]
    P = Tree(tmp_path).P
    for rate, rn, rt in ((0.9, "0.9", "r0p90"), (0.8, "0.8", "r0p80"), (1.05, "1.05", "r1p05")):
        sp = sr.policy_spec(rate, "LVHM", P, None)
        assert list(sp) == ["timeout", "mbs", "nach", "clock", "tbl_timeout", "tbl_mbs", "tbl_nach",
                            "rft_timeout", "rft_mbs", "rft_nach"]
        tags = {k: e["tag"] for k, e in sp.items()}
        assert (tags["timeout"], tags["mbs"], tags["nach"], tags["clock"]) == ("timeout1", "mbs3", "nach", "clock1.5")
        assert tags["tbl_mbs"] == "level1_LVHM_mbs3_b0p003_t1" and tags["rft_nach"] == f"level1_LVHM_nach_{rt}_b0p003_t1"
        assert os.path.basename(sp["rft_nach"]["files"][95]) == \
            f"batch_fire_LVHM_r{rn}_d360_s95_level1_LVHM_nach_{rt}_b0p003_t1_qtcr_scrap.json"
        assert sp["rft_timeout"]["theta"] == os.path.join(P["tables"], f"LVHM_timeout_{rt}_b0p003_t1.json")
        assert sp["tbl_timeout"]["theta"] == os.path.join(P["family"], "LVHM_timeout_b0p003_t1.json")
        assert all(os.path.dirname(p) == P["report"] for e in sp.values() for p in e["files"].values())
    assert sr.policy_spec(1.05, "LVHM", P, None)["rft_nach"]["tag"] == "level1_LVHM_nach_r1p05_b0p003_t1"
    sel = sr.select_spec(0.9, "HVLM", P)
    assert list(sel) == msj.THETAS and sorted(sel["4"]) == msj.SELECT_SEEDS
    assert sel["0.75"][108] == os.path.join(P["select"], "batch_fire_HVLM_r0.9_d360_s108_clock0.75_qtcr_scrap.json")


def test_load_rejects_what_is_not_the_block_and_maps_the_fields(tmp_path):
    t = Tree(tmp_path)
    e = sr.policy_spec(0.9, "HVLM", t.P, None)["tbl_timeout"]
    fire, name = sr.artefact_fire(e["theta"]), os.path.basename(e["theta"])
    good = run("HVLM", 64, 0.9, "level:1", 35.0, theta="../../x/" + name, fire=fire)
    files = {s: e["files"][s] for s in range(64, 71)}
    write(files[64], good)
    write(files[65], dict(good, seed=65, scale=0.98))                                  # a 0.98 file in a 0.9 slot
    write(files[66], dict(good, seed=66, arm="level:2"))                               # another arm
    write(files[67], dict(good, seed=67, theta="../../x/HVLM_mbs3_b0p003_t1.json"))    # another table
    write(files[68], dict(good, seed=68, level={"fire": [[[0]] * 4] * 6}))             # another start map
    with open(files[69], "w") as f:
        f.write('{"dataset": "HVLM", "se')                                             # caught while written
    problems = []                                                                      # 70: missing, silent
    v = sr.load(files, "HVLM", 0.9, "level:1", name, fire, problems)
    assert list(v) == [64] and len(problems) == 5
    for why in ("(scale)", "(arm)", "(theta)", "(level.fire)", "unreadable"):
        assert sum(why in p for p in problems) == 1, why
    r = v[64]
    assert r["scrapped_furnace"] == 5.0 and r["scrapped_other"] == 14.0                # 1365 and 3822 over 273 days
    assert r["underfull_per_day"] == 10.0 and r["underfull_per_day_run"] == 10.0       # 2730 / 273, 3600 / 360
    assert (r["completed"], r["scrapped"], r["cycle_p50_days"], r["released_per_day"]) == (35.0, 19.0, 24.8, 40.0)
    rule = sr.policy_spec(0.9, "HVLM", t.P, None)["timeout"]
    write(rule["files"][64], run("HVLM", 64, 0.9, "timeout:1", 33.0))
    assert list(sr.load(rule["files"], "HVLM", 0.9, "timeout:1", None, None, [])) == [64]


def test_partial_pairing_uses_the_common_seeds(tmp_path, capsys):
    t = Tree(tmp_path)
    t.put(0.9, "HVLM", "timeout", range(64, 80), base=33.0)
    t.put(0.9, "HVLM", "tbl_timeout", range(70, 96), base=35.0)
    out = tmp_path / "r.json"
    sr.main(t.args(out))
    c = strict(out)["rates"]["0.9"]["HVLM"]["comparisons"]["tbl_timeout-timeout"]
    assert (c["n"], c["n_a"], c["n_b"], c["n_expected"], c["complete"]) == (10, 26, 16, 32, False)
    assert len(c["per_seed"]) == 32
    assert all(x is None for x in c["per_seed"][:6] + c["per_seed"][16:])
    assert all(abs(x - 2.0) < 1e-9 for x in c["per_seed"][6:16]) and abs(c["mean"] - 2.0) < 1e-9
    assert c["wins"] == 10 and c["secondary"]["scrapped_furnace"]["n"] == 10
    assert re.search(r"\| R1 \| tbl_timeout - timeout \| 10/32\* \| \+2\.00 ", capsys.readouterr().out)


def test_pick_and_the_selection_file(tmp_path):
    assert sr.pick([1, 2, 3, 3, 2, 1, 0]) == "1"             # a tie goes to the first threshold in grid order
    assert sr.pick([5, 1, 1, 1, 1, 1, 5]) == "0.5"
    assert sr.pick([1, 2, 3, 4, 5, 6, 7]) == "4" and sr.pick([0, 0, 0, 9, 0, 0, 0]) == "1.5"
    assert sr.pick([1, 2, None, 3, 2, 1, 0]) is None
    t = Tree(tmp_path)
    level = {"0.5": 30, "0.75": 31, "1": 32, "1.5": 33, "2": 34, "3": 33.5, "4": 33}
    files = sr.select_spec(0.9, "HVLM", t.P)
    for th, fs in files.items():
        for s, p in fs.items():
            if (th, s) != ("4", 115):
                write(p, run("HVLM", s, 0.9, f"clock:{th}", level[th] + 0.01 * (s - 108)))
    b = sr.selection_block(0.9, "HVLM", t.P, [])
    assert b["grid"]["4"]["n"] == 7 and b["selected_from_files"] is None and b["selected_h"] is None
    write(files["4"][115], run("HVLM", 115, 0.9, "clock:4", 33.07))
    b = sr.selection_block(0.9, "HVLM", t.P, [])
    assert (b["selected_from_files"], b["selected_h"], b["selected_source"]) == ("2", "2", "files (provisional)")
    assert abs(b["grid"]["2"]["mean"] - sum(34 + 0.01 * i for i in range(8)) / 8) < 1e-12
    assert b["n_present"] == b["n_expected"] == 56 and b["complete"]
    write(os.path.join(t.P["select"], "selection_r0p90.json"),
          [{"fab": "HVLM", "rate": "0.9", "grid": {th: round(b["grid"][th]["mean"], 3) for th in msj.THETAS},
            "selected": "4"}])
    problems = []
    b = sr.selection_block(0.9, "HVLM", t.P, problems)
    assert (b["selected_h"], b["selected_source"], b["agree"], b["grid_agree"]) == ("4", "selection_r0p90.json",
                                                                                   False, True)
    assert len(problems) == 1 and "selects 4 h" in problems[0]


def test_retuned_threshold_equal_to_and_different_from_1p5(tmp_path):
    P = Tree(tmp_path).P
    sel = {"selected_h": "1.5", "selected_source": "selection_r0p90.json", "agree": True,
           "grid": {th: {"n": 8, "mean": 33.0} for th in msj.THETAS}}
    sp = sr.policy_spec(0.9, "HVLM", P, "1.5")
    assert "clock_rt" not in sp
    cmp = sr.comparisons({k: {} for k in sp}, SEEDS, "1.5")
    assert cmp["rft_timeout-clock_rt"]["same_as"] == "rft_timeout-clock" and cmp["rft_timeout-clock_rt"]["reason"] == sr.EQUAL
    assert cmp["clock_rt-clock"]["same_policy"] is True
    rd = sr.readings(cmp, {}, sel, None, "HVLM", 0.9, {})
    assert rd["R4"]["by_rule"]["timeout"]["vs_retuned"]["same_as"] == "rft_timeout-clock"
    assert rd["R4"]["retuned"]["note"] == sr.EQUAL and rd["R5"]["threshold_direction"] == "same"
    pend = sr.comparisons({k: {} for k in sp}, SEEDS, None)
    assert pend["rft_mbs-clock_rt"]["pending"] == sr.PENDING

    sp = sr.policy_spec(0.9, "HVLM", P, "2")
    assert (sp["clock_rt"]["arm"], sp["clock_rt"]["tag"]) == ("clock:2", "clock2")
    assert os.path.basename(sp["clock_rt"]["files"][64]) == "batch_fire_HVLM_r0.9_d360_s64_clock2_qtcr_scrap.json"
    rows = lambda x: {s: {"completed": x + 0.01 * s} for s in SEEDS}                    # noqa: E731
    data = {k: {} for k in sp}
    data.update(rft_timeout=rows(35.5), clock_rt=rows(35.0), clock=rows(34.0))
    cmp = sr.comparisons(data, SEEDS, "2")
    c = cmp["rft_timeout-clock_rt"]
    assert (c["n"], c["wins"], c["complete"]) == (32, 32, True) and abs(c["mean"] - 0.5) < 1e-9
    assert abs(cmp["clock_rt-clock"]["mean"] - 1.0) < 1e-9 and cmp["clock_rt-clock"]["declared"] is False
    rd = sr.readings(cmp, {}, dict(sel, selected_h="2"), None, "HVLM", 0.9, {})
    assert rd["R4"]["by_rule"]["timeout"]["checks"] == {"mean_nonnegative_vs_retuned": True,
                                                        "noninferior_0p25_vs_retuned": True,
                                                        "superior_sign_0p05_vs_retuned": True}
    assert "checks" not in rd["R4"]["by_rule"]["nach"]
    assert rd["R5"]["threshold_direction"] == "higher" and rd["R5"]["checks"]["threshold_rises"] is True
    assert rd["R5"]["checks"]["tables_start_earlier"] is None                       # no refitted table yet
    assert sr.readings(cmp, {}, dict(sel, selected_h="2"), None, "HVLM", 1.05, {})["R5"]["checks"] == \
        {"threshold_rises": None, "tables_start_earlier": None, "same_direction": None}


def test_table_change_and_monotone_split(tmp_path):
    old = cr.table_facts(write(tmp_path / "old.json", table(CL)))
    new = [r[:] for r in CL]
    new[2][0], new[3][1] = 1, 1                 # starts where the 0.98 table waits: 2 cells
    new[1][3] = 0                               # waits where it starts: 1 cell
    nf = cr.table_facts(write(tmp_path / "new.json", table(new)))
    ch = sr.table_change(nf, old)
    assert (ch["cells_differ"], ch["fire_gained"], ch["fire_lost"], ch["direction"]) == (3, 2, 1, "mixed")
    assert old["level_h_by_arrival_bin"] == [0.5, 1.0, 2.0, 2.0]
    assert ch["level_new"] == [1.0, 2.0, 2.0, None] and ch["level_shift"] == [0.5, 1.0, 0.0, None]
    earlier = [r[:] for r in CL]
    earlier[2][0] = 1
    assert sr.table_change(cr.table_facts(write(tmp_path / "e.json", table(earlier))), old)["direction"] == "earlier"
    assert sr.table_change(old, cr.table_facts(tmp_path / "e.json"))["direction"] == "later"
    same = sr.table_change(old, old)
    assert (same["cells_differ"], same["direction"], same["agree_old_on_new_records"]) == (0, "same", 1.0)
    assert sr.table_change(None, old) is None
    two = [[0] * 4 for _ in range(6)]
    two[1][0] = 1                               # 0 above 1 in the residual, and 1 then 0 along the arrival
    assert sr.monotone_split(two) == (1, 1)
    assert cr.table_facts(write(tmp_path / "two.json", table(two)))["monotone_violations"] == 2
    assert sr.monotone_split(CL) == (0, 0)


def test_crn_breach_is_a_problem():
    data = {"timeout": {64: {"released_per_day": 40.0}, 65: {"released_per_day": 41.0}},
            "clock": {64: {"released_per_day": 40.0}, 65: {"released_per_day": 41.5}}}
    problems = []
    assert sr.crn_check(data, problems, "rate 0.9 HVLM") == [65]
    assert len(problems) == 1 and "seed 65" in problems[0]


def test_end_to_end_on_a_partial_tree(tmp_path, capsys):
    t = Tree(tmp_path)
    for k in ("timeout", "mbs", "nach", "clock"):
        t.put(0.9, "HVLM", k, range(64, 68), base=33.0)
    for k in ("tbl_timeout", "tbl_mbs", "tbl_nach"):
        t.put(0.9, "HVLM", k, range(64, 67), base=35.0)
    launched = sr.policy_spec(0.9, "HVLM", t.P, None)["tbl_nach"]["files"][67] + ".err"
    open(launched, "w").close()
    out = tmp_path / "res" / "r.json"
    res = sr.main(t.args(out))
    R = strict(out)
    assert {k: (v["status"], v["stage"]) for k, v in R["rates"].items()} == {
        "0.9": ("partial", "A"), "0.8": ("not_started", None), "1.05": ("not_gated", None)}
    assert R["meta"]["finished"] is False and R["meta"]["complete"] is False and R["reference_0p98"] is None
    B = R["rates"]["0.9"]["HVLM"]
    assert B["status"]["runs_present"]["report"] == 4 * 4 + 3 * 3 and B["status"]["started_no_output"] == 1
    assert B["status"]["runs_expected"] == {"report": 320, "report_pending": 32, "select": 56, "records": 6,
                                            "tables": 3}
    for rk, rate in R["rates"].items():
        for fab in msj.FABS:
            for key, c in (rate.get(fab) or {}).get("comparisons", {}).items():
                if "n" in c:
                    assert c["n_expected"] == 32 and len(c["per_seed"]) == 32, (rk, fab, key)
    assert B["comparisons"]["tbl_timeout-timeout"]["n"] == 3 and B["policies"]["tbl_nach"]["started_no_output"] == [67]
    rd = B["readings"]
    for r in ("R2", "R3"):
        assert rd[r]["by_rule"]["timeout"]["pending"] == "no refitted table yet"
    assert rd["R4"]["by_rule"]["mbs"]["vs_clock"]["pending"] == "no refitted table yet"
    assert rd["R6"]["by_rule"]["nach"]["pending"] and rd["cells"]["by_rule"]["nach"]["pending"]
    assert rd["R1"]["by_rule"]["timeout"]["checks"]["positive_on_most_seeds"] is True
    assert rd["R1"]["by_rule"]["timeout"]["checks"]["smaller_than_0p98_mean"] is None      # no 0.98 reference
    assert B["tables"]["rft_timeout"] is None and B["tables"]["tbl_timeout"]["pinned_ok"] is False
    assert R["meta"]["missing"]["0.9"]["HVLM"]["timeout"] == list(range(68, 96))
    assert not any(n.startswith("results") for n in os.listdir(t.P["shift"]))
    assert "[NOT FINISHED]" in capsys.readouterr().out and res["meta"]["rates"] == ["0.9", "0.8", "1.05"]

    # the refitted table arrives with two runs: R2 is computed on those, R6 reads the table
    t.refit(0.9, "HVLM", "timeout", CL)
    t.put(0.9, "HVLM", "rft_timeout", range(64, 66), base=36.0)
    sr.main(t.args(out, "--quiet"))
    B = strict(out)["rates"]["0.9"]["HVLM"]
    assert B["comparisons"]["rft_timeout-timeout"]["n"] == 2 and "pending" not in B["readings"]["R2"]["by_rule"]["timeout"]
    assert B["tables"]["rft_timeout"]["source_ok"] is True
    assert B["readings"]["R6"]["by_rule"]["timeout"]["cells_differ_0p98"] == 0
    assert B["readings"]["cells"]["by_rule"]["timeout"]["cells_both"] == 24


def test_high_rate_skipped(tmp_path):
    t = Tree(tmp_path)
    assert sr.rate_status(1.05, t.P)["status"] == "not_gated"
    open(os.path.join(t.P["jobs"], "shift_r1p05_a.txt"), "w").close()
    assert sr.rate_status(1.05, t.P)["status"] == "not_started"
    note = "2026-10-20 12:00:00 rate 1.05 skipped; back-half WIP slopes (lots/day) and WIP at day 360: {...}"
    with open(os.path.join(t.P["shift"], "HIGH_SKIPPED.txt"), "w") as f:
        f.write(note + "\n")
    out = tmp_path / "r.json"
    sr.main(t.args(out, "--quiet"))
    R = strict(out)["rates"]["1.05"]
    assert (R["status"], R["high_skipped"]) == ("skipped", note) and "HVLM" not in R and "LVHM" not in R


def test_default_out_and_the_refusal(tmp_path):
    t = Tree(tmp_path)
    assert not sr.under(sr.default_out(False, t.P), t.P["shift"])
    assert sr.default_out(True, t.P) == os.path.join(t.P["shift"], "results.json")
    inside = os.path.join(t.P["shift"], "results.json")
    with pytest.raises(SystemExit) as e:
        sr.main(t.args(inside))
    assert e.value.code == 2 and not os.path.exists(inside)
    for name in ("shift_r0p90_b.done", "shift_r0p80_b.done"):
        with open(os.path.join(t.P["jobs"], name), "w") as f:
            f.write("done 2026-10-20 12:00:00 failed=1\n")
    open(os.path.join(t.P["shift"], "HIGH_SKIPPED.txt"), "w").close()
    res = sr.main(t.args(None, "--quiet"))                     # finished: the default is the block's results.json
    assert res["meta"]["finished"] is True and strict(inside)["meta"]["finished"] is True
    assert sum("failed job" in d for d in res["meta"]["deviations"]) == 2


def test_tex(tmp_path):
    pytest.importorskip("confirm_tables")
    t = Tree(tmp_path)
    for k in ("timeout", "tbl_timeout"):
        t.put(0.9, "HVLM", k, range(64, 67))
    out = tmp_path / "r.json"
    with pytest.raises(SystemExit) as e:
        sr.main(t.args(out, "--tex", "--quiet"))
    assert e.value.code == 2 and not out.exists()
    tex = tmp_path / "shift.tex"
    sr.main(t.args(out, "--tex", "--tex-out", str(tex), "--quiet"))
    s = tex.read_text(encoding="utf-8")
    assert r"\textbf{??}" in s and "Paired on 3 of the 32 seeds." in s and r"\label{tab:shift}" in s
    assert "% PARTIAL" in s and r"\emph{HVLM}" in s and r"1.5~h at 0.98" in s and " & timeout & " in s


# ---------------------------------------------------------------- the block's own files (read only)

REAL = sr.paths()


@pytest.mark.parametrize("rate", [0.9, 0.8])
def test_real_job_files_name_the_expected_outputs(rate):
    jf = os.path.join(REAL["jobs"], f"shift_{msj.rtag(rate)}_a.txt")
    if not os.path.exists(jf):
        pytest.skip(f"no {jf}")
    with open(jf, encoding="utf-8") as f:
        got = {os.path.basename(msj.out_of(ln.strip())) for ln in f if "  ->  " in ln and not ln.startswith("#")}
    want = set()
    for fab in msj.FABS:
        sp = sr.policy_spec(rate, fab, REAL, None)
        want |= {os.path.basename(p) for k, e in sp.items() if not k.startswith("rft_") for p in e["files"].values()}
        want |= {os.path.basename(p) for fs in sr.select_spec(rate, fab, REAL).values() for p in fs.values()}
        want |= {os.path.basename(p) for tag, _ in msj.RULES for p in sr.dump_paths(fab, tag, rate, REAL).values()}
    assert got == want and len(got) == 572
    specs = {fab: sr.policy_spec(rate, fab, REAL, sr.selection_block(rate, fab, REAL, [])["selected_h"])
             for fab in msj.FABS}
    problems = []
    chk = sr.check_job_files(rate, specs, REAL, problems)
    assert chk["a"]["agree"] and (chk["fit"] is None or chk["fit"]["agree"]) and problems == []


def test_real_stale_tables():
    ref = os.path.join(sr.FINAL, "confirm", "results.json")
    R = json.load(open(ref, encoding="utf-8")) if os.path.exists(ref) else None
    for fab in msj.FABS:
        for tag, _ in msj.RULES:
            p = os.path.join(REAL["family"], os.path.basename(msj.stale(fab, tag)))
            if not os.path.exists(p):
                pytest.skip(f"no {p}")
            problems = []
            f = sr.facts(p, problems, pinned=True)
            assert f["pinned_ok"] is True and problems == []
            assert sum(sr.monotone_split(f["fire"])) == f["monotone_violations"]
            if R is not None:
                t = R[fab]["tables"][f"tbl_{sr.KEY[tag]}"]
                assert (f["monotone_violations"], f["cells_both"]) == (t["monotone_violations"], t["cells_both"])
            ch = sr.table_change(f, f)
            assert (ch["cells_differ"], ch["fire_gained"], ch["fire_lost"], ch["direction"]) == (0, 0, 0, "same")
            assert all(x in (None, 0.0) for x in ch["level_shift"]) and ch["agree_old_on_new_records"] == 1.0


def test_smoke_on_the_live_block(tmp_path):
    if not os.path.isdir(REAL["report"]):
        pytest.skip("no final/shift/report")

    def snapshot():
        return {os.path.join(d, n) for d, _, ns in os.walk(REAL["shift"]) for n in ns}

    sp = sr.policy_spec(0.9, "HVLM", REAL, None)
    A, B = sp["tbl_timeout"]["files"], sp["timeout"]["files"]

    def both():
        return [s for s in SEEDS if os.path.exists(A[s]) and os.path.exists(B[s])]

    before, both_before = snapshot(), both()
    out = tmp_path / "r.json"
    sr.main(["--out", str(out), "--no-log", "--quiet"])
    new = snapshot() - before                    # the chain keeps writing run files; this script writes none
    assert not [p for p in new if os.path.basename(p).startswith("results") or p.endswith("interim_looks.log")]
    if both() != both_before:
        pytest.skip("a run file appeared during the read")
    c = strict(out)["rates"]["0.9"]["HVLM"]["comparisons"]["tbl_timeout-timeout"]
    assert c["n"] == len(both_before)
    completed = lambda p: json.load(open(p, encoding="utf-8"))["scrap_kpi"]["completed_per_day"]   # noqa: E731
    for s, x in zip(SEEDS, c["per_seed"]):
        if s in both_before:
            assert abs(x - (completed(A[s]) - completed(B[s]))) < 1e-12
        else:
            assert x is None
    stats = pytest.importorskip("scipy.stats")
    if c["n"] > 1:
        d = np.array([x for x in c["per_seed"] if x is not None])
        lo, hi = stats.t.interval(0.95, len(d) - 1, loc=c["mean"], scale=d.std(ddof=1) / np.sqrt(len(d)))
        assert abs(c["lo"] - lo) < 1e-9 and abs(c["hi"] - hi) < 1e-9


@pytest.mark.parametrize("rate", [0.9, 0.8, 1.05])
def test_real_selection_agrees_with_its_file(rate):
    p = os.path.join(REAL["select"], f"selection_{msj.rtag(rate)}.json")
    if not os.path.exists(p):
        pytest.skip(f"no {p} yet")
    js = json.load(open(p, encoding="utf-8"))
    if not js:
        pytest.skip("rate skipped")
    for e in js:
        b = sr.selection_block(rate, e["fab"], REAL, [])
        assert b["selected_from_files"] == e["selected"]
        assert {th: round(b["grid"][th]["mean"], 3) for th in msj.THETAS} == e["grid"]


# ---------------------------------------------------------------- a block in the run files' own layout
#
# Two trees in temporary folders, as the chain leaves the block: run files with every field of a real file under
# final/shift/report, in its order (the ledgers and the trace trimmed); the six 0.98 tables copied from
# final/betarx/family (so their SHA-256 is the one PROTOCOL_confirm.md records); refitted tables in fit_q.py's
# layout; record dumps; the selection runs and the selection file stage_b writes; the job files of
# make_shift_jobs.py and run_queue.py's markers; the step-0 pair; a 0.98 reference (synthetic numbers).
#   full     0.90 and 0.80 finished with every run; 1.05 skipped after an unstable probe
#   partial  0.90 finished; 0.80 in stage B with LVHM's runs missing on some seeds, one file caught while written,
#            one file of another rate in a slot, two runs launched without output, one table not fitted yet;
#            1.05 not gated
# The retuned threshold is 1.5 h at 0.90 (both scenarios) and differs at 0.80 (HVLM 3 h, LVHM 0.75 h). Every number
# of the results file is recomputed here from what was written, the paired statistics with scipy.

import contextlib                   # noqa: E402
import hashlib                      # noqa: E402
import io                           # noqa: E402
import shutil                       # noqa: E402
import subprocess                   # noqa: E402
import zlib                         # noqa: E402

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RK = ("timeout", "mbs", "nach")
TAG = {"timeout": "timeout", "mbs": "mbs3", "nach": "nach"}         # policy key -> the rule's file tag
ARM = dict(msj.RULES)                                                 # file tag -> the rule's arm
FAB_I = {"HVLM": 0, "LVHM": 1}
H_STAR = {(0.9, "HVLM"): "1.5", (0.9, "LVHM"): "1.5", (0.8, "HVLM"): "3", (0.8, "LVHM"): "0.75"}
REFIT = {(0.9, "HVLM"): {"timeout": "same", "mbs": "same", "nach": "same"},
         (0.9, "LVHM"): {"timeout": "earlier", "mbs": "later", "nach": "mixed"},
         (0.8, "HVLM"): {"timeout": "earlier", "mbs": "earlier", "nach": "earlier"},
         (0.8, "LVHM"): {"timeout": "later", "mbs": "drawn", "nach": "later"}}
DRAWN = [[1, 1, 1, 1], [1, 1, 1, 1], [1, 0, 1, 1], [0, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]   # 1 + 1 violations
GAP = (0.8, "LVHM")                                                   # where the partial tree has its holes
HOLES = {"timeout": range(70, 74), "clock_rt": (64, 65), "tbl_timeout": range(90, 96), "rft_timeout": range(80, 96),
         "rft_mbs": range(65, 96), "rft_nach": SEEDS}
TRUNCATED, OTHER_RATE = ("clock_rt", 66), ("mbs", 95)
LAUNCHED = (("rft_timeout", 80), ("rft_timeout", 81))
NOT_FITTED, NO_DUMP = "nach", 101                                     # LVHM nach at 0.80: one dump, no table yet
BASE = {"timeout": 33.0, "mbs": 31.6, "nach": 31.9, "clock": 34.4, "clock_rt": 34.7, "tbl_timeout": 34.9,
        "tbl_mbs": 34.6, "tbl_nach": 34.3, "rft_timeout": 35.3, "rft_mbs": 34.9, "rft_nach": 34.5}
UNDERFULL = {"timeout": 26900, "mbs": 35500, "nach": 29200, "clock": 2700, "clock_rt": 2400}  # loads, days 87-360
TIES = (70, 71)                     # seeds on which tbl_nach completes exactly as many lots as the control limit
REF = {"HVLM": {"timeout": (1.76, 5.0, 0.47, 1.3), "mbs": (2.87, 8.5, 0.21, 0.6), "nach": (2.58, 7.6, -0.06, -0.2)},
       "LVHM": {"timeout": (1.93, 5.5, 0.30, 0.8), "mbs": (3.30, 9.6, 0.12, 0.3), "nach": (3.02, 8.8, -0.15, -0.4)}}
WINDOW = 360 - 87                   # days 87-360, over which completions, scraps and loads are counted


def layout(arm, fab, rate, seed, theta=None, level=None):
    """a run file with every field batch_fire.py writes, in its order (copied from final/shift/report/
    batch_fire_HVLM_r0.9_d360_s64_level1_HVLM_timeout_b0p003_t1_qtcr_scrap.json, ledgers and trace trimmed; a rule's
    file has no level); fill() sets the numbers shift_report reads"""
    j = {"arm": arm, "dataset": fab, "scale": rate, "seed": seed, "days": 360, "base": "cr", "cqt_rule": "qtcr",
         "scrap": True,
         "scrap_kpi": {"completed_per_day": None, "scrapped_per_day": None, "on_time_pct_of_completed": 99.31,
                       "on_time_pct_of_completed_plus_scrapped": 67.84, "cycle_p50_days": None, "scrapped_total": None},
         "warmup_days": 87.0, "wall_s": 941.8, "on_time_regular_pct": 100.0, "act_regular_days": 27.140117201154208,
         "resolved": 309805, "violations": 4424, "violation_rate_pct": 1.428, "clocks_started": 431960,
         "batch_fill": 0.9601, "batches_fired": 33371, "batches_partial": None, "batch_fill_all": 0.9725,
         "batches_fired_all": 35109, "batches_partial_all": None,
         "family_ledger": {
             "Diffusion_BE_123|468_Diffusion": {"batch_max": 4, "loads": 2605, "lots": 10070, "partial": 222,
                                                "fill": 0.9664, "partial_pct": 8.52, "util_pct": 48.61},
             "Diffusion_BE_123|635_Diffusion": {"batch_max": 5, "loads": 2145, "lots": 9543, "partial": 579,
                                                "fill": 0.8898, "partial_pct": 26.99, "util_pct": 48.61}},
         "fam_util": {"DE_BE_11": {"n": 10, "util_pct": 44.07, "down_pct": 0.0, "setup_pct": 0.0},
                      "DE_BE_12": {"n": 9, "util_pct": 53.66, "down_pct": 0.0, "setup_pct": 0.0}},
         "blocking": {"batch_deaths": None, "batch_deaths_no_server": 364, "nonbatch_deaths": None,
                      "by_family": {"EPI_38": 664, "Diffusion_FE_94": 686, "Diffusion_FE_126": 91}},
         "entry_slack_h": {"Diffusion_BE_123|468_Diffusion": {
             "n": 9415, "min": 4.38, "max": 10.0, "mean": 9.959, "distinct_rounded": [4.4, 4.5, 4.8, 4.9, 5.2],
             "n_distinct_rounded": 49, "p05": 10.0, "p95": 10.0}},
         "variant": "none", "variant_manifest": [], "throughput_back_half": 34.85925925925926, "wip_end": None,
         "wip_slope_back_half": None, "released_per_day": None,
         "env_stats": {"went_tardy": 92, "dispatch": 6187209, "lots_dispatched": 6367806, "auto": 6274256,
                       "defer": 677169, "defer_minruns": 254839, "ontime": 13381, "late": 90},
         "trace": [{"day": 10.0, "wip": 2010, "done": 437}, {"day": 20.0, "wip": 1659, "done": 1079},
                   {"day": 360.0, "wip": 1298, "done": 13471}],
         "minrun_break_h": 0.0, "theta": theta, "temp": 1.0, "eps": 0.0, "eps_fw": 0.0, "eps_wf": 0.0,
         "nxt_noise_min": 0.0, "nxt_missing": 0.0, "hmap": None, "source_gate": None}
    if level is not None:
        j["level"] = level
    j["minrun_net_setup"] = False
    return j


def level_of(art):
    """the level field batch_fire.py writes for a table (level.py's to_dict): the artefact's start map and edges"""
    z11, z6 = [0.0] * 11, [0.0] * 6
    return {"h0": art["h0"], "kind": "table", "beta": art["beta"], "hidden": art["hidden"], "features": art["features"],
            "w": z11, "W1": [z11] * 6, "b1": z6, "w2": z6, "b2": 0.0, "gamma": z11, "g0": 1.0, "t_head": -1.0,
            "t_own": -1.0, "Wp": [z11] * 6, "bp": z6, "wg": z6, "bg": 0.0, "ww": z6, "bw": 0.5, "mask": [],
            "masked_features": [], "wq": z11, "q0": -1.0, "temp": 1.0, "edges": art["edges"], "fire": art["fire"],
            "lam": art["lam"], "H": None}


def fill(j, fab, rate, seed, key, level, sd=0.3):
    """the numbers of one run: the policy's level, a seed effect every policy of the seed shares and the run's own
    noise, completions rounded as batch_fire.py rounds them; every policy of a seed releases the same lots"""
    r100 = int(round(rate * 100))
    e = np.random.default_rng([FAB_I[fab], r100, seed]).normal(0.0, 0.6)
    g = np.random.default_rng([FAB_I[fab], r100, seed, zlib.crc32(key.encode())])
    c = round(float(level - 10.0 * (0.9 - rate) - 0.5 * FAB_I[fab] + e + g.normal(0.0, sd)), 2)
    sc = round(float(19.0 - 0.4 * (c - 33.0) + g.normal(0.0, 0.3)), 2)
    bpa = int(UNDERFULL.get(key, 2300) + g.integers(-300, 300))
    j["scrap_kpi"].update(completed_per_day=c, scrapped_per_day=sc, scrapped_total=int(round(sc * 360)),
                          cycle_p50_days=round(float(22.8 + g.normal(0.0, 0.1)), 2))
    j["blocking"].update(batch_deaths=int(1500 - 120 * (c - 33.0) + g.integers(-80, 80)),
                         nonbatch_deaths=int(3400 + g.integers(-150, 150)))
    j.update(batches_partial_all=bpa, batches_partial=int(1.33 * bpa + g.integers(0, 50)),
             released_per_day=51.53333333333333 * rate / 0.9 + 0.01 * (seed % 7),
             wip_slope_back_half=float(g.normal(0.05, 0.1)), wip_end=int(1200 + g.integers(-100, 100)))
    return j


def grid_level(h):
    """completions over the threshold grid, highest at h"""
    return {th: 34.6 - 0.8 * abs(np.log2(float(th) / float(h))) for th in msj.THETAS}


def file_of(fab, arm, theta, rate, seed):
    """a run file's name as make_shift_jobs.py's job lines name it"""
    line = msj.rule_run(fab, arm, rate, seed, "x") if theta is None else msj.table_run(fab, theta, rate, seed, "x")
    return os.path.basename(msj.out_of(line))


def stage_b_text(rate):
    """the job file make_shift_jobs.stage_b writes after the fits and the selection runs (stage_b itself writes into
    the block, so it is not called here)"""
    lines = []
    for fab in msj.FABS:
        for tag, _ in msj.RULES:
            lines += [msj.table_run(fab, msj.refit(fab, tag, rate), rate, s, f"{msj.S}/report") for s in msj.REPORT_SEEDS]
        if H_STAR[(rate, fab)] != "1.5":
            lines += [msj.rule_run(fab, f"clock:{H_STAR[(rate, fab)]}", rate, s, f"{msj.S}/report")
                      for s in msj.REPORT_SEEDS]
    return msj.job_file(f"stage B at rate {msj.rname(rate)}: refitted tables and the retuned control limit on seeds "
                        f"64-95", lines)


def fire2d(art):
    return [[c[0] for c in row] for row in art["fire"]]


def wrap(m):
    return [[[int(v)] for v in row] for row in m]


def start_map(mode, S):
    """a refitted start map from the 0.98 one: starts in one more cell, waits in one more, both, or DRAWN"""
    if mode == "drawn":
        return [r[:] for r in DRAWN]
    F = [r[:] for r in S]
    if mode in ("earlier", "mixed"):
        i = next(i for i, r in enumerate(S) if 0 in r)                  # the first row that waits somewhere
        F[i][max(j for j, v in enumerate(S[i]) if v == 0)] = 1           # starts in its last waiting cell
    if mode in ("later", "mixed"):
        i = max(i for i, r in enumerate(S) if 1 in r)                   # the last row that starts somewhere
        F[i][min(j for j, v in enumerate(S[i]) if v == 1)] = 0           # waits in its first starting cell
    return F


def refit_artefact(stale_art, fab, tag, rate, F, ri):
    """a refitted table in fit_q.py's layout: the 0.98 artefact's fields with the start map F, the new records'
    cell counts (one cell at exactly n0, three or four short of it) and the two new dumps as its source"""
    a = json.loads(json.dumps(stale_art))
    nf = [[40 + 7 * i + 3 * j for j in range(4)] for i in range(6)]
    nw = [[150 + 20 * i * (j + 1) for j in range(4)] for i in range(6)]
    nf[1][3], nf[5][2], nw[0][2], nf[4][ri] = 10, 2, 9, 3
    if ri == 2:
        nw[3][3] = 0
    k0 = a["K0"]
    both = [[int(nf[i][j] >= k0 and nw[i][j] >= k0) for j in range(4)] for i in range(6)]
    a.update(fire=wrap(F), fire_own=wrap(F), own_entry=wrap(both), n_fired=wrap(nf), n_waited=wrap(nw),
             source=[msj.dump(fab, tag, rate, s) for s in msj.RECORD_SEEDS], n_transitions=150000 + 1000 * ri)
    return a


def reference_file():
    """final/confirm/results.json reduced to what shift_report reads, with the numbers of REF"""
    R = {"meta": {"generated": "2026-10-10 03:27:03", "finished": True}}
    for fab in msj.FABS:
        C, Pp, T = {}, {"clock": {"n": 32, "completed": 34.5}}, {}
        for i, k in enumerate(RK):
            m1, p1, m2, p2 = REF[fab][k]
            C[f"tbl_{k}-{k}"] = {"n": 32, "mean": m1, "lo": m1 - 0.2, "hi": m1 + 0.2, "wins": 32, "losses": 0,
                                 "ties": 0, "pct": p1}
            C[f"tbl_{k}-clock"] = {"n": 32, "mean": m2, "lo": m2 - 0.2, "hi": m2 + 0.2, "wins": 18, "losses": 14,
                                   "ties": 0, "pct": p2}
            Pp[k], Pp[f"tbl_{k}"] = {"n": 32, "completed": 33.0 + 0.3 * i}, {"n": 32, "completed": 35.0 + 0.3 * i}
            T[f"tbl_{k}"] = {"cells_both": 22 - 10 * (k == "nach"), "monotone_violations": 0}
        R[fab] = {"comparisons": C, "policies": Pp, "tables": T}
    return R


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


class Block:
    """a block on disk, and a registry of what it holds that shift_report should read: runs[(rate, fab, key)] and
    select[(rate, fab, theta)] = {seed: run file}, refits[(rate, fab, rule)] and stale[(fab, rule)] = artefact,
    dumps = {(rate, fab, rule, seed)}"""

    def __init__(self, root, partial, like=None):
        self.root, self.partial, self.like, self.hashes, self.dirs = str(root), partial, like, {}, set()
        self.P = sr.paths(os.path.join(self.root, "final", "shift"),
                          os.path.join(self.root, "final", "betarx", "family"), os.path.join(self.root, "jobs"),
                          os.path.join(self.root, "final", "confirm", "results.json"))
        self.runs, self.select, self.refits, self.stale, self.dumps, self.probe = {}, {}, {}, {}, set(), {}
        self.high = None
        for fab in msj.FABS:
            for k in RK:
                src = os.path.join(sr.FAMILY, os.path.basename(msj.stale(fab, TAG[k])))
                if not os.path.exists(src):
                    pytest.skip(f"no {src}")
                dst = os.path.join(self.P["family"], os.path.basename(src))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)                          # byte for byte: the pinned SHA-256 holds
                with open(dst, encoding="utf-8") as f:
                    self.stale[(fab, k)] = json.load(f)
        self.put_json(self.P["reference"], reference_file())
        for rate in (0.9, 0.8):
            self.write_rate(rate)
        self.write_step0()
        if not partial:
            self.write_skipped_high()

    def put(self, path, text):
        """write a file, or hard-link it to the same file of the tree this one is built like: that one has been
        read once already, and a file read for the first time after it was written costs several times more"""
        rel = os.path.relpath(path, self.root)
        h = self.hashes[rel] = hashlib.sha1(text.encode("utf-8")).digest()
        d = os.path.dirname(path)
        if d not in self.dirs:
            os.makedirs(d, exist_ok=True)
            self.dirs.add(d)
        if self.like is not None and self.like.hashes.get(rel) == h:
            try:
                os.link(os.path.join(self.like.root, rel), path)
                return
            except OSError:                                         # no hard links here: write it
                pass
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def put_json(self, path, obj):
        self.put(path, json.dumps(obj))

    def gap(self, rate, fab):
        return self.partial and (rate, fab) == GAP

    def write_rate(self, rate):
        t, J = msj.rtag(rate), self.P["jobs"]
        self.put(os.path.join(J, f"shift_{t}_a.txt"), msj.stage_a(rate))
        self.put(os.path.join(J, f"shift_{t}_fit.txt"), msj.stage_fit(rate))
        self.put(os.path.join(J, f"shift_{t}_b.txt"), stage_b_text(rate))
        for st in (("a", "fit") if self.partial and rate == 0.8 else ("a", "fit", "b")):
            self.put(os.path.join(J, f"shift_{t}_{st}.done"), "done 2026-10-14 12:00:00 failed=0\n")
        notes = []
        for fab in msj.FABS:
            notes.append(self.write_selection(rate, fab))
            self.write_records(rate, fab)
            self.write_report(rate, fab)
        self.put_json(os.path.join(self.P["select"], f"selection_{t}.json"), notes)

    def write_selection(self, rate, fab):
        """the grid runs, and the entry stage_b writes for them"""
        lv, means = grid_level(H_STAR[(rate, fab)]), []
        for th in msj.THETAS:
            V = self.select[(rate, fab, th)] = {}
            for s in msj.SELECT_SEEDS:
                V[s] = fill(layout(f"clock:{th}", fab, rate, s), fab, rate, s, f"clock:{th}", lv[th], sd=0.1)
                self.put_json(os.path.join(self.P["select"], file_of(fab, f"clock:{th}", None, rate, s)), V[s])
            means.append(sum(V[s]["scrap_kpi"]["completed_per_day"] for s in msj.SELECT_SEEDS) / len(msj.SELECT_SEEDS))
        best = msj.THETAS[max(range(len(msj.THETAS)), key=lambda i: (means[i], -i))]
        assert best == H_STAR[(rate, fab)], (rate, fab, means)    # the design holds
        return {"fab": fab, "rate": msj.rname(rate), "grid": dict(zip(msj.THETAS, [round(m, 3) for m in means])),
                "selected": best}

    def write_records(self, rate, fab):
        for ri, k in enumerate(RK):
            tag = TAG[k]
            for s in msj.RECORD_SEEDS:
                if self.gap(rate, fab) and (k, s) == (NOT_FITTED, NO_DUMP):
                    continue
                self.put_json(os.path.join(self.P["records"], os.path.basename(msj.dump(fab, tag, rate, s))),
                              {"seed": s, "arm": ARM[tag], "decisions": [], "scrapped": []})
                self.dumps.add((rate, fab, k, s))
            if self.gap(rate, fab) and k == NOT_FITTED:
                continue
            art = refit_artefact(self.stale[(fab, k)], fab, tag, rate,
                                 start_map(REFIT[(rate, fab)][k], fire2d(self.stale[(fab, k)])), ri)
            self.put_json(os.path.join(self.P["tables"], os.path.basename(msj.refit(fab, tag, rate))), art)
            self.refits[(rate, fab, k)] = art

    def write_report(self, rate, fab):
        h = H_STAR[(rate, fab)]
        pols = [(k, ARM[TAG[k]], None) for k in RK] + [("clock", "clock:1.5", None)]
        pols += [("clock_rt", f"clock:{h}", None)] if h != "1.5" else []
        pols += [(f"tbl_{k}", "level:1", msj.stale(fab, TAG[k])) for k in RK]
        pols += [(f"rft_{k}", "level:1", msj.refit(fab, TAG[k], rate)) for k in RK]
        gap = self.gap(rate, fab)
        for key, arm, theta in pols:
            V = self.runs[(rate, fab, key)] = {}
            art = (None if theta is None else self.stale[(fab, key[4:])] if key.startswith("tbl_")
                   else self.refits.get((rate, fab, key[4:])))
            for s in SEEDS:
                p = os.path.join(self.P["report"], file_of(fab, arm, theta, rate, s))
                if gap and (key, s) in LAUNCHED:
                    self.put(p + ".err", "")                             # the queue has started it
                if gap and s in HOLES.get(key, ()):
                    continue
                j = fill(layout(arm, fab, rate, s, theta, None if art is None else level_of(art)),
                         fab, rate, s, key, BASE[key])
                if key == "tbl_nach" and s in TIES:
                    j["scrap_kpi"]["completed_per_day"] = self.runs[(rate, fab, "clock")][s]["scrap_kpi"]["completed_per_day"]
                if gap and (key, s) == TRUNCATED:
                    self.put(p, json.dumps(j)[:300])                     # caught while it is written
                    continue
                if gap and (key, s) == OTHER_RATE:
                    self.put_json(p, dict(j, scale=0.9))                 # a 0.90 file in a 0.80 slot
                    continue
                self.put_json(p, j)
                if gap and key == "rft_timeout":
                    self.put(p + ".err", "")                             # the queue's log beside a finished run
                V[s] = j

    def write_step0(self):
        name = file_of("HVLM", "timeout:1", None, 0.9, msj.STEP0_SEED)
        j = self.runs[(0.9, "HVLM", "timeout")][msj.STEP0_SEED]
        for d, wall in (("a", 1284.1), ("b", 1290.7)):
            self.put_json(os.path.join(self.P["step0"], d, name), dict(j, wall_s=wall))
        self.put(os.path.join(self.P["jobs"], "shift_step0.pass"),
                 "2026-10-14 16:30:00 1 pairs identical (all fields but wall_s)\n")

    def write_skipped_high(self):
        """what make_shift_jobs.gate_high leaves after a probe with one back-half WIP slope of 1 lot/day or more"""
        slopes = {}
        for fab, s, slope in (("HVLM", 64, 0.21), ("HVLM", 65, 1.37), ("LVHM", 64, -0.12), ("LVHM", 65, 0.48)):
            j = fill(layout("clock:1.5", fab, msj.HIGH, s), fab, msj.HIGH, s, "clock", BASE["clock"])
            j["wip_slope_back_half"] = slope
            self.put_json(os.path.join(self.P["probe"], file_of(fab, "clock:1.5", None, msj.HIGH, s)), j)
            self.probe[f"{fab} s{s}"] = j
            slopes[f"{fab} s{s}"] = (slope, j["wip_end"])
        for st in ("a", "fit"):
            self.put(os.path.join(self.P["jobs"], f"shift_{msj.rtag(msj.HIGH)}_{st}.txt"),
                     msj.job_file(f"rate {msj.rname(msj.HIGH)} skipped: unstable", []))
        self.high = (f"2026-10-20 12:00:00 rate {msj.rname(msj.HIGH)} skipped; back-half WIP slopes (lots/day) and "
                     f"WIP at day 360: {slopes}")
        self.put(os.path.join(self.P["shift"], "HIGH_SKIPPED.txt"), self.high + "\n")

    def args(self):
        P = self.P
        return ["--shift-dir", P["shift"], "--family-dir", P["family"], "--jobs-dir", P["jobs"],
                "--reference", P["reference"], "--no-log"]

    def read(self, *more):
        self.out, self.tex = os.path.join(self.root, "results.json"), os.path.join(self.root, "shift.tex")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sr.main(self.args() + ["--out", self.out] + list(more))
        self.res, self.md = strict(self.out), buf.getvalue()
        return self

    def block(self, rate, fab):
        return self.res["rates"][msj.rname(rate)][fab]


@pytest.fixture(scope="module")
def partial(tmp_path_factory):
    return Block(tmp_path_factory.mktemp("partial"), partial=True).read()


@pytest.fixture(scope="module")
def full(partial, tmp_path_factory):
    b = Block(tmp_path_factory.mktemp("full"), partial=False, like=partial)
    return b.read("--tex", "--tex-out", os.path.join(b.root, "shift.tex"))


def value(run, key):
    """a number shift_report takes from a run file, from the file's own fields"""
    k, blk = run["scrap_kpi"], run["blocking"]
    return {"completed": k["completed_per_day"], "scrapped": k["scrapped_per_day"], "cycle_p50_days": k["cycle_p50_days"],
            "scrapped_furnace": blk["batch_deaths"] / WINDOW, "scrapped_other": blk["nonbatch_deaths"] / WINDOW,
            "underfull_per_day": run["batches_partial_all"] / WINDOW,
            "underfull_per_day_run": run["batches_partial"] / 360.0}[key]


def by_hand(stats, A, B, key="completed"):
    """A - B on the seeds both have: the mean, the 95% interval from scipy's Student quantile and again from
    scipy.stats.ttest_rel, the sign test from scipy.stats.binomtest with ties dropped"""
    s = [x for x in SEEDS if x in A and x in B]
    a = np.array([value(A[x], key) for x in s], float)
    b = np.array([value(B[x], key) for x in s], float)
    d, n = a - b, len(s)
    e = {"n": n, "seeds": s, "d": d, "mean": None, "pct": None, "lo": None, "hi": None, "sd": None, "p_sign": None,
         "wins": 0, "losses": 0, "ties": 0}
    if n:
        w, lo = int((d > 0).sum()), int((d < 0).sum())
        e.update(mean=float(d.mean()), wins=w, losses=lo, ties=n - w - lo, pct=100.0 * d.mean() / b.mean(),
                 p_sign=stats.binomtest(w, w + lo, 0.5).pvalue if w + lo else 1.0)
    if n > 1:
        sd = float(d.std(ddof=1))
        half = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
        r = stats.ttest_rel(a, b)
        ci = r.confidence_interval(0.95)
        e.update(sd=sd, lo=e["mean"] - half, hi=e["mean"] + half, t=float(r.statistic), ci=(ci.low, ci.high))
    return e


def close(x, y, tol=1e-9, where=""):
    assert x is not None and y is not None and abs(x - y) <= tol * max(1.0, abs(y)), (where, x, y)


def check_pair(c, e, where):
    assert c["n"] == e["n"], where
    if not e["n"]:
        assert c["mean"] is None and c["lo"] is None and c["pct"] is None and c["p_sign"] is None, where
        assert (c["wins"], c["losses"], c["ties"]) == (0, 0, 0), where
        return
    close(c["mean"], e["mean"], where=where)
    close(c["pct"], e["pct"], where=where)
    close(c["p_sign"], e["p_sign"], 1e-12, where)
    assert (c["wins"], c["losses"], c["ties"]) == (e["wins"], e["losses"], e["ties"]), where
    if e["n"] > 1:
        close(c["sd"], e["sd"], where=where)
        for got, want in ((c["lo"], e["lo"]), (c["hi"], e["hi"]), (c["lo"], e["ci"][0]), (c["hi"], e["ci"][1])):
            close(got, want, where=where)
        close(c["t"], e["t"], 1e-8, where)
    else:
        assert c["lo"] is None and c["hi"] is None and c["sd"] is None, where


def lt(x, y):
    return None if x is None or y is None else x < y


def ge(x, y):
    return None if x is None or y is None else x >= y


def violations(F):
    """(residual, arrival): a start below a wait in the residual; a wait right of a start along the arrival"""
    res = sum(F[i][j] == 0 and F[i + 1][j] == 1 for i in range(len(F) - 1) for j in range(len(F[0])))
    arr = sum(F[i][j] == 1 and F[i][j + 1] == 0 for i in range(len(F)) for j in range(len(F[0]) - 1))
    return res, arr


def levels(F, edges):
    """per arrival bin, the residual edge below which the column starts, where the column is 1...1 0...0"""
    out = []
    for j in range(len(F[0])):
        col = [F[i][j] for i in range(len(F))]
        k = sum(col)
        out.append(edges[k] if col == [1] * k + [0] * (len(col) - k) else None)
    return out


def test_the_run_files_have_the_block_s_layout(partial):
    """the hand-built run files carry every field of the block's own files, in order and of the same type"""
    pairs = [((0.9, "HVLM", "timeout"), file_of("HVLM", "timeout:1", None, 0.9, 64)),
             ((0.9, "HVLM", "tbl_timeout"), file_of("HVLM", "level:1", msj.stale("HVLM", "timeout"), 0.9, 64))]
    if not all(os.path.exists(os.path.join(REAL["report"], n)) for _, n in pairs):
        pytest.skip("no seed-64 runs in final/shift/report")
    for key, name in pairs:
        mine = partial.runs[key][64]
        with open(os.path.join(REAL["report"], name), encoding="utf-8") as f:
            real = json.load(f)
        assert list(mine) == list(real), name
        assert {k: type(v).__name__ for k, v in mine.items()} == {k: type(v).__name__ for k, v in real.items()}, name
        for f in ("scrap_kpi", "blocking", "env_stats"):
            assert list(mine[f]) == list(real[f]), (name, f)
        for f in ("family_ledger", "fam_util", "entry_slack_h"):
            first = next(iter(mine[f]))
            assert set(mine[f]) <= set(real[f]) and list(mine[f][first]) == list(real[f][first]), (name, f)
        assert list(mine["trace"][0]) == list(real["trace"][0])
        if "level" in real:
            assert list(mine["level"]) == list(real["level"]) and mine["level"]["fire"] == real["level"]["fire"]
            assert os.path.basename(mine["theta"]) == os.path.basename(real["theta"])


def test_partial_block_status_counts_and_problems(partial):
    R, m = partial.res, partial.res["meta"]
    assert {k: (v["status"], v["stage"]) for k, v in R["rates"].items()} == {
        "0.9": ("finished", None), "0.8": ("partial", "B"), "1.05": ("not_gated", None)}
    assert (m["finished"], m["complete"], m["block"]) == (False, False, False)
    for (rate, fab), h in H_STAR.items():
        st = partial.block(rate, fab)["status"]
        keys = [k for (r, f, k) in partial.runs if (r, f) == (rate, fab)]
        assert len(keys) == 10 + (h != "1.5")
        assert st["runs_expected"] == {"report": 32 * len(keys), "report_pending": 0, "select": 56, "records": 6,
                                       "tables": 3}
        assert st["runs_present"] == {
            "report": sum(len(partial.runs[(rate, fab, k)]) for k in keys), "select": 56,
            "records": sum((rate, fab, k, s) in partial.dumps for k in RK for s in msj.RECORD_SEEDS),
            "tables": sum((rate, fab, k) in partial.refits for k in RK)}
        assert st["complete"] is ((rate, fab) != GAP)
    LV = partial.block(*GAP)
    assert LV["status"]["runs_present"] == {"report": 28 + 31 + 32 + 32 + 29 + 26 + 32 + 32 + 16 + 1 + 0,
                                            "select": 56, "records": 5, "tables": 2}
    assert LV["status"]["started_no_output"] == 2 and LV["policies"]["rft_timeout"]["started_no_output"] == [80, 81]
    want = {k: [s for s in SEEDS if s not in partial.runs[GAP + (k,)]] for k in LV["policies"]}
    want = {k: v for k, v in want.items() if v}
    assert want == {"timeout": [70, 71, 72, 73], "mbs": [95], "clock_rt": [64, 65, 66],
                    "tbl_timeout": list(range(90, 96)), "rft_timeout": list(range(80, 96)),
                    "rft_mbs": list(range(65, 96)), "rft_nach": SEEDS}
    assert m["missing"]["0.8"] == {"LVHM": want} and set(m["missing"]) == {"0.8", "1.05"}
    assert len(m["problems"]) == 2, m["problems"]
    assert sum("unreadable, treated as missing" in p and "s66_clock0.75" in p for p in m["problems"]) == 1
    assert sum("not the block's configuration (scale)" in p and "s95_mbs3" in p for p in m["problems"]) == 1
    assert m["deviations"] == [] and len(m["notes"]) == 2
    assert all(v is True for v in m["stale_tables_pinned"].values()) and len(m["stale_tables_pinned"]) == 6
    assert m["step0"] == {"a_vs_b": True, "a_vs_block": True, "pass_lines": [
        "2026-10-14 16:30:00 1 pairs identical (all fields but wall_s)"]}
    assert m["reference"]["generated"] == "2026-10-10 03:27:03"
    ok = lambda n: {"jobs": n, "expected": n, "agree": True}                                           # noqa: E731
    assert R["rates"]["0.9"]["job_files"] == {"a": ok(572), "fit": ok(6), "b": ok(192)}
    assert R["rates"]["0.8"]["job_files"] == {"a": ok(572), "fit": ok(6), "b": ok(192 + 64)}
    assert R["rates"]["1.05"]["job_files"] == {"a": None, "fit": None, "b": None}
    present = sum(len(v) for v in partial.runs.values())
    assert m["runs_present"] == {"report": present, "select": 224, "records": 23, "tables": 11}
    assert m["runs_expected"] == {"report": 640 + 704 + 640, "report_pending": 64, "select": 336, "records": 36,
                                  "tables": 18}
    assert (f"Runs present of expected: report {present}/1984 (+64 if a retuned threshold is not 1.5 h), selection "
            f"224/336, record dumps 23/36, refitted tables 11/18; launched without output yet: 2.") in partial.md
    for fab in msj.FABS:                                    # the rate not gated yet: every policy and reading empty
        B = partial.block(1.05, fab)
        assert all(q["n"] == 0 for q in B["policies"].values()) and "clock_rt" not in B["policies"]
        assert all(c["n"] == 0 and c["per_seed"] == [None] * 32 for c in B["comparisons"].values() if "n" in c)
        assert B["status"]["runs_expected"]["report_pending"] == 32 and B["readings"]["R5"]["pending"] == sr.PENDING


def test_every_paired_statistic_against_scipy(partial, full):
    stats = pytest.importorskip("scipy.stats")
    seen = {"32": 0, "fewer": 0, "one": 0, "none": 0, "ties": 0, "equal_h": 0}
    for b in (partial, full):
        for (rate, fab), h in H_STAR.items():
            C = b.block(rate, fab)["comparisons"]
            assert len(C) == 19
            for key, c in C.items():
                a, bb = key.split("-")
                if "n" not in c:
                    assert h == "1.5" and "clock_rt" in key and c["reason"] == sr.EQUAL
                    seen["equal_h"] += 1
                    continue
                where = (b.partial, rate, fab, key)
                A, B = b.runs[(rate, fab, a)], b.runs[(rate, fab, bb)]
                e = by_hand(stats, A, B)
                check_pair(c, e, where)
                assert (c["n_a"], c["n_b"], c["n_expected"], c["complete"]) == (len(A), len(B), 32, e["n"] == 32), where
                assert len(c["per_seed"]) == 32
                for s, x in zip(SEEDS, c["per_seed"]):
                    if s in e["seeds"]:
                        close(x, e["d"][e["seeds"].index(s)], where=where)
                    else:
                        assert x is None, where
                for k in sr.SECONDARY:
                    check_pair(c["secondary"][k], by_hand(stats, A, B, k), where + (k,))
                seen["32" if e["n"] == 32 else "fewer" if e["n"] > 1 else "one" if e["n"] == 1 else "none"] += 1
                seen["ties"] += e["ties"] > 0
    assert seen["32"] > 100 and seen["fewer"] >= 6 and seen["one"] == 3 and seen["none"] >= 4, seen
    assert seen["ties"] >= 8 and seen["equal_h"] == 2 * 2 * 4, seen


def test_policy_means_by_hand(partial, full):
    for b in (partial, full):
        for (rate, fab), h in H_STAR.items():
            Pol = b.block(rate, fab)["policies"]
            assert set(Pol) == {k for (r, f, k) in b.runs if (r, f) == (rate, fab)}
            for key, q in Pol.items():
                V, where = b.runs[(rate, fab, key)], (b.partial, rate, fab, key)
                s = sorted(V)
                assert q["n"] == len(V) and q["seeds_missing"] == [x for x in SEEDS if x not in V], where
                for f in ("completed", "scrapped", "scrapped_furnace", "scrapped_other", "cycle_p50_days",
                          "underfull_per_day", "underfull_per_day_run"):
                    assert q["per_seed"][f] == [value(V[x], f) if x in V else None for x in SEEDS], where
                    if V:
                        close(q[f], float(np.mean([value(V[x], f) for x in s])), where=where + (f,))
                    else:
                        assert q[f] is None, where
                if len(V) > 1:
                    close(q["sd"], float(np.std([value(V[x], "completed") for x in s], ddof=1)), where=where)
                if V:
                    close(q["line"]["released_per_day"], float(np.mean([V[x]["released_per_day"] for x in s])))
            assert Pol["clock"]["arm"] == "clock:1.5" and Pol["tbl_mbs"]["theta"].endswith(f"{fab}_mbs3_b0p003_t1.json")
            assert Pol["rft_nach"]["theta"].endswith(f"tables/{fab}_nach_{msj.rtag(rate)}_b0p003_t1.json")
            if h != "1.5":
                assert (Pol["clock_rt"]["arm"], Pol["clock_rt"]["tag"]) == (f"clock:{h}", f"clock{h}")
                assert Pol["clock_rt"]["label"] == f"control limit, $h = {h}$ h, retuned at {msj.rname(rate)}"


def test_selection_grid_by_hand(partial, full):
    for b in (partial, full):
        for (rate, fab), h in H_STAR.items():
            sel = b.block(rate, fab)["selection"]
            means = []
            for th in msj.THETAS:
                c = [b.select[(rate, fab, th)][s]["scrap_kpi"]["completed_per_day"] for s in msj.SELECT_SEEDS]
                g = sel["grid"][th]
                assert g["n"] == 8 and g["per_seed"] == c
                close(g["mean"], sum(c) / 8)
                close(g["sd"], float(np.std(c, ddof=1)))
                means.append(sum(c) / 8)
            assert means.index(max(means)) == msj.THETAS.index(h)
            assert (sel["selected_from_files"], sel["selected_h"], sel["agree"], sel["grid_agree"], sel["complete"]) == \
                (h, h, True, True, True)
            assert sel["selected_source"] == f"selection_{msj.rtag(rate)}.json" and sel["n_present"] == 56
            assert sel["selection_json"]["grid"] == {th: round(mu, 3) for th, mu in zip(msj.THETAS, means)}
            r5 = b.block(rate, fab)["readings"]["R5"]
            assert {th: g["n"] for th, g in r5["grid"].items()} == {th: 8 for th in msj.THETAS}


def test_retuned_threshold_equal_to_1p5(partial, full):
    for b in (partial, full):
        for fab in msj.FABS:
            B = b.block(0.9, fab)
            assert "clock_rt" not in B["policies"] and B["status"]["runs_expected"]["report"] == 320
            for k in RK:
                assert B["comparisons"][f"rft_{k}-clock_rt"] == {"same_as": f"rft_{k}-clock", "reason": sr.EQUAL,
                                                                 "reading": "R4", "declared": True}
            assert B["comparisons"]["clock_rt-clock"] == {"same_policy": True, "reason": sr.EQUAL,
                                                          "reading": "not declared (supplement to R5)",
                                                          "declared": False}
            assert B["readings"]["R4"]["retuned"] == {"selected_h": "1.5", "selected_source": "selection_r0p90.json",
                                                      "note": sr.EQUAL}
            assert B["readings"]["R5"]["threshold_direction"] == "same"
    assert "| R4 | rft_timeout - clock_rt | = rft_timeout-clock (retuned threshold is 1.5 h) |" in partial.md
    assert "| -- | clock_rt - clock | = identical (retuned threshold is 1.5 h) |" in partial.md


def test_r4_against_both_control_limits_by_hand(partial, full):
    stats = pytest.importorskip("scipy.stats")
    for b in (partial, full):
        for (rate, fab), h in H_STAR.items():
            R4 = b.block(rate, fab)["readings"]["R4"]
            assert R4["retuned"]["selected_h"] == h and R4["retuned"]["note"] == (sr.EQUAL if h == "1.5" else None)
            for k in RK:
                e, rft = R4["by_rule"][k], b.runs[(rate, fab, f"rft_{k}")]
                vc = by_hand(stats, rft, b.runs[(rate, fab, "clock")])
                assert e["vs_clock"]["n"] == vc["n"] and e["ref_0p98"]["mean"] == REF[fab][k][2]
                if h == "1.5":
                    use = vc
                    assert e["vs_retuned"] == {"comparison": f"rft_{k}-clock_rt", "same_as": f"rft_{k}-clock",
                                               "reason": sr.EQUAL, "reading": "R4", "declared": True}
                else:
                    use = by_hand(stats, rft, b.runs[(rate, fab, "clock_rt")])
                    assert e["vs_retuned"]["comparison"] == f"rft_{k}-clock_rt" and e["vs_retuned"]["n"] == use["n"]
                    if use["n"]:
                        close(e["vs_retuned"]["mean"], use["mean"])
                if k == "nach":
                    assert "checks" not in e
                    continue
                ok = use["n"] > 0
                assert e["checks"] == {
                    "mean_nonnegative_vs_retuned": ge(use["mean"], 0.0) if ok else None,
                    "noninferior_0p25_vs_retuned": None if not ok or use["lo"] is None else use["lo"] > -0.25,
                    "superior_sign_0p05_vs_retuned": (use["p_sign"] <= 0.05 and use["wins"] > use["losses"]) if ok
                    else None}, (b.partial, rate, fab, k)
    LV = partial.block(*GAP)["readings"]["R4"]["by_rule"]["mbs"]
    assert LV["vs_retuned"]["n"] == 0 and LV["vs_retuned"]["pending"] == "no runs yet"       # the table is there
    assert LV["vs_clock"]["n"] == 1 and LV["checks"] == {"mean_nonnegative_vs_retuned": None,
                                                         "noninferior_0p25_vs_retuned": None,
                                                         "superior_sign_0p05_vs_retuned": None}
    assert partial.block(*GAP)["readings"]["R4"]["by_rule"]["nach"]["vs_retuned"]["pending"] == "no refitted table yet"


def test_retuned_threshold_different_and_r5(partial, full):
    want = {(0.9, "HVLM"): ("same", {"timeout": "same", "mbs": "same", "nach": "same"}, (False, False, True)),
            (0.9, "LVHM"): ("same", {"timeout": "earlier", "mbs": "later", "nach": "mixed"}, (False, False, False)),
            (0.8, "HVLM"): ("higher", {"timeout": "earlier", "mbs": "earlier", "nach": "earlier"}, (True, True, True)),
            (0.8, "LVHM"): ("lower", {"timeout": "later", "mbs": "mixed", "nach": "later"}, (False, False, False))}
    for b in (partial, full):
        for (rate, fab), (direction, tables, checks) in want.items():
            r5 = b.block(rate, fab)["readings"]["R5"]
            if b.partial and (rate, fab) == GAP:
                tables, checks = dict(tables, nach=None), (False, None, None)    # LVHM nach not refitted yet
            assert (r5["selected_h"], r5["threshold_direction"], r5["agree_files_json"]) == (H_STAR[(rate, fab)],
                                                                                          direction, True)
            assert {k: v["direction"] for k, v in r5["tables"].items()} == tables, (b.partial, rate, fab)
            assert r5["checks"] == dict(zip(("threshold_rises", "tables_start_earlier", "same_direction"), checks))
            assert r5["note"] is None
    for b in (partial, full):
        for fab, h in (("HVLM", "3"), ("LVHM", "0.75")):
            c = b.block(0.8, fab)["comparisons"]["clock_rt-clock"]
            assert c["declared"] is False and c["reading"] == "not declared (supplement to R5)" and c["n"] > 0
            assert b.block(0.8, fab)["policies"]["clock_rt"]["n"] == (29 if b.partial and fab == "LVHM" else 32)
    assert ("R5: h* = 3 h (selection_r0p80.json; files and selection file agree yes); direction against 1.5 h higher; "
            "tables timeout earlier, mbs earlier, nach earlier; checks threshold_rises yes; tables_start_earlier yes; "
            "same_direction yes") in partial.md
    assert ("direction against 1.5 h lower; tables timeout later, mbs mixed, nach --; checks threshold_rises no; "
            "tables_start_earlier --; same_direction --") in partial.md


def test_r1_to_r3_checks_by_hand(partial, full):
    stats = pytest.importorskip("scipy.stats")
    for b in (partial, full):
        for (rate, fab) in H_STAR:
            RD, runs = b.block(rate, fab)["readings"], b.runs
            for k in RK:
                ref = b.res["reference_0p98"][fab]["comparisons"][f"tbl_{k}-{k}"]
                assert (ref["mean"], ref["pct"]) == REF[fab][k][:2]
                r1 = by_hand(stats, runs[(rate, fab, f"tbl_{k}")], runs[(rate, fab, k)])
                r2 = by_hand(stats, runs[(rate, fab, f"rft_{k}")], runs[(rate, fab, k)])
                r3 = by_hand(stats, runs[(rate, fab, f"rft_{k}")], runs[(rate, fab, f"tbl_{k}")])
                where = (b.partial, rate, fab, k)
                assert RD["R1"]["by_rule"][k]["checks"] == {
                    "positive_on_most_seeds": r1["wins"] > r1["n"] / 2 if r1["n"] else None,
                    "smaller_than_0p98_mean": lt(r1["mean"], ref["mean"]),
                    "smaller_than_0p98_pct": lt(r1["pct"], ref["pct"])}, where
                assert RD["R2"]["by_rule"][k]["checks"] == {
                    "positive_on_every_seed": r2["wins"] == r2["n"] if r2["n"] else None,
                    "at_least_0p98_mean": ge(r2["mean"], ref["mean"]),
                    "at_least_0p98_pct": ge(r2["pct"], ref["pct"])}, where
                assert RD["R3"]["by_rule"][k]["checks"] == {
                    "r1_short_of_0p98_pct": lt(r1["pct"], ref["pct"]),
                    "positive_mean": None if r3["mean"] is None else r3["mean"] > 0,
                    "positive_sign_0p05": None if not r3["n"] else r3["p_sign"] <= 0.05 and r3["wins"] > r3["losses"]}, where
                for r, e in (("R1", r1), ("R2", r2), ("R3", r3)):
                    assert RD[r]["by_rule"][k]["n"] == e["n"] and RD[r]["operationalised"].startswith("this script's")
    RD = partial.block(*GAP)["readings"]
    assert RD["R2"]["by_rule"]["nach"]["pending"] == "no refitted table yet" and RD["R2"]["by_rule"]["mbs"]["n"] == 1
    assert RD["R1"]["by_rule"]["timeout"]["n"] == 22 and "pending" not in RD["R1"]["by_rule"]["timeout"]


def test_refitted_tables_by_hand(partial, full):
    direction = {"same": "same", "earlier": "earlier", "later": "later", "mixed": "mixed", "drawn": "mixed"}
    for b in (partial, full):
        for (rate, fab) in H_STAR:
            B = b.block(rate, fab)
            for k in RK:
                r6, ce, rec = B["readings"]["R6"]["by_rule"][k], B["readings"]["cells"]["by_rule"][k], B["records"][k]
                st, S = b.stale[(fab, k)], fire2d(b.stale[(fab, k)])
                edges, where = st["edges"]["tightest"], (b.partial, rate, fab, k)
                assert B["tables"][f"tbl_{k}"]["pinned_ok"] is True
                assert r6["fire_0p98"] == S and r6["monotone_violations_0p98"] == sum(violations(S))
                assert r6["level_by_arrival_bin_0p98"] == levels(S, edges)
                dumps = [(rate, fab, k, s) in b.dumps for s in msj.RECORD_SEEDS]
                assert ce["dumps_present"] == sum(dumps) and [d["present"] for d in rec["dumps"].values()] == dumps
                art = b.refits.get((rate, fab, k))
                if art is None:
                    assert r6["pending"] == ce["pending"] == "no refitted table yet" and B["tables"][f"rft_{k}"] is None
                    assert rec["cells_differ"] is None and rec["cells_both"] is None
                    continue
                F = fire2d(art)
                gained = sum(F[i][j] > S[i][j] for i in range(6) for j in range(4))
                lost = sum(F[i][j] < S[i][j] for i in range(6) for j in range(4))
                d = "same" if not gained + lost else "earlier" if not lost else "later" if not gained else "mixed"
                assert d == direction[REFIT[(rate, fab)][k]], where
                rv, av = violations(F)
                assert (r6["violations_residual"], r6["violations_arrival"], r6["monotone_violations"]) == \
                    (rv, av, rv + av), where
                assert r6["control_limit_form"] is (rv + av == 0) and r6["adjacent_pairs"] == 5 * 4 + 6 * 3
                assert (r6["cells_differ_0p98"], r6["fire_gained"], r6["fire_lost"], r6["direction"]) == \
                    (gained + lost, gained, lost, d), where
                assert r6["fire"] == F and r6["level_by_arrival_bin"] == levels(F, edges)
                assert r6["level_shift"] == [None if x is None or y is None else x - y
                                             for x, y in zip(levels(F, edges), levels(S, edges))]
                nf, nw = np.array(art["n_fired"])[:, :, 0], np.array(art["n_waited"])[:, :, 0]
                both = (nf >= 10) & (nw >= 10)
                assert ce["cells_both"] == rec["cells_both"] == int(both.sum()) == (20 if k == "nach" else 21)
                assert ce["cells"] == 24 and ce["cells_both_0p98"] == B["tables"][f"tbl_{k}"]["cells_both"]
                close(ce["share_decisions_own"], float((nf + nw)[both].sum() / (nf + nw).sum()))
                same = np.array(F) == np.array(S)
                close(rec["agree_old_on_new_records"], float((nf + nw)[same].sum() / (nf + nw).sum()))
                n_old = np.array(st["n_fired"])[:, :, 0] + np.array(st["n_waited"])[:, :, 0]
                close(rec["agree_new_on_old_records"], float(n_old[same].sum() / n_old.sum()))
                assert B["tables"][f"rft_{k}"]["source_ok"] is True
    r6 = partial.block(*GAP)["readings"]["R6"]["by_rule"]["mbs"]                  # DRAWN against LVHM's mbs table
    assert (r6["violations_residual"], r6["violations_arrival"], r6["control_limit_form"]) == (1, 1, False)
    assert r6["level_by_arrival_bin"] == [1.0, None, 2.0, 2.0]
    assert (r6["cells_differ_0p98"], r6["fire_gained"], r6["fire_lost"], r6["direction"]) == (3, 2, 1, "mixed")


def test_markdown_rows_by_hand(partial):
    stats = pytest.importorskip("scipy.stats")
    md, runs = partial.md, partial.runs
    assert md.splitlines()[0].endswith("**NOT FINISHED**")
    assert "Rates: 0.9 finished; 0.8 partial (stage B); 1.05 not_gated." in md
    e = by_hand(stats, runs[GAP + ("tbl_timeout",)], runs[GAP + ("timeout",)])
    p = "<0.001" if e["p_sign"] < 0.001 else f"{e['p_sign']:.3f}"
    assert (f"| R1 | tbl_timeout - timeout | 22/32* | {e['mean']:+.2f} | [{e['lo']:+.2f}, {e['hi']:+.2f}] | "
            f"{e['wins']}/{e['losses']}/{e['ties']} | {p} | {e['pct']:+.1f} | +1.93 / +5.5% |") in md
    e = by_hand(stats, runs[GAP + ("rft_mbs",)], runs[GAP + ("mbs",)])
    assert f"| R2 | rft_mbs - mbs | 1/32* | {e['mean']:+.2f} | -- | " in md
    assert "| R4 | rft_mbs - clock_rt | 0/32* | pending |  |  |  |  | " in md           # the reason sits in readings
    V = runs[GAP + ("clock_rt",)]
    mu = {f: np.mean([value(V[s], f) for s in sorted(V)]) for f in ("completed", "scrapped_furnace", "scrapped_other",
                                                                      "underfull_per_day", "cycle_p50_days")}
    assert (f"| control limit, h = 0.75 h, retuned at 0.8 | 29/32* | {mu['completed']:.2f} | "
            f"{mu['scrapped_furnace']:.1f} | {mu['scrapped_other']:.1f} | {mu['underfull_per_day']:.1f} | "
            f"{mu['cycle_p50_days']:.1f} |") in md
    assert "Job files at 0.8: a agree (572 jobs), fit agree (6 jobs), b agree (256 jobs)" in md
    assert md.rstrip().splitlines()[-1] == f"[NOT FINISHED] wrote {partial.out}"


def test_full_block(full):
    stats = pytest.importorskip("scipy.stats")
    ct = pytest.importorskip("confirm_tables")
    R, m = full.res, full.res["meta"]
    assert (m["finished"], m["complete"]) == (True, True)
    assert m["statuses"] == {"0.9": "finished", "0.8": "finished", "1.05": "skipped"}
    assert m["problems"] == [] and m["deviations"] == [] and m["missing"] == {} and m["started_no_output"] == 0
    assert m["runs_expected"] == {"report": 640 + 704, "report_pending": 0, "select": 224, "records": 24, "tables": 12}
    assert m["runs_present"] == {"report": 640 + 704, "select": 224, "records": 24, "tables": 12}
    for (rate, fab) in H_STAR:
        B = full.block(rate, fab)
        assert B["status"]["complete"] is True and B["status"]["started_no_output"] == 0
        assert all(c["n"] == 32 and c["complete"] for c in B["comparisons"].values() if "n" in c)
        assert all(q["n"] == 32 for q in B["policies"].values())
    H = R["rates"]["1.05"]
    assert (H["status"], H["high_skipped"]) == ("skipped", full.high) and "HVLM" not in H and "LVHM" not in H
    assert H["job_files"] == {"a": {"jobs": 0, "expected": 0, "agree": True},
                              "fit": {"jobs": 0, "expected": 0, "agree": True}, "b": None}
    pr = H["probe"]
    assert (pr["n_present"], pr["n_expected"], pr["stable"]) == (4, 4, False)
    assert pr["runs"] == {k: {"present": True, "slope": j["wip_slope_back_half"], "wip_end": j["wip_end"]}
                          for k, j in full.probe.items()}
    lines = full.md.rstrip().splitlines()
    assert "NOT FINISHED" not in full.md and "## Rate 1.05: skipped" in full.md
    assert lines[-2:] == [f"wrote {full.out}", f"wrote {full.tex}"]
    with open(full.tex, encoding="utf-8") as f:
        tex = f.read()
    assert ct.HOLE not in tex and "% PARTIAL" not in tex and r"\label{tab:shift}" in tex and "Paired on" not in tex
    assert "are 1.5~h at 0.90 and 3~h at 0.80 on HVLM, and 1.5~h at 0.90 and 0.75~h at 0.80 on LVHM, against 1.5~h at 0.98." in tex
    assert "Rate 1.05" not in tex
    runs = full.runs
    for rate, fab, b_key in ((0.9, "HVLM", "clock"), (0.8, "LVHM", "clock_rt")):   # 1.5 h at 0.90: the same policy
        for i, k in enumerate(RK):
            r1 = by_hand(stats, runs[(rate, fab, f"tbl_{k}")], runs[(rate, fab, k)])
            r2 = by_hand(stats, runs[(rate, fab, f"rft_{k}")], runs[(rate, fab, k)])
            r4 = by_hand(stats, runs[(rate, fab, f"rft_{k}")], runs[(rate, fab, b_key)])
            row = " & ".join([f"{rate:.2f}" if i == 0 else "", ct.tex(sr.LABEL[k]), str(20 if k == "nach" else 21),
                              ct.num(r1["pct"], 1), ct.num(r2["pct"], 1), ct.sgn(r4["mean"]),
                              ct.ci(r4["lo"], r4["hi"])])
            assert row + r" \\" in tex, row


def test_cli_in_a_fresh_interpreter(partial, tmp_path):
    out = tmp_path / "cli.json"
    env = dict(os.environ, OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-B", os.path.join(SRC, "shift_report.py")] + partial.args() + ["--out", str(out)],
                       cwd=str(tmp_path), env=env, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and r.stderr == "", r.stderr
    lines = r.stdout.rstrip().splitlines()
    assert lines[-1] == f"[NOT FINISHED] wrote {out}"
    assert lines[1:-1] == partial.md.rstrip().splitlines()[1:-1]          # all but the time of the read
    got, want = strict(out), json.loads(json.dumps(partial.res))
    got["meta"].pop("generated")
    want["meta"].pop("generated")
    assert got == want
