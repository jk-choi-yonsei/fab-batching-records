"""The batch-decision arms in batch_fire.choose, on hand-built decisions.

Run from fabhybrid/smt2020:  python -m pytest tests -q
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import batch_fire  # noqa: E402


class Step:
    def __init__(self, batch_max, order=5, step_name="s", family="F", proc_min=463.0):
        self.batch_max, self.order = batch_max, order
        self.step_name, self.family = step_name, family
        self.processing_time = types.SimpleNamespace(m=proc_min * 60.0)


class Lot:
    def __init__(self, step, free_since=0.0):
        self.actual_step, self.free_since = step, free_since


class Env:
    """Just enough of FabEnv for choose(): the groups, the machine's waiting
    lots, the clock, the open-clock table and the next-arrival index."""

    def __init__(self, groups, now, open_clocks=None, next_arr=None):
        self._groups = groups
        self._machine = types.SimpleNamespace(waiting_lots=[l for g in groups for l in g])
        self.instance = types.SimpleNamespace(current_time=now)
        self.cqt = types.SimpleNamespace(open=open_clocks or {})
        self._na = next_arr

    def next_arrival(self, family, step_name):
        return self._na

    def rule_action(self):
        return 0 if batch_fire.group_is_full(self._groups[0]) else len(self._groups)


def test_full_and_clock0_are_upstream():
    st = Step(batch_max=6)
    g = [[Lot(st), Lot(st)]]
    env = Env(g, now=0.0)
    assert batch_fire.choose(env, "full", 0.0) == env.rule_action() == len(g)
    assert batch_fire.choose(env, "clock", 0.0) == env.rule_action()


def test_full_group_always_runs():
    st = Step(batch_max=2)
    g = [[Lot(st), Lot(st)]]
    for kind, coef in (("full", 0.0), ("mbs", 3), ("timeout", 99.0), ("clock", 0.0), ("nach", 0.0), ("nach_dl", 2.0)):
        assert batch_fire.choose(Env(g, now=0.0), kind, coef) == 0


def test_timeout_fires_when_oldest_waited_long_enough():
    st = Step(batch_max=6)
    g = [[Lot(st, free_since=0.0), Lot(st, free_since=3600.0)]]
    env = Env(g, now=2.5 * 3600)
    assert batch_fire.choose(env, "timeout", 2.0) == 0            # oldest waited 2.5 h >= 2 h
    assert batch_fire.choose(env, "timeout", 3.0) == len(g)       # not yet


def test_clock_fires_only_inside_the_margin():
    st = Step(batch_max=6)
    a, b = Lot(st), Lot(st)
    g = [[a, b]]
    env = Env(g, now=0.0, open_clocks={id(a): (st.order, 5400.0, 1, 3600.0)})   # 1.5 h left
    assert batch_fire.choose(env, "clock", 2.0) == 0
    assert batch_fire.choose(env, "clock", 1.0) == len(g)
    env = Env(g, now=0.0, open_clocks={id(a): (st.order, -10.0, 1, 3600.0)})    # already expired
    assert batch_fire.choose(env, "clock", 2.0) == len(g)


def test_clockany_reads_clocks_that_stop_downstream():
    st = Step(batch_max=6, order=5)
    a, b = Lot(st), Lot(st)
    g = [[a, b]]
    # a's clock stops at order 9, not here: `clock` ignores it, `clockany` acts on it
    env = Env(g, now=0.0, open_clocks={id(a): (9, 1800.0, 1, 3600.0)})
    assert batch_fire.choose(env, "clock", 2.0) == len(g)
    assert batch_fire.choose(env, "clockany", 2.0) == 0
    assert batch_fire.choose(env, "clockany", 0.0) == env.rule_action()


def test_nach_waits_only_when_next_arrival_is_worth_it():
    st = Step(batch_max=6)
    g = [[Lot(st), Lot(st)]]
    S = st.processing_time.m
    env = Env(g, now=0.0, next_arr=600.0)                # 2 lots x 10 min < one lot x S: wait
    assert batch_fire.choose(env, "nach", 0.0) == len(g)
    env = Env(g, now=0.0, next_arr=S)                    # 2 x S > S: run now
    assert batch_fire.choose(env, "nach", 0.0) == 0
    env = Env(g, now=0.0, next_arr=None)                 # nothing on its way: run now
    assert batch_fire.choose(env, "nach", 0.0) == 0


def test_nach_dl_never_outwaits_a_clock():
    st = Step(batch_max=6)
    a, b = Lot(st), Lot(st)
    g = [[a, b]]
    # a's clock ends in 15 min, the next arrival is 30 min away: run now
    env = Env(g, now=0.0, open_clocks={id(a): (st.order, 900.0, 1, 3600.0)}, next_arr=1800.0)
    assert batch_fire.choose(env, "nach_dl", 0.0) == 0
    # clock ends in 2 h, next arrival in 10 min: NACH's wait stands
    env = Env(g, now=0.0, open_clocks={id(a): (st.order, 7200.0, 1, 3600.0)}, next_arr=600.0)
    assert batch_fire.choose(env, "nach_dl", 0.0) == len(g)


def test_parse_arm():
    assert batch_fire.parse_arm("full") == ("full", 0.0)
    assert batch_fire.parse_arm("clock:2") == ("clock", 2.0)
    assert batch_fire.parse_arm("timeout:1.5") == ("timeout", 1.5)
    assert batch_fire.parse_arm("nach") == ("nach", 0.0)
    assert batch_fire.parse_arm("nach_dl:2") == ("nach_dl", 2.0)
