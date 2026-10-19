#!/usr/bin/env bash
# One-period 24-cell tables (period-1 records: full-batch rule with 2% starts, seeds 100-101)
# refitted over a price grid, to see over which prices the table is constant and where the
# records' own price estimates fall (final/betahat/beta_*.json). Fitting only; no simulation.
# Same estimator as t1rx in make_rx_jobs.py: --chain family --backoff --from-day 90 --fold fill.
cd "$(dirname "$0")/../../../../fabhybrid/smt2020" || exit 1
export OMP_NUM_THREADS=1 PYTHONIOENCODING=utf-8
C=../../experiments/smt2020/final/collect
O=../../experiments/smt2020/final/betarx
fitone() {
  fab=$1; b=$2; tag=b$(echo "$b" | sed 's/\./p/')
  out=$O/${fab}_${tag}_t1rx.json
  [ -s "$out" ] && return 0
  python fit_q.py $C/${fab}_p1_s100.json $C/${fab}_p1_s101.json --chain family --lam "$b" \
    --backoff --from-day 90 --fold fill --out "$out" > "$O/${fab}_${tag}_t1rx.log" 2>&1
}
export -f fitone; export C O
for fab in HVLM LVHM; do
  for b in 0.0005 0.001 0.0013 0.0016 0.002 0.0022 0.0025 0.0028 0.003 0.004 0.005 0.0062 0.0075 0.01 0.015 0.02; do
    echo "$fab $b"
  done
done | xargs -P 6 -n 2 bash -c 'fitone "$0" "$1"'
echo done
