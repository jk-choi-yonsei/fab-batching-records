# PROTOCOL_confirm — the confirmatory block on fresh seeds 64-95

Written 2026-10-02, before any run of this block (step 0 included) and while the selection runs of
PROTOCOL_binedges.md step 2 were still running.

## Why

The learner's state (24 cells: tightest residual x time to the next arrival) and its price were fixed
after the report seeds 0-31 had been read many times (the rx pipeline, the price grid). The numbers in the
manuscript's Tables I-III are therefore development numbers. This block measures the same policies on 32
seeds that no result of this project has used.

- The paper's Tables I-III are reported on these seeds.
- The report seeds 0-31 stay as the development record (appendix).
- No result here changes any table, price, bin edge, rule parameter, estimator constant or policy. The
  block decides only what the paper says, by the readings declared below.
- Tables I-III carry the rows listed under "Tables on these seeds" whatever the block shows. No row is
  added, dropped or swapped after the block is read.

## Fixed before this block

- **The learner.** The table fitted from one logging period of the testbed default's records: the
  full-batch rule, which starts an under-full load holding a live clock at 2% of the free decisions
  (`explore:0.02`), seeds 100-101, days 90-181, `collect/{fab}_p1_s10{0,1}.json`. Fit: `fit_q.py` at
  `--lam 0.003`, the exact command being the `learner` line of `betarx/fit_family.sh` (24 cells; n0 = 10;
  gamma 0.9 per hour; edges 0.25/0.5/1/2/4 h of the residual and 0.25/1/3 h of the arrival). Fixed on
  2026-10-02.
- **The price.** beta = 0.003 lots per empty slot-hour on both scenarios. It is a declared management
  parameter and is not selected by simulation.
  - 0.003 lies inside the 95% interval of the records' own price estimate on LVHM (0.0021
    [-0.0009, 0.0051]) and just above it on HVLM (0.0016 [0.0001, 0.0028])
    (`betahat/beta_{fab}_p23_adj_head.json`). The learner's table is the same for every price on the grid
    from 0.0028 (HVLM) and 0.0022 (LVHM) up to 0.01, so on HVLM the table at 0.003 is the table at the
    interval's upper end (`betarx/grid_summary.json`; the next grid value, 0.015, changes one cell on each).
  - Every fitted table of this block is fitted at 0.003. Unlike the learner, the other tables change
    between 0.003 and 0.01 (cells that differ, HVLM/LVHM: residual only 1/1, timeout records 2/2,
    minimum-batch records 3/1, NACH records 7/0).
  - Under PROTOCOL_rx.md the selection seeds chose 0.02 on HVLM and 0.01 on LVHM among three-period
    tables (`rx/selection_rx.json`); the three-period 0.01 table takes the learner's decision in every
    cell on both scenarios. On HVLM it completed 36.55 lots a day on the 8 selection seeds against the
    control limit's 36.67; on report seeds 0-31 it led the control limit by +0.43. No run on seeds 64-95
    informs the value.
- **The rules' parameters.** Selected on the selection seeds 108-115 under PROTOCOL.md
  (`selection.json`): q = 3, T = 1 h, h = 1.5 h, the same on both scenarios.
- **BC and PPO.** The frozen weights of 2026-09 (`runs/batch_{fab}/weights_bc.pt`, `weights_best.pt`,
  `norm.json`), evaluated greedily by `eval_batch.py` as in Table I.

## Seeds

- Seeds 64-95 (32 seeds) on both scenarios.
- **Checked on 2026-10-02.** No file under `experiments/`, `archive/` or `~/fab_runs` has a seed from
  64-95 in its name (`_s64_` ... `_s95_`, or `seed64` and the like). No job line under `experiments/`,
  other than this block's own `jobs/confirm_step0.txt` and `jobs/confirm_report.txt`, passes `--seed 64`
  ... `--seed 99`. Under `experiments/` and `archive/` the only files with seeds 96-99
  are nine `archive/` smokes of the July operating-point harness. Seeds 32-63 are not used because 96
  LVHM 180-day runs of 2026-09-13 already used them.
- **Pairing by seed (CRN).** The release schedule is the dataset's fixed order schedule with every gap
  stretched by 1/0.98 (`scenarios.scale_release`), the same for every seed and policy. The seed sets the
  simulator's single shared random stream (`Randomizer`, reseeded in `rl_env.new_instance`), from which
  breakdowns, PMs, processing times, sampling, rework and tie-breaks are drawn in event order. Every policy
  on a seed starts from the same state and stream; once two policies take one decision differently they
  draw from it at different points, and their realisations differ from then on. Draws that belong to one
  policy come from that policy's own stream, which nothing else reads:
  - the logging policy's starts: `seed*7919 + 17`;
  - a table's exploration: `+ 29` (off here).

  BC and PPO act by argmax. The seed is the unit of replication: the 32 paired differences are independent
  and the paired tests are valid, but pairing removes little variance. Over all pairs of distinct policies
  with 32 seeds in `final/report/` (817 HVLM, 814 LVHM) the paired SD of completions per day is 0.52-0.74
  (HVLM) and 0.59-0.82 (LVHM) (10th-90th percentile), with between-policy correlations near zero. n = 32
  is judged on that SD.

## Configuration (every run)

`--scale 0.98 --days 360 --measure-from 0.241667 --cqt-rule qtcr --scrap`, as in every report run: SMT2020
on PySCFabSim at the pinned commit 77103ed, unmodified. A lot that breaks a queue-time constraint is
scrapped. Completions, scraps and under-full loads are counted over days 87-360 (273 days).

Every run is one random realisation of the fab. Tools break down at random, and processing times,
sampling and rework are random, so lots reach the furnaces at times that differ from seed to seed although
releases follow a fixed schedule. Every claim below is a statement over these 32 realisations.

## Policies (both scenarios, seeds 64-95)

| # | policy | role | how it is run | artefact (SHA-256, first 16 hex) |
|---|---|---|---|---|
| 1 | learner | the method | `--arm level:1 --theta collect/{fab}_b0p003_t1rx.json` | HVLM 856250f7843215b8, LVHM c16cef1c9840371c |
| 2 | residual-only table (6 cells) | ablation of the state (same records and estimator, the residual only); not a comparator | `... betarx/family/{fab}_resid_b0p003_t1.json` | 0f863cc59da686bd, f2ca8be50172cfa5 |
| 3 | timeout-records table | the learner's estimator on the timeout rule's own period-1 records (C3); not a comparator | `... betarx/family/{fab}_timeout_b0p003_t1.json` | 62efe962e4110ab6, 66025948e409f11e |
| 4 | minimum-batch-records table | the same on the minimum-batch rule's records (C3); not a comparator | `... betarx/family/{fab}_mbs3_b0p003_t1.json` | c59747a7e4d3bf6b, 421fbc63bd96b223 |
| 5 | NACH-records table | the same on NACH's records (C3); not a comparator | `... betarx/family/{fab}_nach_b0p003_t1.json` | 20ab0a923e12b817, 13a1cecb30b1553c |
| 6 | logging policy (full-batch, 2% starts) | the logging design: what the fab completes while it logs; not a comparator | `--arm explore:0.02` | — |
| 7 | control limit h = 1.5 h | simulator-tuned reference: h chosen from 6 levels on the 8 selection seeds, 48 full-fab 360-day runs per scenario | `--arm clock:1.5` | — |
| 8 | minimum batch size q = 3 | literature rule; q chosen from {2, 3, 4, step minimum} on the selection seeds, 32 runs per scenario | `--arm mbs:3` | — |
| 9 | timeout T = 1 h | literature rule; T chosen from {0.5, 1, 2, 3} h on the selection seeds, 32 runs per scenario | `--arm timeout:1` | — |
| 10 | NACH | literature rule (Fowler, Phillips and Hogg 1992), no parameter | `--arm nach` | — |
| 11 | full-batch rule (simulator default) | the simulator's default; reference row, never the yardstick | `--arm full` | — |
| 12 | BC | the authors' simulator-trained scheduler (behaviour cloning of the control limit at h = 2 h); reference row, no claim | `eval_batch.py --weights runs/batch_{fab}/weights_bc.pt --tag bc{fab}` | ac3a4ca63d41fbe8, fa352602ee04f5ca |
| 13 | PPO | BC trained further by PPO in the simulator; reference row, no claim | `eval_batch.py --weights runs/batch_{fab}/weights_best.pt --tag ppo{fab}` | 7699d27d4d80d86e, 4e6c2ad2146081e8 |
| 14 | HVLM only: the one-period table at the records' price estimate, beta 0.0016 | sensitivity row; never used to choose anything | `... betarx/HVLM_b0p0016_t1rx.json` | b666a7a797065f45 |

Norm files for BC and PPO: `runs/batch_HVLM/norm.json` 92b5a8b0ff621ef0 and `runs/batch_LVHM/norm.json`
c489af94a46c246e.

**Run count: 13 x 2 x 32 + 32 = 864.** The jobs are in `jobs/confirm_report.txt`, written by
`fabhybrid/smt2020/make_confirm_jobs.py`, which refuses to write if any hash above differs. Outputs go to
`final/confirm/report/`.

Notes on the artefacts:
- The learner's file is byte-identical to `betarx/family/{fab}_learner_b0p003_t1.json` and to
  `betarx/{fab}_b0p003_t1rx.json`. It takes the same decision in every cell (same fire array and edges) as
  `collect/{fab}_b0p01_t1rx.json`. The development record ran it on seeds 0-31 as
  `collect/{fab}_b0p01_t3rx.json` (both scenarios) and `collect/LVHM_b0p01_t1rx.json`; the path
  `collect/{fab}_b0p003_t1rx.json` itself was never run on those seeds.
- The residual-only tables are fitted to the same period-1 records as the learner, with the arrival axis
  folded out (the `resid` line of `betarx/fit_family.sh`).
- `norev` in the development record's file names is the timeout rule's records, made without reversals.
- The manuscript's Table III tables (HVLM at beta 0.02, LVHM at 0.01) differ from the 0.003 tables here
  in 3, 4 and 7 cells on HVLM (timeout, minimum batch, NACH) and in 2, 1 and 0 on LVHM.
- Policies of this block that take the same decision in every cell as a table already run on seeds 0-31:
  the learner (both scenarios), the residual-only table (both: `collect/{fab}_b0p003_t3_abl_residual.json`),
  the HVLM minimum-batch-records table (`collect/HVLM_b0p003_t3rx.json`) and the LVHM NACH-records table
  (`collect/LVHM_nach_b0p01_t1rx.json`). The timeout-records tables (both), the HVLM NACH-records table,
  the LVHM minimum-batch-records table and the sensitivity row have not been run on seeds 0-31. Two of
  them have 360-day runs on the selection seeds 108-115 in `binedges/search/` (PROTOCOL_binedges.md): the
  sensitivity row itself, and `betarx/HVLM_b0p002_t1rx.json`, which takes the HVLM timeout-records
  table's decision in every cell. The other three have not been evaluated on any seed; the LVHM
  minimum-batch-records table's decisions ran only as an exploring logging policy
  (`collect/LVHM_b0p003_t2rx.json`, seeds 104-105, 181 days).
- The artefacts under `betarx/family/` were untracked when this file was written. They are committed with
  it.

## What is deliberately absent

No policy derived from the station analysis or read off a fitted table is run: not the two-index hand rule
of 2026-09-18, not the next-arrival rule of the 2026-09-22 diagnostic. Such rules can appear only as a
readout of what the learner found, never as a row of Tables I-III. No rule parameter is tuned on these
seeds.

## Step 0: bit identity (before the block, CLAUDE.md section 4)

- `make_confirm_jobs.py --prelaunch` waits for `jobs/binedges_search.done`, then removes every
  `__pycache__` under `fabhybrid/` and `external/`, and refuses to continue unless the generator, the job
  files, `jobs/confirm.cmd` and the artefacts above are tracked and unmodified,
  `git status --short fabhybrid/ external/` is empty, every hash matches, no file under `experiments/`
  outside `final/confirm/` carries a seed from 64-95, and the job files on disk equal what the generator
  writes.
- Run the learner on seed 64, both scenarios, twice: into `final/confirm/step0/a/` and
  `final/confirm/step0/b/` (`jobs/confirm_step0.txt`, 4 runs).
- **Pass.** Each pair is identical in every output field except `wall_s`
  (`make_confirm_jobs.py --check-step0`, which appends to `jobs/confirm_step0.pass`). The block starts
  only on a pass.
- **Fail.** No block run is made. The cause is found first: stale bytecode, or a source file reverted by
  OneDrive.
- **After the block.** Its own seed-64 learner runs must equal the step-0 runs (the same check, run again
  by the launch chain). A mismatch means the code changed between step 0 and the block; the chain stops,
  and nothing is read until the affected runs are redone.

## Tests (declared now)

**Metric.** Completed lots per day (`scrap_kpi.completed_per_day`), paired by seed. For a difference
A - B over the n seeds where both ran:
- the mean;
- the 95% paired-t interval: mean ± t(0.975, n - 1) x sd / sqrt(n), with t = 2.040 at n = 32;
- the wins and losses of A;
- the exact two-sided sign test with ties dropped: p = min(1, 2 x sum over i <= min(w, l) of C(w + l, i) / 2^(w + l)).

These are the helpers `paired` and `sign_p` of `final_report.py`. Its `t_crit` tabulates only 7, 15, 31
and 63 degrees of freedom and returns 1.96 otherwise; the analysis of this block uses the exact Student
quantile for the n of each comparison.

**No interim looks.** No output of the block is opened, and no partial summary is computed, until every
run has finished or failed twice. `--check-step0` compares files and prints no metric.

**Superiority.** The sign test at 0.05, after Holm where a family is named. The claim holds only if the
test rejects with the policy named first ahead (wins > losses). A rejection the other way is reported as
the opposite finding.

**Non-inferiority.** The lower end of the two-sided 95% paired-t interval of A - B is above -0.25
completed lots per day. This is a one-sided test at 2.5%.
- **The margin.** 0.25 lots a day is 0.7% of either scenario's completions (36.6 and 35.5 for the control
  limit on the development record).
- **What it demands.** On the development record the paired SD of learner - control limit was 0.59
  (HVLM) and 0.88 (LVHM) lots a day. At n = 32 that gives a 95% half-width of about 0.21 and 0.32, so
  non-inferiority needs an observed mean above about -0.04 (HVLM) and +0.07 (LVHM).
- A failure of the test is read as "not shown within 0.25", never as a loss; a loss is stated only when
  the sign test rejects with the other policy ahead.

**Holm.** For a family of three, the p-values are sorted p(1) <= p(2) <= p(3). H(k) is rejected while
p(k) <= 0.05 / (4 - k), stopping at the first non-rejection. The adjusted p-values,
p~(k) = max over j <= k of min(1, (4 - j) p(j)), are reported.

**Scope of each claim.** Every claim is tested on each scenario separately. The scenarios are not pooled
and not adjusted together. Multiplicity is controlled within C1 and within C3 (Holm over three), and not
across claims. The paper states each claim per scenario. A sentence that states a claim for both scenarios
needs it to hold on each; that is an intersection and needs no further adjustment.

## Primary comparisons (completions per day)

| claim | comparison(s) | test |
|---|---|---|
| C1 | learner - mbs:3, learner - nach, learner - timeout:1 | superiority; sign test, Holm within the three |
| C2 | learner - clock:1.5 | non-inferiority, margin 0.25; then, as the second step of a fixed sequence, superiority by sign test (no adjustment; "more" is said only if non-inferiority holds) |
| C3 | timeout table - timeout:1, minimum-batch table - mbs:3, NACH table - nach | superiority; sign test, Holm within the three |
| C4 | learner - residual-only table | superiority; sign test |

## Secondary (reported with mean, 95% t-interval, wins/losses and sign p; no claim, no adjustment)

- For every primary pair: scrapped lots per day (`scrap_kpi.scrapped_per_day`), median cycle time
  (`scrap_kpi.cycle_p50_days`), and under-full loads started per day.
  - Under-full loads per day is `batches_partial_all` / 273: the ledger's count of under-full loads
    started in days 87-360. The development tables' `batches_partial` / 273 counts over all 360 days and
    runs 1.27-1.40 times higher (median 1.33 over the development runs in `final/report/`, never lower than
    the window count); it is reported beside the window count only to link the two records.
- The logging policy minus the full-batch default: what the fab gains or loses while it logs.
- The learner minus the logging policy (Table III, last row of each scenario).
- Each rule-records table minus the learner (Table III, "against reversals").
- Each rule-records table minus the control limit.
- The learner minus the full-batch default, BC and PPO (Table I rows).
- **Sensitivity row (HVLM).** The records-price table (beta 0.0016; it differs from the learner in 2 of
  the 24 cells) minus the learner and minus the control limit. It is never used to choose anything.

Wins and losses count A > B and A < B whatever the preferred direction of the measure.

## Tables on these seeds

- **Table I.** full-batch default, minimum batch q = 3, NACH, timeout T = 1 h, control limit h = 1.5 h,
  BC, PPO, learner.
  - The selection-seed column is unchanged.
  - The "Report" column is replaced by these seeds.
  - Learner - policy, scrapped per day and median cycle time come from this block.
- **Table II.** Residual only (6 cells) and the learner (24 cells), both fitted to the learner's
  one-period records; the learner against the residual-only table (C4). No other row.
  - The residual-only tables take the same decision in every cell as
    `collect/{fab}_b0p003_t3_abl_residual.json`, run on seeds 0-31. The manuscript's residual-only rows
    (HVLM 0.02, LVHM 0.01) are different tables (one cell each).
- **Table III.** Records of the timeout rule, minimum batch, NACH and the logging policy: policy, table,
  table - policy, and table - learner from this block.
  - The fit-only columns (cells holding each action at least n0 = 10 times, and agreement on the logged
    free decisions) are recomputed from the 0.003 artefacts. They do not depend on seeds.
  - The current manuscript has HVLM at 0.02 and LVHM at 0.01.
- The selection seeds 108-115 keep their role: they chose q, T and h, and they choose nothing here.
- Every number in the paper that this block does not produce (the selection-seed column, the figures drawn
  from simulation, the behaviour readout, the multi-period refits) is development record and is labelled
  so.

## Reading (declared now; per scenario)

| outcome | what the paper says |
|---|---|
| C1 holds for all three rules | "completes more lots than each of the three rules" with the differences and wins of Table I |
| C1 fails for a rule | that rule is named with its difference and interval; the sentence covers the others only |
| C2 non-inferiority holds | the abstract and conclusion say "no fewer than the simulator-tuned control limit, within a margin of 0.25 lots a day (0.7%)"; "at least as many" only if the lower end of the interval is at or above 0; if the superiority sign test then rejects with the learner ahead, "and more on <scenario>" |
| C2 non-inferiority fails | that sentence is removed for that scenario; Table I reports the difference and interval, and the text says the learner was not shown to be within 0.25 lots a day of the control limit |
| C2: sign test rejects with the control limit ahead | "the control limit completes more on <scenario>", with the difference and interval, whatever the non-inferiority test shows |
| C3 holds for a rule | "the table fitted from one period of that rule's own records completes more than the rule" |
| C3 fails for a rule | named, with its difference |
| C4 holds | "reading the next arrival adds d [lo, hi] lots a day over the residual alone" |
| C4 fails | the arrival axis is reported as not shown to add completions on that scenario |
| sensitivity row (HVLM) | reported as one row whatever it shows, with its difference from the learner and from the control limit; the declared price is not changed |

Whatever the block shows, the report seeds 0-31 are not pooled with these seeds. If a confirmatory number
contradicts a development number, the confirmatory number is the one the paper's text uses. The
development number stays in the appendix as measured.

## Failures and deviations

- A run that exits non-zero is rerun once with the same command. The launch chain does this by running
  the queue file a second time; `run_queue.py` relaunches only the runs whose output is missing. The
  simulator is deterministic, so the rerun is the same run.
- A run that fails twice is reported. Its seed is dropped from every comparison that involves that
  policy, and n is printed with each comparison.
- Every deviation from this file goes into the results file with its reason.

## Launch

`jobs/confirm.cmd` (written by `make_confirm_jobs.py`; RL environment, `OMP_NUM_THREADS=1`,
`PYTHONIOENCODING=utf-8`, from `fabhybrid/smt2020`, log in `jobs/confirm.out`) runs, each step only if the
one before it succeeded:
1. `make_confirm_jobs.py --prelaunch` (waits for `jobs/binedges_search.done`, so the selection runs of
   PROTOCOL_binedges.md finish first; then the checks of step 0);
2. step 0 (4 runs);
3. `--check-step0`;
4. the block (864 runs), then the same queue again for the reruns;
5. `--check-step0` (the block's seed-64 learner runs against step 0).

At about 25-33 min per run and 14 in parallel, that is about 30 hours.

## Deviation of 2026-10-10: rows 12 and 13 (BC and PPO) retrained with the queue-time critical ratio

The 2026-09-07 weights named above were trained in windows without the queue-time critical ratio
(`train_batch.make_env` and `scrap_snap.py` built the environment with `cqt_rule` none) and evaluated with
it (`--cqt-rule qtcr`), which the Section 5 audit of 2026-10-10 found. The author decided to retrain rather
than to state the mismatch. Everything else of rows 12-13 is unchanged: the same control limit at 2 h as the
cloned policy, eight 10-day BC windows and 60 epochs, 16 PPO iterations of six 10-day windows from the BC
weights with the critic warmed up for two, the iterate with the highest deterministic yield kept, greedy
evaluation by `eval_batch.py` on seeds 64-95 with the same command line.

- Warm-ups: `jobs/snaps_qtcr.txt`, 90 days under the control limit at 2 h with QTCR, seeds 0-3 per scenario
  (`scrap_snaps/snap_{fab}_r0.98_qtcr_s{0..3}.pkl.gz`, 2026-10-09 23:33-23:37).
- Training: `run_training.py --dataset {fab} --cqt-rule qtcr --suffix _qtcr --no-eval`
  (`jobs/retrain_bcppo_qtcr.sh`), 2026-10-09 23:37 to 2026-10-10 00:05, into `runs/batch_{fab}_qtcr/`.
  BC agreement with the cloned policy on held-out decisions: HVLM 0.9966, LVHM 0.9970 (`bc.json`).
  PPO's kept iterate: HVLM 7 (deterministic yield 144.8), LVHM 12 (189.7) (`best.json`).
- Hashes (sha256[:16]): HVLM `weights_bc.pt` 4f5bdf82ed67be40, `weights_best.pt` 9a6e4a1dad87e7ce,
  `norm.json` 07abc5aa3f8ca0d2; LVHM `weights_bc.pt` 3527d4beb80c7c5c, `weights_best.pt` 442da61888e2bdc0,
  `norm.json` 96f34c5a7a389091. `make_confirm_jobs.py` pins these from 2026-10-10.
- Evaluation: `jobs/confirm_bcppo_qtcr.txt`, 128 runs (2 networks x 2 scenarios x seeds 64-95), started
  2026-10-10 00:06, outputs under `final/confirm/report/` with the same file names as before. The 2026-09
  network runs of the block were moved beforehand to `final/confirm/report_bcppo_2026-09/` (256 files)
  and are the record of the rows the manuscript carried until this date.
- The results file, Tables 1-2 and Figure 5 of the manuscript are regenerated from the block with the new
  rows; no other row of the block changes.
