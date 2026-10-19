"""table_agree.py: the share of logged free decisions at which a table takes the reference table's action, and the
share it fires, on a hand-built dump and three hand-built tables. No simulation.

Run from fabhybrid/smt2020:  python -B -m pytest tests/test_table_agree.py -q -p no:cacheprovider
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import table_agree  # noqa: E402


def decision(day, clocks, nxt_h, full=False, act=1, size=2):
    """one record as readout --dump-lots writes it (the fields fit_q.chains reads); clocks are
    [lot, residual h, in the head load]"""
    return {"day": day, "mach": 7, "step": "Diffusion_FE_120|109_Diffusion", "act": act, "n_groups": 1,
            "full": full, "size": size, "nxt_h": nxt_h, "clocks": clocks}


# six free decisions, (tightest residual h, next arrival h)
FREE = [
    decision(90.0, [[1, 3.0, False], [2, 0.2, True]], 0.5),   # (0.2, 0.5): the tightest of two clocks; day == from-day
    decision(91.0, [[3, 0.8, True]], 2.0),                     # (0.8, 2.0): arrival exactly on the reference's edge
    decision(92.0, [[4, 1.0, True]], 1.0),                     # (1.0, 1.0): residual exactly on the reference's edge
    decision(93.0, [[5, 1.5, True]], 0.1),                     # (1.5, 0.1)
    decision(94.0, [[6, 2.0, True]], 0.1, act=0),              # (2.0, 0.1): exactly on table B's edge
    decision(95.0, [[7, 5.0, True]], 24.0),                    # (5.0, 24.0): nothing announced
]
# decisions that are not free, which the agreement must not count
NOT_FREE = [
    decision(89.9, [[8, 0.1, True]], 0.1),                     # before the logging window
    decision(96.0, [[9, 0.1, True]], 0.1, full=True, act=0),   # a full load
    decision(97.0, [], 0.1),                                   # no live clock
    decision(98.0, [[10, -0.5, True], [11, 0.3, True]], 0.1),  # the tightest clock has expired
]

FOLD = [0.0, 1.001]
# REF fires iff residual < 1 h and next arrival < 2 h: of the six, only (0.2, 0.5)          -> fires 1/6
REF = {"edges": {"tightest": [0.0, 1.0, 24.01], "nxt": [0.0, 2.0, 24.01], "fill": FOLD},
       "fire": [[[1], [0]], [[0], [0]]], "lam": 0.003}
# B fires iff residual < 2 h, whatever the arrival: (0.2), (0.8), (1.0), (1.5)              -> fires 4/6
#   agrees with REF at (0.2, 0.5), (2.0, 0.1), (5.0, 24.0)                                  -> agree 3/6
B = {"edges": {"tightest": [0.0, 0.5, 2.0, 24.01], "nxt": [0.0, 24.01], "fill": FOLD},
     "fire": [[[1]], [[1]], [[0]]], "lam": 0.01}
# C has REF's edges and fires iff residual < 1 h: (0.2), (0.8)                              -> fires 2/6
#   disagrees with REF only at (0.8, 2.0)                                                   -> agree 5/6
C = {"edges": REF["edges"], "fire": [[[1], [1]], [[0], [0]]]}            # no "lam": reported as None
EXPECT = {"ref.json": (1.0, 1 / 6), "B.json": (3 / 6, 4 / 6), "C.json": (5 / 6, 2 / 6)}


def write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return str(path)


def run(tmp_path, monkeypatch, dumps):
    tables = [write(tmp_path / name, t) for name, t in (("ref.json", REF), ("B.json", B), ("C.json", C))]
    out = tmp_path / "agree.json"
    monkeypatch.setattr(sys, "argv", ["table_agree.py", "--ref", tables[0], "--tables", *tables,
                                      "--dumps", *dumps, "--from-day", "90", "--out", str(out)])
    table_agree.main()
    with open(out, encoding="utf-8") as f:
        return json.load(f)


def check(res):
    assert res["ref"] == "ref.json"
    assert res["n_free_decisions"] == 6
    assert res["ref_fire_share"] == pytest.approx(1 / 6, abs=1e-12)
    assert list(res["tables"]) == ["ref.json", "B.json", "C.json"]
    for name, (agree, fires) in EXPECT.items():
        t = res["tables"][name]
        assert t["agree"] == pytest.approx(agree, abs=1e-12), name
        assert t["fire_share"] == pytest.approx(fires, abs=1e-12), name
    assert res["tables"]["B.json"]["edges"] == B["edges"]
    assert res["tables"]["B.json"]["lam"] == 0.01
    assert res["tables"]["C.json"]["lam"] is None


def test_agreement_on_six_free_decisions(tmp_path, monkeypatch, capsys):
    dump = write(tmp_path / "d1.json", {"seed": 100, "arm": "test", "decisions": FREE, "scrapped": []})
    check(run(tmp_path, monkeypatch, [dump]))
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert "agree  50.00%" in lines[1] and "fires 66.67%" in lines[1] and "(ref fires 16.67%, n 6)" in lines[1]


def test_decisions_that_are_not_free_are_not_counted(tmp_path, monkeypatch):
    d1 = write(tmp_path / "d1.json", {"seed": 100, "arm": "test", "decisions": FREE[:3], "scrapped": []})
    d2 = write(tmp_path / "d2.json", {"seed": 101, "arm": "test", "decisions": NOT_FREE + FREE[3:], "scrapped": []})
    check(run(tmp_path, monkeypatch, [d1, d2]))
