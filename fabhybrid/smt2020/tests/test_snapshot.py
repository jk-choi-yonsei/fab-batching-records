"""scrap_snap.py -> FabEnv.reset(snapshot=...) round trip: the open clocks come
back, the fab keeps running, and two restores from the same snapshot with the
same seed give the same window (common random numbers)."""
import gzip
import os
import subprocess
import sys

import cloudpickle

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import batch_fire  # noqa: E402
from fab_env import FabEnv  # noqa: E402

SNAP = os.path.join(HERE, "..", "..", "experiments", "smt2020", "scrap_snaps", "_test_snap_HVLM_s0.pkl.gz")


def make_snapshot():
    if os.path.exists(SNAP):
        return
    cmd = [sys.executable, "scrap_snap.py", "--dataset", "HVLM", "--scale", "0.98", "--seed", "0",
           "--days", "2", "--window", "4", "--out", SNAP]
    subprocess.run(cmd, cwd=HERE, check=True, env=dict(os.environ, OMP_NUM_THREADS="1", PYTHONIOENCODING="utf-8"))


def window(seed, days=1):
    env = FabEnv(dataset="HVLM", seed=seed, episode_days=days, horizon_days=days + 1,
                 rule="cr", scrap=True, reward="yield", batch_only=True)
    obs = env.reset(seed=seed, snapshot=SNAP)
    n_open = len(env.cqt.open)
    total, steps = 0.0, 0
    while obs is not None:
        obs, r, done, _ = env.step(batch_fire.choose(env, "clock", 2.0))
        total += r
        steps += 1
        if done:
            break
    return env, n_open, total, steps


def test_round_trip_restores_clocks_and_is_reproducible():
    make_snapshot()
    with gzip.open(SNAP, "rb") as f:
        meta = cloudpickle.load(f)["meta"]
    env, n_open, total, steps = window(seed=0)
    assert n_open == meta["open_clocks"] > 0
    assert env.t0 > 0 and env.instance.current_time > env.t0
    assert steps > 0
    assert len(env.instance.done_lots) > meta["done"]         # the fab kept completing lots
    env2, n_open2, total2, steps2 = window(seed=0)
    assert (n_open2, steps2) == (n_open, steps)
    assert abs(total2 - total) < 1e-9
    assert len(env2.instance.done_lots) == len(env.instance.done_lots)
