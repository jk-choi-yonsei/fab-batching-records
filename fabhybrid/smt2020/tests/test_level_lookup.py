"""The deployed lookup of a fitted table (level.py, kind "table"): (tightest residual, next arrival) -> cell -> action,
through Level.decide with the paper's timeout-records table, at hand-chosen points and at the bin edges.

decide() computes the arrival coordinate through phi(env, g0, now); the fake environment below holds only what that
path reads when the lot has no route ahead and no clock is open (no frame, no family state, no waiting lots).

Run from fabhybrid/smt2020:  python -B -m pytest tests/test_level_lookup.py -q -p no:cacheprovider
"""
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import fit_q  # noqa: E402
import level  # noqa: E402
import table_agree  # noqa: E402
from level import HOUR, Level, _cell  # noqa: E402

ARTEFACT = os.path.normpath(os.path.join(HERE, "..", "..", "experiments", "smt2020", "final", "betarx", "family",
                                         "HVLM_timeout_b0p003_t1.json"))
NOW = 1000.0 * HOUR

# the artefact's start region, residual bin (rows) x arrival bin (columns), fill folded:
#                 nxt [0,.25) [.25,1) [1,3) [3,24.01)
#   [0, .25) h        1       1       1      1
#   [.25, .5)         1       1       1      1
#   [.5, 1)           0       1       1      1
#   [1, 2)            0       0       1      1
#   [2, 4)            0       0       0      0
#   [4, 24.01)        0       0       0      0
MAP = [[1, 1, 1, 1], [1, 1, 1, 1], [0, 1, 1, 1], [0, 0, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]


def fake(nxt_h, size=2, batch_max=4):
    """the smallest env and head load phi() reads: next arrival nxt_h hours from now (None: none announced)"""
    step = SimpleNamespace(batch_max=batch_max, family="Diffusion", step_name="Diffusion_FE_120", order=0)
    g0 = [SimpleNamespace(actual_step=step) for _ in range(size)]
    env = SimpleNamespace(
        cqt=SimpleNamespace(open={}),                       # no clock records: the residual is passed in
        fam_machines={},
        instance=SimpleNamespace(),                         # no free_machines
        next_arrival=lambda family, step_name: None if nxt_h is None else NOW + nxt_h * HOUR,
        _fam_state={},
        _machine=SimpleNamespace(waiting_lots=[]))
    return env, g0


@pytest.fixture(scope="module")
def table():
    L = Level.load(ARTEFACT)
    assert L.kind == "table" and not L.table["head_axis"] and L.rng is None
    assert L.table["edges"]["tightest"] == [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 24.01]
    assert L.table["edges"]["nxt"] == [0.0, 0.25, 1.0, 3.0, 24.01]
    assert L.table["edges"]["fill"] == [0.0, 1.001]
    assert [[c[0] for c in r] for r in L.table["fire"]] == MAP
    return L


@pytest.fixture(autouse=True)
def no_arrival_noise(monkeypatch):
    monkeypatch.setitem(level.NXT_NOISE, "rng", None)


def decide(L, res_h, nxt_h, size=2):
    env, g0 = fake(nxt_h, size)
    return L.decide(env, g0, NOW, res_h * HOUR, False)


# (residual h, next arrival h or None, residual bin, arrival bin, action)
POINTS = [
    (0.1, 0.1, 0, 0, 1),
    (0.3, 0.5, 1, 1, 1),
    (0.9, 2.0, 2, 2, 1),
    (1.5, None, 3, 3, 1),          # nothing announced: read as 24 h, the last arrival bin
    (3.0, 0.1, 4, 0, 0),
    (10.0, None, 5, 3, 0),
]


@pytest.mark.parametrize("res_h,nxt_h,i,j,act", POINTS)
def test_hand_chosen_points(table, res_h, nxt_h, i, j, act):
    e = table.table["edges"]
    assert _cell(res_h, e["tightest"]) == i
    assert _cell(24.0 if nxt_h is None else nxt_h, e["nxt"]) == j
    assert decide(table, res_h, nxt_h) is bool(act)
    # fill is folded, so the size of the head load does not matter
    assert decide(table, res_h, nxt_h, size=1) is decide(table, res_h, nxt_h, size=4) is bool(act)


# the bins are half-open [a, b): a residual exactly at an edge belongs to the bin above it. Where the action
# changes across the edge, the arrival column is chosen so that it does (0.5, 1 and 2 h); at 0.25 and 4 h it
# changes in no column, and only the cell index tells the two sides apart.
EDGE_POINTS = [
    (0.25, 0.1, 1, 1, 1),
    (0.5, 0.1, 2, 1, 0),
    (1.0, 0.5, 3, 1, 0),
    (2.0, 2.0, 4, 1, 0),
    (2.0, None, 4, 1, 0),
    (4.0, 0.1, 5, 0, 0),
]


@pytest.mark.parametrize("res_h,nxt_h,i,act_below,act", EDGE_POINTS)
def test_bin_edges_are_half_open(table, res_h, nxt_h, i, act_below, act):
    e = table.table["edges"]["tightest"]
    below = np.nextafter(res_h, 0.0)
    assert _cell(res_h, e) == i
    assert _cell(below, e) == i - 1
    assert decide(table, res_h, nxt_h) is bool(act)
    assert decide(table, below, nxt_h) is bool(act_below)


@pytest.mark.parametrize("res_h,nxt_h,below,act_below,act", [(0.6, 0.25, 0.2499, 0, 1), (1.5, 1.0, 0.999, 0, 1)])
def test_arrival_edges_are_half_open_through_phi(table, res_h, nxt_h, below, act_below, act):
    """the arrival coordinate reaches the lookup as phi's x[3] * 24 (the dump logs nxt_h the same way); an
    arrival exactly on an edge lands in the bin above it"""
    assert decide(table, res_h, nxt_h) is bool(act)
    assert decide(table, res_h, below) is bool(act_below)


def test_forced_states(table):
    env, g0 = fake(0.1)
    # a full load always fires; no live clock, or only expired ones, waits -- whatever the table says
    assert table.decide(env, g0, NOW, 10.0 * HOUR, True) is True
    assert table.decide(env, g0, NOW, None, False) is False
    assert table.decide(env, g0, NOW, -1e-9, False) is False
    # a residual of exactly zero is live
    assert table.decide(env, g0, NOW, 0.0, False) is True


def test_deployment_bins_match_the_fit_and_the_agreement_bins():
    """level._cell (deployment), fit_q.cell (fit) and table_agree.cell (agreement) assign the same bin"""
    for edges in (fit_q.EDGES["tightest"], fit_q.EDGES["nxt"], [0.0, 24.01]):
        xs = [-1.0, 0.0, 30.0, 24.0, 24.01] + [x for b in edges for x in (np.nextafter(b, -1.0), b, np.nextafter(b, 99.0))]
        xs += list(np.linspace(0.0, 25.0, 1001))
        for x in xs:
            assert _cell(x, edges) == fit_q.cell(x, edges) == table_agree.cell(x, edges), (x, edges)
