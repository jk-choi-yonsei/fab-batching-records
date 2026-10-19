#!/bin/bash
# 2026-10-19: BC and PPO retrained without the two elapsed-time inputs (train_l1.global_vec), into
# runs/batch_<fab>_qtcr2, from the 2026-10-10 snapshots; then evaluated on the confirmatory seeds 64-95 as rows 12-13
# of PROTOCOL_confirm.md (the 2026-10-10 evaluations move to final/confirm/report_bcppo_2026-10-10), and the results
# file, Table 3 and the paper rebuilt. Run from anywhere; logs under experiments/smt2020/runs and final/confirm.
set -u
export PATH="/c/Users/jkchoi/miniconda3/envs/RL:/c/Users/jkchoi/miniconda3/envs/RL/Scripts:$PATH"
export OMP_NUM_THREADS=1 PYTHONIOENCODING=utf-8
cd "$(dirname "$0")/../../../fabhybrid/smt2020" || exit 1
EXP=../../experiments/smt2020
LOG=$EXP/final/confirm/retrain_qtcr2.log
say() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }

say "training HVLM and LVHM in parallel"
python -B run_training.py --dataset HVLM --cqt-rule qtcr --suffix _qtcr --runs-suffix _qtcr2 --no-eval > $EXP/runs/train_HVLM_qtcr2.out 2>&1 &
python -B run_training.py --dataset LVHM --cqt-rule qtcr --suffix _qtcr --runs-suffix _qtcr2 --no-eval > $EXP/runs/train_LVHM_qtcr2.out 2>&1 &
wait
for fab in HVLM LVHM; do
  if [ ! -f $EXP/runs/batch_${fab}_qtcr2/pipeline.done ]; then say "training of $fab did not finish; see runs/train_${fab}_qtcr2.out"; exit 1; fi
done
say "training done"

OLD=$EXP/final/confirm/report_bcppo_2026-10-10
mkdir -p "$OLD"
n=$(ls $EXP/final/confirm/report/batch_fire_*_rl-*_qtcr_scrap.json 2>/dev/null | wc -l)
if [ "$n" -gt 0 ]; then
  mv $EXP/final/confirm/report/batch_fire_*_rl-*_qtcr_scrap.json* "$OLD"/
  say "moved $n evaluations of the 2026-10-10 weights to $OLD"
fi
JOB=$EXP/jobs/confirm_bcppo_qtcr2.txt
{
  echo "# 2026-10-19: BC and PPO retrained without the elapsed-time inputs (runs/batch_<fab>_qtcr2), evaluated on the confirmatory seeds 64-95 as rows 12-13 of PROTOCOL_confirm.md; the 2026-10-10 evaluations are in final/confirm/report_bcppo_2026-10-10"
  grep -v '^#' $EXP/jobs/confirm_bcppo_qtcr.txt | sed 's#/batch_\(HVLM\|LVHM\)_qtcr/#/batch_\1_qtcr2/#g'
} > "$JOB"
say "evaluating: $(grep -c eval_batch "$JOB") runs, 14 at a time"
python -B run_queue.py "$JOB" --parallel 14 >> "$LOG" 2>&1 || { say "run_queue failed"; exit 1; }
say "evaluation done; results file, Table 3, paper"
python -B confirm_report.py >> "$LOG" 2>&1 || { say "confirm_report failed"; exit 1; }
python -B confirm_tables.py >> "$LOG" 2>&1 || { say "confirm_tables failed"; exit 1; }
python -B figures/fig_diffs.py >> "$LOG" 2>&1
( cd ../../paper && latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex > /dev/null 2>&1 && cp build/main.pdf main.pdf ) && say "paper rebuilt" || say "paper build failed"
say "all done"
