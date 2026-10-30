# Batching under queue-time constraints learned from dispatching records

Code and data for the paper of this title (Jongkwan Choi and Chang Ouk Kim, Yonsei University).

## Setup

Python 3.9 with `requirements.txt`, `OMP_NUM_THREADS=1`. The simulator PySCFabSim is a git submodule at commit
0dbff6a and ships the SMT2020 data.

```
git clone --recursive https://github.com/jk-choi-yonsei/fab-batching-records.git
cd fab-batching-records/fabhybrid/smt2020
python -m pytest -q tests
```

Every command below runs from `fabhybrid/smt2020`.

## Tables and figures

From the results files in `experiments/`, without simulation:

```
python confirm_tables.py                  # Table 3
python sensitivity_table.py               # Table 4
python shift_report.py --tex              # Table 5
python figures/fig_setting.py             # Figure 1
python figures/fig_station.py             # Figure 2
python figures/fig_method.py              # Figure 3
python figures/fig_diffs.py               # Figure 5
python figures/fig_tables.py --mark dot   # Figure 6
python theory/announced_summary.py        # the numbers of Section 3.2
```

Figure 4 is drawn by hand.

## Runs

Each stage is a job file in `experiments/smt2020/jobs/`, one command per line, run by
`python run_queue.py <file> --parallel N`. The dispatching records (0.9 GB) are not included; stage 1
regenerates them. A 360-day run takes about 15 minutes on one core.

1. Records: `collect_p1.txt`, `norev_log.txt`, `incumbent_log.txt`.
2. Tables: `bash ../../experiments/smt2020/final/betarx/fit_family.sh`.
3. Settings of the rules: `final_search.txt`, then `python final_select.py`.
4. BC and PPO: `snaps_qtcr.txt`, then `retrain_bcppo_qtcr2.sh`.
5. Results of Section 5.2: `confirm_step0.txt`, `confirm_report.txt`, `confirm_bcppo_qtcr2.txt`, then
   `python confirm_report.py`.
6. Release rates: `shift.cmd`, then `python shift_report.py`.
7. The isolated station: `python theory/announced_station.py --grid`, `lowkappa.cmd`,
   `python theory/announced_cells.py`.

## Layout

| Path | Contents |
|---|---|
| `fabhybrid/smt2020/` | the code; its `README.md` lists the files |
| `experiments/smt2020/final/betarx/family/` | the fitted tables |
| `experiments/smt2020/final/confirm/results.json` | the results of Section 5.2, per seed |
| `experiments/smt2020/final/shift/` | the results at the lower release rates, the tables refitted there, the probe at 1.05 |
| `experiments/smt2020/final/paperfacts/`, `binedges003/` | the facts of Table 1 and the refits of the sensitivity study |
| `experiments/smt2020/final/selection.json` | the selected settings of the rules |
| `experiments/smt2020/theory/` | the solved station instances |
| `experiments/smt2020/runs/` | the BC and PPO weights |
| `experiments/smt2020/jobs/` | the job files |
| `external/PySCFabSim-release` | the simulator (submodule) |

## License

MIT (`LICENSE`). The simulator and the data keep their own terms (`NOTICE`).
