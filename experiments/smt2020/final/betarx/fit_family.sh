#!/usr/bin/env bash
# Every table the confirmatory block would need, fitted at beta 0.003 and 0.01 from one logging
# period, to see whether the choice inside [0.003, 0.01] changes any of them. Fitting only.
#   learner      : period-1 records (full-batch rule, 2% starts), --fold fill          (24 cells)
#   resid        : same records, --fold nxt,fill                                       (6 cells)
#   full72       : same records, no fold                                               (72 cells)
#   timeout/mbs3/nach : that rule's own period-1 records, --fold fill                  (24 cells)
cd "$(dirname "$0")/../../../../fabhybrid/smt2020" || exit 1
export OMP_NUM_THREADS=1 PYTHONIOENCODING=utf-8
C=../../experiments/smt2020/final/collect
O=../../experiments/smt2020/final/betarx/family
mkdir -p $O
fitf() {
  fab=$1; b=$2; kind=$3
  tag=b$(echo "$b" | sed 's/\./p/')
  case $kind in
    learner) src="${fab}_p1";       fold="--fold fill" ;;
    resid)   src="${fab}_p1";       fold="--fold nxt,fill" ;;
    full72)  src="${fab}_p1";       fold="" ;;
    timeout) src="${fab}_norev_p1"; fold="--fold fill" ;;
    mbs3)    src="${fab}_mbs3_p1";  fold="--fold fill" ;;
    nach)    src="${fab}_nach_p1";  fold="--fold fill" ;;
  esac
  out=$O/${fab}_${kind}_${tag}_t1.json
  [ -s "$out" ] && return 0
  python fit_q.py $C/${src}_s100.json $C/${src}_s101.json --chain family --lam "$b" --backoff --from-day 90 \
    $fold --out "$out" > "${out%.json}.log" 2>&1
}
export -f fitf; export C O
for fab in HVLM LVHM; do for b in 0.003 0.01; do for k in learner resid full72 timeout mbs3 nach; do
  echo "$fab $b $k"; done; done; done | xargs -P 8 -n 3 bash -c 'fitf "$0" "$1" "$2"'
python - <<'PY'
import json, glob, os
import numpy as np
O = "../../experiments/smt2020/final/betarx/family"
for fab in ("HVLM", "LVHM"):
    for k in ("learner", "resid", "full72", "timeout", "mbs3", "nach"):
        a = np.asarray(json.load(open(f"{O}/{fab}_{k}_b0p003_t1.json"))["fire"])
        b = np.asarray(json.load(open(f"{O}/{fab}_{k}_b0p01_t1.json"))["fire"])
        print(f"{fab} {k:8s} cells {a.size:3d}  differ between 0.003 and 0.01: {int((a != b).sum())}")
PY
