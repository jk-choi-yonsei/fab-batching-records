# Tables fitted from the records of the fab's own rules

Written 2026-09-29, before any run of the minimum-batch or NACH records below. Nothing here
may change after the first of those runs.

## Why

The learner fits the arbitration from records of the decision. The fit compares the two
actions within each cell of (tightest residual, time to the next arrival), so the records
must hold both actions within a cell. A rule that never starts an under-full load (the
full-batch rule) or that decides from a statistic of the table's state (the control limit,
from the residual) leaves one action per cell. A rule that decides from something outside
the state leaves both: the timeout rule from the oldest lot's wait, the minimum-batch-size
rule from the number of lots in the load, NACH from the load and the next arrival's
processing need. Their records are confounded by that trigger, since it is not in the cell.

The timeout rule's records were fitted on 2026-09-27 (final/norev, refitted with the
24-cell state at the selected prices; jobs/rx_sel_fits.txt). This block adds the two other
rules of Table I that start under-full loads for a reason outside the state.

## Records

One logging period each, the design of period 1 with the logging policy replaced by the
rule itself and no reversals: seeds 100 and 101, 181 days, records from day 90,
`readout.py --arm <rule> --dataset <fab> --days 181 --seed <s> --dump-from 90 --slim --dump-lots`.

| rule | arm | as selected on the selection seeds |
|---|---|---|
| timeout | `timeout:1` | T = 1 h, both scenarios (records exist: collect/{fab}_norev_p1_s10x.json) |
| minimum batch size | `mbs:3` | q = 3, both scenarios |
| NACH | `nach` | no parameter |

## Fit

`fit_q.py <the two dumps> --chain family --lam <beta> --backoff --from-day 90 --fold fill`,
the estimator of the learner unchanged, at the price selected for the learner on the
selection seeds (final/rx/selection_rx.json): beta = 0.02 on HVLM, 0.01 on LVHM.
Outputs `collect/{fab}_mbs3_{b}_t1rx.json` and `collect/{fab}_nach_{b}_t1rx.json`.

## Report

Report seeds 0-31, both scenarios, the final block's configuration (`--scale 0.98 --days
360 --measure-from 0.241667 --cqt-rule qtcr --scrap`): 2 rules x 2 scenarios x 32 = 128 runs.

For each of the three rules, paired over the report seeds, completions per day and
under-full loads started per day (mean, 95% t interval, exact two-sided sign test with ties
dropped):
- the table fitted from the rule's records minus the rule itself;
- the table fitted from the rule's records minus the table fitted from one period of the
  randomised records at the same price (`{fab}_{b}_t1rx`).

Also, from the fitted artefacts: the number of the 24 free cells in which both actions were
recorded at least n0 = 10 times, and their share of the free decisions.

Reported whatever it shows; no decision depends on it.
