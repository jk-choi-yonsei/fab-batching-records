"""fit_q.py refits the paper's timeout-records table from the timeout rule's records, entry for entry.

The records (experiments/smt2020/final/collect/HVLM_norev_p1_s10{0,1}.json, 24 MB each) are gitignored, so on a
clone without them the test is skipped. No simulation: the fit alone, about 20 s.

Run from fabhybrid/smt2020:  python -B -m pytest tests/test_fit_q_reproduces.py -q -p no:cacheprovider
"""
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import fit_q  # noqa: E402

FINAL = os.path.normpath(os.path.join(HERE, "..", "..", "experiments", "smt2020", "final"))
DUMPS = [os.path.join(FINAL, "collect", f"HVLM_norev_p1_s{s}.json") for s in (100, 101)]
ARTEFACT = os.path.join(FINAL, "betarx", "family", "HVLM_timeout_b0p003_t1.json")


@pytest.mark.skipif(not all(os.path.exists(p) for p in DUMPS),
                    reason="the timeout rule's records (collect/HVLM_norev_p1_s100/s101.json) are gitignored and absent")
def test_fit_reproduces_the_papers_timeout_table(tmp_path, monkeypatch):
    # main() rewrites the module-level EDGES in place (--fold, --edges-*) and reads the module-level K0, so each
    # in-process call gets fresh copies, restored when the test ends (as rule_tables.py does by hand)
    monkeypatch.setattr(fit_q, "EDGES", {"tightest": [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 24.01],
                                         "nxt": [0.0, 0.25, 1.0, 3.0, 24.01],
                                         "fill": [0.0, 0.3, 0.55, 1.001]})
    monkeypatch.setattr(fit_q, "K0", 10.0)
    out = tmp_path / "HVLM_timeout_b0p003_t1.json"
    monkeypatch.setattr(sys, "argv", ["fit_q.py", *DUMPS, "--chain", "family", "--lam", "0.003", "--backoff",
                                      "--from-day", "90", "--fold", "fill", "--out", str(out)])
    fit_q.main()

    with open(out) as f:
        got = json.load(f)
    with open(ARTEFACT) as f:
        ref = json.load(f)

    # the settings the artefact records are the ones this call used
    for k in ("kind", "lam", "mu", "gamma_h", "K0", "chain", "fold", "head_axis", "edges", "from_day", "backoff"):
        assert got[k] == ref[k], k
    assert got["n_transitions"] == ref["n_transitions"]
    # the decisions and the counts behind them, exactly
    for k in ("fire", "fire_own", "own_entry", "fire_residual_only", "n_fired", "n_waited"):
        assert got[k] == ref[k], k
    # the value difference Q(fire) - Q(wait) per cell
    np.testing.assert_allclose(np.asarray(got["margin"]), np.asarray(ref["margin"]), rtol=0.0, atol=1e-9)
    # shape of the deployed map: 6 residual bins x 4 arrival bins x 1 (fill folded)
    assert np.asarray(got["fire"]).shape == (6, 4, 1)
