# smt2020 — from the dispatching records to the manuscript

This directory holds the code on the path from the simulator and the dispatching records to the
numbers, tables and figures of the manuscript "Batching under queue-time constraints learned from
dispatching records" (`paper/main.tex`). The order below is the order of the pipeline:
records -> tables -> runs -> report -> floats. The closed research lines that used to live here
are under `archive/2026-10-closed-lines/` of the development repository (not in the public package); nothing on the paper's path
imports them (one import inside a branch of `level.py` the paper does not reach; last section).

Conventions:

- Everything runs from this directory (`cd fabhybrid/smt2020`). Modules are flat top-level imports,
  not a package, because the workers re-exec themselves by path (`run_queue.py`, `run_training.py`).
  Paths in the job files are relative to this directory (`../../experiments/smt2020/...`).
- `rl_env.py` puts the simulator (`external/PySCFabSim-release`) on `sys.path`. Instances are built at
  t=0 from the dataset files; no pre-warmed pickle.
- One run of `batch_fire.py` (or `eval_batch.py`) writes one JSON. `run_queue.py` runs a job file
  (`<command>  ->  <expected output>` per line) N commands at a time and **skips a job whose output
  exists**.

## Environment

conda env `RL`: Python 3.9.19, numpy 1.26.4, scipy 1.13.1, pandas 2.2.2, simpy 4.1.1, torch 2.8.0
(BC/PPO only), matplotlib 3.9.0 (figures), cloudpickle 3.0.0 (snapshots), pytest 8.4.2 (tests).
`OMP_NUM_THREADS=1` (`run_queue.py` and `run_training.py` set it for their children).

The simulator is the git submodule `external/PySCFabSim-release` at `0dbff6a` (`77103ed` plus an MIT
LICENSE; the diff between the two is that one file), used unmodified; it ships the SMT2020 data files.
Clone with `git clone --recursive`, or run `git submodule update --init`.

## 1. Records

| file | what it does | feeds |
|---|---|---|
| `readout.py` | runs one policy (`--arm`) through `batch_fire.py` and, with `--dump-lots`, writes the dispatching record: every batch decision with its live queue-time clocks, the head group, the time to the next arrival, and every scrapped lot. `--dump-from 90` keeps the window after the warm-up; `--slim` keeps only what `fit_q.py` reads. | `experiments/smt2020/final/collect/*_p1_s10{0,1}.json` (gitignored; the job files regenerate them) |
| `make_collect_jobs.py` | writes `jobs/collect_*.txt`. On the paper's path only `collect_p1.txt`: the full-batch rule with 2% of the free decisions started (`explore:0.02`), seeds 100-101. Periods 2-3 and `collect_t*.txt` are the September three-period pipeline (development record). | records of the full-batch rule |
| `make_incumbent_jobs.py` | writes `jobs/incumbent_{log,fit,report}.txt`. On the paper's path only `incumbent_log.txt`: the records of the minimum-batch-size rule (`mbs:3`) and NACH. Its fit and report files use the September prices from `final/rx/selection_rx.json` and seeds 0-31 (development record). | records of `mbs:3` and NACH |
| `jobs/norev_log.txt` | hand-written; no generator. The records of the timeout rule (`timeout:1`). | records of the timeout rule |

A record is 91 days (days 90-181 of a 181-day run) on seeds 100 and 101. One line of each job file:

```
python readout.py --arm explore:0.02 --dataset HVLM --days 181 --seed 100 --dump-from 90 --slim --dump-lots ../../experiments/smt2020/final/collect/HVLM_p1_s100.json
python readout.py --arm timeout:1 --dataset HVLM --days 181 --seed 100 --dump-from 90 --slim --dump-lots ../../experiments/smt2020/final/collect/HVLM_norev_p1_s100.json
python readout.py --arm mbs:3 --dataset HVLM --days 181 --seed 100 --dump-from 90 --slim --dump-lots ../../experiments/smt2020/final/collect/HVLM_mbs3_p1_s100.json
python readout.py --arm nach --dataset HVLM --days 181 --seed 100 --dump-from 90 --slim --dump-lots ../../experiments/smt2020/final/collect/HVLM_nach_p1_s100.json
```

The job files are run by `run_queue.py`, e.g. (from `jobs/retrain_bcppo_qtcr2.sh`, `J=../../experiments/smt2020/jobs`):

```
python run_queue.py $J/confirm_bcppo_qtcr2.txt --parallel 14
```

## 2. Tables

| file | what it does | feeds |
|---|---|---|
| `fit_q.py` | the learner. Every furnace decision of the records becomes a step of a decision chain per tool family, (cell, action) -> (reward, elapsed time, next cell), and value iteration on that empirical model gives the action of each cell. Reward: minus the lots scrapped, minus `--lam` (beta, lots per empty slot-hour) times the empty slot-hours of a started under-full load. `--fold fill` gives the paper's 24 cells (6 bins of the tightest residual x 4 of the time to the next arrival), `--fold nxt,fill` the residual-only table; `--backoff` gives a cell without both actions n0 = 10 times the residual-only entry. Writes a `Level` artefact of kind `table`. | the fitted tables |
| `label.py` | `batch_max_per_step`, the load capacity of each step read from a record; imported by `fit_q.py`. Its own command line writes per-decision labels (`.npz`) from exploration dumps; no stage of the paper runs it. | `fit_q.py` |
| `experiments/smt2020/final/betarx/fit_family.sh` | fits every table the confirmatory block runs, at beta 0.003 and 0.01: `learner`, `resid`, `full72` from the full-batch records; `timeout`, `mbs3`, `nach` from each rule's records | `betarx/family/*_b0p003_t1.json`: the "Table fitted from the records of" rows of Table 3, Figure 6 |
| `make_rx_jobs.py` | job files of `final/rx/PROTOCOL_rx.md`. On the paper's path only the beta 0.003 lines of `jobs/rx_t1.txt`, which wrote `collect/{HVLM,LVHM}_b0p003_t1rx.json`, the learner's artefact as the block ran it (byte-identical to `betarx/family/*_learner_b0p003_t1.json`; `make_confirm_jobs.py` checks this). Stages 2-3 are the development record; stage 3 read `rx_select.py`, now in `archive/2026-10-closed-lines/stage-b-report/`. | the learner's artefact |
| `experiments/smt2020/final/betarx/run_grid.sh` | the full-batch records refitted over a price grid 0.0005-0.02 (`grid_summary.json`) | `betarx/HVLM_b0p0016_t1rx.json`, the HVLM records-price row of the block |
| `table_agree.py` | the share of logged free decisions on which a table takes a reference table's action, without simulation | `binedges003/`; `confirm_report.py --agree-dumps` computes the agreement quoted in Section 5.3 the same way |

```
python fit_q.py ../../experiments/smt2020/final/collect/HVLM_p1_s100.json ../../experiments/smt2020/final/collect/HVLM_p1_s101.json --chain family --lam 0.003 --backoff --from-day 90 --fold fill --out ../../experiments/smt2020/final/collect/HVLM_b0p003_t1rx.json
bash ../../experiments/smt2020/final/betarx/fit_family.sh      # cds here itself; one fit per (scenario, price, records)
python table_agree.py --ref A.json --tables B.json C.json --dumps d1.json d2.json [--from-day 90]
```

The fit line in `fit_family.sh` is
`python fit_q.py $C/${src}_s100.json $C/${src}_s101.json --chain family --lam "$b" --backoff --from-day 90 $fold --out "$out"`.

## 3. Runs

| file | what it does | feeds |
|---|---|---|
| `batch_fire.py` | one simulation run, one JSON (`scrap_kpi`: completed and scrapped lots per day, median cycle time; `batches_partial`, `batch_fill`: the under-full loads; `trace`). The arm decides only whether an under-full load starts: `full` (the simulator's own rule: never below `batch_max`; a reference row), `mbs:k` (minimum batch size), `mbsmin` (the dataset's `BATCHMN`), `timeout:T` (start once the oldest lot has waited T h), `nach` (Glassey & Weng's look-ahead), `clock:h` (the remaining-time threshold, `clock` in the code: start if a waiting lot's clock has less than h h left; theta in the paper), `explore:p`, and `level:1 --theta <artefact>` (a fitted table). `--cqt-rule qtcr` adds Kopp's queue-time critical ratio to the sequencing; `--scrap` scraps a lot whose limit runs out. The paper's runs: `--scale 0.98 --days 360 --measure-from 0.241667` (completions over days 87-360). | every run |
| `level.py` | deploys an artefact: kind `table` looks up (tightest residual, time to the next arrival) and starts or waits; full loads start, no live clock waits. The other kinds belong to closed search lines (SCOPE note in the docstring). | `--arm level:1` |
| `fab_env.py` | PySCFabSim's own dispatch loop with the choice of load handed to the policy (adapted copy of upstream code, see `NOTICE`) | |
| `rl_env.py` | simulator wiring and the t=0 instance (adapted copy of `Instance.next_step`, see `NOTICE`) | |
| `cqt.py` | the queue-time constraints, implemented against the plugin interface because the simulator's own are inert | |
| `kopp.py` | Kopp et al.'s QTCR sequencing rule | |
| `scenarios.py` | release scaling (`scale_release`, the 0.98 of the paper) | |
| `bench_metrics.py` | the benchmark's per-product statistics | |
| `fab_features.py` | the global fab-state features the BC/PPO network reads | |
| `final_select.py` | applies the one selection rule of `final/PROTOCOL.md` (highest mean completions per day on seeds 108-115) per arm family | `final/selection.json`: the grids and the selected q = 3, T = 1 h, theta = 1.5 h of Table 2 |
| `make_confirm_jobs.py` | job files of `final/confirm/PROTOCOL_confirm.md`: step 0 (the learner on seed 64 twice) and the block, 13 policies x 2 scenarios x seeds 64-95 plus the HVLM records-price row (864 runs), and `jobs/confirm.cmd`, which chains them with the protocol's checks (`--prelaunch`, `--check-step0`). Its BC/PPO lines in `jobs/confirm_report.txt` point at the earlier weights in `runs/batch_<fab>/`; the block's BC/PPO runs came from `jobs/confirm_bcppo_qtcr.txt` with the retrained `_qtcr` weights, which are the ones kept | `final/confirm/report/` |
| `run_queue.py` | the job runner | |
| `scrap_snap.py` | warm-up snapshots (`.pkl.gz`) that the training windows start from | `scrap_snaps/` (gitignored) |
| `run_training.py` | per scenario: normalisation (`train_batch.py --calibrate`), BC on the remaining-time threshold at 2 h (`--bc --law clock:2`), PPO from the BC weights (`--learn`) | `runs/batch_<fab><suffix>/` |
| `train_batch.py` | the BC/PPO trainer of the batch policy | |
| `train_l1.py` | library only: feature normalisation, feature rows, the global vector and the PPO update shared by `train_batch.py` and `eval_batch.py` | |
| `eval_batch.py` | greedy evaluation of trained weights, written in `batch_fire.py`'s JSON layout as `rl-<tag>` | the BC and PPO rows |

Selection (seeds 108-115; `jobs/final_search.txt`, hand-written, then `final_select.py`):

```
python batch_fire.py --dataset HVLM --scale 0.98 --days 360 --measure-from 0.241667 --arm clock:1.5 --cqt-rule qtcr --scrap --seed 108 --out ../../experiments/smt2020/final/search
python final_select.py
```

The confirmatory block (seeds 64-95):

```
python make_confirm_jobs.py                # writes jobs/confirm_step0.txt, confirm_report.txt and
                                           # jobs/confirm.cmd, the launch chain
python batch_fire.py --dataset HVLM --scale 0.98 --days 360 --measure-from 0.241667 --arm level:1 --theta ../../experiments/smt2020/final/betarx/family/HVLM_timeout_b0p003_t1.json --cqt-rule qtcr --scrap --seed 64 --out ../../experiments/smt2020/final/confirm/report
```

BC and PPO, retrained 2026-10-19 without the two elapsed-time inputs (`train_l1.global_vec`; the days since
the episode start and the episode progress spanned 10 days in training and 360 in evaluation), from the
2026-10-10 snapshots with the queue-time critical ratio in their training windows (`jobs/retrain_bcppo_qtcr2.sh`
chains the steps; the 2026-10-10 evaluations of the block were moved to `final/confirm/report_bcppo_2026-10-10/`,
the 2026-09 ones to `report_bcppo_2026-09/`):

```
python scrap_snap.py --dataset HVLM --scale 0.98 --seed 0 --days 90 --window 60 --cqt-rule qtcr --out ../../experiments/smt2020/scrap_snaps/snap_HVLM_r0.98_qtcr_s0.pkl.gz
python run_training.py --dataset HVLM --cqt-rule qtcr --suffix _qtcr --runs-suffix _qtcr2 --no-eval
python eval_batch.py --weights ../../experiments/smt2020/runs/batch_HVLM_qtcr2/weights_bc.pt --norm ../../experiments/smt2020/runs/batch_HVLM_qtcr2/norm.json --dataset HVLM --scale 0.98 --days 360 --measure-from 0.241667 --cqt-rule qtcr --seed 64 --tag bcHVLM --out ../../experiments/smt2020/final/confirm/report
```

(`jobs/snaps_qtcr.txt`, `retrain_bcppo_qtcr2.sh`, `jobs/confirm_bcppo_qtcr2.txt`.) `bc.json` in each runs
folder holds the BC agreement with the cloned policy; Table 2 quotes it (99.5% and 99.7%, from
`runs/batch_<fab>_qtcr2/bc.json`; the 2026-10-10 weights in `runs/batch_<fab>_qtcr/` gave 99.7% on both).

## 4. Report

| file | what it does | feeds |
|---|---|---|
| `confirm_report.py` | every number of the block from the run files, written once: per policy, per paired comparison (95% paired-t interval, exact sign test with ties dropped, Holm), per fitted table. `--dev` reads the development record (`final/report/`, seeds 0-31). | `final/confirm/results.json` |
| `confirm_tables.py` | renders the results file and nothing else | `paper/tables/policies.tex` (Table 3), `numbers.tex` (the `\num...` macros the text quotes) |

```
python confirm_report.py                    # the block: final/confirm/report, seeds 64-95, the file
                                            # tags of jobs/confirm_report.txt -> final/confirm/results.json
python confirm_tables.py                              # final/confirm/results.json -> paper/tables/
```

Facts the text quotes that no run produces are computed by scripts next to their outputs in
`experiments/smt2020/final/` (`paperfacts/README.md` says where each is quoted):

- `paperfacts/testbed_facts.py` (`python -B testbed_facts.py`): Table 1's testbed rows and kappa at beta 0.003, from the data files.
- `paperfacts/rule_tables.py` (`python -B rule_tables.py FAB KIND`, `python -B rule_tables.py --summary`): the record facts of Section 5.1.2 and the refits over price, discount and n0 (Table 4, Section 5.3).
- `paperfacts/bin_dist.py` (`python bin_dist.py`): the two state quantities of the records against the bin edges.
- `binedges003/` (`fit_variants003.sh`, `agree003.sh`, `analyse003.py`): bin-edge variants at beta 0.003; `perfamily/` (`filter_records.py`, `run_fits.sh`, `run_agree.sh`, `analyse.py`): per-family tables against the pooled one. Both fit only and use `fit_q.py` and `table_agree.py`.

## 5. Floats

| float | file | made by |
|---|---|---|
| Figure 1 | `paper/figures/setting.pdf` | `figures/fig_setting.py` |
| Figure 2 | `station.pdf` | `figures/fig_station.py --variant v2` (three costs of waiting) from `experiments/smt2020/theory/announced.json` |
| Figure 3 | `method.pdf` | `figures/fig_method.py` |
| Figure 4 | `fab.pdf` | no script: exported from `paper/figures/src/figures.pptx` |
| Figure 5 | `diffs.pdf` | `figures/fig_diffs.py` from `final/confirm/results.json` |
| Figure 6 | `tables.pdf` | `figures/fig_tables.py` from `final/confirm/results.json` |
| Tables 1-2 | `paper/sections/setup.tex` | typed from `paperfacts/testbed_facts.json`, `rule_tables_summary.json`, `final/selection.json`, `runs/batch_<fab>*/bc.json` |
| Table 3 | `paper/tables/policies.tex` | `confirm_tables.py` (with `numbers.tex`, the macros the text quotes) |
| Table 4 | `paper/tables/sensitivity.tex` | `sensitivity_table.py` (price rows; `--full` for every setting) |
| Table 5 | `paper/tables/shift.tex` | `shift_report.py --tex` |

`figures/house_style.py` holds the typography every figure applies first.

```
python figures/fig_setting.py             -> paper/figures/setting.pdf (+ a PNG preview)
python figures/fig_station.py --out ../../paper/figures/station.pdf     # the manuscript's file is --variant v2
python figures/fig_method.py            -> paper/figures/method.pdf (+ a PNG preview)
python figures/fig_diffs.py --results ../../experiments/smt2020/final/confirm/results.json \
    --out ../../paper/figures/diffs.pdf
python figures/fig_tables.py --mark dot --results ../../experiments/smt2020/final/confirm/results.json \
    --out ../../paper/figures/tables.pdf
```

The isolated station of Section 3.2 and Appendix A (`theory/`):

| file | what it does | feeds |
|---|---|---|
| `theory/announced_station.py` | the station with a price on the tool's time and announced arrivals, solved exactly by value iteration; `--grid` solves 540 instances | `experiments/smt2020/theory/announced.json`, Figure 2 |
| `theory/announced_lowkappa.py` | the same at kappa = 0.1 (180 instances) | `announced_kappa0p1_{R8,R12_L2,R12_L4}.json` |
| `theory/announced_cells.py` | classifies the cells in which the rest of the state decides | `announced_cells.json` |
| `theory/announced_summary.py` | prints the numbers of Section 3.2 and Appendix A.2 over the 720 instances | `\stationInstances`, `\stationPurePct` in `main.tex` |
| `theory/check_lastmoment.py` | brute-force check that the last-moment policy is optimal without a cost of waiting (the sentence of Section 3.2 that cites Berg et al. 1998; the proposition itself left the paper on 2026-10-19) | |

```
python theory/announced_station.py --grid --out ../../experiments/smt2020/theory/announced.json
python announced_lowkappa.py 8 2,4 0.1 ../../../experiments/smt2020/theory/announced_kappa0p1_R8.json          # from theory/
python announced_lowkappa.py 12 4 0.1 ../../../experiments/smt2020/theory/announced_kappa0p1_R12_L4.json       # from theory/ (jobs/lowkappa.cmd)
python theory/announced_cells.py
python theory/announced_summary.py
python theory/check_lastmoment.py
```

`announced_kappa0p1_R12_L2.json` has no recorded command.

## Tests

`python -m pytest tests -q` from this directory. `test_confirm_report.py` (statistics and formats),
`test_confirm_tables_regenerates.py` (`policies.tex` and `numbers.tex` re-rendered byte for byte),
`test_fit_q_reproduces.py` (the timeout-records table refitted entry for entry; skipped without the
records), `test_level_lookup.py` and `test_table_agree.py` run without the simulator.
`test_batch_arms.py`, `test_minrun_break.py`, `test_snapshot.py` and `test_yield_env.py` exercise the
arms, the environment and the snapshots.

## What is not here (the development repository's `archive/`; not in the public package)

- The closed lines of 2026-09/10 (the September reporting chain `final_report.py` -> `final_tables.py`,
  `bf_report.py`, `make_stage_b.py`, `rx_select.py` and the other report scripts; the set learner; the
  fork check; `behaviour_summary.py`, `beta_from_records.py`, `lvhm_base.py`, `variants.py`; three
  September figures; four auxiliary station models; the p-batch testbed that was `fabhybrid/pbatch/`):
  `archive/2026-10-closed-lines/`. `level.py`'s kind `setnet` still imports `setnet_feat` inside that
  branch; the paper's tables are kind `table`.
- Earlier retirements: `archive/2026-09-batch-line-closed/` (`fit_decision.py`, `fit_level.py`,
  `distill.py`, `confusion.py`, `report_block.py`, `validate_freeze.py`, ...),
  `archive/2026-09-closed-axes/` (`batch_probe.py`, `pm_probe.py`, `cqt_windows.py`, ...),
  `archive/2026-08-closed-probes/smt2020/`, `archive/2026-09-paper-figures-superseded/`.
- The HVLM/Tassel reproduction line: `archive/2026-09-sota-repro-line/`; its outputs are in
  `experiments/sota_repro/`.
