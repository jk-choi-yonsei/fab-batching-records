# PROTOCOL_shift — the release rate moved: stale thresholds, refitted tables, and the simulator's retuning

Written 2026-10-14, before any run of this block.

## Why

The introduction states the limit of the existing methods as a structure: the thresholds of a rule, or
the policy of a learned dispatcher, come from a simulation model of the line, and the study has to be
repeated when the conditions change. This block puts the same change to the method. The release rate of
the testbed is moved from 0.98 of the nominal rate, at which every table and every parameter of the paper
was fitted or selected, to 0.90 and to 0.80 (and, if the line stays stable there, to 1.05). At each rate
the block measures

1. the rules as tuned at 0.98 (timeout T = 1 h, minimum batch size q = 3, NACH) and the control limit at
   the threshold tuned at 0.98 (h = 1.5 h);
2. the tables fitted from the rules' records at 0.98 (the paper's Table 4 tables), deployed unchanged;
3. the tables refitted from the rules' records made at the new rate, under the same rules with the same
   parameters, the records taken as they stand, with every setting of the learner unchanged;
4. the control limit retuned at the new rate by the selection procedure of the paper (the simulation
   study repeated: 7 thresholds on the 8 selection seeds).

The paper's claim is that the records replace the simulation study. The block tests it where the
simulation study would be repeated.

## Fixed before this block

- The learner: `fit_q.py --chain family --lam 0.003 --backoff --from-day 90 --fold fill`, 24 cells,
  n0 = 10, gamma 0.9 per hour, edges 0.25/0.5/1/2/4 h of the residual and 0.25/1/3 h of the arrival.
  beta = 0.003 at every rate: a declared parameter, not selected.
- The rules' parameters and the control limit's threshold as selected at 0.98 (`final/selection.json`):
  T = 1 h, q = 3, h = 1.5 h. They are not retuned at the new rates, since a fab that runs a rule keeps
  running it; only the control limit is retuned, because it is the simulator-tuned comparator of the paper.
- The stale tables: `betarx/family/{fab}_{timeout,mbs3,nach}_b0p003_t1.json` at the SHA-256 recorded in
  PROTOCOL_confirm.md.
- Rates: 0.90 and 0.80 are run in that order. 1.05 is run only if a probe (the control limit h = 1.5 h,
  seeds 64 and 65, both scenarios, 360 days) shows a back-half WIP slope below 1.0 lots per day in all
  four runs; otherwise the high rate is recorded as unstable and skipped. The rate is applied as in every
  run of the paper (`scenarios.scale_release` below 1, `compress_release` above 1): the inter-arrival gaps
  are stretched or shrunk and nothing else changes.
- Seeds: records 100 and 101 (181 days, records from day 90, as in PROTOCOL_incumbent.md); selection
  108-115; report 64-95. Every policy is paired by seed (CRN) as in PROTOCOL_confirm.md.
- Configuration of every report and selection run: `--days 360 --measure-from 0.241667 --cqt-rule qtcr
  --scrap` at the block's `--scale`. Completions, scraps and under-full loads are counted over days 87-360.
- Step 0: the timeout rule at 0.90 on HVLM seed 64, run twice; the block starts only if the two files are
  identical in every field but wall_s. The block's own seed-64 run is compared with them at the end.

## Runs

Per rate and scenario: records 3 rules x 2 seeds (181 days); report seeds 64-95: 3 rules + the control
limit at 1.5 h + 3 stale tables + 3 refitted tables + the retuned control limit (only if its threshold is
not 1.5 h) = 10 or 11 x 32; selection: 7 thresholds {0.5, 0.75, 1, 1.5, 2, 3, 4} h x 8 seeds. The retuned
threshold is the one with the highest mean completions per day over the 8 seeds, ties to the first in grid
order, as in PROTOCOL.md. Outputs under `final/shift/{records,tables,report,select,probe,step0}`. Job
files `jobs/shift_*.txt`, written by `fabhybrid/smt2020/make_shift_jobs.py`; the chain `jobs/shift.cmd`,
launched detached (WMI) so that it survives the session.

## Readings (declared before the runs; reported whatever they show)

Per scenario and rate, paired over seeds 64-95, completions per day with the 95% t interval and the number
of seeds on which the difference is positive:

- R1. Stale table minus its rule, for each of the three rules. Prediction: positive on most seeds at 0.90
  and 0.80, since the rule's parameter is as stale as the table, but by less than at 0.98.
- R2. Refitted table minus its rule. Prediction: positive on every seed, by at least the 0.98 margin.
- R3. Refitted table minus the stale table. Prediction: positive where R1 fell short of the 0.98 margin.
- R4. Refitted table minus the control limit at 1.5 h, and minus the retuned control limit. Prediction: the
  timeout and minimum-batch-size tables at least as good as the retuned control limit, as at 0.98.
- R5. The retuned threshold against 1.5 h, with the selection means. Prediction: at the lower rates the
  threshold rises (an under-full run costs less capacity, and a load takes longer to fill), and the
  refitted tables start earlier in the same way; the direction of the change is read off the tables'
  entries.
- R6. The refitted tables' form: control limits on the residual whose thresholds do not fall with the time
  to the next arrival, and the number of entries that differ from the 0.98 tables.
- Cells with both actions at least n0 times in the new records, per rule.

The block adds or removes no table, parameter, bin edge or policy of the paper. What it decides is one
paragraph of Section 5 (and a row group of a table) on what happens when the conditions change.
