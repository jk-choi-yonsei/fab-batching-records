@echo off
rem written by fabhybrid/smt2020/make_shift_jobs.py: PROTOCOL_shift.md
set "RL=%USERPROFILE%\miniconda3\envs\RL"
set "PATH=%RL%;%RL%\Library\mingw-w64\bin;%RL%\Library\usr\bin;%RL%\Library\bin;%RL%\Scripts;%RL%\bin;%PATH%"
set OMP_NUM_THREADS=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0..\..\..\fabhybrid\smt2020"
set "J=../../experiments/smt2020/jobs"
set "PY=%RL%\python.exe"
"%PY%" make_shift_jobs.py --prelaunch >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_step0.txt --parallel 2 --done-marker ../../experiments/smt2020/jobs/shift_step0.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" make_shift_jobs.py --check-step0 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p90_a.txt --parallel 14 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p90_a.txt --parallel 14 --done-marker ../../experiments/smt2020/jobs/shift_r0p90_a.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p90_fit.txt --parallel 6 --done-marker ../../experiments/smt2020/jobs/shift_r0p90_fit.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" make_shift_jobs.py --stage-b 0.9 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p90_b.txt --parallel 14 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p90_b.txt --parallel 14 --done-marker ../../experiments/smt2020/jobs/shift_r0p90_b.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p80_a.txt --parallel 14 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p80_a.txt --parallel 14 --done-marker ../../experiments/smt2020/jobs/shift_r0p80_a.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p80_fit.txt --parallel 6 --done-marker ../../experiments/smt2020/jobs/shift_r0p80_fit.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" make_shift_jobs.py --stage-b 0.8 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p80_b.txt --parallel 14 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r0p80_b.txt --parallel 14 --done-marker ../../experiments/smt2020/jobs/shift_r0p80_b.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_probe.txt --parallel 4 --done-marker ../../experiments/smt2020/jobs/shift_probe.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" make_shift_jobs.py --gate-high >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r1p05_a.txt --parallel 14 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r1p05_a.txt --parallel 14 --done-marker ../../experiments/smt2020/jobs/shift_r1p05_a.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r1p05_fit.txt --parallel 6 --done-marker ../../experiments/smt2020/jobs/shift_r1p05_fit.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" make_shift_jobs.py --stage-b 1.05 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r1p05_b.txt --parallel 14 >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" run_queue.py ../../experiments/smt2020/jobs/shift_r1p05_b.txt --parallel 14 --done-marker ../../experiments/smt2020/jobs/shift_r1p05_b.done >> %J%/shift.out 2>&1 || exit /b 1
"%PY%" make_shift_jobs.py --check-step0 >> %J%/shift.out 2>&1 || exit /b 1
