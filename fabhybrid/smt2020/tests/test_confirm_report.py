"""The statistics of confirm_report.py and the formats of confirm_tables.py, on hand-built inputs.

Run from fabhybrid/smt2020:  python -B -m pytest tests/test_confirm_report.py -q -p no:cacheprovider
"""
import json
import os
import sys
from math import comb

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import confirm_report as cr  # noqa: E402
import confirm_tables as ct  # noqa: E402


def test_t_crit_known_quantiles():
    # two-sided 95% Student quantiles; final_report.t_crit tabulated 2.365, 2.131, 2.040, 1.998
    for n, t in ((2, 12.706204736), (8, 2.364624252), (16, 2.131449546), (32, 2.039513446), (64, 1.998340543)):
        assert abs(cr.t_crit(n) - t) < 1e-8
    assert cr.t_crit(1) is None
    assert abs(cr.t_crit(10 ** 6) - 1.959966) < 1e-5


def test_t_crit_against_scipy():
    stats = pytest.importorskip("scipy.stats")
    for n in list(range(2, 70)) + [100, 1000]:
        assert abs(cr.t_crit(n) - stats.t.ppf(0.975, n - 1)) < 1e-8


def test_sign_test():
    assert cr.sign_p(0, 0) == 1.0
    assert cr.sign_p(32, 0) == 2 / 2 ** 32
    assert cr.sign_p(26, 6) == cr.sign_p(6, 26) == 2 * sum(comb(32, i) for i in range(7)) / 2 ** 32
    assert cr.sign_p(16, 16) == 1.0


def test_holm_is_the_protocols_formula():
    # p~(k) = max over j <= k of min(1, (4 - j) p(j)) on the sorted p-values of a family of three
    assert np.allclose(cr.holm([0.03, 0.01, 0.04], 3), [0.06, 0.03, 0.06])
    assert cr.holm([0.5, 0.6, 0.7], 3) == [1.0, 1.0, 1.0]
    assert cr.holm([0.01, None, 0.04], 3) == [0.03, None, 0.08]      # a missing member keeps the family at three


def test_paired_uses_the_common_seeds():
    seeds = [64, 65, 66, 67]
    a = {64: {"completed": 36.0}, 65: {"completed": 37.0}, 66: {"completed": 35.0}, 67: {"completed": 36.5}}
    b = {64: {"completed": 35.0}, 65: {"completed": 37.0}, 67: {"completed": 37.0}}        # 66 missing, 65 a tie
    p = cr.paired(a, b, seeds)
    assert (p["n"], p["wins"], p["losses"], p["ties"]) == (3, 1, 1, 1)
    assert abs(p["mean"] - (1.0 + 0.0 - 0.5) / 3) < 1e-12
    assert p["per_seed"] == [1.0, 0.0, None, -0.5]
    assert p["p_sign"] == 1.0
    d = np.array([1.0, 0.0, -0.5])
    half = cr.t_crit(3) * d.std(ddof=1) / np.sqrt(3)
    assert abs(p["lo"] - (d.mean() - half)) < 1e-12 and abs(p["hi"] - (d.mean() + half)) < 1e-12
    assert abs(p["pct"] - 100 * d.mean() / np.mean([35.0, 37.0, 37.0])) < 1e-12
    none = cr.paired(a, {}, seeds)
    assert none["n"] == 0 and none["mean"] is None and none["per_seed"] == [None] * 4
    one = cr.paired(a, {64: b[64]}, seeds)
    assert one["n"] == 1 and one["mean"] == 1.0 and one["lo"] is None


def test_job_lines_name_their_policy():
    f = "../../experiments/smt2020/final"
    for cmd, want in (
            (f"python batch_fire.py --dataset HVLM --arm level:1 --theta {f}/collect/HVLM_b0p003_t1rx.json --seed 64", "learner"),
            (f"python batch_fire.py --dataset HVLM --arm level:1 --theta {f}/betarx/HVLM_b0p0016_t1rx.json --seed 64", "sens"),
            (f"python batch_fire.py --dataset HVLM --arm level:1 --theta {f}/betarx/family/HVLM_resid_b0p003_t1.json --seed 64", "resid"),
            (f"python batch_fire.py --dataset HVLM --arm level:1 --theta {f}/betarx/family/HVLM_mbs3_b0p003_t1.json --seed 64", "tbl_mbs"),
            (f"python batch_fire.py --dataset HVLM --arm level:1 --theta {f}/betarx/family/HVLM_timeout_b0p003_t1.json --seed 64", "tbl_timeout"),
            (f"python batch_fire.py --dataset HVLM --arm level:1 --theta {f}/betarx/family/HVLM_nach_b0p003_t1.json --seed 64", "tbl_nach"),
            ("python batch_fire.py --dataset HVLM --arm explore:0.02 --seed 64", "logging"),
            ("python batch_fire.py --dataset HVLM --arm clock:1.5 --seed 64", "clock"),
            ("python batch_fire.py --dataset HVLM --arm mbs:3 --seed 64", "mbs"),
            ("python batch_fire.py --dataset HVLM --arm timeout:1 --seed 64", "timeout"),
            ("python batch_fire.py --dataset HVLM --arm nach --seed 64", "nach"),
            ("python batch_fire.py --dataset HVLM --arm full --seed 64", "default"),
            ("python eval_batch.py --weights w/weights_bc.pt --dataset HVLM --seed 64 --tag bcHVLM", "bc"),
            ("python eval_batch.py --weights w/weights_best.pt --dataset HVLM --seed 64 --tag ppoHVLM", "ppo")):
        assert cr._classify(cmd, "HVLM")[0] == want


def test_the_blocks_job_file_gives_864_runs(tmp_path):
    if not os.path.exists(cr.JOBFILE):
        pytest.skip("no jobs/confirm_report.txt")
    spec = cr.block_spec(cr.JOBFILE, str(tmp_path), list(range(64, 96)))
    assert sum(len(e["files"]) for fab in cr.FABS for e in spec[fab].values()) == 13 * 2 * 32 + 32
    assert set(spec["HVLM"]) - set(spec["LVHM"]) == {"sens"}
    assert spec["LVHM"]["learner"]["tag"] == "level1_LVHM_b0p003_t1rx" and spec["HVLM"]["bc"]["tag"] == "rl-bcHVLM"


def test_missing_and_unreadable_runs_do_not_crash(tmp_path):
    run = {"dataset": "HVLM", "seed": 64, "scale": 0.98, "days": 360, "cqt_rule": "qtcr", "scrap": True, "warmup_days": 87.0,
           "scrap_kpi": {"completed_per_day": 36.5, "scrapped_per_day": 19.0, "cycle_p50_days": 24.8},
           "batches_partial": 3600, "batches_partial_all": 2730}
    files = {s: str(tmp_path / f"s{s}.json") for s in (64, 65, 66, 67)}
    json.dump(run, open(files[64], "w"))
    open(files[65], "w").write('{"dataset": "HVLM", "se')                     # caught while it is written
    json.dump(dict(run, seed=66, days=180), open(files[66], "w"))             # another configuration
    problems = []
    v = cr.load(files, "HVLM", problems)
    assert list(v) == [64] and len(problems) == 2
    assert v[64]["underfull_per_day"] == 10.0 and v[64]["underfull_per_day_run"] == 10.0
    s = cr.summary(v, [64, 65, 66, 67], "learner", "learner", "tag")
    assert s["n"] == 1 and s["sd"] is None and s["per_seed"]["completed"] == [36.5, None, None, None]
    assert cr.summary({}, [64, 65], "rule", "x", None)["completed"] is None


def test_formats():
    assert ct.sgn(0.184) == "$+0.18$" and ct.sgn(-1.456) == "$-1.46$" and ct.sgn(-0.004) == "$+0.00$"
    assert ct.num(-0.001) == "0.00" and ct.num(36.835) in ("36.83", "36.84") and ct.num(None) == ct.HOLE
    assert ct.ci(-0.0085, 0.376) == r"$[-0.01,\,0.38]$" and ct.ci(None, 1.0) == ct.HOLE
    assert ct.pval(0.0004) == "$<0.001$" and ct.pval(0.0501) == "0.050" and ct.pval(None) == ct.HOLE
    assert ct.tex("control limit, $h = 1.5$ h") == r"control limit, $\theta = 1.5$~h"
    assert ct.tex("full-batch rule, 2% started") == r"full-batch rule, 2\% started"
    c = {"mean": -0.17, "lo": -0.39, "hi": 0.05, "wins": 13, "losses": 19}
    assert ct.flip(c) == {"mean": 0.17, "lo": -0.05, "hi": 0.39, "wins": 19, "losses": 13}


def test_scrap_location_is_per_day_of_the_window(tmp_path):
    run = {"dataset": "HVLM", "seed": 64, "scale": 0.98, "days": 360, "cqt_rule": "qtcr", "scrap": True, "warmup_days": 87.0,
           "scrap_kpi": {"completed_per_day": 36.5, "scrapped_per_day": 19.0, "cycle_p50_days": 24.8},
           "batches_partial": 3600, "batches_partial_all": 2730,
           "blocking": {"batch_deaths": 1365, "batch_deaths_no_server": 400, "nonbatch_deaths": 3822}}
    files = {64: str(tmp_path / "s64.json"), 65: str(tmp_path / "s65.json")}
    json.dump(run, open(files[64], "w"))
    json.dump({k: v for k, v in dict(run, seed=65).items() if k != "blocking"}, open(files[65], "w"))   # as eval_batch.py writes
    v = cr.load(files, "HVLM", [])
    assert v[64]["scrapped_furnace"] == 5.0 and v[64]["scrapped_other"] == 14.0
    assert v[65]["scrapped_furnace"] is None and v[65]["scrapped_other"] is None
    s = cr.summary(v, [64, 65], "learner", "learned table", "tag")
    assert s["scrapped_furnace"] == 5.0 and s["per_seed"]["scrapped_furnace"] == [5.0, None]
    notes = ct.Notes()
    assert ct.scrap_cells({"scrapped_furnace": 4.67, "scrapped_other": 13.86, "scrapped": 18.53}, notes) == "4.7 & 13.9"
    assert ct.scrap_cells({"scrapped_furnace": None, "scrapped_other": None, "scrapped": 19.82}, notes) == \
        r"\multicolumn{2}{c}{19.8\textsuperscript{a}}"
    assert notes.render("General.").strip() == r"\tabnote{General. \textsuperscript{a}" + ct.NETWORK_NOTE + "}"


def test_macros_are_control_words_defined_once():
    m = ct.Macros()
    m.add("numHVLMlearnerMbsPct", "9")
    with pytest.raises(AssertionError):
        m.add("numHVLMlearnerMbsPct", "9")
    with pytest.raises(AssertionError):
        m.add("numHVLMmbs3", "1")
