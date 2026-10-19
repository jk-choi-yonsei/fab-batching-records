"""Job files of experiments/smt2020/final/confirm/PROTOCOL_confirm.md: the confirmatory block on fresh
seeds 64-95.

  python make_confirm_jobs.py                # writes jobs/confirm_step0.txt, confirm_report.txt and
                                             # jobs/confirm.cmd, the launch chain
  python make_confirm_jobs.py --prelaunch    # first step of confirm.cmd: waits for jobs/binedges_search.done,
                                             # removes __pycache__ under fabhybrid/ and external/, then refuses
                                             # (exit 1) unless this file, the job files, confirm.cmd and the
                                             # artefacts are tracked and unmodified, fabhybrid/ and external/
                                             # are clean, every hash matches, and the job files on disk equal
                                             # what this script writes
  python make_confirm_jobs.py --check-step0  # bit identity of each step-0 pair, and of the block's own seed-64
                                             # learner runs against step 0 once they exist; appends to
                                             # jobs/confirm_step0.pass on success, exits 1 otherwise. It
                                             # compares files and prints no metric.

Before writing, every deployed artefact is checked against the SHA-256 the protocol records, the learner
against its family copy, every table's h0 against the arm level:1, and the tree under experiments/ for
any file name that already carries one of the seeds 64-95.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
EXP = os.path.join(ROOT, "experiments")
JOBS = os.path.join(EXP, "smt2020", "jobs")
F = "../../experiments/smt2020/final"
C, B = f"{F}/collect", f"{F}/betarx"
FAM = f"{B}/family"
RUNS = "../../experiments/smt2020/runs"
REPORT, STEP0 = f"{F}/confirm/report", f"{F}/confirm/step0"
CFG = "--scale 0.98 --days 360 --measure-from 0.241667"
FABS = ["HVLM", "LVHM"]
SEEDS = list(range(64, 96))
STEP0_SEED = 64
RULES = ["explore:0.02", "clock:1.5", "mbs:3", "timeout:1", "nach", "full"]
RECORDS = ("resid", "timeout", "mbs3", "nach")   # family tables fitted at the declared price besides the learner
PARALLEL = 14                               # as jobs/binedges.cmd
RL = os.path.dirname(os.path.abspath(sys.executable))  # the env of the interpreter running this; BC and PPO need its torch
JOBFILES = ("confirm_step0.txt", "confirm_report.txt", "confirm.cmd")

# first 16 hex digits of the SHA-256 recorded in PROTOCOL_confirm.md
PINNED = {
    f"{C}/HVLM_b0p003_t1rx.json": "856250f7843215b8", f"{C}/LVHM_b0p003_t1rx.json": "c16cef1c9840371c",
    f"{FAM}/HVLM_resid_b0p003_t1.json": "0f863cc59da686bd", f"{FAM}/LVHM_resid_b0p003_t1.json": "f2ca8be50172cfa5",
    f"{FAM}/HVLM_timeout_b0p003_t1.json": "62efe962e4110ab6", f"{FAM}/LVHM_timeout_b0p003_t1.json": "66025948e409f11e",
    f"{FAM}/HVLM_mbs3_b0p003_t1.json": "c59747a7e4d3bf6b", f"{FAM}/LVHM_mbs3_b0p003_t1.json": "421fbc63bd96b223",
    f"{FAM}/HVLM_nach_b0p003_t1.json": "20ab0a923e12b817", f"{FAM}/LVHM_nach_b0p003_t1.json": "13a1cecb30b1553c",
    f"{B}/HVLM_b0p0016_t1rx.json": "b666a7a797065f45",
    # BC and PPO retrained 2026-10-19 without the elapsed-time inputs (runs/batch_<fab>_qtcr2); the 2026-10-10 weights
    # (batch_<fab>_qtcr: 4f5bdf82ed67be40, 3527d4beb80c7c5c, 9a6e4a1dad87e7ce, 442da61888e2bdc0, 07abc5aa3f8ca0d2,
    # 96f34c5a7a389091) are evaluated in final/confirm/report_bcppo_2026-10-10
    f"{RUNS}/batch_HVLM_qtcr2/weights_bc.pt": "ad8cb9396859177b", f"{RUNS}/batch_LVHM_qtcr2/weights_bc.pt": "a83764b9676e5348",
    f"{RUNS}/batch_HVLM_qtcr2/weights_best.pt": "e8aa8850918423a1", f"{RUNS}/batch_LVHM_qtcr2/weights_best.pt": "8a848afdd31176ec",
    f"{RUNS}/batch_HVLM_qtcr2/norm.json": "ffa2b9b9f320a267", f"{RUNS}/batch_LVHM_qtcr2/norm.json": "f814f2965ca5bac7",
}


def learner(fab):
    return f"{C}/{fab}_b0p003_t1rx.json"


def family_copy(fab):
    return f"{FAM}/{fab}_learner_b0p003_t1.json"


def tables(fab):
    """The fitted tables of the block, all at beta 0.003, plus the HVLM records-price sensitivity row."""
    t = [learner(fab)] + [f"{FAM}/{fab}_{k}_b0p003_t1.json" for k in RECORDS]
    return t + ([f"{B}/HVLM_b0p0016_t1rx.json"] if fab == "HVLM" else [])


def table_run(fab, theta, seed, out):
    stem = os.path.basename(theta)[:-5]
    return (f"python batch_fire.py --dataset {fab} {CFG} --arm level:1 --theta {theta} --cqt-rule qtcr --scrap "
            f"--seed {seed} --out {out}  ->  {out}/batch_fire_{fab}_r0.98_d360_s{seed}_level1_{stem}_qtcr_scrap.json")


def rule_run(fab, arm, seed, out):
    return (f"python batch_fire.py --dataset {fab} {CFG} --arm {arm} --cqt-rule qtcr --scrap --seed {seed} --out {out}  ->  "
            f"{out}/batch_fire_{fab}_r0.98_d360_s{seed}_{arm.replace(':', '')}_qtcr_scrap.json")


def net_run(fab, kind, seed, out):
    w = {"bc": "weights_bc.pt", "ppo": "weights_best.pt"}[kind]
    return (f"python eval_batch.py --weights {RUNS}/batch_{fab}_qtcr2/{w} --norm {RUNS}/batch_{fab}_qtcr2/norm.json --dataset {fab} "
            f"{CFG} --cqt-rule qtcr --seed {seed} --tag {kind}{fab} --out {out}  ->  "
            f"{out}/batch_fire_{fab}_r0.98_d360_s{seed}_rl-{kind}{fab}_qtcr_scrap.json")


def local(p):
    return os.path.normpath(os.path.join(HERE, p))


def out_of(line):
    return line.split("  ->  ")[1]


def preflight():
    for p, h in PINNED.items():
        got = hashlib.sha256(open(local(p), "rb").read()).hexdigest()[:16]
        assert got == h, f"{p}: sha256 {got}, the protocol records {h}"
    for fab in FABS:
        a = open(local(learner(fab)), "rb").read()
        assert a == open(local(family_copy(fab)), "rb").read(), f"{fab}: learner != family copy"
        for t in tables(fab):
            assert float(json.load(open(local(t)))["h0"]) == 1.0, f"{t}: h0 is not the arm's level:1"
    own = os.path.join(EXP, "smt2020", "final", "confirm")
    pat = re.compile(r"_s(6[4-9]|[78][0-9]|9[0-5])[_.]")
    hits = [os.path.join(d, f) for d, _, fs in os.walk(EXP) if not d.startswith(own) for f in fs if pat.search(f)]
    assert not hits, f"seeds 64-95 already used: {hits[:5]}"


def job_file(header, lines):
    outs = [out_of(l) for l in lines]
    assert len(set(outs)) == len(outs), f"{header}: two jobs share an output path"
    return "# " + header + "\n\n" + "\n".join(lines) + "\n"


def launch_cmd():
    """jobs/confirm.cmd: the whole chain, each step only if the one before it succeeded. The block queue
    runs twice: run_queue relaunches only missing outputs, which is the protocol's single rerun."""
    J = "../../experiments/smt2020/jobs"
    q = lambda name, done=True: (f'"%PY%" run_queue.py {J}/{name}.txt --parallel {PARALLEL}'
                                 + (f" --done-marker {J}/{name}.done" if done else ""))
    steps = ['"%PY%" make_confirm_jobs.py --prelaunch',
             f'"%PY%" run_queue.py {J}/confirm_step0.txt --parallel 4 --done-marker {J}/confirm_step0.done',
             '"%PY%" make_confirm_jobs.py --check-step0',
             q("confirm_report", False), q("confirm_report"),
             '"%PY%" make_confirm_jobs.py --check-step0']
    head = ["@echo off",
            "rem written by fabhybrid/smt2020/make_confirm_jobs.py: PROTOCOL_confirm.md",
            f'set "RL={RL}"',
            'set "PATH=%RL%;%RL%\\Library\\mingw-w64\\bin;%RL%\\Library\\usr\\bin;%RL%\\Library\\bin;'
            '%RL%\\Scripts;%RL%\\bin;%PATH%"',
            "set OMP_NUM_THREADS=1",
            "set PYTHONIOENCODING=utf-8",
            'cd /d "%~dp0..\\..\\..\\fabhybrid\\smt2020"',      # this file's folder (jobs/) -> fabhybrid/smt2020
            f'set "J={J}"',
            'set "PY=%RL%\\python.exe"']
    body = [f"{s} >> %J%/confirm.out 2>&1 || exit /b 1" for s in steps]
    return "\r\n".join(head + body) + "\r\n"


def build():
    """{file name in jobs/: content}. Deterministic: the same call always gives the same bytes."""
    H = "final/confirm/PROTOCOL_confirm.md: "
    s0 = [table_run(fab, learner(fab), STEP0_SEED, f"{STEP0}/{c}") for c in ("a", "b") for fab in FABS]
    rep = []
    for s in SEEDS:
        for fab in FABS:
            rep += [table_run(fab, t, s, REPORT) for t in tables(fab)]
            rep += [rule_run(fab, arm, s, REPORT) for arm in RULES]
            rep += [net_run(fab, k, s, REPORT) for k in ("bc", "ppo")]
    assert (len(s0), len(rep)) == (4, 13 * 2 * 32 + 32) == (4, 864), (len(s0), len(rep))
    allouts = [out_of(l) for l in s0 + rep]
    assert len(set(allouts)) == len(allouts), "two jobs in different files share an output path"
    return {
        "confirm_step0.txt": job_file(H + "step 0, the learner on seed 64 twice; compare with "
                                      "make_confirm_jobs.py --check-step0", s0),
        "confirm_report.txt": job_file(H + "13 policies x 2 scenarios + the HVLM records-price table, seeds 64-95", rep),
        "confirm.cmd": launch_cmd(),
    }


def git(*args):
    r = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True)
    return r.returncode, r.stdout


def prelaunch():
    done = os.path.join(JOBS, "binedges_search.done")
    if not os.path.exists(done):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} waiting for {os.path.relpath(done, ROOT)}", flush=True)
        while not os.path.exists(done):
            time.sleep(60)
    n = 0
    for top in ("fabhybrid", "external"):
        for d, sub, _ in os.walk(os.path.join(ROOT, top)):
            if "__pycache__" in sub:
                shutil.rmtree(os.path.join(d, "__pycache__"))
                sub.remove("__pycache__")
                n += 1
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} removed {n} __pycache__ directories", flush=True)
    bad = []
    try:
        preflight()
    except AssertionError as e:
        bad.append(f"preflight: {e}")
    for name, text in build().items():
        with open(os.path.join(JOBS, name), encoding="utf-8", newline="") as f:
            if f.read() != text:
                bad.append(f"jobs/{name} differs from what make_confirm_jobs.py writes")
    if bad:
        print("\n".join(bad))
        sys.exit(1)
    print("prelaunch: PASS")


def strip(p):
    """Every top-level field but wall_s, each as canonical JSON text (so NaN equals NaN)."""
    j = json.load(open(p))
    j.pop("wall_s", None)
    return {k: json.dumps(v, sort_keys=True) for k, v in j.items()}


def check_step0():
    def out(fab, d):
        return local(out_of(table_run(fab, learner(fab), STEP0_SEED, d)))

    pairs = []
    for fab in FABS:
        pairs.append((out(fab, f"{STEP0}/a"), out(fab, f"{STEP0}/b")))
        blk = out(fab, REPORT)                  # the block's own seed-64 learner run, once it exists
        if os.path.exists(blk):
            pairs.append((out(fab, f"{STEP0}/a"), blk))
        else:
            print(f"not yet run: {os.path.relpath(blk, ROOT)}")
    bad = []
    for p, q in pairs:
        if not (os.path.exists(p) and os.path.exists(q)):
            bad.append(f"missing: {p if not os.path.exists(p) else q}")
            continue
        a, b = strip(p), strip(q)
        if a != b:
            keys = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            bad.append(f"DIFFER: {os.path.basename(p)} vs {os.path.relpath(q, ROOT)}; fields: {', '.join(keys)}")
        else:
            print(f"identical: {os.path.basename(p)}  ({os.path.relpath(q, ROOT)})")
    if bad:
        print("\n".join(bad))
        sys.exit(1)
    with open(os.path.join(JOBS, "confirm_step0.pass"), "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {len(pairs)} pairs identical (all fields but wall_s)\n")
    print(f"PASS: {len(pairs)} pairs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-step0", action="store_true")
    ap.add_argument("--prelaunch", action="store_true")
    a = ap.parse_args()
    if a.check_step0:
        check_step0()
        return
    if a.prelaunch:
        prelaunch()
        return
    preflight()
    files = build()
    for name, text in files.items():
        with open(os.path.join(JOBS, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
    for name in JOBFILES[:2]:
        print(f"{name}: {sum(1 for l in files[name].splitlines() if '  ->  ' in l)}")
    print("launch (after the artefacts, this script, the job files and confirm.cmd are committed):  jobs\\confirm.cmd")


if __name__ == "__main__":
    main()
