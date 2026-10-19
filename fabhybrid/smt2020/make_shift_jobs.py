"""Job files and launch chain of experiments/smt2020/final/shift/PROTOCOL_shift.md: the release rate
moved from 0.98 to 0.90, 0.80 and (if stable) 1.05; stale rules and tables, refitted tables, and the
control limit retuned at each rate.

  python make_shift_jobs.py                  # writes jobs/shift_step0.txt, shift_probe.txt,
                                             # shift_<rate>_{a,fit}.txt for 0.90 and 0.80, and jobs/shift.cmd
  python make_shift_jobs.py --prelaunch      # removes __pycache__ under fabhybrid/ and external/; refuses
                                             # (exit 1) unless the stale tables match the hashes of
                                             # PROTOCOL_confirm.md, fabhybrid/ and external/ are clean in git,
                                             # and the job files on disk equal what this script writes
  python make_shift_jobs.py --check-step0    # the two step-0 runs identical in every field but wall_s, and
                                             # the block's own seed-64 run against them once it exists
  python make_shift_jobs.py --stage-b 0.90   # after stage A and the fits of that rate: writes
                                             # shift_<rate>_b.txt with the refitted tables on seeds 64-95 and,
                                             # if the retuned threshold is not 1.5 h, that control limit too
  python make_shift_jobs.py --gate-high      # after the probe: writes shift_r1p05_{a,fit}.txt if every probe
                                             # run has |back-half WIP slope| < 1 lot/day, else empty files and
                                             # final/shift/HIGH_SKIPPED.txt
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

from make_confirm_jobs import PINNED, strip  # the artefact hashes of PROTOCOL_confirm.md; the field comparison

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
EXP = os.path.join(ROOT, "experiments")
JOBS = os.path.join(EXP, "smt2020", "jobs")
F = "../../experiments/smt2020/final"
S = f"{F}/shift"
FAM = f"{F}/betarx/family"
CFG = "--days 360 --measure-from 0.241667"
FABS = ["HVLM", "LVHM"]
RULES = [("timeout", "timeout:1"), ("mbs3", "mbs:3"), ("nach", "nach")]
REPORT_SEEDS = list(range(64, 96))
SELECT_SEEDS = list(range(108, 116))
RECORD_SEEDS = (100, 101)
THETAS = ["0.5", "0.75", "1", "1.5", "2", "3", "4"]
RATES = [0.90, 0.80]
HIGH = 1.05
SLOPE_MAX = 1.0                 # lots per day, back half of the probe runs
PARALLEL = 14
STEP0_SEED = 64
RL = os.path.dirname(os.path.abspath(sys.executable))


def rname(rate):
    """What batch_fire.py prints into the file name for --scale <rate>."""
    return f"{float(rate):g}"


def rtag(rate):
    return "r" + f"{float(rate):.2f}".replace(".", "p")


def stale(fab, tag):
    return f"{FAM}/{fab}_{tag}_b0p003_t1.json"


def dump(fab, tag, rate, seed):
    return f"{S}/records/{fab}_{tag}_{rtag(rate)}_p1_s{seed}.json"


def refit(fab, tag, rate):
    return f"{S}/tables/{fab}_{tag}_{rtag(rate)}_b0p003_t1.json"


def rule_run(fab, arm, rate, seed, out):
    return (f"python batch_fire.py --dataset {fab} --scale {rname(rate)} {CFG} --arm {arm} --cqt-rule qtcr --scrap "
            f"--seed {seed} --out {out}  ->  "
            f"{out}/batch_fire_{fab}_r{rname(rate)}_d360_s{seed}_{arm.replace(':', '')}_qtcr_scrap.json")


def table_run(fab, theta, rate, seed, out):
    stem = os.path.basename(theta)[:-5]
    return (f"python batch_fire.py --dataset {fab} --scale {rname(rate)} {CFG} --arm level:1 --theta {theta} "
            f"--cqt-rule qtcr --scrap --seed {seed} --out {out}  ->  "
            f"{out}/batch_fire_{fab}_r{rname(rate)}_d360_s{seed}_level1_{stem}_qtcr_scrap.json")


def record_run(fab, arm, tag, rate, seed):
    d = dump(fab, tag, rate, seed)
    return (f"python readout.py --arm {arm} --dataset {fab} --scale {rname(rate)} --days 181 --seed {seed} "
            f"--dump-from 90 --slim --dump-lots {d}  ->  {d}")


def fit_job(fab, tag, rate):
    t = refit(fab, tag, rate)
    dumps = " ".join(dump(fab, tag, rate, s) for s in RECORD_SEEDS)
    return (f"python fit_q.py {dumps} --chain family --lam 0.003 --backoff --from-day 90 --fold fill --out {t}"
            f"  ->  {t}")


def out_of(line):
    return line.split("  ->  ")[1]


def local(p):
    return os.path.normpath(os.path.join(HERE, p))


def job_file(header, lines):
    outs = [out_of(l) for l in lines]
    assert len(set(outs)) == len(outs), f"{header}: two jobs share an output path"
    return "# PROTOCOL_shift.md: " + header + "\n\n" + "\n".join(lines) + "\n"


def stage_a(rate):
    lines = []
    for fab in FABS:
        for tag, arm in RULES:
            lines += [record_run(fab, arm, tag, rate, s) for s in RECORD_SEEDS]
    for fab in FABS:
        for _, arm in RULES + [("clock", "clock:1.5")]:
            lines += [rule_run(fab, arm, rate, s, f"{S}/report") for s in REPORT_SEEDS]
        for tag, _ in RULES:
            lines += [table_run(fab, stale(fab, tag), rate, s, f"{S}/report") for s in REPORT_SEEDS]
        for th in THETAS:
            lines += [rule_run(fab, f"clock:{th}", rate, s, f"{S}/select") for s in SELECT_SEEDS]
    return job_file(f"stage A at rate {rname(rate)}: records, the rules and tables of 0.98 on seeds 64-95, "
                    f"the threshold grid on seeds 108-115", lines)


def stage_fit(rate):
    return job_file(f"fits at rate {rname(rate)}: the learner on each rule's records, beta 0.003",
                    [fit_job(fab, tag, rate) for fab in FABS for tag, _ in RULES])


def step0():
    return job_file("step 0: the timeout rule at 0.90, HVLM seed 64, twice",
                    [rule_run("HVLM", "timeout:1", RATES[0], STEP0_SEED, f"{S}/step0/{x}") for x in "ab"])


def probe():
    return job_file(f"probe at rate {rname(HIGH)}: the control limit at 1.5 h, seeds 64 and 65",
                    [rule_run(fab, "clock:1.5", HIGH, s, f"{S}/probe") for fab in FABS for s in (64, 65)])


def build():
    files = {"shift_step0.txt": step0(), "shift_probe.txt": probe()}
    for r in RATES:
        files[f"shift_{rtag(r)}_a.txt"] = stage_a(r)
        files[f"shift_{rtag(r)}_fit.txt"] = stage_fit(r)
    files["shift.cmd"] = launch_cmd()
    return files


def launch_cmd():
    J = "../../experiments/smt2020/jobs"

    def q(name, parallel=PARALLEL, done=True):
        return (f'"%PY%" run_queue.py {J}/{name}.txt --parallel {parallel}'
                + (f" --done-marker {J}/{name}.done" if done else ""))

    def rate_steps(r):
        t = rtag(r)
        return [q(f"shift_{t}_a", done=False), q(f"shift_{t}_a"),
                q(f"shift_{t}_fit", parallel=6),
                f'"%PY%" make_shift_jobs.py --stage-b {rname(r)}',
                q(f"shift_{t}_b", done=False), q(f"shift_{t}_b")]

    steps = ['"%PY%" make_shift_jobs.py --prelaunch',
             q("shift_step0", parallel=2),
             '"%PY%" make_shift_jobs.py --check-step0']
    for r in RATES:
        steps += rate_steps(r)
    steps += [q("shift_probe", parallel=4), '"%PY%" make_shift_jobs.py --gate-high'] + rate_steps(HIGH)
    steps += ['"%PY%" make_shift_jobs.py --check-step0']
    head = ["@echo off",
            "rem written by fabhybrid/smt2020/make_shift_jobs.py: PROTOCOL_shift.md",
            f'set "RL={RL}"',
            'set "PATH=%RL%;%RL%\\Library\\mingw-w64\\bin;%RL%\\Library\\usr\\bin;%RL%\\Library\\bin;'
            '%RL%\\Scripts;%RL%\\bin;%PATH%"',
            "set OMP_NUM_THREADS=1",
            "set PYTHONIOENCODING=utf-8",
            'cd /d "%~dp0..\\..\\..\\fabhybrid\\smt2020"',
            f'set "J={J}"',
            'set "PY=%RL%\\python.exe"']
    body = [f"{s} >> %J%/shift.out 2>&1 || exit /b 1" for s in steps]
    return "\r\n".join(head + body) + "\r\n"


def write_all():
    os.makedirs(JOBS, exist_ok=True)
    for name, text in build().items():
        with open(os.path.join(JOBS, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        n = sum(1 for l in text.splitlines() if l and not l.startswith("#") and "  ->  " in l)
        print(f"{name}: {n} jobs" if name.endswith(".txt") else f"{name}: launch chain")


def prelaunch():
    n = 0
    for top in ("fabhybrid", "external"):
        for d, sub, _ in os.walk(os.path.join(ROOT, top)):
            if "__pycache__" in sub:
                shutil.rmtree(os.path.join(d, "__pycache__"))
                sub.remove("__pycache__")
                n += 1
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} removed {n} __pycache__ directories", flush=True)
    bad = []
    for fab in FABS:
        for tag, _ in RULES:
            p = stale(fab, tag)
            got = hashlib.sha256(open(local(p), "rb").read()).hexdigest()[:16]
            if got != PINNED[p]:
                bad.append(f"{p}: sha256 {got}, PROTOCOL_confirm.md records {PINNED[p]}")
            if float(json.load(open(local(p)))["h0"]) != 1.0:
                bad.append(f"{p}: h0 is not the arm's level:1")
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "fabhybrid", "external"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        bad.append("fabhybrid/ or external/ not clean in git:\n" + dirty)
    for name, text in build().items():
        p = os.path.join(JOBS, name)
        if not os.path.exists(p):
            bad.append(f"jobs/{name} missing")
            continue
        with open(p, encoding="utf-8", newline="") as f:
            if f.read() != text:
                bad.append(f"jobs/{name} differs from what make_shift_jobs.py writes")
    if bad:
        print("\n".join(bad))
        sys.exit(1)
    print("prelaunch: PASS", flush=True)


def check_step0():
    a = local(out_of(rule_run("HVLM", "timeout:1", RATES[0], STEP0_SEED, f"{S}/step0/a")))
    b = local(out_of(rule_run("HVLM", "timeout:1", RATES[0], STEP0_SEED, f"{S}/step0/b")))
    blk = local(out_of(rule_run("HVLM", "timeout:1", RATES[0], STEP0_SEED, f"{S}/report")))
    pairs = [(a, b)] + ([(a, blk)] if os.path.exists(blk) else [])
    if not os.path.exists(blk):
        print(f"not yet run: {os.path.relpath(blk, ROOT)}")
    bad = []
    for p, q_ in pairs:
        if not (os.path.exists(p) and os.path.exists(q_)):
            bad.append(f"missing: {p if not os.path.exists(p) else q_}")
            continue
        x, y = strip(p), strip(q_)
        if x != y:
            keys = sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))
            bad.append(f"DIFFER: {os.path.basename(p)} vs {os.path.relpath(q_, ROOT)}; fields: {', '.join(keys)}")
        else:
            print(f"identical: {os.path.basename(p)}  ({os.path.relpath(q_, ROOT)})")
    if bad:
        print("\n".join(bad))
        sys.exit(1)
    with open(os.path.join(JOBS, "shift_step0.pass"), "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {len(pairs)} pairs identical (all fields but wall_s)\n")
    print(f"PASS: {len(pairs)} pairs")


def completed(path):
    return float(json.load(open(path))["scrap_kpi"]["completed_per_day"])


def stage_b(rate):
    """The refitted tables on seeds 64-95, and the retuned control limit if its threshold is not 1.5 h."""
    t = rtag(rate)
    skipped = os.path.exists(local(f"{S}/HIGH_SKIPPED.txt")) and abs(float(rate) - HIGH) < 1e-9
    lines, notes = [], []
    if not skipped:
        for fab in FABS:
            for tag, _ in RULES:
                p = local(refit(fab, tag, rate))
                if not os.path.exists(p):
                    print(f"missing refit: {os.path.relpath(p, ROOT)}")
                    sys.exit(1)
                if float(json.load(open(p))["h0"]) != 1.0:
                    print(f"{p}: h0 is not the arm's level:1")
                    sys.exit(1)
                lines += [table_run(fab, refit(fab, tag, rate), rate, s, f"{S}/report") for s in REPORT_SEEDS]
            means = []
            for th in THETAS:
                outs = [local(out_of(rule_run(fab, f"clock:{th}", rate, s, f"{S}/select"))) for s in SELECT_SEEDS]
                missing = [o for o in outs if not os.path.exists(o)]
                if missing:
                    print(f"missing selection runs: {os.path.relpath(missing[0], ROOT)} (+{len(missing) - 1})")
                    sys.exit(1)
                means.append(sum(completed(o) for o in outs) / len(outs))
            best = THETAS[max(range(len(THETAS)), key=lambda i: (means[i], -i))]
            notes.append({"fab": fab, "rate": rname(rate), "grid": dict(zip(THETAS, [round(m, 3) for m in means])),
                          "selected": best})
            if best != "1.5":
                lines += [rule_run(fab, f"clock:{best}", rate, s, f"{S}/report") for s in REPORT_SEEDS]
    sel = local(f"{S}/select/selection_{t}.json")
    os.makedirs(os.path.dirname(sel), exist_ok=True)
    with open(sel, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=1)
    text = job_file(f"stage B at rate {rname(rate)}: refitted tables and the retuned control limit on seeds 64-95"
                    + (" (rate skipped)" if skipped else ""), lines)
    with open(os.path.join(JOBS, f"shift_{t}_b.txt"), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"shift_{t}_b.txt: {len(lines)} jobs; " + "; ".join(f"{n['fab']} selected {n['selected']} h" for n in notes))


def gate_high():
    slopes = {}
    for fab in FABS:
        for s in (64, 65):
            p = local(out_of(rule_run(fab, "clock:1.5", HIGH, s, f"{S}/probe")))
            if not os.path.exists(p):
                print(f"missing probe run: {os.path.relpath(p, ROOT)}")
                sys.exit(1)
            d = json.load(open(p))
            slopes[f"{fab} s{s}"] = (float(d["wip_slope_back_half"]), int(d["wip_end"]))
    stable = all(abs(v[0]) < SLOPE_MAX for v in slopes.values())
    t = rtag(HIGH)
    if stable:
        files = {f"shift_{t}_a.txt": stage_a(HIGH), f"shift_{t}_fit.txt": stage_fit(HIGH)}
    else:
        files = {f"shift_{t}_a.txt": job_file(f"rate {rname(HIGH)} skipped: unstable", []),
                 f"shift_{t}_fit.txt": job_file(f"rate {rname(HIGH)} skipped: unstable", [])}
        with open(local(f"{S}/HIGH_SKIPPED.txt"), "w", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} rate {rname(HIGH)} skipped; back-half WIP slopes "
                    f"(lots/day) and WIP at day 360: {slopes}\n")
    for name, text in files.items():
        with open(os.path.join(JOBS, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
    print(f"probe slopes {slopes}; rate {rname(HIGH)} {'runs' if stable else 'skipped'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prelaunch", action="store_true")
    ap.add_argument("--check-step0", action="store_true")
    ap.add_argument("--stage-b", default=None)
    ap.add_argument("--gate-high", action="store_true")
    a = ap.parse_args()
    if a.prelaunch:
        prelaunch()
    elif a.check_step0:
        check_step0()
    elif a.stage_b is not None:
        stage_b(float(a.stage_b))
    elif a.gate_high:
        gate_high()
    else:
        write_all()


if __name__ == "__main__":
    main()
