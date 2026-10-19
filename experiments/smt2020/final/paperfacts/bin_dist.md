# Distribution of m_min and u in the records against the bin edges

Free decisions of days >= 90, seeds 100 and 101, per record set (fab x rule). m_min = tightest live residual (h), u = hours to the next announced arrival (24.0 = none announced). Started iff act < n_groups. Bins are [a, b) as fit_q.cell reads them; the last u bin [3, inf) holds u = 24.0.

Reference edges: m_min 0.25 / 0.5 / 1 / 2 / 4 h; u 0.25 / 1 / 3 h.

## HVLM_timeout

Files: collect/HVLM_norev_p1_s100.json, collect/HVLM_norev_p1_s101.json. Free decisions 85,339, started 5,253 (6.16%). Diffusion_BE_123: 48,877/2,910; Diffusion_FE_120: 21,987/900; Diffusion_FE_94: 14,475/1,443

### m_min (tightest residual)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 655 | 0.8% | 79 | 12.1% | 1.5% |
| [0.25,0.5) | 586 | 0.7% | 96 | 16.4% | 1.8% |
| [0.5,1) | 1,284 | 1.5% | 180 | 14.0% | 3.4% |
| [1,2) | 3,162 | 3.7% | 499 | 15.8% | 9.5% |
| [2,4) | 37,810 | 44.3% | 2,785 | 7.4% | 53.0% |
| [4,inf) | 41,842 | 49.0% | 1,614 | 3.9% | 30.7% |

Sextiles (edges a six-bin quantile binning would use): 3.050, 3.482, 3.972, 9.152, 9.719 h.
Percentiles of m_min: p25 3.250, p50 3.972, p75 9.474, p90 9.965, p99 10.000; min 0.000, max 10.000, mean 5.627 h.
Share with m_min < 0.5 h 1.5%, < 1 h 3.0%, < 2 h 6.7%, < 4 h 51.0%.
Among starts: median m_min 2.913 h; share of starts with m_min < 2 h 16.3%, < 4 h 69.3%.
Atoms at the limits (m_min exactly 4, 8, 10 h): 4 h: 7,725, 8 h: 0, 10 h: 7,819. Share of free decisions / of starts by band: [3,4) 35.8% / 10.3%; [4,4.5) 11.2% / 4.2%; [4.5,7) 0.0% / 0.1%; [7,8) 0.0% / 0.8%; [8,9) 1.6% / 25.7%; [9,10] 36.2% / 0.0%.

Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 655 | 79 |
| 0.25 | 586 | 96 |
| 0.5 | 588 | 86 |
| 0.75 | 696 | 94 |
| 1.0 | 735 | 104 |
| 1.25 | 682 | 113 |
| 1.5 | 839 | 118 |
| 1.75 | 906 | 164 |
| 2.0 | 1,175 | 197 |
| 2.25 | 1,250 | 316 |
| 2.5 | 1,870 | 583 |
| 2.75 | 2,961 | 1,150 |
| 3.0 | 8,399 | 213 |
| 3.25 | 7,580 | 140 |
| 3.5 | 7,384 | 107 |
| 3.75 | 7,191 | 79 |
| 4.0 | 9,153 | 197 |
| 4.25 | 442 | 22 |
| 4.5 | 0 | 0 |
| 4.75 | 0 | 0 |
| 5.0 | 1 | 1 |
| 5.25 | 1 | 1 |
| 5.5 | 0 | 0 |
| 5.75 | 0 | 0 |
| 6.0 | 1 | 1 |
| 6.25 | 0 | 0 |
| 6.5 | 0 | 0 |
| 6.75 | 2 | 2 |
| 7.0 | 4 | 4 |
| 7.25 | 3 | 3 |
| 7.5 | 12 | 12 |
| 7.75 | 22 | 22 |
| 8.0 | 38 | 38 |
| 8.25 | 131 | 131 |
| 8.5 | 320 | 320 |
| 8.75 | 860 | 860 |
| 9.0 | 4,214 | 0 |
| 9.25 | 5,873 | 0 |
| 9.5 | 7,228 | 0 |
| 9.75 | 5,710 | 0 |
| 10.0 | 7,827 | 0 |

### u (time to the next announced arrival)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 31,198 | 36.6% | 1,733 | 5.6% | 33.0% |
| [0.25,1) | 27,024 | 31.7% | 1,576 | 5.8% | 30.0% |
| [1,3) | 1,763 | 2.1% | 151 | 8.6% | 2.9% |
| [3,inf) | 25,354 | 29.7% | 1,793 | 7.1% | 34.1% |

u = 24.0 (none announced): 25,339 (29.7%), start rate there 7.05%; 3 <= u < 24: 15 (0.02%); u < 24: 60,000 (70.3%), start rate there 5.78%.
Quartiles of u among u < 24: p25 0.114, p50 0.239, p75 0.375 h; p99 1.308; max below 24: 4.065 h. Share with u = 0 exactly: 0.00%.

0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 16,341 | 978 |
| 0.125 | 14,857 | 755 |
| 0.25 | 13,764 | 615 |
| 0.375 | 5,508 | 369 |
| 0.5 | 2,929 | 208 |
| 0.625 | 2,180 | 161 |
| 0.75 | 1,805 | 144 |
| 0.875 | 838 | 79 |
| 1.0 | 527 | 51 |
| 1.125 | 460 | 26 |
| 1.25 | 301 | 23 |
| 1.375 | 170 | 20 |
| 1.5 | 117 | 9 |
| 1.625 | 24 | 1 |
| 1.75 | 35 | 4 |
| 1.875 | 28 | 3 |
| 2.0 | 32 | 3 |
| 2.125 | 12 | 0 |
| 2.25 | 13 | 2 |
| 2.375 | 23 | 0 |
| 2.5 | 3 | 1 |
| 2.625 | 2 | 2 |
| 2.75 | 5 | 3 |
| 2.875 | 11 | 3 |
| 3.0 | 25,354 | 1,793 |

### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10

| m_min \ u | [0,0.25) | [0.25,1) | [1,3) | [3,inf) |
|---|---:|---:|---:|---:|
| [0,0.25) | 181 / 22 | 260 / 29 | 84 / 11 | 130 / 17 |
| [0.25,0.5) | 181 / 30 | 258 / 38 | 66 / 8 (thin) | 81 / 20 |
| [0.5,1) | 369 / 55 | 522 / 64 | 166 / 20 | 227 / 41 |
| [1,2) | 763 / 140 | 1,439 / 163 | 300 / 41 | 660 / 155 |
| [2,4) | 12,623 / 884 | 15,510 / 1,059 | 862 / 69 | 8,815 / 773 |
| [4,inf) | 17,081 / 602 | 9,035 / 223 | 285 / 2 (thin) | 15,441 / 787 |

Cells with >= 10 of each action: 22 of 24; artefact own_entry: 22 of 24 (match). Artefact betarx/family/HVLM_timeout_b0p003_t1.json: sum n_fired 5,253, n_waited 80,085; total absolute difference from the record counts 1 decisions (chain ends dropped by fit_q.chains).
Artefact fire table (1 = start): [[1, 1, 1, 1], [1, 1, 1, 1], [0, 1, 1, 1], [0, 0, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]; residual-only back-off [1, 1, 1, 1, 0, 0]. Share of the rule's starts that lie in the table's start cells: 9.4%; share of free decisions in those cells: 3.7%.

### Load size at free decisions

| size | free | starts | start rate |
|---:|---:|---:|---:|
| 1 | 27,377 | 757 | 2.8% |
| 2 | 29,751 | 1,694 | 5.7% |
| 3 | 23,325 | 2,056 | 8.8% |
| 4 | 4,442 | 627 | 14.1% |
| 5 | 444 | 119 | 26.8% |

Share with size >= 3: 33.1%; start rate at size >= 3 9.93%, at size < 3 4.29%.

Start rate by size within each m_min bin (n in parentheses):

| m_min bin | size 1 | size 2 | size 3 | size 4 | size 5 |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 3% (199) | 13% (223) | 21% (148) | 15% (61) | 21% (24) |
| [0.25,0.5) | 7% (163) | 19% (182) | 16% (159) | 21% (73) | 89% (9) |
| [0.5,1) | 7% (278) | 14% (434) | 16% (418) | 23% (110) | 25% (44) |
| [1,2) | 9% (787) | 14% (1,273) | 19% (762) | 24% (230) | 39% (110) |
| [2,4) | 4% (6,296) | 6% (15,214) | 9% (12,203) | 13% (3,884) | 23% (213) |
| [4,inf) | 2% (19,654) | 4% (12,425) | 7% (9,635) | 12% (84) | 5% (44) |

## HVLM_mbs3

Files: collect/HVLM_mbs3_p1_s100.json, collect/HVLM_mbs3_p1_s101.json. Free decisions 84,960, started 7,900 (9.30%). Diffusion_BE_123: 49,652/4,046; Diffusion_FE_120: 18,768/2,401; Diffusion_FE_94: 16,540/1,453

### m_min (tightest residual)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 1,190 | 1.4% | 106 | 8.9% | 1.3% |
| [0.25,0.5) | 1,252 | 1.5% | 128 | 10.2% | 1.6% |
| [0.5,1) | 2,987 | 3.5% | 301 | 10.1% | 3.8% |
| [1,2) | 6,899 | 8.1% | 716 | 10.4% | 9.1% |
| [2,4) | 34,089 | 40.1% | 3,537 | 10.4% | 44.8% |
| [4,inf) | 38,543 | 45.4% | 3,112 | 8.1% | 39.4% |

Sextiles (edges a six-bin quantile binning would use): 2.183, 3.243, 3.849, 5.353, 9.560 h.
Percentiles of m_min: p25 2.829, p50 3.849, p75 8.942, p90 9.832, p99 10.000; min 0.000, max 10.000, mean 4.997 h.
Share with m_min < 0.5 h 2.9%, < 1 h 6.4%, < 2 h 14.5%, < 4 h 54.6%.
Among starts: median m_min 3.524 h; share of starts with m_min < 2 h 15.8%, < 4 h 60.6%.
Atoms at the limits (m_min exactly 4, 8, 10 h): 4 h: 7,335, 8 h: 0, 10 h: 5,311. Share of free decisions / of starts by band: [3,4) 26.8% / 27.7%; [4,4.5) 11.4% / 0.4%; [4.5,7) 2.8% / 1.4%; [7,8) 2.0% / 1.7%; [8,9) 4.7% / 8.1%; [9,10] 24.5% / 27.8%.

Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 1,190 | 106 |
| 0.25 | 1,252 | 128 |
| 0.5 | 1,500 | 146 |
| 0.75 | 1,487 | 155 |
| 1.0 | 1,601 | 156 |
| 1.25 | 1,591 | 164 |
| 1.5 | 1,878 | 199 |
| 1.75 | 1,829 | 197 |
| 2.0 | 2,381 | 250 |
| 2.25 | 2,534 | 276 |
| 2.5 | 2,983 | 381 |
| 2.75 | 3,398 | 445 |
| 3.0 | 4,872 | 699 |
| 3.25 | 4,977 | 591 |
| 3.5 | 6,441 | 541 |
| 3.75 | 6,503 | 354 |
| 4.0 | 8,971 | 27 |
| 4.25 | 710 | 6 |
| 4.5 | 167 | 3 |
| 4.75 | 162 | 10 |
| 5.0 | 143 | 5 |
| 5.25 | 188 | 12 |
| 5.5 | 269 | 15 |
| 5.75 | 222 | 10 |
| 6.0 | 314 | 17 |
| 6.25 | 266 | 9 |
| 6.5 | 330 | 10 |
| 6.75 | 310 | 19 |
| 7.0 | 353 | 25 |
| 7.25 | 356 | 24 |
| 7.5 | 389 | 32 |
| 7.75 | 616 | 57 |
| 8.0 | 700 | 70 |
| 8.25 | 721 | 74 |
| 8.5 | 957 | 164 |
| 8.75 | 1,590 | 328 |
| 9.0 | 2,048 | 515 |
| 9.25 | 3,542 | 846 |
| 9.5 | 5,117 | 694 |
| 9.75 | 4,779 | 140 |
| 10.0 | 5,323 | 0 |

### u (time to the next announced arrival)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 25,485 | 30.0% | 2,824 | 11.1% | 35.7% |
| [0.25,1) | 22,064 | 26.0% | 2,595 | 11.8% | 32.8% |
| [1,3) | 1,208 | 1.4% | 176 | 14.6% | 2.2% |
| [3,inf) | 36,203 | 42.6% | 2,305 | 6.4% | 29.2% |

u = 24.0 (none announced): 36,155 (42.6%), start rate there 6.37%; 3 <= u < 24: 48 (0.06%); u < 24: 48,805 (57.4%), start rate there 11.47%.
Quartiles of u among u < 24: p25 0.112, p50 0.237, p75 0.374 h; p99 1.293; max below 24: 4.026 h. Share with u = 0 exactly: 0.00%.

0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 13,567 | 1,461 |
| 0.125 | 11,918 | 1,363 |
| 0.25 | 11,181 | 1,341 |
| 0.375 | 4,840 | 523 |
| 0.5 | 2,069 | 290 |
| 0.625 | 1,665 | 204 |
| 0.75 | 1,529 | 175 |
| 0.875 | 780 | 62 |
| 1.0 | 288 | 37 |
| 1.125 | 380 | 51 |
| 1.25 | 188 | 31 |
| 1.375 | 96 | 17 |
| 1.5 | 66 | 12 |
| 1.625 | 29 | 5 |
| 1.75 | 19 | 5 |
| 1.875 | 18 | 4 |
| 2.0 | 13 | 1 |
| 2.125 | 9 | 4 |
| 2.25 | 28 | 1 |
| 2.375 | 12 | 2 |
| 2.5 | 7 | 2 |
| 2.625 | 28 | 2 |
| 2.75 | 25 | 2 |
| 2.875 | 2 | 0 |
| 3.0 | 36,203 | 2,305 |

### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10

| m_min \ u | [0,0.25) | [0.25,1) | [1,3) | [3,inf) |
|---|---:|---:|---:|---:|
| [0,0.25) | 233 / 29 | 327 / 54 | 49 / 7 (thin) | 581 / 16 |
| [0.25,0.5) | 314 / 33 | 383 / 55 | 27 / 10 | 528 / 30 |
| [0.5,1) | 673 / 99 | 720 / 113 | 109 / 23 | 1,485 / 66 |
| [1,2) | 1,505 / 197 | 2,013 / 293 | 266 / 44 | 3,115 / 182 |
| [2,4) | 9,510 / 1,133 | 11,187 / 1,503 | 537 / 90 | 12,855 / 811 |
| [4,inf) | 13,250 / 1,333 | 7,434 / 577 | 220 / 2 (thin) | 17,639 / 1,200 |

Cells with >= 10 of each action: 22 of 24; artefact own_entry: 22 of 24 (match). Artefact betarx/family/HVLM_mbs3_b0p003_t1.json: sum n_fired 7,899, n_waited 77,058; total absolute difference from the record counts 3 decisions (chain ends dropped by fit_q.chains).
Artefact fire table (1 = start): [[1, 1, 1, 1], [0, 1, 1, 1], [0, 1, 1, 1], [0, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]; residual-only back-off [1, 1, 1, 1, 0, 0]. Share of the rule's starts that lie in the table's start cells: 11.7%; share of free decisions in those cells: 11.6%.

### Load size at free decisions

| size | free | starts | start rate |
|---:|---:|---:|---:|
| 1 | 26,557 | 0 | 0.0% |
| 2 | 50,503 | 0 | 0.0% |
| 3 | 7,712 | 7,712 | 100.0% |
| 4 | 170 | 170 | 100.0% |
| 5 | 18 | 18 | 100.0% |

Share with size >= 3: 9.3%; start rate at size >= 3 100.00%, at size < 3 0.00%.

Start rate by size within each m_min bin (n in parentheses):

| m_min bin | size 1 | size 2 | size 3 | size 4 | size 5 |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 0% (250) | 0% (834) | 100% (96) | 100% (9) | 100% (1) |
| [0.25,0.5) | 0% (263) | 0% (861) | 100% (124) | 100% (4) | - |
| [0.5,1) | 0% (487) | 0% (2,199) | 100% (274) | 100% (21) | 100% (6) |
| [1,2) | 0% (1,130) | 0% (5,053) | 100% (674) | 100% (36) | 100% (6) |
| [2,4) | 0% (6,834) | 0% (23,718) | 100% (3,436) | 100% (96) | 100% (5) |
| [4,inf) | 0% (17,593) | 0% (17,838) | 100% (3,108) | 100% (4) | - |

## HVLM_nach

Files: collect/HVLM_nach_p1_s100.json, collect/HVLM_nach_p1_s101.json. Free decisions 70,805, started 4,882 (6.89%). Diffusion_BE_123: 39,511/2,854; Diffusion_FE_120: 5,097/1,494; Diffusion_FE_94: 26,197/534

### m_min (tightest residual)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 1,369 | 1.9% | 33 | 2.4% | 0.7% |
| [0.25,0.5) | 1,432 | 2.0% | 25 | 1.7% | 0.5% |
| [0.5,1) | 2,880 | 4.1% | 48 | 1.7% | 1.0% |
| [1,2) | 6,138 | 8.7% | 122 | 2.0% | 2.5% |
| [2,4) | 35,250 | 49.8% | 1,329 | 3.8% | 27.2% |
| [4,inf) | 23,736 | 33.5% | 3,325 | 14.0% | 68.1% |

Sextiles (edges a six-bin quantile binning would use): 1.996, 2.947, 3.478, 4.000, 9.481 h.
Percentiles of m_min: p25 2.576, p50 3.478, p75 4.042, p90 9.765, p99 10.000; min 0.000, max 10.000, mean 4.330 h.
Share with m_min < 0.5 h 4.0%, < 1 h 8.0%, < 2 h 16.7%, < 4 h 66.5%.
Among starts: median m_min 9.315 h; share of starts with m_min < 2 h 4.7%, < 4 h 31.9%.
Atoms at the limits (m_min exactly 4, 8, 10 h): 4 h: 5,715, 8 h: 0, 10 h: 3,975. Share of free decisions / of starts by band: [3,4) 32.0% / 19.9%; [4,4.5) 11.9% / 9.4%; [4.5,7) 0.0% / 0.0%; [7,8) 0.0% / 0.1%; [8,9) 0.8% / 2.9%; [9,10] 20.9% / 55.6%.

Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 1,369 | 33 |
| 0.25 | 1,432 | 25 |
| 0.5 | 1,279 | 16 |
| 0.75 | 1,601 | 32 |
| 1.0 | 1,268 | 24 |
| 1.25 | 1,443 | 18 |
| 1.5 | 1,531 | 34 |
| 1.75 | 1,896 | 46 |
| 2.0 | 2,268 | 68 |
| 2.25 | 2,681 | 77 |
| 2.5 | 3,435 | 101 |
| 2.75 | 4,209 | 113 |
| 3.0 | 6,063 | 186 |
| 3.25 | 5,348 | 198 |
| 3.5 | 5,677 | 252 |
| 3.75 | 5,569 | 334 |
| 4.0 | 7,432 | 443 |
| 4.25 | 967 | 18 |
| 4.5 | 0 | 0 |
| 4.75 | 0 | 0 |
| 5.0 | 0 | 0 |
| 5.25 | 0 | 0 |
| 5.5 | 0 | 0 |
| 5.75 | 0 | 0 |
| 6.0 | 0 | 0 |
| 6.25 | 0 | 0 |
| 6.5 | 1 | 1 |
| 6.75 | 0 | 0 |
| 7.0 | 0 | 0 |
| 7.25 | 2 | 2 |
| 7.5 | 3 | 2 |
| 7.75 | 2 | 2 |
| 8.0 | 10 | 0 |
| 8.25 | 44 | 15 |
| 8.5 | 162 | 35 |
| 8.75 | 342 | 92 |
| 9.0 | 897 | 188 |
| 9.25 | 2,282 | 424 |
| 9.5 | 4,320 | 734 |
| 9.75 | 3,295 | 598 |
| 10.0 | 3,977 | 771 |

### u (time to the next announced arrival)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 29,573 | 41.8% | 0 | 0.0% | 0.0% |
| [0.25,1) | 33,134 | 46.8% | 0 | 0.0% | 0.0% |
| [1,3) | 3,264 | 4.6% | 57 | 1.7% | 1.2% |
| [3,inf) | 4,834 | 6.8% | 4,825 | 99.8% | 98.8% |

u = 24.0 (none announced): 4,814 (6.8%), start rate there 100.00%; 3 <= u < 24: 20 (0.03%); u < 24: 65,991 (93.2%), start rate there 0.10%.
Quartiles of u among u < 24: p25 0.131, p50 0.284, p75 0.471 h; p99 1.342; max below 24: 3.977 h. Share with u = 0 exactly: 0.00%.

0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 15,816 | 0 |
| 0.125 | 13,757 | 0 |
| 0.25 | 13,633 | 0 |
| 0.375 | 7,511 | 0 |
| 0.5 | 4,319 | 0 |
| 0.625 | 3,459 | 0 |
| 0.75 | 2,727 | 0 |
| 0.875 | 1,485 | 0 |
| 1.0 | 1,275 | 0 |
| 1.125 | 892 | 0 |
| 1.25 | 526 | 7 |
| 1.375 | 280 | 4 |
| 1.5 | 120 | 9 |
| 1.625 | 73 | 3 |
| 1.75 | 26 | 2 |
| 1.875 | 15 | 2 |
| 2.0 | 19 | 7 |
| 2.125 | 15 | 8 |
| 2.25 | 3 | 3 |
| 2.375 | 1 | 1 |
| 2.5 | 0 | 0 |
| 2.625 | 12 | 4 |
| 2.75 | 4 | 4 |
| 2.875 | 3 | 3 |
| 3.0 | 4,834 | 4,825 |

### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10

| m_min \ u | [0,0.25) | [0.25,1) | [1,3) | [3,inf) |
|---|---:|---:|---:|---:|
| [0,0.25) | 389 / 0 (thin) | 777 / 0 (thin) | 174 / 4 (thin) | 29 / 29 (thin) |
| [0.25,0.5) | 431 / 0 (thin) | 780 / 0 (thin) | 199 / 3 (thin) | 22 / 22 (thin) |
| [0.5,1) | 1,014 / 0 (thin) | 1,545 / 0 (thin) | 277 / 4 (thin) | 44 / 44 (thin) |
| [1,2) | 1,953 / 0 (thin) | 3,394 / 0 (thin) | 673 / 13 | 118 / 109 (thin) |
| [2,4) | 13,993 / 0 (thin) | 18,432 / 0 (thin) | 1,524 / 28 | 1,301 / 1,301 (thin) |
| [4,inf) | 11,793 / 0 (thin) | 8,206 / 0 (thin) | 417 / 5 (thin) | 3,320 / 3,320 (thin) |

Cells with >= 10 of each action: 2 of 24; artefact own_entry: 2 of 24 (match). Artefact betarx/family/HVLM_nach_b0p003_t1.json: sum n_fired 4,881, n_waited 65,922; total absolute difference from the record counts 2 decisions (chain ends dropped by fit_q.chains).
Artefact fire table (1 = start): [[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]; residual-only back-off [1, 1, 1, 1, 0, 0]. Share of the rule's starts that lie in the table's start cells: 4.7%; share of free decisions in those cells: 16.7%.

### Load size at free decisions

| size | free | starts | start rate |
|---:|---:|---:|---:|
| 1 | 16,839 | 2,032 | 12.1% |
| 2 | 18,353 | 1,409 | 7.7% |
| 3 | 18,380 | 1,133 | 6.2% |
| 4 | 11,913 | 220 | 1.8% |
| 5 | 5,320 | 88 | 1.7% |

Share with size >= 3: 50.3%; start rate at size >= 3 4.05%, at size < 3 9.78%.

Start rate by size within each m_min bin (n in parentheses):

| m_min bin | size 1 | size 2 | size 3 | size 4 | size 5 |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 2% (106) | 5% (217) | 2% (352) | 1% (376) | 3% (318) |
| [0.25,0.5) | 4% (171) | 2% (214) | 2% (246) | 1% (403) | 1% (398) |
| [0.5,1) | 4% (262) | 2% (477) | 2% (645) | 1% (673) | 1% (823) |
| [1,2) | 4% (395) | 2% (969) | 2% (1,425) | 1% (1,859) | 2% (1,490) |
| [2,4) | 7% (3,795) | 4% (10,546) | 4% (10,638) | 2% (8,213) | 2% (2,058) |
| [4,inf) | 14% (12,110) | 15% (5,930) | 14% (5,074) | 1% (389) | 1% (233) |

## HVLM_learner

Files: collect/HVLM_p1_s100.json, collect/HVLM_p1_s101.json. Free decisions 126,636, started 2,548 (2.01%). Diffusion_BE_123: 64,992/1,313; Diffusion_FE_120: 30,685/604; Diffusion_FE_94: 30,959/631

### m_min (tightest residual)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 2,830 | 2.2% | 48 | 1.7% | 1.9% |
| [0.25,0.5) | 2,582 | 2.0% | 56 | 2.2% | 2.2% |
| [0.5,1) | 6,106 | 4.8% | 132 | 2.2% | 5.2% |
| [1,2) | 14,012 | 11.1% | 294 | 2.1% | 11.5% |
| [2,4) | 48,557 | 38.3% | 997 | 2.1% | 39.1% |
| [4,inf) | 52,549 | 41.5% | 1,021 | 1.9% | 40.1% |

Sextiles (edges a six-bin quantile binning would use): 1.722, 2.833, 3.606, 4.357, 9.572 h.
Percentiles of m_min: p25 2.320, p50 3.606, p75 9.013, p90 9.841, p99 10.000; min 0.000, max 10.000, mean 4.792 h.
Share with m_min < 0.5 h 4.3%, < 1 h 9.1%, < 2 h 20.2%, < 4 h 58.5%.
Among starts: median m_min 3.510 h; share of starts with m_min < 2 h 20.8%, < 4 h 59.9%.
Atoms at the limits (m_min exactly 4, 8, 10 h): 4 h: 7,602, 8 h: 0, 10 h: 8,719. Share of free decisions / of starts by band: [3,4) 22.2% / 23.4%; [4,4.5) 8.4% / 7.0%; [4.5,7) 1.9% / 1.7%; [7,8) 1.7% / 1.4%; [8,9) 4.4% / 4.4%; [9,10] 25.1% / 25.5%.

Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 2,830 | 48 |
| 0.25 | 2,582 | 56 |
| 0.5 | 2,972 | 64 |
| 0.75 | 3,134 | 68 |
| 1.0 | 3,026 | 59 |
| 1.25 | 3,230 | 61 |
| 1.5 | 3,689 | 78 |
| 1.75 | 4,067 | 96 |
| 2.0 | 4,906 | 82 |
| 2.25 | 4,569 | 83 |
| 2.5 | 5,108 | 108 |
| 2.75 | 5,898 | 128 |
| 3.0 | 7,898 | 202 |
| 3.25 | 6,492 | 137 |
| 3.5 | 7,031 | 143 |
| 3.75 | 6,655 | 114 |
| 4.0 | 9,739 | 158 |
| 4.25 | 908 | 21 |
| 4.5 | 137 | 2 |
| 4.75 | 153 | 3 |
| 5.0 | 151 | 5 |
| 5.25 | 132 | 2 |
| 5.5 | 220 | 3 |
| 5.75 | 241 | 6 |
| 6.0 | 265 | 4 |
| 6.25 | 343 | 5 |
| 6.5 | 400 | 6 |
| 6.75 | 328 | 7 |
| 7.0 | 412 | 4 |
| 7.25 | 486 | 8 |
| 7.5 | 555 | 8 |
| 7.75 | 669 | 16 |
| 8.0 | 770 | 18 |
| 8.25 | 1,092 | 15 |
| 8.5 | 1,453 | 28 |
| 8.75 | 2,267 | 51 |
| 9.0 | 3,488 | 61 |
| 9.25 | 5,420 | 132 |
| 9.5 | 7,533 | 159 |
| 9.75 | 6,654 | 127 |
| 10.0 | 8,733 | 172 |

### u (time to the next announced arrival)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 41,211 | 32.5% | 852 | 2.1% | 33.4% |
| [0.25,1) | 37,867 | 29.9% | 756 | 2.0% | 29.7% |
| [1,3) | 4,052 | 3.2% | 91 | 2.2% | 3.6% |
| [3,inf) | 43,506 | 34.4% | 849 | 2.0% | 33.3% |

u = 24.0 (none announced): 43,205 (34.1%), start rate there 1.95%; 3 <= u < 24: 301 (0.24%); u < 24: 83,431 (65.9%), start rate there 2.04%.
Quartiles of u among u < 24: p25 0.124, p50 0.253, p75 0.425 h; p99 1.939; max below 24: 3.989 h. Share with u = 0 exactly: 0.00%.

0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 21,010 | 425 |
| 0.125 | 20,201 | 427 |
| 0.25 | 17,563 | 341 |
| 0.375 | 7,893 | 158 |
| 0.5 | 4,506 | 101 |
| 0.625 | 3,596 | 61 |
| 0.75 | 2,900 | 58 |
| 0.875 | 1,409 | 37 |
| 1.0 | 1,119 | 31 |
| 1.125 | 886 | 24 |
| 1.25 | 601 | 16 |
| 1.375 | 394 | 3 |
| 1.5 | 209 | 4 |
| 1.625 | 127 | 2 |
| 1.75 | 135 | 3 |
| 1.875 | 90 | 0 |
| 2.0 | 92 | 2 |
| 2.125 | 99 | 2 |
| 2.25 | 99 | 3 |
| 2.375 | 35 | 0 |
| 2.5 | 61 | 1 |
| 2.625 | 30 | 0 |
| 2.75 | 30 | 0 |
| 2.875 | 45 | 0 |
| 3.0 | 43,506 | 849 |

### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10

| m_min \ u | [0,0.25) | [0.25,1) | [1,3) | [3,inf) |
|---|---:|---:|---:|---:|
| [0,0.25) | 596 / 11 | 1,006 / 18 | 186 / 3 (thin) | 1,042 / 16 |
| [0.25,0.5) | 571 / 11 | 833 / 21 | 217 / 8 (thin) | 961 / 16 |
| [0.5,1) | 1,443 / 34 | 1,952 / 43 | 500 / 12 | 2,211 / 43 |
| [1,2) | 3,509 / 70 | 5,172 / 111 | 899 / 27 | 4,432 / 86 |
| [2,4) | 14,745 / 313 | 18,912 / 379 | 1,832 / 31 | 13,068 / 274 |
| [4,inf) | 20,347 / 413 | 9,992 / 184 | 418 / 10 | 21,792 / 414 |

Cells with >= 10 of each action: 22 of 24; artefact own_entry: 22 of 24 (match). Artefact betarx/family/HVLM_learner_b0p003_t1.json: sum n_fired 2,548, n_waited 124,088; total absolute difference from the record counts 0 decisions (chain ends dropped by fit_q.chains).
Artefact fire table (1 = start): [[1, 1, 1, 1], [0, 1, 1, 1], [0, 1, 1, 1], [0, 0, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]; residual-only back-off [1, 1, 1, 1, 0, 0]. Share of the rule's starts that lie in the table's start cells: 11.9%; share of free decisions in those cells: 11.7%.

### Load size at free decisions

| size | free | starts | start rate |
|---:|---:|---:|---:|
| 1 | 27,099 | 522 | 1.9% |
| 2 | 36,968 | 763 | 2.1% |
| 3 | 40,604 | 799 | 2.0% |
| 4 | 15,623 | 340 | 2.2% |
| 5 | 6,342 | 124 | 2.0% |

Share with size >= 3: 49.4%; start rate at size >= 3 2.02%, at size < 3 2.01%.

Start rate by size within each m_min bin (n in parentheses):

| m_min bin | size 1 | size 2 | size 3 | size 4 | size 5 |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 1% (280) | 2% (545) | 1% (867) | 2% (652) | 1% (486) |
| [0.25,0.5) | 1% (179) | 3% (517) | 2% (786) | 2% (714) | 3% (386) |
| [0.5,1) | 1% (502) | 3% (1,199) | 2% (1,924) | 2% (1,474) | 2% (1,007) |
| [1,2) | 2% (948) | 2% (2,888) | 2% (4,480) | 2% (3,776) | 2% (1,920) |
| [2,4) | 2% (5,172) | 2% (15,159) | 2% (17,347) | 2% (8,650) | 2% (2,229) |
| [4,inf) | 2% (20,018) | 2% (16,660) | 2% (15,200) | 3% (357) | 3% (314) |

## LVHM_timeout

Files: collect/LVHM_norev_p1_s100.json, collect/LVHM_norev_p1_s101.json. Free decisions 51,371, started 6,242 (12.15%). Diffusion_BE_123: 22,106/2,856; Diffusion_FE_120: 7,146/1,131; Diffusion_FE_94: 22,119/2,255

### m_min (tightest residual)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 1,119 | 2.2% | 111 | 9.9% | 1.8% |
| [0.25,0.5) | 856 | 1.7% | 97 | 11.3% | 1.6% |
| [0.5,1) | 1,847 | 3.6% | 258 | 14.0% | 4.1% |
| [1,2) | 4,156 | 8.1% | 864 | 20.8% | 13.8% |
| [2,4) | 23,841 | 46.4% | 2,974 | 12.5% | 47.6% |
| [4,inf) | 19,552 | 38.1% | 1,938 | 9.9% | 31.0% |

Sextiles (edges a six-bin quantile binning would use): 2.094, 3.078, 3.586, 4.000, 9.403 h.
Percentiles of m_min: p25 2.696, p50 3.586, p75 8.567, p90 9.759, p99 10.000; min 0.001, max 10.000, mean 4.604 h.
Share with m_min < 0.5 h 3.8%, < 1 h 7.4%, < 2 h 15.5%, < 4 h 61.9%.
Among starts: median m_min 2.882 h; share of starts with m_min < 2 h 21.3%, < 4 h 69.0%.
Atoms at the limits (m_min exactly 4, 8, 10 h): 4 h: 3,516, 8 h: 0, 10 h: 3,521. Share of free decisions / of starts by band: [3,4) 30.7% / 12.4%; [4,4.5) 12.0% / 4.1%; [4.5,7) 0.0% / 0.2%; [7,8) 0.2% / 2.0%; [8,9) 3.0% / 24.8%; [9,10] 22.8% / 0.0%.

Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 1,119 | 111 |
| 0.25 | 856 | 97 |
| 0.5 | 958 | 115 |
| 0.75 | 889 | 143 |
| 1.0 | 886 | 149 |
| 1.25 | 962 | 195 |
| 1.5 | 1,042 | 244 |
| 1.75 | 1,266 | 276 |
| 2.0 | 1,546 | 348 |
| 2.25 | 1,635 | 386 |
| 2.5 | 2,184 | 635 |
| 2.75 | 2,698 | 831 |
| 3.0 | 4,753 | 334 |
| 3.25 | 3,639 | 213 |
| 3.5 | 3,806 | 155 |
| 3.75 | 3,580 | 72 |
| 4.0 | 5,249 | 230 |
| 4.25 | 893 | 23 |
| 4.5 | 2 | 2 |
| 4.75 | 0 | 0 |
| 5.0 | 0 | 0 |
| 5.25 | 0 | 0 |
| 5.5 | 0 | 0 |
| 5.75 | 0 | 0 |
| 6.0 | 0 | 0 |
| 6.25 | 4 | 4 |
| 6.5 | 4 | 4 |
| 6.75 | 3 | 3 |
| 7.0 | 13 | 13 |
| 7.25 | 15 | 15 |
| 7.5 | 25 | 25 |
| 7.75 | 72 | 72 |
| 8.0 | 131 | 131 |
| 8.25 | 216 | 216 |
| 8.5 | 437 | 437 |
| 8.75 | 763 | 763 |
| 9.0 | 1,786 | 0 |
| 9.25 | 2,260 | 0 |
| 9.5 | 2,460 | 0 |
| 9.75 | 1,689 | 0 |
| 10.0 | 3,530 | 0 |

### u (time to the next announced arrival)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 13,882 | 27.0% | 1,756 | 12.6% | 28.1% |
| [0.25,1) | 17,219 | 33.5% | 1,754 | 10.2% | 28.1% |
| [1,3) | 1,543 | 3.0% | 199 | 12.9% | 3.2% |
| [3,inf) | 18,727 | 36.5% | 2,533 | 13.5% | 40.6% |

u = 24.0 (none announced): 18,679 (36.4%), start rate there 13.48%; 3 <= u < 24: 48 (0.09%); u < 24: 32,692 (63.6%), start rate there 11.39%.
Quartiles of u among u < 24: p25 0.142, p50 0.293, p75 0.440 h; p99 1.576; max below 24: 4.026 h. Share with u = 0 exactly: 0.00%.

0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 7,223 | 974 |
| 0.125 | 6,659 | 782 |
| 0.25 | 8,015 | 779 |
| 0.375 | 4,069 | 399 |
| 0.5 | 1,706 | 189 |
| 0.625 | 1,376 | 140 |
| 0.75 | 1,511 | 174 |
| 0.875 | 542 | 73 |
| 1.0 | 409 | 47 |
| 1.125 | 305 | 41 |
| 1.25 | 290 | 33 |
| 1.375 | 136 | 23 |
| 1.5 | 180 | 20 |
| 1.625 | 45 | 6 |
| 1.75 | 47 | 3 |
| 1.875 | 14 | 4 |
| 2.0 | 26 | 5 |
| 2.125 | 18 | 4 |
| 2.25 | 23 | 5 |
| 2.375 | 8 | 2 |
| 2.5 | 13 | 1 |
| 2.625 | 19 | 1 |
| 2.75 | 2 | 2 |
| 2.875 | 8 | 2 |
| 3.0 | 18,727 | 2,533 |

### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10

| m_min \ u | [0,0.25) | [0.25,1) | [1,3) | [3,inf) |
|---|---:|---:|---:|---:|
| [0,0.25) | 402 / 36 | 464 / 42 | 48 / 10 | 205 / 23 |
| [0.25,0.5) | 310 / 36 | 361 / 30 | 49 / 7 (thin) | 136 / 24 |
| [0.5,1) | 605 / 85 | 728 / 88 | 114 / 12 | 400 / 73 |
| [1,2) | 1,331 / 257 | 1,624 / 289 | 238 / 47 | 963 / 271 |
| [2,4) | 5,878 / 788 | 9,292 / 1,006 | 924 / 117 | 7,747 / 1,063 |
| [4,inf) | 5,356 / 554 | 4,750 / 299 | 170 / 6 (thin) | 9,276 / 1,079 |

Cells with >= 10 of each action: 22 of 24; artefact own_entry: 22 of 24 (match). Artefact betarx/family/LVHM_timeout_b0p003_t1.json: sum n_fired 6,242, n_waited 45,127; total absolute difference from the record counts 2 decisions (chain ends dropped by fit_q.chains).
Artefact fire table (1 = start): [[1, 1, 1, 1], [0, 1, 1, 1], [0, 1, 1, 1], [0, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]; residual-only back-off [1, 1, 1, 1, 0, 0]. Share of the rule's starts that lie in the table's start cells: 15.3%; share of free decisions in those cells: 11.2%.

### Load size at free decisions

| size | free | starts | start rate |
|---:|---:|---:|---:|
| 1 | 15,971 | 907 | 5.7% |
| 2 | 19,099 | 2,109 | 11.0% |
| 3 | 14,078 | 2,439 | 17.3% |
| 4 | 1,905 | 647 | 34.0% |
| 5 | 318 | 140 | 44.0% |

Share with size >= 3: 31.7%; start rate at size >= 3 19.79%, at size < 3 8.60%.

Start rate by size within each m_min bin (n in parentheses):

| m_min bin | size 1 | size 2 | size 3 | size 4 | size 5 |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 6% (204) | 5% (415) | 11% (394) | 25% (99) | 100% (7) |
| [0.25,0.5) | 7% (170) | 4% (298) | 13% (308) | 37% (62) | 44% (18) |
| [0.5,1) | 8% (419) | 11% (709) | 14% (569) | 44% (107) | 44% (43) |
| [1,2) | 13% (806) | 19% (1,405) | 21% (1,473) | 38% (367) | 42% (105) |
| [2,4) | 7% (4,719) | 10% (10,016) | 15% (7,741) | 33% (1,226) | 43% (139) |
| [4,inf) | 4% (9,653) | 12% (6,256) | 22% (3,593) | 9% (44) | 33% (6) |

## LVHM_mbs3

Files: collect/LVHM_mbs3_p1_s100.json, collect/LVHM_mbs3_p1_s101.json. Free decisions 65,412, started 7,001 (10.70%). Diffusion_BE_123: 30,317/2,823; Diffusion_FE_120: 10,529/1,779; Diffusion_FE_94: 24,566/2,399

### m_min (tightest residual)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 1,652 | 2.5% | 169 | 10.2% | 2.4% |
| [0.25,0.5) | 1,458 | 2.2% | 172 | 11.8% | 2.5% |
| [0.5,1) | 3,347 | 5.1% | 371 | 11.1% | 5.3% |
| [1,2) | 7,970 | 12.2% | 971 | 12.2% | 13.9% |
| [2,4) | 26,464 | 40.5% | 2,875 | 10.9% | 41.1% |
| [4,inf) | 24,521 | 37.5% | 2,443 | 10.0% | 34.9% |

Sextiles (edges a six-bin quantile binning would use): 1.593, 2.701, 3.479, 4.000, 9.198 h.
Percentiles of m_min: p25 2.196, p50 3.479, p75 6.495, p90 9.700, p99 10.000; min 0.000, max 10.000, mean 4.342 h.
Share with m_min < 0.5 h 4.8%, < 1 h 9.9%, < 2 h 22.1%, < 4 h 62.5%.
Among starts: median m_min 3.225 h; share of starts with m_min < 2 h 24.0%, < 4 h 65.1%.
Atoms at the limits (m_min exactly 4, 8, 10 h): 4 h: 3,901, 8 h: 0, 10 h: 3,917. Share of free decisions / of starts by band: [3,4) 23.4% / 21.5%; [4,4.5) 11.2% / 1.5%; [4.5,7) 1.8% / 1.9%; [7,8) 1.7% / 3.0%; [8,9) 4.5% / 11.5%; [9,10] 18.3% / 16.9%.

Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 1,652 | 169 |
| 0.25 | 1,458 | 172 |
| 0.5 | 1,634 | 195 |
| 0.75 | 1,713 | 176 |
| 1.0 | 1,736 | 200 |
| 1.25 | 1,949 | 221 |
| 1.5 | 2,126 | 271 |
| 1.75 | 2,159 | 279 |
| 2.0 | 2,409 | 301 |
| 2.25 | 2,605 | 355 |
| 2.5 | 2,945 | 328 |
| 2.75 | 3,196 | 389 |
| 3.0 | 3,911 | 499 |
| 3.25 | 3,559 | 327 |
| 3.5 | 4,019 | 357 |
| 3.75 | 3,820 | 319 |
| 4.0 | 6,170 | 85 |
| 4.25 | 1,132 | 20 |
| 4.5 | 84 | 7 |
| 4.75 | 120 | 8 |
| 5.0 | 65 | 7 |
| 5.25 | 87 | 10 |
| 5.5 | 95 | 11 |
| 5.75 | 110 | 11 |
| 6.0 | 121 | 13 |
| 6.25 | 186 | 23 |
| 6.5 | 144 | 21 |
| 6.75 | 150 | 23 |
| 7.0 | 187 | 33 |
| 7.25 | 197 | 39 |
| 7.5 | 322 | 65 |
| 7.75 | 419 | 74 |
| 8.0 | 450 | 107 |
| 8.25 | 615 | 161 |
| 8.5 | 808 | 237 |
| 8.75 | 1,095 | 302 |
| 9.0 | 1,427 | 362 |
| 9.25 | 2,045 | 447 |
| 9.5 | 2,487 | 322 |
| 9.75 | 2,076 | 55 |
| 10.0 | 3,929 | 0 |

### u (time to the next announced arrival)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 16,737 | 25.6% | 1,798 | 10.7% | 25.7% |
| [0.25,1) | 17,488 | 26.7% | 2,315 | 13.2% | 33.1% |
| [1,3) | 1,594 | 2.4% | 209 | 13.1% | 3.0% |
| [3,inf) | 29,593 | 45.2% | 2,679 | 9.1% | 38.3% |

u = 24.0 (none announced): 29,476 (45.1%), start rate there 9.06%; 3 <= u < 24: 117 (0.18%); u < 24: 35,936 (54.9%), start rate there 12.05%.
Quartiles of u among u < 24: p25 0.126, p50 0.271, p75 0.409 h; p99 2.095; max below 24: 4.054 h. Share with u = 0 exactly: 0.00%.

0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 8,932 | 940 |
| 0.125 | 7,805 | 858 |
| 0.25 | 8,750 | 1,078 |
| 0.375 | 4,136 | 479 |
| 0.5 | 1,437 | 230 |
| 0.625 | 1,259 | 199 |
| 0.75 | 1,391 | 242 |
| 0.875 | 515 | 87 |
| 1.0 | 302 | 41 |
| 1.125 | 316 | 45 |
| 1.25 | 233 | 38 |
| 1.375 | 196 | 19 |
| 1.5 | 125 | 17 |
| 1.625 | 54 | 10 |
| 1.75 | 42 | 3 |
| 1.875 | 45 | 5 |
| 2.0 | 64 | 6 |
| 2.125 | 59 | 4 |
| 2.25 | 25 | 6 |
| 2.375 | 47 | 4 |
| 2.5 | 32 | 7 |
| 2.625 | 18 | 0 |
| 2.75 | 10 | 1 |
| 2.875 | 26 | 3 |
| 3.0 | 29,593 | 2,679 |

### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10

| m_min \ u | [0,0.25) | [0.25,1) | [1,3) | [3,inf) |
|---|---:|---:|---:|---:|
| [0,0.25) | 380 / 56 | 445 / 54 | 86 / 10 | 741 / 49 |
| [0.25,0.5) | 325 / 42 | 441 / 66 | 51 / 6 (thin) | 641 / 58 |
| [0.5,1) | 765 / 93 | 961 / 167 | 154 / 20 | 1,467 / 91 |
| [1,2) | 1,912 / 228 | 2,306 / 386 | 254 / 41 | 3,498 / 316 |
| [2,4) | 6,390 / 648 | 8,551 / 1,198 | 817 / 120 | 10,706 / 909 |
| [4,inf) | 6,965 / 731 | 4,784 / 444 | 232 / 12 | 12,540 / 1,256 |

Cells with >= 10 of each action: 23 of 24; artefact own_entry: 23 of 24 (match). Artefact betarx/family/LVHM_mbs3_b0p003_t1.json: sum n_fired 7,000, n_waited 58,409; total absolute difference from the record counts 3 decisions (chain ends dropped by fit_q.chains).
Artefact fire table (1 = start): [[1, 1, 1, 1], [1, 1, 1, 1], [0, 1, 0, 1], [0, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]]; residual-only back-off [1, 1, 1, 1, 0, 0]. Share of the rule's starts that lie in the table's start cells: 19.2%; share of free decisions in those cells: 17.7%.

### Load size at free decisions

| size | free | starts | start rate |
|---:|---:|---:|---:|
| 1 | 18,185 | 0 | 0.0% |
| 2 | 40,226 | 0 | 0.0% |
| 3 | 6,795 | 6,795 | 100.0% |
| 4 | 156 | 156 | 100.0% |
| 5 | 50 | 50 | 100.0% |

Share with size >= 3: 10.7%; start rate at size >= 3 100.00%, at size < 3 0.00%.

Start rate by size within each m_min bin (n in parentheses):

| m_min bin | size 1 | size 2 | size 3 | size 4 | size 5 |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 0% (303) | 0% (1,180) | 100% (155) | 100% (9) | 100% (5) |
| [0.25,0.5) | 0% (254) | 0% (1,032) | 100% (167) | 100% (4) | 100% (1) |
| [0.5,1) | 0% (536) | 0% (2,440) | 100% (341) | 100% (18) | 100% (12) |
| [1,2) | 0% (1,463) | 0% (5,536) | 100% (924) | 100% (32) | 100% (15) |
| [2,4) | 0% (5,434) | 0% (18,155) | 100% (2,772) | 100% (88) | 100% (15) |
| [4,inf) | 0% (10,195) | 0% (11,883) | 100% (2,436) | 100% (5) | 100% (2) |

## LVHM_nach

Files: collect/LVHM_nach_p1_s100.json, collect/LVHM_nach_p1_s101.json. Free decisions 58,660, started 5,482 (9.35%). Diffusion_BE_123: 14,922/3,038; Diffusion_FE_120: 3,589/1,545; Diffusion_FE_94: 40,149/899

### m_min (tightest residual)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 2,377 | 4.1% | 39 | 1.6% | 0.7% |
| [0.25,0.5) | 2,238 | 3.8% | 51 | 2.3% | 0.9% |
| [0.5,1) | 4,954 | 8.4% | 100 | 2.0% | 1.8% |
| [1,2) | 9,926 | 16.9% | 224 | 2.3% | 4.1% |
| [2,4) | 25,469 | 43.4% | 1,513 | 5.9% | 27.6% |
| [4,inf) | 13,696 | 23.3% | 3,555 | 26.0% | 64.8% |

Sextiles (edges a six-bin quantile binning would use): 1.023, 2.009, 2.830, 3.522, 4.280 h.
Percentiles of m_min: p25 1.526, p50 2.830, p75 3.932, p90 9.552, p99 10.000; min 0.000, max 10.000, mean 3.431 h.
Share with m_min < 0.5 h 7.9%, < 1 h 16.3%, < 2 h 33.2%, < 4 h 76.7%.
Among starts: median m_min 8.998 h; share of starts with m_min < 2 h 7.6%, < 4 h 35.2%.
Atoms at the limits (m_min exactly 4, 8, 10 h): 4 h: 2,101, 8 h: 0, 10 h: 2,747. Share of free decisions / of starts by band: [3,4) 22.9% / 19.1%; [4,4.5) 8.4% / 8.1%; [4.5,7) 0.0% / 0.1%; [7,8) 0.1% / 0.7%; [8,9) 1.2% / 6.0%; [9,10] 13.6% / 50.0%.

Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 2,377 | 39 |
| 0.25 | 2,238 | 51 |
| 0.5 | 2,429 | 50 |
| 0.75 | 2,525 | 50 |
| 1.0 | 2,443 | 46 |
| 1.25 | 2,382 | 39 |
| 1.5 | 2,576 | 65 |
| 1.75 | 2,525 | 74 |
| 2.0 | 2,803 | 80 |
| 2.25 | 2,941 | 118 |
| 2.5 | 3,153 | 122 |
| 2.75 | 3,113 | 145 |
| 3.0 | 4,126 | 241 |
| 3.25 | 3,251 | 250 |
| 3.5 | 3,113 | 261 |
| 3.75 | 2,969 | 296 |
| 4.0 | 3,804 | 417 |
| 4.25 | 1,152 | 29 |
| 4.5 | 1 | 1 |
| 4.75 | 0 | 0 |
| 5.0 | 1 | 1 |
| 5.25 | 0 | 0 |
| 5.5 | 0 | 0 |
| 5.75 | 0 | 0 |
| 6.0 | 0 | 0 |
| 6.25 | 2 | 1 |
| 6.5 | 2 | 1 |
| 6.75 | 0 | 0 |
| 7.0 | 4 | 3 |
| 7.25 | 7 | 6 |
| 7.5 | 8 | 5 |
| 7.75 | 27 | 22 |
| 8.0 | 72 | 29 |
| 8.25 | 104 | 53 |
| 8.5 | 221 | 108 |
| 8.75 | 329 | 140 |
| 9.0 | 605 | 230 |
| 9.25 | 1,220 | 400 |
| 9.5 | 1,922 | 591 |
| 9.75 | 1,462 | 506 |
| 10.0 | 2,753 | 1,012 |

### u (time to the next announced arrival)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 21,893 | 37.3% | 0 | 0.0% | 0.0% |
| [0.25,1) | 28,617 | 48.8% | 0 | 0.0% | 0.0% |
| [1,3) | 2,742 | 4.7% | 96 | 3.5% | 1.8% |
| [3,inf) | 5,408 | 9.2% | 5,386 | 99.6% | 98.2% |

u = 24.0 (none announced): 5,370 (9.2%), start rate there 100.00%; 3 <= u < 24: 38 (0.06%); u < 24: 53,290 (90.8%), start rate there 0.21%.
Quartiles of u among u < 24: p25 0.141, p50 0.306, p75 0.497 h; p99 1.411; max below 24: 4.011 h. Share with u = 0 exactly: 0.00%.

0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 12,007 | 0 |
| 0.125 | 9,886 | 0 |
| 0.25 | 11,529 | 0 |
| 0.375 | 6,645 | 0 |
| 0.5 | 3,567 | 0 |
| 0.625 | 2,860 | 0 |
| 0.75 | 2,726 | 0 |
| 0.875 | 1,290 | 0 |
| 1.0 | 966 | 0 |
| 1.125 | 686 | 0 |
| 1.25 | 518 | 8 |
| 1.375 | 233 | 13 |
| 1.5 | 158 | 10 |
| 1.625 | 52 | 11 |
| 1.75 | 31 | 7 |
| 1.875 | 16 | 6 |
| 2.0 | 21 | 8 |
| 2.125 | 16 | 1 |
| 2.25 | 18 | 13 |
| 2.375 | 10 | 5 |
| 2.5 | 7 | 4 |
| 2.625 | 1 | 1 |
| 2.75 | 7 | 7 |
| 2.875 | 2 | 2 |
| 3.0 | 5,408 | 5,386 |

### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10

| m_min \ u | [0,0.25) | [0.25,1) | [1,3) | [3,inf) |
|---|---:|---:|---:|---:|
| [0,0.25) | 952 / 0 (thin) | 1,268 / 0 (thin) | 122 / 4 (thin) | 35 / 35 (thin) |
| [0.25,0.5) | 866 / 0 (thin) | 1,215 / 0 (thin) | 113 / 7 (thin) | 44 / 44 (thin) |
| [0.5,1) | 1,889 / 0 (thin) | 2,673 / 0 (thin) | 298 / 6 (thin) | 94 / 94 (thin) |
| [1,2) | 3,914 / 0 (thin) | 5,244 / 0 (thin) | 546 / 22 | 222 / 202 |
| [2,4) | 9,184 / 0 (thin) | 13,420 / 0 (thin) | 1,403 / 53 | 1,462 / 1,460 (thin) |
| [4,inf) | 5,088 / 0 (thin) | 4,797 / 0 (thin) | 260 / 4 (thin) | 3,551 / 3,551 (thin) |

Cells with >= 10 of each action: 3 of 24; artefact own_entry: 3 of 24 (match). Artefact betarx/family/LVHM_nach_b0p003_t1.json: sum n_fired 5,479, n_waited 53,177; total absolute difference from the record counts 4 decisions (chain ends dropped by fit_q.chains).
Artefact fire table (1 = start): [[1, 1, 1, 1], [0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 1], [0, 0, 0, 0], [0, 0, 0, 0]]; residual-only back-off [1, 0, 1, 0, 0, 0]. Share of the rule's starts that lie in the table's start cells: 6.2%; share of free decisions in those cells: 12.9%.

### Load size at free decisions

| size | free | starts | start rate |
|---:|---:|---:|---:|
| 1 | 11,747 | 2,358 | 20.1% |
| 2 | 13,042 | 1,619 | 12.4% |
| 3 | 15,055 | 1,153 | 7.7% |
| 4 | 10,112 | 217 | 2.1% |
| 5 | 8,704 | 135 | 1.6% |

Share with size >= 3: 57.7%; start rate at size >= 3 4.44%, at size < 3 16.04%.

Start rate by size within each m_min bin (n in parentheses):

| m_min bin | size 1 | size 2 | size 3 | size 4 | size 5 |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 2% (193) | 2% (405) | 4% (538) | 1% (588) | 1% (653) |
| [0.25,0.5) | 4% (175) | 3% (412) | 3% (528) | 2% (455) | 1% (668) |
| [0.5,1) | 3% (397) | 3% (795) | 2% (1,384) | 2% (1,156) | 1% (1,222) |
| [1,2) | 3% (773) | 4% (1,446) | 2% (2,582) | 2% (2,538) | 1% (2,587) |
| [2,4) | 10% (3,230) | 9% (6,330) | 5% (7,460) | 3% (5,136) | 2% (3,313) |
| [4,inf) | 28% (6,979) | 26% (3,654) | 24% (2,563) | 1% (239) | 0% (261) |

## LVHM_learner

Files: collect/LVHM_p1_s100.json, collect/LVHM_p1_s101.json. Free decisions 108,171, started 2,169 (2.01%). Diffusion_BE_123: 40,335/829; Diffusion_FE_120: 14,926/289; Diffusion_FE_94: 52,910/1,051

### m_min (tightest residual)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 4,679 | 4.3% | 81 | 1.7% | 3.7% |
| [0.25,0.5) | 4,387 | 4.1% | 84 | 1.9% | 3.9% |
| [0.5,1) | 8,639 | 8.0% | 162 | 1.9% | 7.5% |
| [1,2) | 18,247 | 16.9% | 361 | 2.0% | 16.6% |
| [2,4) | 43,008 | 39.8% | 911 | 2.1% | 42.0% |
| [4,inf) | 29,211 | 27.0% | 570 | 2.0% | 26.3% |

Sextiles (edges a six-bin quantile binning would use): 1.021, 2.004, 2.849, 3.658, 7.927 h.
Percentiles of m_min: p25 1.520, p50 2.849, p75 4.000, p90 9.415, p99 10.000; min 0.000, max 10.000, mean 3.588 h.
Share with m_min < 0.5 h 8.4%, < 1 h 16.4%, < 2 h 33.2%, < 4 h 73.0%.
Among starts: median m_min 2.830 h; share of starts with m_min < 2 h 31.7%, < 4 h 73.7%.
Atoms at the limits (m_min exactly 4, 8, 10 h): 4 h: 3,830, 8 h: 0, 10 h: 4,927. Share of free decisions / of starts by band: [3,4) 20.0% / 19.9%; [4,4.5) 7.7% / 7.7%; [4.5,7) 1.4% / 1.4%; [7,8) 1.3% / 0.9%; [8,9) 3.5% / 2.5%; [9,10] 13.1% / 13.8%.

Fine grid (0.25 h bins from 0 to 10 h, then >= 10 h): free decisions / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 4,679 | 81 |
| 0.25 | 4,387 | 84 |
| 0.5 | 4,281 | 72 |
| 0.75 | 4,358 | 90 |
| 1.0 | 4,398 | 95 |
| 1.25 | 4,600 | 92 |
| 1.5 | 4,533 | 83 |
| 1.75 | 4,716 | 91 |
| 2.0 | 5,194 | 133 |
| 2.25 | 5,324 | 109 |
| 2.5 | 5,245 | 117 |
| 2.75 | 5,569 | 120 |
| 3.0 | 7,562 | 148 |
| 3.25 | 4,615 | 84 |
| 3.5 | 4,788 | 99 |
| 3.75 | 4,711 | 101 |
| 4.0 | 6,846 | 137 |
| 4.25 | 1,483 | 30 |
| 4.5 | 96 | 3 |
| 4.75 | 92 | 5 |
| 5.0 | 118 | 1 |
| 5.25 | 123 | 1 |
| 5.5 | 120 | 1 |
| 5.75 | 175 | 1 |
| 6.0 | 157 | 5 |
| 6.25 | 176 | 5 |
| 6.5 | 257 | 2 |
| 6.75 | 253 | 6 |
| 7.0 | 271 | 6 |
| 7.25 | 365 | 3 |
| 7.5 | 343 | 7 |
| 7.75 | 460 | 3 |
| 8.0 | 691 | 8 |
| 8.25 | 665 | 11 |
| 8.5 | 1,059 | 19 |
| 8.75 | 1,319 | 17 |
| 9.0 | 1,694 | 50 |
| 9.25 | 2,499 | 45 |
| 9.5 | 2,769 | 63 |
| 9.75 | 2,251 | 47 |
| 10.0 | 4,929 | 94 |

### u (time to the next announced arrival)

| bin | free | share | starts | start rate | share of starts |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 28,261 | 26.1% | 570 | 2.0% | 26.3% |
| [0.25,1) | 34,003 | 31.4% | 706 | 2.1% | 32.5% |
| [1,3) | 4,611 | 4.3% | 107 | 2.3% | 4.9% |
| [3,inf) | 41,296 | 38.2% | 786 | 1.9% | 36.2% |

u = 24.0 (none announced): 40,717 (37.6%), start rate there 1.91%; 3 <= u < 24: 579 (0.54%); u < 24: 67,454 (62.4%), start rate there 2.06%.
Quartiles of u among u < 24: p25 0.143, p50 0.302, p75 0.521 h; p99 2.912; max below 24: 4.070 h. Share with u = 0 exactly: 0.00%.

0.125 h grid from 0 to 3 h (then >= 3 h incl. 24): free / starts

| from (h) | free | starts |
|---:|---:|---:|
| 0.0 | 14,811 | 298 |
| 0.125 | 13,450 | 272 |
| 0.25 | 14,232 | 314 |
| 0.375 | 7,312 | 137 |
| 0.5 | 3,999 | 77 |
| 0.625 | 3,503 | 74 |
| 0.75 | 3,413 | 70 |
| 0.875 | 1,544 | 34 |
| 1.0 | 919 | 26 |
| 1.125 | 778 | 22 |
| 1.25 | 737 | 15 |
| 1.375 | 406 | 14 |
| 1.5 | 341 | 7 |
| 1.625 | 154 | 0 |
| 1.75 | 161 | 2 |
| 1.875 | 159 | 3 |
| 2.0 | 122 | 3 |
| 2.125 | 90 | 3 |
| 2.25 | 158 | 2 |
| 2.375 | 119 | 2 |
| 2.5 | 111 | 4 |
| 2.625 | 106 | 2 |
| 2.75 | 104 | 1 |
| 2.875 | 146 | 1 |
| 3.0 | 41,296 | 786 |

### Joint 6 x 4 (rows m_min, columns u): free count / starts, and whether both actions reach 10

| m_min \ u | [0,0.25) | [0.25,1) | [1,3) | [3,inf) |
|---|---:|---:|---:|---:|
| [0,0.25) | 1,172 / 19 | 1,669 / 32 | 294 / 5 (thin) | 1,544 / 25 |
| [0.25,0.5) | 1,034 / 25 | 1,636 / 27 | 206 / 8 (thin) | 1,511 / 24 |
| [0.5,1) | 1,837 / 36 | 3,129 / 60 | 493 / 14 | 3,180 / 52 |
| [1,2) | 4,464 / 83 | 6,420 / 132 | 996 / 25 | 6,367 / 121 |
| [2,4) | 11,364 / 245 | 15,471 / 333 | 2,294 / 44 | 13,879 / 289 |
| [4,inf) | 8,390 / 162 | 5,678 / 122 | 328 / 11 | 14,815 / 275 |

Cells with >= 10 of each action: 22 of 24; artefact own_entry: 22 of 24 (match). Artefact betarx/family/LVHM_learner_b0p003_t1.json: sum n_fired 2,168, n_waited 105,998; total absolute difference from the record counts 5 decisions (chain ends dropped by fit_q.chains).
Artefact fire table (1 = start): [[1, 1, 1, 1], [0, 1, 1, 1], [0, 1, 1, 1], [0, 0, 0, 1], [0, 0, 0, 0], [0, 0, 0, 0]]; residual-only back-off [1, 1, 1, 1, 0, 0]. Share of the rule's starts that lie in the table's start cells: 17.8%; share of free decisions in those cells: 19.6%.

### Load size at free decisions

| size | free | starts | start rate |
|---:|---:|---:|---:|
| 1 | 16,433 | 320 | 1.9% |
| 2 | 28,774 | 561 | 1.9% |
| 3 | 36,921 | 744 | 2.0% |
| 4 | 14,844 | 308 | 2.1% |
| 5 | 11,199 | 236 | 2.1% |

Share with size >= 3: 58.2%; start rate at size >= 3 2.05%, at size < 3 1.95%.

Start rate by size within each m_min bin (n in parentheses):

| m_min bin | size 1 | size 2 | size 3 | size 4 | size 5 |
|---|---:|---:|---:|---:|---:|
| [0,0.25) | 2% (256) | 1% (900) | 2% (1,660) | 2% (1,156) | 2% (707) |
| [0.25,0.5) | 1% (268) | 2% (926) | 2% (1,689) | 3% (998) | 2% (506) |
| [0.5,1) | 3% (520) | 2% (1,804) | 2% (2,864) | 2% (2,008) | 2% (1,443) |
| [1,2) | 2% (1,047) | 2% (3,760) | 2% (6,344) | 2% (4,052) | 2% (3,044) |
| [2,4) | 2% (4,082) | 2% (12,169) | 2% (15,568) | 2% (6,206) | 2% (4,983) |
| [4,inf) | 2% (10,260) | 2% (9,215) | 2% (8,796) | 4% (424) | 3% (516) |
