"""Warm the scrap game under an arm and snapshot the fab for training windows.

The learned batch policy starts from the law, so its windows start from a fab
the law has been running: warm `--days` days under `--arm` (default clock:2),
then pickle the instance and the simulator's RNG state. The queue-time monitor
keys its open clocks by object identity, which a pickle round-trip destroys,
so every open clock is stamped on its lot (`lot._cqt_open`) before pickling and
FabEnv.reset(snapshot=...) rebuilds the table from the lots.

  python scrap_snap.py --dataset HVLM --scale 0.98 --seed 0 --days 90 --window 60 \
      --out ../../experiments/smt2020/scrap_snaps/snap_HVLM_r0.98_s0.pkl.gz
"""
import argparse
import gzip
import os
import time

import cloudpickle

import batch_fire
import scenarios
from fab_env import FabEnv
from simulation.randomizer import Randomizer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="HVLM")
    ap.add_argument("--scale", type=float, default=0.98)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--days", type=int, default=90, help="warm-up length")
    ap.add_argument("--window", type=int, default=60, help="release supply kept beyond the warm-up")
    ap.add_argument("--arm", default="clock:2")
    ap.add_argument("--cqt-rule", default="none",
                    help="queue-time rule of the warm-up (none or qtcr); the 2026-09 snapshots used none")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    kind, coef = batch_fire.parse_arm(a.arm)
    t_wall = time.time()
    horizon = int((a.days + a.window) * max(1.0, a.scale)) + 2
    env = FabEnv(dataset=a.dataset, seed=a.seed, episode_days=a.days, horizon_days=horizon,
                 rule="cr", scrap=True, reward="yield", cqt_rule=a.cqt_rule)
    obs = env.reset(seed=a.seed)
    if a.scale < 1.0:
        scenarios.scale_release(env.instance, a.scale)
        env.rebuild_deadlines()
    elif a.scale > 1.0:
        scenarios.compress_release(env.instance, a.scale)
        env.rebuild_deadlines()
    while obs is not None:
        obs, _, done, _ = env.step(batch_fire.choose(env, kind, coef))
        if done:
            break
    inst = env.instance
    # stamp the open clocks on their lots; the monitor's table is rebuilt on load
    n_open = 0
    for lot in inst.active_lots:
        rec = env.cqt.open.get(id(lot))
        if rec is not None:
            lot._cqt_open = rec
            n_open += 1
    inst.plugins = []                      # the monitor holds a bound method of the env
    snap = {"inst": inst, "rng": Randomizer().random.getstate(),
            "meta": {"dataset": a.dataset, "scale": a.scale, "seed": a.seed, "days": a.days,
                     "arm": a.arm, "cqt_rule": a.cqt_rule, "wip": len(inst.active_lots), "open_clocks": n_open,
                     "done": len(inst.done_lots), "scrapped": len(env.cqt.scrapped),
                     "pending_releases": len(inst.dispatchable_lots)}}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with gzip.open(a.out, "wb", compresslevel=4) as f:
        cloudpickle.dump(snap, f)
    print(snap["meta"], f"wall {time.time() - t_wall:.0f}s", "wrote", a.out)


if __name__ == "__main__":
    main()
