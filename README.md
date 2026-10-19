# Batching under queue-time constraints learned from dispatching records

Code and data of the paper (Jongkwan Choi and Chang Ouk Kim, Yonsei University; submitted to the International
Journal of Production Research). In the code the paper's remaining-time threshold is the arm `clock`.

| Path | What |
|---|---|
| `fabhybrid/smt2020/` | the code; its `README.md` maps each file to the paper |
| `fabhybrid/smt2020/tests/` | tests |
| `fabhybrid/smt2020/theory/` | the isolated station (Section 3.2, Appendix A) |
| `fabhybrid/smt2020/figures/` | the figures |
| `experiments/smt2020/final/betarx/family/` | the fitted tables |
| `experiments/smt2020/final/confirm/` | the confirmatory block: protocol, runs, `results.json` |
| `experiments/smt2020/final/shift/` | the release-rate block: protocol, runs, `results.json` |
| `experiments/smt2020/final/selection.json` | the selection of the rules' settings |
| `experiments/smt2020/final/paperfacts/`, `binedges003/` | the facts quoted in the text and the refits |
| `experiments/smt2020/theory/` | the solved station instances |
| `experiments/smt2020/runs/batch_*_qtcr2/` | the BC and PPO weights |
| `experiments/smt2020/jobs/` | the job files that ran each stage |
| `external/PySCFabSim-release` | the simulator, a submodule at the paper's commit; ships the SMT2020 data |

Not here: the dispatching records (0.9 GB; the job files regenerate them) and Figure 4, drawn by hand.

## Environment

Python 3.9; `requirements.txt`. `OMP_NUM_THREADS=1`. Run everything from `fabhybrid/smt2020/`.

```
git clone --recursive <this repository>
# from the zip: git clone https://github.com/prosysscience/PySCFabSim-release.git external/PySCFabSim-release
#               git -C external/PySCFabSim-release checkout 0dbff6a
cd fabhybrid/smt2020
python -B -m pytest -q tests -p no:cacheprovider
```

The `.cmd` files expect a conda environment named `RL`. On Windows use a short clone path.

## Tables and figures

From the results files here, no simulation:

```
python confirm_tables.py                      # Table 3, numbers.tex
python sensitivity_table.py                   # Table 4 (--full OUT.tex: every setting)
python shift_report.py --tex                  # Table 5
python figures/fig_setting.py                 # Figure 1
python figures/fig_station.py --variant v2    # Figure 2
python figures/fig_method.py                  # Figure 3
python figures/fig_diffs.py                   # Figure 5
python figures/fig_tables.py --mark dot       # Figure 6
python theory/announced_summary.py            # the station numbers
```

## Experiments

Each stage is a job file in `experiments/smt2020/jobs/`, run by `run_queue.py <file> --parallel N` (a job whose
output exists is skipped):

1. Records: `collect_p1.txt`, `norev_log.txt`, `incumbent_log.txt` (181 days, the last 91 recorded).
2. Tables: `final/betarx/fit_family.sh`; refits: `final/paperfacts/rule_tables.py`, `final/binedges003/fit_variants003.sh`.
3. Selection: `final_search.txt`, then `final_select.py`.
4. BC and PPO: `snaps_qtcr.txt`, then `run_training.py --cqt-rule qtcr --suffix _qtcr --runs-suffix _qtcr2 --no-eval`
   (`retrain_bcppo_qtcr2.sh`).
5. Confirmatory block: `confirm_step0.txt`, `confirm_report.txt`, `confirm_bcppo_qtcr2.txt`, then `confirm_report.py`.
   The BC/PPO lines of `confirm_report.txt` point at earlier weights; the block's are in `confirm_bcppo_qtcr2.txt`.
6. Release-rate block: `make_shift_jobs.py`, `shift.cmd`, then `shift_report.py`.
7. Station: `theory/announced_station.py --grid`, `lowkappa.cmd`, `theory/announced_cells.py`.

A 360-day run takes 13 to 15 minutes on one core (i7-12700). The whole study is about 900 CPU-hours.

## Licence

MIT (`LICENSE`); the simulator and the data keep their own terms (`NOTICE`).
