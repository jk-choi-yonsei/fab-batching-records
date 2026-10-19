# A table fitted from the records of a deterministic incumbent

Written 2026-09-26, before any run below. Nothing here may change after the first run.

## Why

A fab's existing arbitration is a deterministic rule. Its records either never show the
other action in a state (the full-batch rule never starts an under-full load; the
control limit's trigger is a cell axis, so the action is a function of the cell) or show
it for reasons outside the state (the timeout rule starts a load when the oldest lot has
waited T, which the cell does not record). This block fits the learner to the records of
the timeout rule, the incumbent among the compared rules whose records contain both
actions within cells, and compares it with the table fitted from one period of the
randomised logging policy.

## Pipeline

- Logging: `readout.py --arm timeout:1` (T = 1 h, the timeout selected on the selection
  seeds on both scenarios), seeds 100 and 101, 181 days with the window from day 90,
  `--slim --dump-lots`: the period-1 design with the logging policy replaced.
- Fit: `fit_q.py` on the two dumps, `--chain family --lam 0.003 --backoff --from-day 90`,
  the estimator of table 1 of the final block unchanged.
- Report: seeds 0-31, both scenarios, 64 runs, the final block's configuration.

## Reported

Paired over report seeds 0-31: the timeout-fitted table minus the table fitted from one
randomised period (`*_b0p003_t1`, already on the report seeds): completions per day
(mean, 95% t interval, exact sign test) and under-full loads per day; also the timeout
rule itself (already on the report seeds) for reference. Reported whatever it shows; no
decision depends on it.
