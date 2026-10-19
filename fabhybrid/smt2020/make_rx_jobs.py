"""Job files of experiments/smt2020/final/rx/PROTOCOL_rx.md: the learner on (residual, arrival).

Stage 1 (collection, per beta and scenario): t1rx -> p2rx -> t2rx -> p3rx -> t3rx, every fit
with --fold fill, the period-2/3 loggers being the 24-cell tables themselves.
Stage 2: the five t3rx tables on the selection seeds (80 runs) and the report seeds (320).
Stage 3 (after rx_select.py, archived): the selected price's t1rx/t2rx, the three restrictions of its
records, and the timeout-records table refitted without the fill, on the report seeds.

  python make_rx_jobs.py            # stages 1-2, prints the launch lines
  python make_rx_jobs.py --stage 3  # needs final/rx/selection_rx.json
"""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(HERE, "..", "..", "experiments", "smt2020", "jobs")
FINAL = os.path.join(HERE, "..", "..", "experiments", "smt2020", "final")
C = "../../experiments/smt2020/final/collect"
REPORT = "../../experiments/smt2020/final/report"
SEARCH = "../../experiments/smt2020/final/search"
BETAS = [0.001, 0.003, 0.01, 0.02, 0.04]
FABS = ["HVLM", "LVHM"]
WARMUP, WINDOW = 90, 91
EPS, EPS_FIRE = 0.02, 0.30
SEEDS = {1: (100, 101), 2: (102, 103), 3: (104, 105)}
CFG = "--scale 0.98 --days 360 --measure-from 0.241667"


def btag(b):
    return "b" + f"{b:g}".replace(".", "p")


def dump(fab, period, seed, b=None):
    return f"{C}/{fab}_p1_s{seed}.json" if period == 1 else f"{C}/{fab}_{btag(b)}_p{period}rx_s{seed}.json"


def table(fab, b, k):
    return f"{C}/{fab}_{btag(b)}_t{k}rx.json"


def dumps_upto(fab, b, k):
    d = [dump(fab, 1, s) for s in SEEDS[1]]
    for p in range(2, k + 1):
        d += [dump(fab, p, s, b) for s in SEEDS[p]]
    return " ".join(d)


def fit(fab, b, k, fold="fill", out=None):
    out = out or table(fab, b, k)
    fo = f" --fold {fold}" if fold else ""
    return (f"python fit_q.py {dumps_upto(fab, b, k)} --chain family --lam {b:g} --backoff --from-day {WARMUP}{fo} "
            f"--out {out}  ->  {out}")


def log(fab, period, seed, b):
    d = dump(fab, period, seed, b)
    return (f"python readout.py --arm level:1 --theta {table(fab, b, period - 1)} --eps-wf {EPS} --eps-fw {EPS_FIRE} "
            f"--dataset {fab} --days {WARMUP + WINDOW} --seed {seed} --dump-from {WARMUP} --slim --dump-lots {d}  ->  {d}")


def run(fab, theta, seed, out_dir):
    stem = os.path.basename(theta)[:-5]
    return (f"python batch_fire.py --dataset {fab} {CFG} --arm level:1 --theta {theta} --cqt-rule qtcr --scrap "
            f"--seed {seed} --out {out_dir}  ->  {out_dir}/batch_fire_{fab}_r0.98_d360_s{seed}_level1_{stem}_qtcr_scrap.json")


def write(name, header, lines):
    with open(os.path.join(JOBS, name), "w", encoding="utf-8", newline="\n") as f:
        f.write("# " + header + "\n\n" + "\n".join(lines) + "\n")
    return len(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=12)
    a = ap.parse_args()
    H = "final/rx/PROTOCOL_rx.md: "
    if a.stage == 12:
        order = []
        for k in (1, 2, 3):
            n = write(f"rx_t{k}.txt", H + f"table {k} on (residual, arrival), periods 1-{k}",
                      [fit(f, b, k) for f in FABS for b in BETAS])
            order.append((f"rx_t{k}", n, 4))
            if k < 3:
                n = write(f"rx_p{k + 1}.txt", H + f"period {k + 1}, logged by the 24-cell table {k} with reversals",
                          [log(f, k + 1, s, b) for f in FABS for b in BETAS for s in SEEDS[k + 1]])
                order.append((f"rx_p{k + 1}", n, 10))
        n = write("rx_search.txt", H + "the five t3rx tables on the selection seeds 108-115",
                  [run(f, table(f, b, 3), s, SEARCH) for s in range(108, 116) for f in FABS for b in BETAS])
        order.append(("rx_search", n, 10))
        n = write("rx_report.txt", H + "the five t3rx tables on the report seeds 0-31",
                  [run(f, table(f, b, 3), s, REPORT) for s in range(32) for f in FABS for b in BETAS])
        order.append(("rx_report", n, 10))
        prev = None
        cmds = []
        for name, n, par in order:
            after = f" --after ../../experiments/smt2020/jobs/{prev}.done" if prev else ""
            cmds.append(f"python run_queue.py ../../experiments/smt2020/jobs/{name}.txt --parallel {par}{after} "
                        f"--done-marker ../../experiments/smt2020/jobs/{name}.done")
            print(f"{name}: {n}")
            prev = name
        print(" && ".join(cmds))
        return
    sel = json.load(open(os.path.join(FINAL, "rx", "selection_rx.json")))
    fits, runs = [], []
    for fab in FABS:
        b = float(sel[fab]["selected_beta"])
        bt = btag(b)
        for fold, name in (("nxt,fill", "residual"), ("nxt", "residual_fill"), ("", "addfill")):
            out = f"{C}/{fab}_{bt}_t3rx_abl_{name}.json"
            fits.append(fit(fab, b, 3, fold, out))
            runs += [run(fab, out, s, REPORT) for s in range(32)]
        nr = f"{C}/{fab}_norev_{bt}_t1rx.json"
        fits.append(f"python fit_q.py {C}/{fab}_norev_p1_s100.json {C}/{fab}_norev_p1_s101.json --chain family "
                    f"--lam {b:g} --backoff --from-day {WARMUP} --fold fill --out {nr}  ->  {nr}")
        runs += [run(fab, nr, s, REPORT) for s in range(32)]
        for k in (1, 2):
            runs += [run(fab, table(fab, b, k), s, REPORT) for s in range(32)]
    print("rx_sel_fits:", write("rx_sel_fits.txt", H + "restrictions and the timeout-records table at the selected price", fits))
    print("rx_sel_report:", write("rx_sel_report.txt", H + "report seeds for the selected price's ablations, t1rx, t2rx, norev", runs))


if __name__ == "__main__":
    main()
