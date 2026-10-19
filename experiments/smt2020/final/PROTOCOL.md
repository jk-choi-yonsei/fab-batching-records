# The final block: what is fixed before the report seeds are touched

Written 2026-09-21, while stage A (selection) was running and before any report-seed
run of this block existed. Nothing below may be changed after the first report-seed
result is read; a change after that point is a new block with a new file.

## Measurement

- Benchmark: SMT2020 on PySCFabSim at the pinned commit, unmodified; scenarios HVLM
  and LVHM; release scale 0.98; queue-time dispatching rule `qtcr` stacked on the
  critical-ratio dispatcher; a lot that violates a queue-time constraint is scrapped.
- Horizon 360 days. Completions are counted over days 87-360 (273 days).
- Metric: completed lots per day. Secondary: scrapped lots per day, realised fill,
  under-full loads started.
- Seeds. Logging 100-105. Selection (search) 108-115. Report 0-31. The three sets are
  disjoint, and the report seeds are read only in stage B.

## Arms and their selection grids

Every parameterised arm takes its parameter from the search seeds by ONE rule: the
value with the highest mean completions per day over seeds 108-115. One value per
scenario. The grid size is reported next to each arm.

| arm | what it is | grid | size |
|---|---|---|---|
| `full` | the simulator's default: no load below capacity is started | none | 1 |
| `mbs:k` | minimum batch size | k in {2, 3, 4} | 3 |
| `mbsmin` | minimum batch size at each step's own BATCHMN | none | 1 |
| `nach` | next-arrival look-ahead (Fowler, Phillips & Hogg 1992) | none | 1 |
| `timeout:T` | start once the oldest lot has waited T hours | T in {0.5, 1, 2, 3} | 4 |
| `clock:h` | start when the tightest residual is under h hours | h in {0.5, 0.75, 1, 1.5, 2, 3} | 6 |
| learner | the fitted table, below | beta in {0.001, 0.003, 0.01, 0.02, 0.04} | 5 |
| BC, PPO | learned schedulers, frozen weights from 2026-09 | none | 1 each |

`mbs:k` and `mbsmin` form one family; the family's representative is its best member
on the search seeds. The headline comparison is the learner against that
representative. `full` is a reference row and is never the yardstick.

## The learner

One pipeline per beta, identical on both scenarios (`make_collect_jobs.py`):

1. Period 1: the load-building rule (`full`), firing an under-full load that has a
   live clock with probability 0.02. Seeds 100, 101.
2. Table 1: `fit_q.py` on period 1.
3. Period 2: table 1, a wait reversed with probability 0.02 and a fire with 0.30.
   Seeds 102, 103.
4. Table 2: `fit_q.py` on periods 1-2.
5. Period 3: table 2, same reversal probabilities. Seeds 104, 105.
6. Table 3: `fit_q.py` on periods 1-3. This is the table that is evaluated.

A period is a 91-day window (days 90-181) of a 181-day run under that period's
logging policy. Estimator constants, none of them selected: family chains; discount
0.9 per hour; n0 = 10; cell edges 0.25/0.5/1/2/4 h, 0.25/1/3 h, 0.3/0.55; holding
term off; `--backoff` on (an entry is the cell's own decision only where both actions
were observed at least n0 times there; elsewhere it is the residual-only table's).

## Stage B (report seeds 0-31)

Arms: `full`; the minimum-batch representative; `nach`; `timeout` at its selected T;
`clock` at its selected h; BC; PPO; the learner at its selected beta.

Ablations of the learner at the selected beta, which are not selected and are
reported as ablations: the tables restricted to (residual), (residual, arrival),
(residual, fill); tables 1 and 2 of the same pipeline (the data budget); and the
logging policy of period 1 as a row of its own (what the fab produces while it logs).

Tests, all reported whatever they show: exact two-sided sign test with ties dropped,
paired t, and the 95% interval of the paired difference. Primary: learner against the
minimum-batch representative. Secondary: learner against every other arm.

## What is deliberately absent

The two-index hand rule of 2026-09-18: its structure was read off the learner's own
ablation, so it cannot be a comparator for the learner. `select:h`: it keeps
`clock:h`'s trigger and changes which load is started, a different decision; it is a
scope statement, not an arm.
