# Bin-edge variants at beta 0.003, four sets of records, both scenarios (TASK A1, 2026-10-09)

Estimator: `fit_q.py --chain family --lam 0.003 --backoff --from-day 90 --fold fill` (n0 = K0 = 10, gamma 0.9/h),
exactly as `betarx/family/{FAB}_{KIND}_b0p003_t1.json`; only `--edges-tightest` / `--edges-nxt` change.
Records: `collect/{FAB}_{STEM}_s{100,101}.json`, days >= 90. Agreement = share of the KIND's own free decisions
on which the variant takes the reference fit's action (`table_agree.py`, each table looked up through its own edges).
Start limit per u column = the largest m edge below which every m bin starts (the lower edge of the first wait);
`clean` = the starts form an initial segment of the m bins. Violations are pair counts: m = a start at a larger
m bin above a wait in the same u column; u = a wait at a larger u bin beside a start in the same m row.
Own = cells where both actions reached n0 = 10 (the others carry the residual-only decision).

| variant | axis | interior edges (h) |
|---|---|---|
| ref | - | m: 0.25,0.5,1,2,4 / u: 0.25,1,3 |
| Rc | m | m: 0.5,1,2,4 |
| Rf | m | m: 0.25,0.5,0.75,1,1.5,2,3,4 |
| Rl | m | m: 0.1875,0.375,0.75,1.5,3 |
| Rh | m | m: 0.375,0.75,1.5,3,6 |
| Ac | u | u: 0.5,2 |
| Af | u | u: 0.25,0.5,1,2,3,6 |
| Al | u | u: 0.125,0.5,1.5 |
| Ah | u | u: 0.5,2,6 |

## HVLM timeout (records `HVLM_norev_p1_s100/101`, 85,339 free decisions; ref starts 3.65%, ref fit == paper artefact: True)

| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |
|---|---|---|---|---|---|---|---|
| ref | 100.00 | 3.65 | 13 | 22/24 | yes | [0,0.25): 0.5; [0.25,1): 1; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rc | 99.11 | 4.55 | 10 | 19/20 | NO | [0,0.25): 0.5 (SwSww); [0.25,1): 1; [1,3): 2; [3,all): 2 | 1 / 1 |
| Rf | 93.45 | 9.76 | 20 | 33/36 | NO | [0,0.25): 0.5; [0.25,1): 1 (SSSSwSSww); [1,3): 1.5; [3,all): 3 | 2 / 2 |
| Rl | 93.03 | 9.35 | 15 | 22/24 | NO | [0,0.25): 0.375; [0.25,1): 0.75 (SSSwSw); [1,3): 1.5; [3,all): 3 | 1 / 1 |
| Rh | 93.03 | 9.35 | 11 | 23/24 | NO | [0,0.25): 0.375; [0.25,1): 0.75 (SSwSww); [1,3): 1.5; [3,all): 3 | 1 / 1 |
| Ac | 98.85 | 4.08 | 10 | 17/18 | yes | [0,0.5): 0.5; [0.5,2): 2; [2,all): 2 | 0 / 0 |
| Af | 98.87 | 4.11 | 24 | 26/42 | yes | [0,0.25): 0.5; [0.25,0.5): 1; [0.5,1): 2; [1,2): 1; [2,3): 2; [3,6): 2; [6,all): 2 | 0 / 1 |
| Al | 98.85 | 4.08 | 12 | 23/24 | yes | [0,0.125): 0.5; [0.125,0.5): 0.5; [0.5,1.5): 2; [1.5,all): 2 | 0 / 0 |
| Ah | 98.85 | 4.08 | 14 | 17/24 | yes | [0,0.5): 0.5; [0.5,2): 2; [2,6): 2; [6,all): 2 | 0 / 0 |

Agreement over variants: min 93.03% (Rh), max 99.11% (Rc); m-axis variants mean 94.65% (min 93.03%), u-axis variants mean 98.85% (min 98.85%).

Largest disagreement, Rh vs ref, by reference cell (ref action -> variant action, n, % of free decisions, m range, u range):

- m [2,4) x u [0.25,1): wait -> start, n 2,841 (3.33%), m in [2.003, 3.000] h, u in [0.250, 0.995] h
- m [2,4) x u [3,all): wait -> start, n 1,823 (2.14%), m in [2.005, 3.000] h, u in [3.221, 24.000] h
- m [1,2) x u [0.25,1): wait -> start, n 740 (0.87%), m in [1.503, 2.000] h, u in [0.252, 1.000] h
- m [0.5,1) x u [0.25,1): start -> wait, n 262 (0.31%), m in [0.750, 1.000] h, u in [0.253, 0.998] h
- m [1,2) x u [1,3): start -> wait, n 188 (0.22%), m in [1.501, 1.997] h, u in [1.001, 2.986] h
- m [0.25,0.5) x u [0,0.25): start -> wait, n 92 (0.11%), m in [0.377, 0.498] h, u in [0.005, 0.231] h

Reference fire map (S = start, w = wait, * = residual-only entry):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S      |      S     
    [0.25,0.5) |      S      |      S      |      S*     |      S     
       [0.5,1) |      w      |      S      |      S      |      S     
         [1,2) |      w      |      w      |      S      |      S     
         [2,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w*     |      w     
```

Rc fire map (violations m 1, u 1):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
       [0,0.5) |      S      |      S      |      S      |      S     
       [0.5,1) |      w      |      S      |      S      |      S     
         [1,2) |      S      |      w      |      S      |      S     
         [2,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w*     |      w     
```

Rf fire map (violations m 2, u 2):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S      |      S     
    [0.25,0.5) |      S      |      S      |      S*     |      S     
    [0.5,0.75) |      w      |      S      |      S*     |      S     
      [0.75,1) |      w      |      S      |      S      |      S     
       [1,1.5) |      w      |      w      |      S      |      S     
       [1.5,2) |      w      |      S      |      w      |      S     
         [2,3) |      w      |      S      |      w      |      S     
         [3,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w*     |      w     
```

Rl fire map (violations m 1, u 1):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
    [0,0.1875) |      S      |      S      |      S*     |      S     
[0.1875,0.375) |      S      |      S      |      S*     |      S     
  [0.375,0.75) |      w      |      S      |      S      |      S     
    [0.75,1.5) |      w      |      w      |      S      |      S     
       [1.5,3) |      w      |      S      |      w      |      S     
       [3,all) |      w      |      w      |      w      |      w     
```

Rh fire map (violations m 1, u 1):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
     [0,0.375) |      S      |      S      |      S      |      S     
  [0.375,0.75) |      w      |      S      |      S      |      S     
    [0.75,1.5) |      w      |      w      |      S      |      S     
       [1.5,3) |      w      |      S      |      w      |      S     
         [3,6) |      w      |      w      |      w      |      w     
       [6,all) |      w      |      w      |      w*     |      w     
```

Af fire map (violations m 0, u 1):

```
         m \ u |   [0,0.25)  |  [0.25,0.5) |   [0.5,1)   |    [1,2)    |    [2,3)    |    [3,6)    |   [6,all)  
      [0,0.25) |      S      |      S      |      S      |      S*     |      S*     |      S*     |      S     
    [0.25,0.5) |      S      |      S      |      S      |      S*     |      S*     |      S*     |      S     
       [0.5,1) |      w      |      S      |      S      |      S      |      S*     |      S*     |      S     
         [1,2) |      w      |      w      |      S      |      w      |      S*     |      S*     |      S     
         [2,4) |      w      |      w      |      w      |      w      |      w*     |      w*     |      w     
       [4,all) |      w      |      w      |      w*     |      w*     |      w*     |      w*     |      w     
```

## HVLM mbs3 (records `HVLM_mbs3_p1_s100/101`, 84,960 free decisions; ref starts 11.58%, ref fit == paper artefact: True)

| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |
|---|---|---|---|---|---|---|---|
| ref | 100.00 | 11.58 | 13 | 22/24 | yes | [0,0.25): 0.25; [0.25,1): 2; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rc | 99.63 | 11.95 | 10 | 19/20 | yes | [0,0.25): 0.5; [0.25,1): 2; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rf | 91.76 | 17.25 | 20 | 34/36 | NO | [0,0.25): 0.25 (SwwwwSwww); [0.25,1): 1 (SSSSwSwww); [1,3): 1.5 (SSSSSwSww); [3,all): 3 | 6 / 2 |
| Rl | 90.38 | 20.77 | 15 | 22/24 | yes | [0,0.25): 0.1875; [0.25,1): 3; [1,3): 1.5; [3,all): 3 | 0 / 1 |
| Rh | 90.28 | 20.99 | 12 | 23/24 | yes | [0,0.25): 0.375; [0.25,1): 3; [1,3): 1.5; [3,all): 3 | 0 / 1 |
| Ac | 97.64 | 9.95 | 10 | 18/18 | yes | [0,0.5): 0.5; [0.5,2): 2; [2,all): 2 | 0 / 0 |
| Af | 98.01 | 9.58 | 23 | 26/42 | yes | [0,0.25): 0.25; [0.25,0.5): 0.5; [0.5,1): 2; [1,2): 2; [2,3): 2; [3,6): 2; [6,all): 2 | 0 / 0 |
| Al | 97.64 | 9.95 | 12 | 23/24 | yes | [0,0.125): 0.5; [0.125,0.5): 0.5; [0.5,1.5): 2; [1.5,all): 2 | 0 / 0 |
| Ah | 97.64 | 9.95 | 14 | 19/24 | yes | [0,0.5): 0.5; [0.5,2): 2; [2,6): 2; [6,all): 2 | 0 / 0 |

Agreement over variants: min 90.28% (Rh), max 99.63% (Rc); m-axis variants mean 93.01% (min 90.28%), u-axis variants mean 97.73% (min 97.64%).

Largest disagreement, Rh vs ref, by reference cell (ref action -> variant action, n, % of free decisions, m range, u range):

- m [2,4) x u [3,all): wait -> start, n 4,836 (5.69%), m in [2.001, 3.000] h, u in [3.282, 24.000] h
- m [2,4) x u [0.25,1): wait -> start, n 3,152 (3.71%), m in [2.001, 2.999] h, u in [0.250, 0.982] h
- m [0.25,0.5) x u [0,0.25): wait -> start, n 143 (0.17%), m in [0.251, 0.373] h, u in [0.004, 0.238] h
- m [1,2) x u [1,3): start -> wait, n 131 (0.15%), m in [1.521, 2.000] h, u in [1.004, 2.847] h

Reference fire map (S = start, w = wait, * = residual-only entry):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S*     |      S     
    [0.25,0.5) |      w      |      S      |      S      |      S     
       [0.5,1) |      w      |      S      |      S      |      S     
         [1,2) |      w      |      S      |      S      |      S     
         [2,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w*     |      w     
```

Rf fire map (violations m 6, u 2):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S*     |      S     
    [0.25,0.5) |      w      |      S      |      S      |      S     
    [0.5,0.75) |      w      |      S      |      S      |      S     
      [0.75,1) |      w      |      S      |      S      |      S     
       [1,1.5) |      w      |      w      |      S      |      S     
       [1.5,2) |      S      |      S      |      w      |      S     
         [2,3) |      w      |      w      |      S      |      S     
         [3,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w*     |      w     
```

Rl fire map (violations m 0, u 1):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
    [0,0.1875) |      S      |      S      |      S*     |      S     
[0.1875,0.375) |      w      |      S      |      S*     |      S     
  [0.375,0.75) |      w      |      S      |      S      |      S     
    [0.75,1.5) |      w      |      S      |      S      |      S     
       [1.5,3) |      w      |      S      |      w      |      S     
       [3,all) |      w      |      w      |      w      |      w     
```

Rh fire map (violations m 0, u 1):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
     [0,0.375) |      S      |      S      |      S      |      S     
  [0.375,0.75) |      w      |      S      |      S      |      S     
    [0.75,1.5) |      w      |      S      |      S      |      S     
       [1.5,3) |      w      |      S      |      w      |      S     
         [3,6) |      w      |      w      |      w      |      w     
       [6,all) |      w      |      w      |      w*     |      w     
```

## HVLM nach (records `HVLM_nach_p1_s100/101`, 70,805 free decisions; ref starts 16.69%, ref fit == paper artefact: True)

| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |
|---|---|---|---|---|---|---|---|
| ref | 100.00 | 16.69 | 16 | 2/24 | yes | [0,0.25): 2; [0.25,1): 2; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rc | 100.00 | 16.69 | 12 | 2/20 | yes | [0,0.25): 2; [0.25,1): 2; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rf | 93.35 | 10.05 | 16 | 2/36 | NO | [0,0.25): 0.5 (SSwSSwwww); [0.25,1): 0.5 (SSwSSwwww); [1,3): 0.5 (SSwSSwwww); [3,all): 0.5 (SSwSSwwww) | 8 / 0 |
| Rl | 92.30 | 8.99 | 12 | 2/24 | NO | [0,0.25): 0.375 (SSwSww); [0.25,1): 0.375 (SSwSww); [1,3): 0.375 (SSwSww); [3,all): 0.375 (SSwSww) | 4 / 0 |
| Rh | 92.30 | 8.99 | 8 | 2/24 | NO | [0,0.25): 0.375 (SwSwww); [0.25,1): 0.375 (SwSwww); [1,3): 0.375 (SwSwww); [3,all): 0.375 (SwSwww) | 4 / 0 |
| Ac | 100.00 | 16.69 | 12 | 2/18 | yes | [0,0.5): 2; [0.5,2): 2; [2,all): 2 | 0 / 0 |
| Af | 100.00 | 16.69 | 28 | 1/42 | yes | [0,0.25): 2; [0.25,0.5): 2; [0.5,1): 2; [1,2): 2; [2,3): 2; [3,6): 2; [6,all): 2 | 0 / 0 |
| Al | 99.70 | 16.39 | 14 | 5/24 | yes | [0,0.125): 2; [0.125,0.5): 2; [0.5,1.5): 2; [1.5,all): 0.5 | 0 / 6 |
| Ah | 100.00 | 16.69 | 16 | 1/24 | yes | [0,0.5): 2; [0.5,2): 2; [2,6): 2; [6,all): 2 | 0 / 0 |

Agreement over variants: min 92.30% (Rh), max 100.00% (Rc); m-axis variants mean 94.49% (min 92.30%), u-axis variants mean 99.93% (min 99.70%).

Largest disagreement, Rh vs ref, by reference cell (ref action -> variant action, n, % of free decisions, m range, u range):

- m [1,2) x u [0.25,1): start -> wait, n 1,840 (2.60%), m in [1.503, 1.999] h, u in [0.250, 0.993] h
- m [1,2) x u [0,0.25): start -> wait, n 1,123 (1.59%), m in [1.507, 1.999] h, u in [0.001, 0.249] h
- m [0.5,1) x u [0.25,1): start -> wait, n 718 (1.01%), m in [0.504, 0.748] h, u in [0.253, 0.962] h
- m [0.5,1) x u [0,0.25): start -> wait, n 412 (0.58%), m in [0.502, 0.746] h, u in [0.009, 0.243] h
- m [1,2) x u [1,3): start -> wait, n 383 (0.54%), m in [1.506, 1.995] h, u in [1.007, 2.702] h
- m [0.25,0.5) x u [0.25,1): start -> wait, n 361 (0.51%), m in [0.377, 0.499] h, u in [0.253, 0.960] h

Reference fire map (S = start, w = wait, * = residual-only entry):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S*     |      S*     |      S*     |      S*    
    [0.25,0.5) |      S*     |      S*     |      S*     |      S*    
       [0.5,1) |      S*     |      S*     |      S*     |      S*    
         [1,2) |      S*     |      S*     |      S      |      S*    
         [2,4) |      w*     |      w*     |      w      |      w*    
       [4,all) |      w*     |      w*     |      w*     |      w*    
```

Rf fire map (violations m 8, u 0):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S*     |      S*     |      S*     |      S*    
    [0.25,0.5) |      S*     |      S*     |      S*     |      S*    
    [0.5,0.75) |      w*     |      w*     |      w*     |      w*    
      [0.75,1) |      S*     |      S*     |      S*     |      S*    
       [1,1.5) |      S*     |      S*     |      S*     |      S*    
       [1.5,2) |      w*     |      w*     |      w*     |      w*    
         [2,3) |      w*     |      w*     |      w      |      w*    
         [3,4) |      w*     |      w*     |      w      |      w*    
       [4,all) |      w*     |      w*     |      w*     |      w*    
```

Rl fire map (violations m 4, u 0):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
    [0,0.1875) |      S*     |      S*     |      S*     |      S*    
[0.1875,0.375) |      S*     |      S*     |      S*     |      S*    
  [0.375,0.75) |      w*     |      w*     |      w*     |      w*    
    [0.75,1.5) |      S*     |      S*     |      S*     |      S*    
       [1.5,3) |      w*     |      w*     |      w      |      w*    
       [3,all) |      w*     |      w*     |      w      |      w*    
```

Rh fire map (violations m 4, u 0):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
     [0,0.375) |      S*     |      S*     |      S*     |      S*    
  [0.375,0.75) |      w*     |      w*     |      w*     |      w*    
    [0.75,1.5) |      S*     |      S*     |      S*     |      S*    
       [1.5,3) |      w*     |      w*     |      w      |      w*    
         [3,6) |      w*     |      w*     |      w      |      w*    
       [6,all) |      w*     |      w*     |      w*     |      w*    
```

Al fire map (violations m 0, u 6):

```
         m \ u |  [0,0.125)  | [0.125,0.5) |  [0.5,1.5)  |  [1.5,all) 
      [0,0.25) |      S*     |      S*     |      S*     |      S     
    [0.25,0.5) |      S*     |      S*     |      S*     |      S*    
       [0.5,1) |      S*     |      S*     |      S*     |      w     
         [1,2) |      S*     |      S*     |      S*     |      w     
         [2,4) |      w*     |      w*     |      w*     |      w     
       [4,all) |      w*     |      w*     |      w*     |      w     
```

## HVLM learner (records `HVLM_p1_s100/101`, 126,636 free decisions; ref starts 11.71%, ref fit == paper artefact: True)

| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |
|---|---|---|---|---|---|---|---|
| ref | 100.00 | 11.71 | 12 | 22/24 | yes | [0,0.25): 0.25; [0.25,1): 1; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rc | 99.55 | 12.17 | 9 | 20/20 | yes | [0,0.25): 0.5; [0.25,1): 1; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rf | 99.59 | 11.30 | 16 | 31/36 | yes | [0,0.25): 0.25; [0.25,1): 1; [1,3): 1.5; [3,all): 2 | 0 / 0 |
| Rl | 94.13 | 15.05 | 14 | 21/24 | yes | [0,0.25): 0.375; [0.25,1): 0.75; [1,3): 1.5; [3,all): 3 | 0 / 0 |
| Rh | 94.13 | 15.05 | 10 | 22/24 | yes | [0,0.25): 0.375; [0.25,1): 0.75; [1,3): 1.5; [3,all): 3 | 0 / 0 |
| Ac | 96.75 | 13.18 | 10 | 18/18 | yes | [0,0.5): 0.5; [0.5,2): 2; [2,all): 2 | 0 / 0 |
| Af | 99.11 | 10.82 | 22 | 25/42 | yes | [0,0.25): 0.25; [0.25,0.5): 0.5; [0.5,1): 1; [1,2): 2; [2,3): 2; [3,6): 2; [6,all): 2 | 0 / 0 |
| Al | 96.75 | 13.18 | 12 | 22/24 | yes | [0,0.125): 0.5; [0.125,0.5): 0.5; [0.5,1.5): 2; [1.5,all): 2 | 0 / 0 |
| Ah | 96.75 | 13.18 | 14 | 18/24 | yes | [0,0.5): 0.5; [0.5,2): 2; [2,6): 2; [6,all): 2 | 0 / 0 |

Agreement over variants: min 94.13% (Rh), max 99.59% (Rf); m-axis variants mean 96.85% (min 94.13%), u-axis variants mean 97.34% (min 96.75%).

Largest disagreement, Rh vs ref, by reference cell (ref action -> variant action, n, % of free decisions, m range, u range):

- m [2,4) x u [3,all): wait -> start, n 5,553 (4.39%), m in [2.000, 2.999] h, u in [3.050, 24.000] h
- m [0.5,1) x u [0.25,1): start -> wait, n 1,079 (0.85%), m in [0.750, 1.000] h, u in [0.250, 0.988] h
- m [1,2) x u [1,3): start -> wait, n 525 (0.41%), m in [1.507, 1.997] h, u in [1.015, 2.886] h
- m [0.25,0.5) x u [0,0.25): wait -> start, n 273 (0.22%), m in [0.251, 0.371] h, u in [0.007, 0.249] h

Reference fire map (S = start, w = wait, * = residual-only entry):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S*     |      S     
    [0.25,0.5) |      w      |      S      |      S*     |      S     
       [0.5,1) |      w      |      S      |      S      |      S     
         [1,2) |      w      |      w      |      S      |      S     
         [2,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w      |      w     
```

## LVHM timeout (records `LVHM_norev_p1_s100/101`, 51,371 free decisions; ref starts 11.16%, ref fit == paper artefact: True)

| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |
|---|---|---|---|---|---|---|---|
| ref | 100.00 | 11.16 | 13 | 22/24 | yes | [0,0.25): 0.25; [0.25,1): 2; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rc | 99.40 | 11.76 | 10 | 19/20 | yes | [0,0.25): 0.5; [0.25,1): 2; [1,3): 2; [3,all): 2 | 0 / 0 |
| Rf | 93.71 | 17.45 | 21 | 32/36 | NO | [0,0.25): 0.25 (SwwSwwwww); [0.25,1): 3; [1,3): 2; [3,all): 2 | 2 / 2 |
| Rl | 92.12 | 16.84 | 16 | 21/24 | yes | [0,0.25): 0.375; [0.25,1): 3; [1,3): 3; [3,all): 1.5 | 0 / 2 |
| Rh | 88.45 | 22.71 | 13 | 22/24 | yes | [0,0.25): 0.375; [0.25,1): 3; [1,3): 3; [3,all): 3 | 0 / 0 |
| Ac | 95.63 | 15.53 | 12 | 18/18 | yes | [0,0.5): 2; [0.5,2): 2; [2,all): 2 | 0 / 0 |
| Af | 97.78 | 8.94 | 24 | 28/42 | yes | [0,0.25): 0.25; [0.25,0.5): 1; [0.5,1): 2; [1,2): 2; [2,3): 2; [3,6): 2; [6,all): 2 | 0 / 0 |
| Al | 96.95 | 9.77 | 12 | 24/24 | yes | [0,0.125): 0.25; [0.125,0.5): 1; [0.5,1.5): 2; [1.5,all): 2 | 0 / 0 |
| Ah | 95.63 | 15.53 | 16 | 19/24 | yes | [0,0.5): 2; [0.5,2): 2; [2,6): 2; [6,all): 2 | 0 / 0 |

Agreement over variants: min 88.45% (Rh), max 99.40% (Rc); m-axis variants mean 93.42% (min 88.45%), u-axis variants mean 96.50% (min 95.63%).

Largest disagreement, Rh vs ref, by reference cell (ref action -> variant action, n, % of free decisions, m range, u range):

- m [2,4) x u [0.25,1): wait -> start, n 2,940 (5.72%), m in [2.001, 3.000] h, u in [0.250, 0.999] h
- m [2,4) x u [3,all): wait -> start, n 2,451 (4.77%), m in [2.001, 3.000] h, u in [3.207, 24.000] h
- m [2,4) x u [1,3): wait -> start, n 414 (0.81%), m in [2.005, 2.997] h, u in [1.000, 2.880] h
- m [0.25,0.5) x u [0,0.25): wait -> start, n 128 (0.25%), m in [0.250, 0.374] h, u in [0.001, 0.249] h

Reference fire map (S = start, w = wait, * = residual-only entry):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S      |      S     
    [0.25,0.5) |      w      |      S      |      S*     |      S     
       [0.5,1) |      w      |      S      |      S      |      S     
         [1,2) |      w      |      S      |      S      |      S     
         [2,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w*     |      w     
```

Rf fire map (violations m 2, u 2):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S      |      S     
    [0.25,0.5) |      w      |      S      |      S*     |      S     
    [0.5,0.75) |      w      |      S      |      S*     |      S     
      [0.75,1) |      S      |      S      |      S*     |      S     
       [1,1.5) |      w      |      S      |      S      |      S     
       [1.5,2) |      w      |      S      |      S      |      S     
         [2,3) |      w      |      S      |      w      |      w     
         [3,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w*     |      w     
```

Rl fire map (violations m 0, u 2):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
    [0,0.1875) |      S      |      S      |      S*     |      S     
[0.1875,0.375) |      S      |      S      |      S*     |      S     
  [0.375,0.75) |      w      |      S      |      S*     |      S     
    [0.75,1.5) |      w      |      S      |      S      |      S     
       [1.5,3) |      w      |      S      |      S      |      w     
       [3,all) |      w      |      w      |      w      |      w     
```

## LVHM mbs3 (records `LVHM_mbs3_p1_s100/101`, 65,412 free decisions; ref starts 17.73%, ref fit == paper artefact: True)

| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |
|---|---|---|---|---|---|---|---|
| ref | 100.00 | 17.73 | 13 | 23/24 | NO | [0,0.25): 0.5; [0.25,1): 2; [1,3): 0.5 (SSwSww); [3,all): 2 | 1 / 1 |
| Rc | 100.00 | 17.73 | 9 | 20/20 | NO | [0,0.25): 0.5; [0.25,1): 2; [1,3): 0.5 (SwSww); [3,all): 2 | 1 / 1 |
| Rf | 92.57 | 24.72 | 19 | 34/36 | NO | [0,0.25): 0.5; [0.25,1): 2; [1,3): 0.5 (SSwSwSwww); [3,all): 3 | 3 / 2 |
| Rl | 90.45 | 22.80 | 15 | 22/24 | yes | [0,0.25): 0.375; [0.25,1): 1.5; [1,3): 1.5; [3,all): 3 | 0 / 0 |
| Rh | 90.45 | 22.80 | 11 | 23/24 | yes | [0,0.25): 0.375; [0.25,1): 1.5; [1,3): 1.5; [3,all): 3 | 0 / 0 |
| Ac | 95.77 | 19.82 | 11 | 18/18 | NO | [0,0.5): 0.5 (SSwSww); [0.5,2): 2; [2,all): 2 | 1 / 0 |
| Af | 99.96 | 17.77 | 25 | 29/42 | NO | [0,0.25): 0.5; [0.25,0.5): 2; [0.5,1): 2; [1,2): 0.5 (SSwSww); [2,3): 2; [3,6): 2; [6,all): 2 | 1 / 2 |
| Al | 97.87 | 19.86 | 14 | 24/24 | yes | [0,0.125): 0.5; [0.125,0.5): 2; [0.5,1.5): 2; [1.5,all): 2 | 0 / 0 |
| Ah | 96.25 | 14.45 | 14 | 19/24 | yes | [0,0.5): 0.5; [0.5,2): 2; [2,6): 2; [6,all): 2 | 0 / 0 |

Agreement over variants: min 90.45% (Rh), max 100.00% (Rc); m-axis variants mean 93.37% (min 90.45%), u-axis variants mean 97.46% (min 95.77%).

Largest disagreement, Rh vs ref, by reference cell (ref action -> variant action, n, % of free decisions, m range, u range):

- m [2,4) x u [3,all): wait -> start, n 4,628 (7.08%), m in [2.000, 3.000] h, u in [3.270, 24.000] h
- m [1,2) x u [0.25,1): start -> wait, n 1,207 (1.85%), m in [1.502, 1.999] h, u in [0.251, 0.989] h
- m [0.5,1) x u [1,3): wait -> start, n 154 (0.24%), m in [0.512, 0.984] h, u in [1.002, 2.914] h
- m [0.25,0.5) x u [0,0.25): start -> wait, n 147 (0.22%), m in [0.375, 0.499] h, u in [0.003, 0.250] h
- m [1,2) x u [1,3): start -> wait, n 110 (0.17%), m in [1.520, 1.998] h, u in [1.015, 2.911] h

Reference fire map (S = start, w = wait, * = residual-only entry):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S      |      S     
    [0.25,0.5) |      S      |      S      |      S*     |      S     
       [0.5,1) |      w      |      S      |      w      |      S     
         [1,2) |      w      |      S      |      S      |      S     
         [2,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w      |      w     
```

Rc fire map (violations m 1, u 1):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
       [0,0.5) |      S      |      S      |      S      |      S     
       [0.5,1) |      w      |      S      |      w      |      S     
         [1,2) |      w      |      S      |      S      |      S     
         [2,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w      |      w     
```

Rf fire map (violations m 3, u 2):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S      |      S     
    [0.25,0.5) |      S      |      S      |      S*     |      S     
    [0.5,0.75) |      w      |      S      |      w      |      S     
      [0.75,1) |      w      |      S      |      S*     |      S     
       [1,1.5) |      w      |      S      |      w      |      S     
       [1.5,2) |      w      |      S      |      S      |      S     
         [2,3) |      w      |      w      |      w      |      S     
         [3,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w      |      w     
```

Ac fire map (violations m 1, u 0):

```
         m \ u |   [0,0.5)   |   [0.5,2)   |   [2,all)  
      [0,0.25) |      S      |      S      |      S     
    [0.25,0.5) |      S      |      S      |      S     
       [0.5,1) |      w      |      S      |      S     
         [1,2) |      S      |      S      |      S     
         [2,4) |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w     
```

Af fire map (violations m 1, u 2):

```
         m \ u |   [0,0.25)  |  [0.25,0.5) |   [0.5,1)   |    [1,2)    |    [2,3)    |    [3,6)    |   [6,all)  
      [0,0.25) |      S      |      S      |      S      |      S*     |      S*     |      S*     |      S     
    [0.25,0.5) |      S      |      S      |      S      |      S*     |      S*     |      S*     |      S     
       [0.5,1) |      w      |      S      |      S      |      w      |      S*     |      S*     |      S     
         [1,2) |      w      |      S      |      S      |      S      |      S*     |      S*     |      S     
         [2,4) |      w      |      w      |      w      |      w      |      w      |      w*     |      w     
       [4,all) |      w      |      w      |      w      |      w      |      w*     |      w*     |      w     
```

## LVHM nach (records `LVHM_nach_p1_s100/101`, 58,660 free decisions; ref starts 12.88%, ref fit == paper artefact: True)

| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |
|---|---|---|---|---|---|---|---|
| ref | 100.00 | 12.88 | 9 | 3/24 | NO | [0,0.25): 0.25 (SwSwww); [0.25,1): 0.25 (SwSwww); [1,3): 0.25 (SwSwww); [3,all): 0.25 (SwSSww) | 5 / 0 |
| Rc | 96.18 | 16.69 | 9 | 4/20 | yes | [0,0.25): 1; [0.25,1): 1; [1,3): 1; [3,all): 2 | 0 / 0 |
| Rf | 95.70 | 8.57 | 10 | 5/36 | NO | [0,0.25): 0.25 (SwSwwwwww); [0.25,1): 0.25 (SwSwwwwww); [1,3): 0.25 (SwSwwwwww); [3,all): 0.25 (SwSwSSwww) | 8 / 0 |
| Rl | 88.85 | 6.84 | 9 | 5/24 | NO | [0,0.25): 0.375; [0.25,1): 0.375; [1,3): 0.375; [3,all): 0.375 (SSwwSw) | 2 / 0 |
| Rh | 89.08 | 7.06 | 6 | 5/24 | NO | [0,0.25): 0.375; [0.25,1): 0.375; [1,3): 0.375; [3,all): 0.375 (SwSSww) | 2 / 0 |
| Ac | 99.97 | 12.90 | 7 | 4/18 | NO | [0,0.5): 0.25 (SwSwww); [0.5,2): 0.25 (SwSwww); [2,all): 0.25 (SwSSww) | 4 / 0 |
| Af | 97.29 | 14.83 | 15 | 3/42 | NO | [0,0.25): 0.25 (SwSwww); [0.25,0.5): 0.25 (SwSwww); [0.5,1): 0.25 (SwSwww); [1,2): 0.25 (SwSwSw); [2,3): 0.25 (SwSwww); [3,6): 0.25 (SwSwww); [6,all): 0.25 (SwSwww) | 9 / 3 |
| Al | 99.88 | 13.00 | 9 | 5/24 | NO | [0,0.125): 0.25 (SwSwww); [0.125,0.5): 0.25 (SwSwww); [0.5,1.5): 0.25 (SwSwww); [1.5,all): 0.25 (SwSSww) | 5 / 0 |
| Ah | 99.64 | 12.57 | 9 | 4/24 | NO | [0,0.5): 0.25 (SwSwww); [0.5,2): 0.25 (SwSwww); [2,6): 0.25 (SwSSww); [6,all): 0.25 (SwSwww) | 5 / 1 |

Agreement over variants: min 88.85% (Rl), max 99.97% (Ac); m-axis variants mean 92.45% (min 88.85%), u-axis variants mean 99.19% (min 97.29%).

Largest disagreement, Rl vs ref, by reference cell (ref action -> variant action, n, % of free decisions, m range, u range):

- m [0.5,1) x u [0.25,1): start -> wait, n 2,673 (4.56%), m in [0.500, 0.998] h, u in [0.250, 0.997] h
- m [0.5,1) x u [0,0.25): start -> wait, n 1,889 (3.22%), m in [0.501, 0.999] h, u in [0.000, 0.249] h
- m [0.25,0.5) x u [0.25,1): wait -> start, n 573 (0.98%), m in [0.250, 0.374] h, u in [0.250, 0.983] h
- m [2,4) x u [3,all): wait -> start, n 430 (0.73%), m in [2.003, 2.998] h, u in [3.095, 24.000] h
- m [0.25,0.5) x u [0,0.25): wait -> start, n 413 (0.70%), m in [0.251, 0.375] h, u in [0.002, 0.242] h
- m [0.5,1) x u [1,3): start -> wait, n 298 (0.51%), m in [0.500, 0.998] h, u in [1.005, 2.496] h

Reference fire map (S = start, w = wait, * = residual-only entry):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S*     |      S*     |      S*     |      S*    
    [0.25,0.5) |      w*     |      w*     |      w*     |      w*    
       [0.5,1) |      S*     |      S*     |      S*     |      S*    
         [1,2) |      w*     |      w*     |      w      |      S     
         [2,4) |      w*     |      w*     |      w      |      w*    
       [4,all) |      w*     |      w*     |      w*     |      w*    
```

Rf fire map (violations m 8, u 0):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S*     |      S*     |      S*     |      S*    
    [0.25,0.5) |      w*     |      w*     |      w*     |      w*    
    [0.5,0.75) |      S*     |      S*     |      S*     |      S*    
      [0.75,1) |      w*     |      w*     |      w*     |      w*    
       [1,1.5) |      w*     |      w*     |      w*     |      S     
       [1.5,2) |      w*     |      w*     |      w      |      S     
         [2,3) |      w*     |      w*     |      w      |      w*    
         [3,4) |      w*     |      w*     |      w      |      w*    
       [4,all) |      w*     |      w*     |      w*     |      w*    
```

Rl fire map (violations m 2, u 0):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
    [0,0.1875) |      S*     |      S*     |      S*     |      S*    
[0.1875,0.375) |      S*     |      S*     |      S*     |      S*    
  [0.375,0.75) |      w*     |      w*     |      w*     |      w*    
    [0.75,1.5) |      w*     |      w*     |      w      |      w     
       [1.5,3) |      w*     |      w*     |      w      |      S     
       [3,all) |      w*     |      w*     |      w      |      w*    
```

Rh fire map (violations m 2, u 0):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
     [0,0.375) |      S*     |      S*     |      S*     |      S*    
  [0.375,0.75) |      w*     |      w*     |      w*     |      w*    
    [0.75,1.5) |      w*     |      w*     |      w      |      S     
       [1.5,3) |      w*     |      w*     |      w      |      S     
         [3,6) |      w*     |      w*     |      w      |      w*    
       [6,all) |      w*     |      w*     |      w*     |      w*    
```

Ac fire map (violations m 4, u 0):

```
         m \ u |   [0,0.5)   |   [0.5,2)   |   [2,all)  
      [0,0.25) |      S*     |      S*     |      S*    
    [0.25,0.5) |      w*     |      w*     |      w*    
       [0.5,1) |      S*     |      S*     |      S*    
         [1,2) |      w*     |      w      |      S     
         [2,4) |      w*     |      w      |      w     
       [4,all) |      w*     |      w*     |      w*    
```

Af fire map (violations m 9, u 3):

```
         m \ u |   [0,0.25)  |  [0.25,0.5) |   [0.5,1)   |    [1,2)    |    [2,3)    |    [3,6)    |   [6,all)  
      [0,0.25) |      S*     |      S*     |      S*     |      S*     |      S*     |      S*     |      S*    
    [0.25,0.5) |      w*     |      w*     |      w*     |      w*     |      w*     |      w*     |      w*    
       [0.5,1) |      S*     |      S*     |      S*     |      S*     |      S*     |      S*     |      S*    
         [1,2) |      w*     |      w*     |      w*     |      w      |      w*     |      w*     |      w*    
         [2,4) |      w*     |      w*     |      w*     |      S      |      w      |      w*     |      w*    
       [4,all) |      w*     |      w*     |      w*     |      w*     |      w*     |      w*     |      w*    
```

Al fire map (violations m 5, u 0):

```
         m \ u |  [0,0.125)  | [0.125,0.5) |  [0.5,1.5)  |  [1.5,all) 
      [0,0.25) |      S*     |      S*     |      S*     |      S*    
    [0.25,0.5) |      w*     |      w*     |      w*     |      w*    
       [0.5,1) |      S*     |      S*     |      S*     |      S     
         [1,2) |      w*     |      w*     |      w*     |      S     
         [2,4) |      w*     |      w*     |      w      |      w     
       [4,all) |      w*     |      w*     |      w*     |      w     
```

Ah fire map (violations m 5, u 1):

```
         m \ u |   [0,0.5)   |   [0.5,2)   |    [2,6)    |   [6,all)  
      [0,0.25) |      S*     |      S*     |      S*     |      S*    
    [0.25,0.5) |      w*     |      w*     |      w*     |      w*    
       [0.5,1) |      S*     |      S*     |      S*     |      S*    
         [1,2) |      w*     |      w      |      S      |      w*    
         [2,4) |      w*     |      w      |      w      |      w*    
       [4,all) |      w*     |      w*     |      w*     |      w*    
```

## LVHM learner (records `LVHM_p1_s100/101`, 108,171 free decisions; ref starts 19.60%, ref fit == paper artefact: True)

| variant | agree % | start % | start cells | own/total | columns clean | start limit per u column (h) | viol m / u |
|---|---|---|---|---|---|---|---|
| ref | 100.00 | 19.60 | 11 | 22/24 | yes | [0,0.25): 0.25; [0.25,1): 1; [1,3): 1; [3,all): 2 | 0 / 0 |
| Rc | 99.04 | 20.56 | 8 | 20/20 | yes | [0,0.25): 0.5; [0.25,1): 1; [1,3): 1; [3,all): 2 | 0 / 0 |
| Rf | 97.97 | 18.49 | 15 | 32/36 | yes | [0,0.25): 0.25; [0.25,1): 0.75; [1,3): 1.5; [3,all): 2 | 0 / 0 |
| Rl | 94.73 | 15.25 | 12 | 21/24 | yes | [0,0.25): 0.1875; [0.25,1): 0.75; [1,3): 1.5; [3,all): 1.5 | 0 / 0 |
| Rh | 90.72 | 25.74 | 10 | 21/24 | yes | [0,0.25): 0.375; [0.25,1): 0.75; [1,3): 1.5; [3,all): 3 | 0 / 0 |
| Ac | 97.18 | 18.97 | 9 | 18/18 | yes | [0,0.5): 0.5; [0.5,2): 1; [2,all): 2 | 0 / 0 |
| Af | 98.14 | 18.02 | 21 | 24/42 | yes | [0,0.25): 0.25; [0.25,0.5): 0.5; [0.5,1): 1; [1,2): 1; [2,3): 2; [3,6): 2; [6,all): 2 | 0 / 0 |
| Al | 97.56 | 18.60 | 10 | 23/24 | yes | [0,0.125): 0.25; [0.125,0.5): 0.5; [0.5,1.5): 1; [1.5,all): 2 | 0 / 0 |
| Ah | 97.18 | 18.97 | 13 | 19/24 | yes | [0,0.5): 0.5; [0.5,2): 1; [2,6): 2; [6,all): 2 | 0 / 0 |

Agreement over variants: min 90.72% (Rh), max 99.04% (Rc); m-axis variants mean 95.62% (min 90.72%), u-axis variants mean 97.52% (min 97.18%).

Largest disagreement, Rh vs ref, by reference cell (ref action -> variant action, n, % of free decisions, m range, u range):

- m [2,4) x u [3,all): wait -> start, n 7,283 (6.73%), m in [2.001, 3.000] h, u in [3.019, 24.000] h
- m [0.5,1) x u [0.25,1): start -> wait, n 1,696 (1.57%), m in [0.750, 0.999] h, u in [0.252, 0.994] h
- m [0.25,0.5) x u [0,0.25): wait -> start, n 556 (0.51%), m in [0.256, 0.374] h, u in [0.000, 0.248] h
- m [1,2) x u [1,3): wait -> start, n 498 (0.46%), m in [1.007, 1.485] h, u in [1.000, 2.837] h

Reference fire map (S = start, w = wait, * = residual-only entry):

```
         m \ u |   [0,0.25)  |   [0.25,1)  |    [1,3)    |   [3,all)  
      [0,0.25) |      S      |      S      |      S*     |      S     
    [0.25,0.5) |      w      |      S      |      S*     |      S     
       [0.5,1) |      w      |      S      |      S      |      S     
         [1,2) |      w      |      w      |      w      |      S     
         [2,4) |      w      |      w      |      w      |      w     
       [4,all) |      w      |      w      |      w      |      w     
```

## Overall

- agreement over the 64 variant tables: min 88.45% (LVHM_timeout Rh), max 100.00% (LVHM_mbs3 Rc)
- below 99%: LVHM_timeout Rh 88.45%, LVHM_nach Rl 88.85%, LVHM_nach Rh 89.08%, HVLM_mbs3 Rh 90.28%, HVLM_mbs3 Rl 90.38%, LVHM_mbs3 Rh 90.45%, LVHM_mbs3 Rl 90.45%, LVHM_learner Rh 90.72%, HVLM_mbs3 Rf 91.76%, LVHM_timeout Rl 92.12%, HVLM_nach Rh 92.30%, HVLM_nach Rl 92.30%, LVHM_mbs3 Rf 92.57%, HVLM_timeout Rh 93.03%, HVLM_timeout Rl 93.03%, HVLM_nach Rf 93.35%, HVLM_timeout Rf 93.45%, LVHM_timeout Rf 93.71%, HVLM_learner Rh 94.13%, HVLM_learner Rl 94.13%, LVHM_learner Rl 94.73%, LVHM_timeout Ac 95.63%, LVHM_timeout Ah 95.63%, LVHM_nach Rf 95.70%, LVHM_mbs3 Ac 95.77%, LVHM_nach Rc 96.18%, LVHM_mbs3 Ah 96.25%, HVLM_learner Ac 96.75%, HVLM_learner Ah 96.75%, HVLM_learner Al 96.75%, LVHM_timeout Al 96.95%, LVHM_learner Ac 97.18%, LVHM_learner Ah 97.18%, LVHM_nach Af 97.29%, LVHM_learner Al 97.56%, HVLM_mbs3 Ac 97.64%, HVLM_mbs3 Ah 97.64%, HVLM_mbs3 Al 97.64%, LVHM_timeout Af 97.78%, LVHM_mbs3 Al 97.87%, LVHM_learner Rf 97.97%, HVLM_mbs3 Af 98.01%, LVHM_learner Af 98.14%, HVLM_timeout Ac 98.85%, HVLM_timeout Ah 98.85%, HVLM_timeout Al 98.85%, HVLM_timeout Af 98.87%
- mean agreement, m-axis variants 94.23%, u-axis variants 98.06%
- mean / min agreement by variant: Rc 99.11/96.18, Rf 94.76/91.76, Rl 92.00/88.85, Rh 91.06/88.45, Ac 97.72/95.63, Af 98.65/97.29, Al 98.15/96.75, Ah 97.74/95.63
- mean / min agreement by records: timeout 95.86/88.45, mbs3 95.39/90.28, nach 96.52/88.85, learner 96.83/90.72
- mean agreement by scenario: HVLM 96.61, LVHM 95.69
- ref fits equal to the paper artefacts (fire map): HVLM_timeout True, HVLM_mbs3 True, HVLM_nach True, HVLM_learner True, LVHM_timeout True, LVHM_mbs3 True, LVHM_nach True, LVHM_learner True
- wall time per fit (4 in parallel, shared machine): 12.8-38.3 s, mean 20.8 s over 72 fits
## Supplementary facts (extra003.py -> extra.json; records = the free decisions of each KIND, days >= 90)

Distribution of (m_min, u). The open interval u in [3, 24) holds 0.0-0.5% of the free decisions in every set of
records; the top u bin [3, 24.01) is in practice "no next arrival announced" (u = 24.0): HVLM timeout 29.7%, mbs3 42.6%,
nach 6.8%, p1 34.1%; LVHM timeout 36.4%, mbs3 45.1%, nach 9.2%, p1 37.6%. The u bin [1,3) holds 1.4-4.7%. Any u edge at
or above 3 h (Af: 3 and 6; Ah: 6) therefore makes near-empty bins, which is where Af's 13-18 residual-only cells of 42
and Ah's 5-7 of 24 come from (NACH apart). On the m axis the bins [2,4) and [4,24.01) hold 67-93% of the free decisions
(HVLM timeout 44.3 + 49.0%, mbs3 40.1 + 45.4%, nach 49.8 + 33.5%, p1 38.3 + 41.5%; LVHM timeout 46.4 + 38.1%, mbs3
40.5 + 37.5%, nach 43.4 + 23.3%, p1 39.8 + 27.0%); the four bins below 2 h, where every table's start region lies, hold
7-33%.

Where the m-axis sensitivity comes from. For the timeout and mbs3 records 72-98% of the disagreements of Rf, Rl and Rh
with the reference lie in the reference cells m [2,4) (wait -> start), and the decisions involved have m in [2, 3) h.
The recorded rule's own starts concentrate there: start rate at m in [2,3) vs [3,4) is 31.0% vs 1.8% (HVLM timeout),
27.3% vs 4.9% (LVHM timeout), 12.0% vs 9.6% (HVLM mbs3), 12.3% vs 9.8% (LVHM mbs3), against 2.0-2.2% vs 2.0-2.1% for the
p1 records. With the reference edges the pooled cell [2,4) waits (margin -0.009 to -0.128 lots); with an edge at 3 h the
cell [2,3) (Rf) or [1.5,3) (Rl, Rh) has a margin of +0.001 to +0.005 in one to two u columns and starts, while [3,4)
in the same columns keeps -0.013 to -0.109 (extra.json, rf_split). For the p1 records Rf agrees 99.59% (HVLM) / 97.97% (LVHM); Rl and Rh
move the p1 tables because neither has an edge at 2 h, so the reference threshold at m = 2 h in the no-arrival column
snaps to 3 h (HVLM both, LVHM Rh: 73-75% of the disagreement in ref m [2,4)) or to 1.5 h (LVHM Rl: start -> wait at
m in [1.5,2)).

The NACH records. NACH starts only when no arrival is announced: starts by reference u bin [0, 0, 57, 4825] (HVLM) and
[0, 0, 96, 5386] (LVHM), waits in the top u bin 9 and 22. Hence 21-22 of the 24 cells lack ten observations of one action
and the deployed NACH tables are the residual-only (m-only) table in 96.3-96.9% of the decisions (fit logs). The LVHM
residual-only decision is [1, 0, 1, 0, 0, 0] (margins in the no-arrival column +0.281, +0.0045, -0.0029, +0.0376,
-0.0375, -0.0459), so the paper's LVHM NACH table is not monotone in m (5 pair violations, 4 of 4 columns). The NACH
variants Rf, Rl and Rh agree 88.85-95.70% (Rc 100% on HVLM, 96.18% on LVHM) because the m-only decision is re-estimated
from 25-224 starts per bin below 2 h (starts by reference m bin HVLM [33, 25, 48, 122, 1329, 3325], LVHM
[39, 51, 100, 224, 1513, 3555]).

The paper's reference tables. HVLM timeout, HVLM mbs3, HVLM NACH, HVLM p1, LVHM timeout and LVHM p1 are clean thresholds
in every u column with 0 violations. LVHM mbs3 is not: at u [1,3) the column reads S S w S w w (the wait cell m [0.5,1)
has 20 fired / 134 waited, margin -0.072; the start cell m [1,2) 41 / 213, margin +0.005). LVHM NACH is as above.

Comparison with the beta 0.01 study of 2026-10-02 (binedges/, p1 records only): the reference p1 tables are identical at
the two prices on both scenarios (fire maps equal), the variant tables are not (HVLM: only Rc equal; LVHM: Rc, Ac, Al
equal), and the agreements differ accordingly (e.g. HVLM Rf 98.73% at 0.01 vs 99.59% at 0.003, Rh 96.58% vs 94.13%;
LVHM Rh 94.68% vs 90.72%).

Wall time: one fit 12.8-38.3 s (mean 20.8 s over 72 fits, four in parallel on the shared machine: timeout records
12.8-25.2 s, mbs3 14.9-18.9 s, nach 13.2-15.9 s, the larger p1 records 27.3-38.3 s); the whole batch 6 min 19 s
(21:39:58 to 21:46:17).
