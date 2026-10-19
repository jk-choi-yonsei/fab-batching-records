"""Write the job files of the declared data-collection protocol.

One procedure, identical on both scenarios, run once for each value of the
exchange rate beta (the price of an empty slot-hour), so that every candidate is
a self-contained pipeline and nothing is borrowed across candidates:

  period 1   the load-building rule (full batches only), firing an under-full
             load with a live clock with probability EPS               seeds P1
  table 1    fit_q on period 1
  period 2   table 1, a WAIT reversed with probability EPS and a FIRE with
             probability EPS_FIRE                                       seeds P2
  table 2    fit_q on periods 1-2
  period 3   table 2, same reversal probabilities                       seeds P3
  table 3    fit_q on periods 1-3            <- the table that is evaluated

A period is WINDOW days of steady-state operation: every logging run lasts
WARMUP + WINDOW days under its own logging policy and only the window is kept.
WINDOW = 91 is one cycle of the benchmark's quarterly maintenance calendar.
Period 1 does not depend on beta and is shared. Logging seeds are disjoint from
the search seeds (108-115) and the report seeds (0-31).

  python make_collect_jobs.py            # writes jobs/collect_*.txt and prints the launch lines
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(HERE, "..", "..", "experiments", "smt2020", "jobs")
OUT = "../../experiments/smt2020/final/collect"

BETAS = [0.001, 0.003, 0.01, 0.02, 0.04]
FABS = ["HVLM", "LVHM"]
WARMUP, WINDOW = 90, 91
EPS, EPS_FIRE = 0.02, 0.30
SEEDS = {1: (100, 101), 2: (102, 103), 3: (104, 105)}


def btag(b):
    return "b" + f"{b:g}".replace(".", "p")


def dump(fab, period, seed, b=None):
    return f"{OUT}/{fab}_p1_s{seed}.json" if period == 1 else f"{OUT}/{fab}_{btag(b)}_p{period}_s{seed}.json"


def table(fab, b, k):
    return f"{OUT}/{fab}_{btag(b)}_t{k}.json"


def log_cmd(fab, period, seed, b=None):
    days = WARMUP + WINDOW
    common = f"--dataset {fab} --days {days} --seed {seed} --dump-from {WARMUP} --slim --dump-lots {dump(fab, period, seed, b)}"
    if period == 1:
        return f"python readout.py --arm explore:{EPS} {common}"
    return (f"python readout.py --arm level:1 --theta {table(fab, b, period - 1)} "
            f"--eps-wf {EPS} --eps-fw {EPS_FIRE} {common}")


def fit_cmd(fab, b, k):
    dumps = [dump(fab, 1, s) for s in SEEDS[1]]
    for p in range(2, k + 1):
        dumps += [dump(fab, p, s, b) for s in SEEDS[p]]
    return (f"python fit_q.py {' '.join(dumps)} --chain family --lam {b:g} --backoff "
            f"--from-day {WARMUP} --out {table(fab, b, k)}")


def write(name, header, lines):
    p = os.path.join(JOBS, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(["# " + h for h in header] + [""] + lines) + "\n")
    return len(lines)


def main():
    os.makedirs(os.path.join(HERE, OUT), exist_ok=True)
    stages = []
    n = write("collect_p1.txt", ["Collection, period 1: the load-building rule plus a firing probability of "
                                 f"{EPS}; {WINDOW}-day window after a {WARMUP}-day warm-up; shared by every beta."],
              [f"{log_cmd(f, 1, s)}  ->  {dump(f, 1, s)}" for f in FABS for s in SEEDS[1]])
    stages.append(("collect_p1", n))
    for k in (1, 2, 3):
        n = write(f"collect_t{k}.txt", [f"Collection, table {k}: fit_q on periods 1-{k}, one table per beta and scenario."],
                  [f"{fit_cmd(f, b, k)}  ->  {table(f, b, k)}" for f in FABS for b in BETAS])
        stages.append((f"collect_t{k}", n))
        if k < 3:
            n = write(f"collect_p{k + 1}.txt",
                      [f"Collection, period {k + 1}: table {k}, a WAIT reversed with probability {EPS} and a FIRE with "
                       f"{EPS_FIRE}; same window."],
                      [f"{log_cmd(f, k + 1, s, b)}  ->  {dump(f, k + 1, s, b)}"
                       for f in FABS for b in BETAS for s in SEEDS[k + 1]])
            stages.append((f"collect_p{k + 1}", n))
    order = ["collect_p1", "collect_t1", "collect_p2", "collect_t2", "collect_p3", "collect_t3"]
    counts = dict(stages)
    print("stages:", ", ".join(f"{s} ({counts[s]})" for s in order))
    prev = None
    for s in order:
        after = f" --after ../../experiments/smt2020/jobs/{prev}.done" if prev else ""
        print(f"python run_queue.py ../../experiments/smt2020/jobs/{s}.txt --parallel 4{after} "
              f"--done-marker ../../experiments/smt2020/jobs/{s}.done")
        prev = s


if __name__ == "__main__":
    main()
