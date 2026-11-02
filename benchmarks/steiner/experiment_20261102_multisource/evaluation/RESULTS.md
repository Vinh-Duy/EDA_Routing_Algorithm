# Repeated versus multi-source nearest-terminal selection

This experiment compares the previous repeated-per-candidate Dijkstra selector
with a single multi-source Dijkstra selector. It does not compare the input-order
strategy and does not change A* routing, physical costs, or the default terminal order.

## Protocol

- Held-out cases: 60 oracle-feasible and 12 oracle-infeasible controls.
- Fixed fixtures: 6; all route semantics equivalent: True.
- Measurements: 11 repetitions and 1 warm-up per selector and layout; serial execution; paired order alternated by repetition.
- Both methods use the same stored layouts, A* binary, numeric net order, and one pass.
- Runtime comparisons use per-layout medians; repetitions are not independent samples.

## Correctness

- Per-instance held-out route semantic equivalence: 72/72.
- Compared selected-terminal sequence, physical tree edges, physical cost, wirelength,
  VIA count, routing success/failure, and termination reason.
- The repeated selector was also checked against the archived previous-study route JSON
  for every held-out case (semantic fields and historical search counters).
- Independent route validation ran on every output JSON.

## Selection work

- Dijkstra selection runs: 595 repeated vs. 239 multi-source (59.83% fewer).
- Settled vertices: 74338 repeated vs. 26862 multi-source (63.87% fewer).
- Settled-vertex reduction: 47476; expanded legal edges,
  heap pushes/pops, A* searches, and A* expanded nodes are included in per-instance CSV.

## Runtime

- Median of per-layout median router time: repeated 0.356189 ms; multi-source 0.219619 ms.
- Median paired runtime delta (multi-source minus repeated): -0.125966 ms; mean delta -0.252378 ms.
- Faster / tied / slower layouts: 69 / 0 / 3.
- Median within-layout router-time MAD: repeated 0.062638 ms; multi-source 0.026678 ms.
- Median selection time: repeated 0.250905 ms; multi-source 0.113666 ms.
- Median final routing time: repeated 0.045390 ms; multi-source 0.046824 ms.
- Timing is reported rather than inferred from node counts; inspect per-instance and raw
  measurements, including cases where multi-source is slower.

## Per-instance paired comparison

| Case | Feasibility | Equivalent | Selection runs old/new | Settled vertices old/new | A* nodes old/new | Runtime median old/new (ms) | Delta new-old (ms) | Faster? |
|---|---|---:|---:|---:|---:|---:|---:|---|
| feasible_000_k3_l1_none_compact_seed202611030000 | optimal | True | 3/2 | 13/13 | 4/4 | 0.090409/0.087779 | -0.002630 | yes |
| feasible_001_k3_l1_sparse_widely_separated_seed202611031000 | optimal | True | 3/2 | 587/391 | 96/96 | 0.304007/0.261540 | -0.042467 | yes |
| feasible_002_k3_l1_medium_asymmetric_seed202611032000 | optimal | True | 3/2 | 409/206 | 105/105 | 0.264347/0.208815 | -0.055532 | yes |
| feasible_003_k3_l1_corridor_branch_heavy_seed202611033000 | optimal | True | 3/2 | 386/234 | 119/119 | 0.260374/0.219179 | -0.041195 | yes |
| feasible_004_k3_l1_chokepoint_barrier_sides_seed202611034000 | optimal | True | 3/2 | 190/142 | 50/50 | 0.180902/0.167132 | -0.013770 | yes |
| feasible_005_k3_l2_none_widely_separated_seed202611035000 | optimal | True | 3/2 | 819/549 | 68/68 | 0.446343/0.352895 | -0.093448 | yes |
| feasible_006_k3_l2_sparse_asymmetric_seed202611036000 | optimal | True | 3/2 | 474/264 | 96/96 | 0.337999/0.232460 | -0.105539 | yes |
| feasible_007_k3_l2_medium_branch_heavy_seed202611037000 | optimal | True | 3/2 | 896/529 | 96/96 | 0.517757/0.386636 | -0.131121 | yes |
| feasible_008_k3_l2_corridor_barrier_sides_seed202611038000 | optimal | True | 3/2 | 262/170 | 67/67 | 0.234964/0.204319 | -0.030645 | yes |
| feasible_009_k3_l2_chokepoint_compact_seed202611039000 | optimal | True | 3/2 | 104/60 | 4/4 | 0.119520/0.096082 | -0.023438 | yes |
| feasible_010_k3_l3_none_asymmetric_seed202611040000 | optimal | True | 3/2 | 310/168 | 72/72 | 0.257896/0.185156 | -0.072740 | yes |
| feasible_011_k3_l3_sparse_branch_heavy_seed202611041000 | optimal | True | 3/2 | 297/222 | 34/34 | 0.251579/0.206275 | -0.045304 | yes |
| feasible_012_k3_l3_medium_barrier_sides_seed202611042000 | optimal | True | 3/2 | 931/576 | 113/113 | 0.355122/0.317466 | -0.037656 | yes |
| feasible_013_k3_l3_corridor_compact_seed202611043000 | optimal | True | 3/2 | 201/116 | 23/23 | 0.169728/0.140368 | -0.029360 | yes |
| feasible_014_k3_l3_chokepoint_widely_separated_seed202611044000 | optimal | True | 3/2 | 265/153 | 27/27 | 0.198602/0.158189 | -0.040413 | yes |
| feasible_015_k4_l1_none_branch_heavy_seed202611045000 | optimal | True | 6/3 | 1197/652 | 82/82 | 0.473001/0.281389 | -0.191612 | yes |
| feasible_016_k4_l1_sparse_barrier_sides_seed202611046000 | optimal | True | 6/3 | 771/342 | 79/79 | 0.244643/0.242786 | -0.001857 | yes |
| feasible_017_k4_l1_medium_compact_seed202611047000 | optimal | True | 6/3 | 36/23 | 6/6 | 0.077045/0.089420 | 0.012375 | no |
| feasible_018_k4_l1_corridor_widely_separated_seed202611048000 | optimal | True | 6/3 | 726/361 | 43/43 | 0.358588/0.263125 | -0.095463 | yes |
| feasible_019_k4_l1_chokepoint_asymmetric_seed202611049000 | optimal | True | 6/3 | 238/85 | 54/54 | 0.130698/0.129084 | -0.001614 | yes |
| feasible_020_k4_l2_none_barrier_sides_seed202611050000 | optimal | True | 6/3 | 1152/489 | 60/60 | 0.591465/0.234858 | -0.356607 | yes |
| feasible_021_k4_l2_sparse_compact_seed202611051000 | optimal | True | 6/3 | 223/99 | 6/6 | 0.191030/0.116282 | -0.074748 | yes |
| feasible_022_k4_l2_medium_widely_separated_seed202611052000 | optimal | True | 6/3 | 2070/957 | 81/81 | 0.984965/0.585571 | -0.399394 | yes |
| feasible_023_k4_l2_corridor_asymmetric_seed202611053000 | optimal | True | 6/3 | 618/221 | 59/59 | 0.248686/0.196115 | -0.052571 | yes |
| feasible_024_k4_l2_chokepoint_branch_heavy_seed202611054000 | optimal | True | 6/3 | 564/288 | 43/43 | 0.347809/0.261456 | -0.086353 | yes |
| feasible_025_k4_l3_none_compact_seed202611055000 | optimal | True | 6/3 | 214/99 | 6/6 | 0.213986/0.121860 | -0.092126 | yes |
| feasible_026_k4_l3_sparse_widely_separated_seed202611056000 | optimal | True | 6/3 | 1223/557 | 91/91 | 0.485681/0.369092 | -0.116589 | yes |
| feasible_027_k4_l3_medium_asymmetric_seed202611057000 | optimal | True | 6/3 | 305/116 | 33/33 | 0.241572/0.157552 | -0.084020 | yes |
| feasible_028_k4_l3_corridor_branch_heavy_seed202611058000 | optimal | True | 6/3 | 676/305 | 61/61 | 0.405559/0.252432 | -0.153127 | yes |
| feasible_029_k4_l3_chokepoint_barrier_sides_seed202611059000 | optimal | True | 6/3 | 1108/521 | 73/73 | 0.360289/0.302272 | -0.058017 | yes |
| feasible_030_k5_l1_none_widely_separated_seed202611060000 | optimal | True | 10/4 | 858/336 | 82/82 | 0.357255/0.268312 | -0.088943 | yes |
| feasible_031_k5_l1_sparse_asymmetric_seed202611061000 | optimal | True | 10/4 | 572/158 | 78/78 | 0.328233/0.180386 | -0.147847 | yes |
| feasible_032_k5_l1_medium_branch_heavy_seed202611062000 | optimal | True | 10/4 | 1590/620 | 60/60 | 0.783878/0.360640 | -0.423238 | yes |
| feasible_033_k5_l1_corridor_barrier_sides_seed202611063000 | optimal | True | 10/4 | 690/251 | 54/54 | 0.250008/0.227847 | -0.022161 | yes |
| feasible_034_k5_l1_chokepoint_compact_seed202611064000 | optimal | True | 10/4 | 79/32 | 8/8 | 0.142645/0.106543 | -0.036102 | yes |
| feasible_035_k5_l2_none_asymmetric_seed202611065000 | optimal | True | 10/4 | 1944/496 | 149/149 | 0.754385/0.353541 | -0.400844 | yes |
| feasible_036_k5_l2_sparse_branch_heavy_seed202611066000 | optimal | True | 10/4 | 1174/506 | 25/25 | 0.593276/0.351089 | -0.242187 | yes |
| feasible_037_k5_l2_medium_barrier_sides_seed202611067000 | optimal | True | 10/4 | 806/293 | 37/37 | 0.469098/0.244938 | -0.224160 | yes |
| feasible_038_k5_l2_corridor_compact_seed202611068000 | optimal | True | 10/4 | 2521/671 | 113/113 | 1.347903/0.473779 | -0.874124 | yes |
| feasible_039_k5_l2_chokepoint_widely_separated_seed202611069000 | optimal | True | 10/4 | 4111/1487 | 247/247 | 2.120121/0.943659 | -1.176462 | yes |
| feasible_040_k5_l3_none_branch_heavy_seed202611070000 | optimal | True | 10/4 | 2880/1176 | 39/39 | 1.527805/0.618540 | -0.909265 | yes |
| feasible_041_k5_l3_sparse_barrier_sides_seed202611071000 | optimal | True | 10/4 | 1107/443 | 82/82 | 0.585400/0.298804 | -0.286596 | yes |
| feasible_042_k5_l3_medium_compact_seed202611072000 | optimal | True | 10/4 | 492/175 | 16/16 | 0.345196/0.190393 | -0.154803 | yes |
| feasible_043_k5_l3_corridor_widely_separated_seed202611073000 | optimal | True | 10/4 | 1001/359 | 53/53 | 0.544562/0.204315 | -0.340247 | yes |
| feasible_044_k5_l3_chokepoint_asymmetric_seed202611074000 | optimal | True | 10/4 | 729/211 | 40/40 | 0.417336/0.209813 | -0.207523 | yes |
| feasible_045_k6_l1_none_barrier_sides_seed202611075000 | optimal | True | 15/5 | 1289/423 | 66/66 | 0.465839/0.204268 | -0.261571 | yes |
| feasible_046_k6_l1_sparse_compact_seed202611076000 | optimal | True | 15/5 | 107/39 | 10/10 | 0.207141/0.132118 | -0.075023 | yes |
| feasible_047_k6_l1_medium_widely_separated_seed202611077000 | optimal | True | 15/5 | 1733/530 | 95/95 | 0.749568/0.306366 | -0.443202 | yes |
| feasible_048_k6_l1_corridor_asymmetric_seed202611078000 | optimal | True | 15/5 | 723/159 | 97/97 | 0.367744/0.198624 | -0.169120 | yes |
| feasible_049_k6_l1_chokepoint_branch_heavy_seed202611079000 | optimal | True | 15/5 | 1993/582 | 33/33 | 0.714803/0.327176 | -0.387627 | yes |
| feasible_050_k6_l2_none_compact_seed202611080000 | optimal | True | 15/5 | 492/145 | 10/10 | 0.250970/0.130140 | -0.120830 | yes |
| feasible_051_k6_l2_sparse_widely_separated_seed202611081000 | optimal | True | 15/5 | 1303/426 | 57/57 | 0.696316/0.323368 | -0.372948 | yes |
| feasible_052_k6_l2_medium_asymmetric_seed202611082000 | optimal | True | 15/5 | 1377/309 | 62/62 | 0.718015/0.310197 | -0.407818 | yes |
| feasible_053_k6_l2_corridor_branch_heavy_seed202611083000 | optimal | True | 15/5 | 731/238 | 57/57 | 0.460572/0.183505 | -0.277067 | yes |
| feasible_054_k6_l2_chokepoint_barrier_sides_seed202611084000 | optimal | True | 15/5 | 2617/797 | 103/103 | 1.168774/0.365560 | -0.803214 | yes |
| feasible_055_k6_l3_none_widely_separated_seed202611085000 | optimal | True | 15/5 | 2641/729 | 65/65 | 1.105219/0.481067 | -0.624152 | yes |
| feasible_056_k6_l3_sparse_asymmetric_seed202611086000 | optimal | True | 15/5 | 2587/531 | 233/233 | 1.170842/0.305322 | -0.865520 | yes |
| feasible_057_k6_l3_medium_branch_heavy_seed202611087000 | optimal | True | 15/5 | 4050/1388 | 81/81 | 3.097084/0.818874 | -2.278210 | yes |
| feasible_058_k6_l3_corridor_barrier_sides_seed202611088000 | optimal | True | 15/5 | 5730/1809 | 109/109 | 2.499167/1.441502 | -1.057665 | yes |
| feasible_059_k6_l3_chokepoint_compact_seed202611089000 | optimal | True | 15/5 | 564/157 | 10/10 | 0.247918/0.166816 | -0.081102 | yes |
| infeasible_000_k3_l1_seed202612000000 | infeasible | True | 3/2 | 223/141 | 30/30 | 0.108002/0.117296 | 0.009294 | no |
| infeasible_001_k4_l1_seed202612000001 | infeasible | True | 5/2 | 178/47 | 2/2 | 0.070823/0.050356 | -0.020467 | yes |
| infeasible_002_k5_l1_seed202612000002 | infeasible | True | 9/3 | 358/106 | 22/22 | 0.222885/0.091783 | -0.131102 | yes |
| infeasible_003_k6_l1_seed202612000003 | infeasible | True | 12/3 | 1149/249 | 25/25 | 0.469039/0.179665 | -0.289374 | yes |
| infeasible_004_k3_l2_seed202612000004 | infeasible | True | 3/2 | 606/357 | 25/25 | 0.211752/0.220059 | 0.008307 | no |
| infeasible_005_k4_l2_seed202612000005 | infeasible | True | 5/2 | 256/96 | 18/18 | 0.179473/0.113416 | -0.066057 | yes |
| infeasible_006_k5_l2_seed202612000006 | infeasible | True | 7/2 | 1241/343 | 78/78 | 0.544534/0.249256 | -0.295278 | yes |
| infeasible_007_k6_l2_seed202612000007 | infeasible | True | 12/3 | 2012/457 | 29/29 | 0.702902/0.303150 | -0.399752 | yes |
| infeasible_008_k3_l3_seed202612000008 | infeasible | True | 3/2 | 254/136 | 6/6 | 0.157539/0.124980 | -0.032559 | yes |
| infeasible_009_k4_l3_seed202612000009 | infeasible | True | 5/2 | 1064/309 | 7/7 | 0.478925/0.194452 | -0.284473 | yes |
| infeasible_010_k5_l3_seed202612000010 | infeasible | True | 9/3 | 532/130 | 12/12 | 0.304171/0.136184 | -0.167987 | yes |
| infeasible_011_k6_l3_seed202612000011 | infeasible | True | 12/3 | 709/107 | 10/10 | 0.309226/0.084026 | -0.225200 | yes |

## Reproducibility and files

- Experiment root: `benchmarks/steiner/experiment_20261102_multisource`.
- Exact input copies, input SHA-256 values, source/binary hashes, and machine/compiler
  details are recorded in `metadata.json`.
- Raw output JSON and repeated measurements are under `evaluation/raw/` and in
  `raw_runs.csv`; per-layout results are in `paired_results.csv`.
- Fixed fixture outputs and the equivalence audit are retained beside the evaluation.
- Historical experiments are read-only inputs to this run and were not overwritten.
