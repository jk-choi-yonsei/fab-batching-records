@echo off
set "RL=%USERPROFILE%\miniconda3\envs\RL"
set "PATH=%RL%;%RL%\Library\mingw-w64\bin;%RL%\Library\usr\bin;%RL%\Library\bin;%RL%\Scripts;%RL%\bin;%PATH%"
set OMP_NUM_THREADS=1
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
cd /d "%~dp0..\..\..\fabhybrid\smt2020\theory"
"%RL%\python.exe" announced_lowkappa.py 12 4 0.1 ../../../experiments/smt2020/theory/announced_kappa0p1_R12_L4.json > ../../../experiments/smt2020/theory/announced_kappa0p1_R12_L4.log 2>&1
