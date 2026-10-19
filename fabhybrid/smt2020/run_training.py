"""The learned-policy pipeline, end to end, for one training fab:

  1. wait for the warm snapshots (and, optionally, for the arm queues to free the cores)
  2. calibrate feature normalisation on the training snapshots
  3. behaviour-clone the law (theta_0)
  4. PPO from theta_0
  5. evaluate weights_best.pt greedily: training fab 0.98 (8 seeds), the other
     fab 0.98 (8 seeds, zero-shot), training fab at 0.7 and 1.2 (2 seeds)

Every step is skipped if its output already exists, so the script can be
re-run to resume. Logs go to experiments/smt2020/runs/batch_<fab><suffix>/pipeline.log.

  python run_training.py --dataset HVLM --cqt-rule qtcr --suffix _qtcr --no-eval   # as jobs/retrain_bcppo_qtcr.sh
"""
import argparse
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, "..", "..", "experiments", "smt2020")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="HVLM")
    ap.add_argument("--after", default=None, help="wait for this marker before training")
    ap.add_argument("--iters", type=int, default=16)
    ap.add_argument("--days", type=float, default=10.0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--bc-episodes", type=int, default=8)
    ap.add_argument("--bc-days", type=float, default=10.0)
    ap.add_argument("--eval-parallel", type=int, default=6)
    ap.add_argument("--cqt-rule", default="none",
                    help="queue-time rule of the training windows; qtcr for the 2026-10 retraining")
    ap.add_argument("--suffix", default="",
                    help="suffix of the runs directory (runs/batch_<fab><suffix>) and of the snapshot names "
                         "(snap_<fab>_r0.98<suffix>_s*.pkl.gz); '_qtcr' for the 2026-10 retraining")
    ap.add_argument("--runs-suffix", default=None,
                    help="suffix of the runs directory when it differs from the snapshots' (default: --suffix); "
                         "'_qtcr2' for the 2026-10-19 retraining without the elapsed-time inputs")
    ap.add_argument("--no-eval", action="store_true", help="stop after PPO; the block's own jobs evaluate the weights")
    a = ap.parse_args()

    other = "LVHM" if a.dataset == "HVLM" else "HVLM"
    runs = os.path.join(EXP, "runs", f"batch_{a.dataset}{a.runs_suffix if a.runs_suffix is not None else a.suffix}")
    os.makedirs(runs, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", PYTHONIOENCODING="utf-8", FAB_BATCH_RUNS=runs)
    log = open(os.path.join(runs, "pipeline.log"), "a", encoding="utf-8")

    def note(msg):
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"); log.flush()

    def run(args, tag):
        note(f"start {tag}: {' '.join(args)}")
        with open(os.path.join(runs, f"{tag}.log"), "a", encoding="utf-8") as out:
            rc = subprocess.call([sys.executable] + args, cwd=HERE, env=env, stdout=out, stderr=subprocess.STDOUT)
        note(f"end {tag} rc={rc}")
        if rc:
            raise SystemExit(f"{tag} failed (rc={rc}); see {runs}/{tag}.log")

    snap_glob = os.path.join(EXP, "scrap_snaps", f"snap_{a.dataset}_r0.98{a.suffix}_s*.pkl.gz")
    cqt = ["--cqt-rule", a.cqt_rule]
    while len(glob.glob(snap_glob)) < 4:
        note(f"waiting for snapshots {snap_glob}")
        time.sleep(60)
    if a.after:
        while not os.path.exists(a.after):
            note(f"waiting for {a.after}")
            time.sleep(60)

    if not os.path.exists(os.path.join(runs, "norm.json")):
        run(["train_batch.py", "--calibrate", "--dataset", a.dataset, "--snap-glob", snap_glob, "--days", "5"] + cqt,
            "calibrate")
    if not os.path.exists(os.path.join(runs, "weights_bc.pt")):
        run(["train_batch.py", "--bc", "--dataset", a.dataset, "--snap-glob", snap_glob, "--law", "clock:2",
             "--days", str(a.bc_days), "--episodes", str(a.bc_episodes), "--bc-epochs", "60"] + cqt, "bc")
    if not os.path.exists(os.path.join(runs, "weights_best.pt")) or not os.path.exists(os.path.join(runs, "ppo.done")):
        run(["train_batch.py", "--learn", "--dataset", a.dataset, "--snap-glob", snap_glob,
             "--init", os.path.join(runs, "weights_bc.pt"), "--days", str(a.days), "--iters", str(a.iters),
             "--workers", str(a.workers), "--critic-warmup", "2"] + cqt, "ppo")
        open(os.path.join(runs, "ppo.done"), "w").write("done\n")
    if a.no_eval:
        note("pipeline done (no evaluation here)")
        open(os.path.join(runs, "pipeline.done"), "w").write("done\n")
        return

    # evaluation: the arm protocol, greedy, from t=0
    jobs = []
    out_dir = os.path.join(EXP, "batch_fire_scrap")
    w = os.path.join(runs, "weights_best.pt")
    norm = os.path.join(runs, "norm.json")
    tag = f"ppo{a.dataset}"
    for ds, scale, seeds in ((a.dataset, 0.98, range(8)), (other, 0.98, range(8)),
                             (a.dataset, 0.7, range(2)), (a.dataset, 1.2, range(2))):
        for s in seeds:
            expect = os.path.join(out_dir, f"batch_fire_{ds}_r{scale}_d180_s{s}_rl-{tag}_scrap.json")
            if os.path.exists(expect):
                continue
            jobs.append([sys.executable, "eval_batch.py", "--weights", w, "--norm", norm, "--dataset", ds,
                         "--scale", str(scale), "--days", "180", "--seed", str(s), "--tag", tag, "--out", out_dir])
    note(f"evaluation: {len(jobs)} runs")
    running = []
    for cmd in jobs:
        while sum(p.poll() is None for p in running) >= a.eval_parallel:
            time.sleep(10)
        running.append(subprocess.Popen(cmd, cwd=HERE, env=env, stdout=subprocess.DEVNULL,
                                        stderr=open(os.path.join(runs, "eval.err"), "a")))
    while any(p.poll() is None for p in running):
        time.sleep(10)
    note("pipeline done")
    open(os.path.join(runs, "pipeline.done"), "w").write("done\n")


if __name__ == "__main__":
    main()
