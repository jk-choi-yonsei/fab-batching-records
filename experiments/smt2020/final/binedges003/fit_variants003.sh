#!/usr/bin/env bash
# PROTOCOL_binedges.md step 1 redone at the paper's price (beta 0.003) for all four sets of records
# (timeout <-> norev_p1, mbs3 <-> mbs3_p1, nach <-> nach_p1, learner <-> p1), both scenarios.
# Estimator exactly as betarx/family/{FAB}_{KIND}_b0p003_t1.json: --chain family --lam 0.003 --backoff
# --from-day 90 --fold fill; only --edges-tightest / --edges-nxt change. 4 fits at a time.
cd "$(dirname "$0")/../../../../fabhybrid/smt2020" || exit 1
export OMP_NUM_THREADS=1 PYTHONIOENCODING=utf-8
C=../../experiments/smt2020/final/collect
O=../../experiments/smt2020/final/binedges003
PY="${PY:-python}"
fitv() {
  fab=$1; kind=$2; id=$3; et=$4; en=$5
  case $kind in
    timeout) stem=norev_p1 ;; mbs3) stem=mbs3_p1 ;; nach) stem=nach_p1 ;; learner) stem=p1 ;;
  esac
  out=$O/${fab}_${kind}_b0p003_${id}.json
  [ -s "$out" ] && return 0
  args=""; [ "$et" != "-" ] && args="$args --edges-tightest $et"; [ "$en" != "-" ] && args="$args --edges-nxt $en"
  t0=$(date +%s.%N)
  "$PY" fit_q.py $C/${fab}_${stem}_s100.json $C/${fab}_${stem}_s101.json --chain family --lam 0.003 --backoff \
    --from-day 90 --fold fill $args --out "$out" > "${out%.json}.log" 2>&1
  t1=$(date +%s.%N)
  echo "${fab}_${kind}_${id} $(awk "BEGIN{printf \"%.1f\", $t1 - $t0}") s" >> $O/walltime.txt
}
export -f fitv; export C O PY
for fab in HVLM LVHM; do
for kind in timeout mbs3 nach learner; do
  cat <<EOF
$fab $kind ref - -
$fab $kind Rc 0.5,1,2,4 -
$fab $kind Rf 0.25,0.5,0.75,1,1.5,2,3,4 -
$fab $kind Rl 0.1875,0.375,0.75,1.5,3 -
$fab $kind Rh 0.375,0.75,1.5,3,6 -
$fab $kind Ac - 0.5,2
$fab $kind Af - 0.25,0.5,1,2,3,6
$fab $kind Al - 0.125,0.5,1.5
$fab $kind Ah - 0.5,2,6
EOF
done
done | xargs -P 4 -n 5 bash -c 'fitv "$0" "$1" "$2" "$3" "$4"'
echo fits done
