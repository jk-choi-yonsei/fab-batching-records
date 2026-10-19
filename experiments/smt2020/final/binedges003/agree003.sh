#!/usr/bin/env bash
# TASK A1 step 3: table_agree.py per FAB x KIND, ref = the ref fit of this directory, tables = the 8 variants,
# dumps = that KIND's two record files, days >= 90.
cd "$(dirname "$0")/../../../../fabhybrid/smt2020" || exit 1
export OMP_NUM_THREADS=1 PYTHONIOENCODING=utf-8
C=../../experiments/smt2020/final/collect
O=../../experiments/smt2020/final/binedges003
PY="${PY:-python}"
for fab in HVLM LVHM; do
for kind in timeout mbs3 nach learner; do
  case $kind in
    timeout) stem=norev_p1 ;; mbs3) stem=mbs3_p1 ;; nach) stem=nach_p1 ;; learner) stem=p1 ;;
  esac
  echo "== $fab $kind ($stem)"
  "$PY" table_agree.py --ref $O/${fab}_${kind}_b0p003_ref.json \
    --tables $O/${fab}_${kind}_b0p003_Rc.json $O/${fab}_${kind}_b0p003_Rf.json $O/${fab}_${kind}_b0p003_Rl.json $O/${fab}_${kind}_b0p003_Rh.json \
             $O/${fab}_${kind}_b0p003_Ac.json $O/${fab}_${kind}_b0p003_Af.json $O/${fab}_${kind}_b0p003_Al.json $O/${fab}_${kind}_b0p003_Ah.json \
    --dumps $C/${fab}_${stem}_s100.json $C/${fab}_${stem}_s101.json --from-day 90 --out $O/agree_${fab}_${kind}.json
done
done
echo agree done
