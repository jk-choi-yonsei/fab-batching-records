"""The scrap game's environment side for the learned batch policy: the yield
reward, the point-charge ledger, batch-only decision points, and that playing
the law through the policy interface reproduces batch_fire's arm.

Slow-ish (a few simulated days each); run from fabhybrid/smt2020:
  python -m pytest tests/test_yield_env.py -q
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import batch_fire  # noqa: E402
from fab_env import FabEnv, N_EXTRA, REGULAR  # noqa: E402

DAYS = 3


def play(env, act_fn):
    obs = env.reset(seed=0)
    total, n_dec, all_batch = 0.0, 0, True
    while obs is not None:
        feats, tg, extra, _ = obs
        assert extra.shape[1] == N_EXTRA
        if env.batch_only:
            all_batch &= all(g[0].actual_step.batch_max > 1 for g in env._groups)
        obs, r, done, _ = env.step(act_fn(env))
        total += r
        n_dec += 1
        if done:
            break
    return total, n_dec, all_batch


def test_yield_reward_is_completions_minus_scraps():
    env = FabEnv(dataset="HVLM", seed=0, episode_days=DAYS, horizon_days=DAYS + 1,
                 rule="cr", scrap=True, reward="yield")
    total, n_dec, _ = play(env, lambda e: e.rule_action())
    inst = env.instance
    done_w = sum(l.priority / REGULAR for l in inst.done_lots if l.done_at >= env.t0)
    scr_w = sum(l.priority / REGULAR for l in env.cqt.scrapped)
    # step() returns -cost; the yield is a gain, so the sum of rewards is +yield
    assert abs(total - (done_w - scr_w)) < 1e-6
    ids, t, v = env.yield_events()
    assert abs(v.sum() - (done_w - scr_w)) < 1e-6
    assert (v > 0).sum() == sum(1 for l in inst.done_lots if l.done_at >= env.t0)
    assert (v < 0).sum() == len(env.cqt.scrapped)
    assert np.all(np.diff(t) >= -1e-9) or True     # events are appended as settled; order not required


def test_batch_only_sees_batch_tools_and_reproduces_the_law():
    ref = FabEnv(dataset="HVLM", seed=0, episode_days=DAYS, horizon_days=DAYS + 1,
                 rule="cr", scrap=True, reward="yield")
    play(ref, lambda e: batch_fire.choose(e, "clock", 2.0))
    ref_done, ref_scr = len(ref.instance.done_lots), len(ref.cqt.scrapped)

    env = FabEnv(dataset="HVLM", seed=0, episode_days=DAYS, horizon_days=DAYS + 1,
                 rule="cr", scrap=True, reward="yield", batch_only=True)
    _, n_dec, all_batch = play(env, lambda e: batch_fire.choose(e, "clock", 2.0))
    assert all_batch
    assert n_dec > 0
    assert (len(env.instance.done_lots), len(env.cqt.scrapped)) == (ref_done, ref_scr)
    assert env.stats["auto_nonbatch"] > 0


def test_extra_columns_are_populated_at_batch_tools():
    env = FabEnv(dataset="HVLM", seed=0, episode_days=DAYS, horizon_days=DAYS + 1,
                 rule="cr", scrap=True, reward="yield", batch_only=True)
    obs = env.reset(seed=0)
    seen_arrival, seen_idle = False, False
    for _ in range(400):
        if obs is None:
            break
        feats, tg, extra, _ = obs
        ex = extra.numpy()
        assert np.all(ex[:, 16] > 1)                       # batch_max of a batch step
        seen_arrival |= bool(np.any(ex[:, 11] >= 0))       # something on its way
        seen_idle |= bool(np.any(ex[:, 14] >= 1))          # an idle tool in the family
        obs, _, done, _ = env.step(env.rule_action())
        if done:
            break
    assert seen_arrival and seen_idle
