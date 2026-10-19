"""Run the commands in a job file, N at a time, from this directory.

Line format:   <command>  ->  <expected output path>
The output path decides whether a job is skipped (already on disk) and where
its stderr goes (<path>.err). Blank lines and lines starting with # are
ignored. Progress is appended to <jobfile>.log; --done-marker is written when
every job has exited; --after waits for another queue's marker first.

  python run_queue.py ../../experiments/smt2020/jobs/e2.txt --parallel 6 \
      --after ../../experiments/smt2020/batch_fire_scrap/_queue_e1_done.txt \
      --done-marker ../../experiments/smt2020/jobs/e2.done
"""
import argparse
import os
import subprocess
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobfile")
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--after", default=None, help="wait until this file exists")
    ap.add_argument("--done-marker", default=None)
    a = ap.parse_args()

    env = dict(os.environ, OMP_NUM_THREADS="1", PYTHONIOENCODING="utf-8")
    jobs = []
    for line in open(a.jobfile, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cmd, _, out = line.partition("->")
        jobs.append((cmd.strip(), out.strip()))

    log = open(a.jobfile + ".log", "a", encoding="utf-8")

    def note(msg):
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
        log.flush()

    if a.after:
        note(f"waiting for {a.after}")
        while not os.path.exists(a.after):
            time.sleep(20)
    note(f"start: {len(jobs)} jobs, {a.parallel} parallel")
    running = []
    for cmd, out in jobs:
        if out and os.path.exists(out):
            note(f"skip (exists) {out}")
            continue
        while sum(p.poll() is None for p in running) >= a.parallel:
            time.sleep(5)
        if out:
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        err = open(out + ".err", "w") if out else subprocess.DEVNULL
        running.append(subprocess.Popen(cmd, shell=True, env=env,
                                        stdout=subprocess.DEVNULL, stderr=err))
        note(f"launched {cmd}")
    while any(p.poll() is None for p in running):
        time.sleep(5)
    failed = [p for p in running if p.returncode not in (0, None)]
    note(f"all done, {len(failed)} non-zero exits")
    if a.done_marker:
        with open(a.done_marker, "w") as f:
            f.write(f"done {time.strftime('%Y-%m-%d %H:%M:%S')} failed={len(failed)}\n")


if __name__ == "__main__":
    main()
