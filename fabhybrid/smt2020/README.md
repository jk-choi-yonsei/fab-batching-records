# Code

Run everything from this directory; paths in the job files are relative to it. `rl_env.py` puts the
simulator on `sys.path`.

Records

- `readout.py` runs one policy and, with `--dump-lots`, writes its dispatching record.
- `make_collect_jobs.py`, `make_incumbent_jobs.py`, `make_rx_jobs.py` write the job files of the records
  and of the first tables.

Tables

- `fit_q.py` fits a table from records by value iteration: `--lam` the price, `--fold fill` the 24 cells,
  `--fold nxt,fill` the one-axis table, `--backoff` the one-axis table's entry for a cell short of either
  action.
- `label.py` reads the load capacity of each step from a record.
- `table_agree.py` gives the share of recorded decisions on which two tables take the same action.

Runs

- `batch_fire.py` runs one simulation and writes one JSON. `--arm` picks the policy: `full` (full batch),
  `explore:p` (full batch with random starts), `mbs:k` (minimum batch size), `timeout:T`, `nach` (the
  look-ahead rule), `clock:h` (the remaining-time threshold), `level:1 --theta TABLE` (a fitted table).
  `--cqt-rule qtcr` adds the queue-time critical ratio to the sequencing; `--scrap` scraps a lot that
  misses its limit.
- `level.py` applies a fitted table at a free decision.
- `fab_env.py` and `rl_env.py` wire the simulator (adapted from PySCFabSim; see `NOTICE`). `cqt.py` the
  queue-time constraints, `kopp.py` the queue-time critical ratio, `scenarios.py` the release scaling,
  `bench_metrics.py` the per-product statistics, `fab_features.py` the features of the BC/PPO network.
- `final_select.py` selects the settings of the rules. `make_confirm_jobs.py` and `make_shift_jobs.py`
  write the job files of the two result blocks. `run_queue.py` runs a job file.
- `scrap_snap.py` writes warm-up snapshots; `run_training.py`, `train_batch.py` and `train_l1.py` train BC
  and PPO; `eval_batch.py` evaluates trained weights.

Reports and figures

- `confirm_report.py` writes `results.json` from the run files; `confirm_tables.py`, `sensitivity_table.py`
  and `shift_report.py` render Tables 3, 4 and 5.
- `figures/` holds one script per figure and `house_style.py`.
- `theory/` solves the isolated station: `announced_station.py` (value iteration; `--grid` for the
  instances), `announced_lowkappa.py`, `announced_cells.py`, `announced_summary.py`, `check_lastmoment.py`.
- `tests/` runs with `python -m pytest -q tests`.
