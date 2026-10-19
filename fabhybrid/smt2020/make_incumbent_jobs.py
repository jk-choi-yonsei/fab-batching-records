"""Job files of experiments/smt2020/final/incumbent/PROTOCOL_incumbent.md: tables fitted from the
records of the minimum-batch-size rule (q = 3) and NACH, one logging period each, no reversals.

  python make_incumbent_jobs.py     # writes jobs/incumbent_{log,fit,report}.txt
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(HERE, "..", "..", "experiments", "smt2020", "jobs")
FINAL = os.path.join(HERE, "..", "..", "experiments", "smt2020", "final")
C = "../../experiments/smt2020/final/collect"
R = "../../experiments/smt2020/final/report"
CFG = "--scale 0.98 --days 360 --measure-from 0.241667"
RULES = [("mbs3", "mbs:3"), ("nach", "nach")]
FABS = ["HVLM", "LVHM"]


def main():
    sel = json.load(open(os.path.join(FINAL, "rx", "selection_rx.json")))
    H = "# final/incumbent/PROTOCOL_incumbent.md: "
    log, fit, rep = [], [], []
    for fab in FABS:
        beta = sel[fab]["selected_beta"]
        b = "b" + beta.replace(".", "p")
        for tag, arm in RULES:
            dumps = [f"{C}/{fab}_{tag}_p1_s{s}.json" for s in (100, 101)]
            for s, d in zip((100, 101), dumps):
                log.append(f"python readout.py --arm {arm} --dataset {fab} --days 181 --seed {s} --dump-from 90 --slim "
                           f"--dump-lots {d}  ->  {d}")
            t = f"{C}/{fab}_{tag}_{b}_t1rx.json"
            fit.append(f"python fit_q.py {' '.join(dumps)} --chain family --lam {beta} --backoff --from-day 90 "
                       f"--fold fill --out {t}  ->  {t}")
            stem = f"{fab}_{tag}_{b}_t1rx"
            rep += [f"python batch_fire.py --dataset {fab} {CFG} --arm level:1 --theta {t} --cqt-rule qtcr --scrap "
                    f"--seed {s} --out {R}  ->  {R}/batch_fire_{fab}_r0.98_d360_s{s}_level1_{stem}_qtcr_scrap.json"
                    for s in range(32)]
    for name, head, lines in (("incumbent_log.txt", "one logging period under each rule, no reversals", log),
                              ("incumbent_fit.txt", "table 1 on (residual, arrival) from each rule's records", fit),
                              ("incumbent_report.txt", "the rule-records tables on report seeds 0-31", rep)):
        with open(os.path.join(JOBS, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(H + head + "\n\n" + "\n".join(lines) + "\n")
        print(name, len(lines))


if __name__ == "__main__":
    main()
