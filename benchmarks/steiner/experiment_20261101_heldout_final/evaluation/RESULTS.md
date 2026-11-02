# Held-out single-net terminal-ordering evaluation

This frozen evaluation compares only input-order and nearest-next-terminal.
Both use the same A* binary, complete single-net input, numeric net order,
one pass, and planar/VIA costs 1/6. The development split is not scored.

Commit `a319f25b29dd00b9bb51f00696b23a9c4fea6bfa`; machine `x86_64`; compiler `Apple clang version 14.0.3 (clang-1403.0.22.14.1)
Target: x86_64-apple-darwin22.6.0
Thread model: posix
InstalledDir: /Library/Developer/CommandLineTools/usr/bin`.
Seed manifest SHA-256: `150c88f97ba3367628d73697bb584d5bfc987dedada9c161870d03d9dad5beb4`.
Generator config SHA-256: `d9933c8f6a63e9ef2db1eb6b59a85552affc1d86371a3532d40a80cdf9622ea9`.
Measured repetitions per strategy and layout: 11; warmups per strategy and layout: 1.

## Overall results

- Oracle-feasible held-out instances: 60.
- Negative controls proven infeasible by the oracle: 12.
- Success counts: input 60/60; nearest 60/60.
- Mean relative gap among successful routes (denominators are explicit): input 0.07843604146650991; nearest 0.02965155852897832.
- Median relative gap among successful routes: input 0.0; nearest 0.0.
- Paired gap differences (both routed): {'definition': 'nearest relative gap minus input relative gap; both strategies must succeed', 'n_instances': 60, 'mean': -0.0487844829375316, 'median': 0.0, 'bootstrap_95_percentile_ci_for_mean': [-0.07648200850439456, -0.024057317555000166], 'nearest_wins': 20, 'ties': 36, 'input_wins': 4, 'exact_two_sided_sign_test_p': 0.001543879508972168, 'one_sided_only_success_nearest': 0, 'one_sided_only_success_input': 0, 'both_failed': 0}.
- Negative controls: {'count': 12, 'input_successes': 0, 'nearest_successes': 0, 'both_reported_unreachable': 12}.

Successful-route secondary metrics (input vs. nearest; mean / median over 60
feasible layouts): physical cost 27.65 / 27 vs. 26.10 / 26.5; planar
wirelength 21.05 / 22 vs. 20.50 / 22; VIA count 1.10 / 1 vs. 0.93 / 1.
Mean search counts were 3.23 vs. 12.00 and mean expanded nodes were 77.63 vs.
1,161.3. Nearest used more searches and expanded more nodes on all 60 feasible
instances. Per-case wirelength, VIA count, tree-edge count, search effort,
runtime, and termination are retained in `paired_results.csv` and `raw_runs.csv`.

A relative gap is `(router physical cost - oracle optimum) / oracle optimum`.
Zero-optimum cases have a null relative gap; they are retained and reported
separately. Failed routes have no physical cost or gap. A one-sided success
or a double failure is counted separately and not silently omitted.

## Stratified results

The following strata use layout-level observations. Means of gaps use
successful routes only, with success counts shown in each row; paired gap
deltas require both strategies to succeed.

| Stratum | Group | Instances | Feasible/infeasible | Input success | Nearest success | Input mean gap | Nearest mean gap | Paired n | Nearest wins | Ties | Input wins | Mean nodes input/nearest |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| terminal_count | 3 | 18 | 15/3 | 15 | 15 | 0.06575291829511778 | 0.03965190819410768 | 15 | 3 | 11 | 1 | 73 / 474.53333333333336 |
| terminal_count | 4 | 18 | 15/3 | 15 | 15 | 0.05194768030731685 | 0.017192865160344836 | 15 | 3 | 10 | 2 | 64.2 / 793.2 |
| terminal_count | 5 | 18 | 15/3 | 15 | 15 | 0.11240369209334726 | 0.03928282828282828 | 15 | 7 | 7 | 1 | 86.2 / 1442.4666666666667 |
| terminal_count | 6 | 18 | 15/3 | 15 | 15 | 0.08363987517025777 | 0.02247863247863248 | 15 | 7 | 8 | 0 | 87.13333333333334 / 1935 |
| layers | 1 | 24 | 20/4 | 20 | 20 | 0.0516327628041183 | 0.03356835172500134 | 20 | 3 | 14 | 3 | 64.85 / 770.4 |
| layers | 2 | 24 | 20/4 | 20 | 20 | 0.05708267174770007 | 0.009124579124579126 | 20 | 7 | 13 | 0 | 85.65 / 1284.9 |
| layers | 3 | 24 | 20/4 | 20 | 20 | 0.12659268984771135 | 0.04626174473735449 | 20 | 10 | 9 | 1 | 82.4 / 1428.6 |
| obstacle_mode | chokepoint | 12 | 12/0 | 12 | 12 | 0.022000580053141497 | 0.016560678325384208 | 12 | 3 | 7 | 2 | 60.916666666666664 / 1104.5 |
| obstacle_mode | corridor | 12 | 12/0 | 12 | 12 | 0.03543374925727867 | 0.01494949494949495 | 12 | 3 | 9 | 0 | 85.25 / 1260 |
| obstacle_mode | medium | 12 | 12/0 | 12 | 12 | 0.12072754008237879 | 0.015345765345765344 | 12 | 6 | 5 | 1 | 85.08333333333333 / 1290 |
| obstacle_mode | negative_control | 12 | 0/12 | 0 | 0 | None | None | 0 | 0 | 0 | 0 | None / None |
| obstacle_mode | none | 12 | 12/0 | 12 | 12 | 0.11987109658678285 | 0.03155864197530864 | 12 | 5 | 7 | 0 | 77.91666666666667 / 1209.3333333333333 |
| obstacle_mode | sparse | 12 | 12/0 | 12 | 12 | 0.09414724135296776 | 0.06984321204893845 | 12 | 3 | 8 | 1 | 79 / 942.6666666666666 |
| obstacle_density_band | low_lt_10pct | 29 | 23/6 | 23 | 23 | 0.06380282177645533 | 0.03962834251828673 | 23 | 7 | 15 | 1 | 93.91304347826087 / 1457.3478260869565 |
| obstacle_density_band | moderate_10_to_20pct | 31 | 25/6 | 25 | 25 | 0.07200977712362912 | 0.019557517204576026 | 25 | 8 | 14 | 3 | 62.52 / 865.88 |
| obstacle_density_band | none | 12 | 12/0 | 12 | 12 | 0.11987109658678285 | 0.03155864197530864 | 12 | 5 | 7 | 0 | 77.91666666666667 / 1209.3333333333333 |
| terminal_distribution | asymmetric | 14 | 12/2 | 12 | 12 | 0.056591455578647226 | 0.0 | 12 | 6 | 6 | 0 | 101.5 / 947 |
| terminal_distribution | barrier_sides | 14 | 12/2 | 12 | 12 | 0.09080659258041839 | 0.05305036148173403 | 12 | 5 | 4 | 3 | 84.58333333333333 / 1462.1666666666667 |
| terminal_distribution | branch_heavy | 14 | 12/2 | 12 | 12 | 0.1274919524919525 | 0.04495504495504495 | 12 | 3 | 8 | 1 | 74.16666666666667 / 1430.3333333333333 |
| terminal_distribution | compact | 15 | 12/3 | 12 | 12 | 0.0 | 0.0 | 12 | 0 | 12 | 0 | 21.583333333333332 / 438.5 |
| terminal_distribution | widely_separated | 15 | 12/3 | 12 | 12 | 0.11729020668153146 | 0.050252386208112614 | 12 | 6 | 6 | 0 | 106.33333333333333 / 1528.5 |
| oracle_feasibility | oracle_feasible | 60 | 60/0 | 60 | 60 | 0.07843604146650991 | 0.02965155852897832 | 60 | 20 | 36 | 4 | 77.63333333333334 / 1161.3 |
| oracle_feasibility | oracle_infeasible | 12 | 0/12 | 0 | 0 | None | None | 0 | 0 | 0 | 0 | None / None |

## Runtime and effort

Runtime summary: {'measured_invocations': 1584, 'runtime_value_unique_count': 1583, 'runtime_value_count': 1584, 'runtime_min_ms': 0.030664, 'runtime_median_ms': 0.1224825, 'within_instance_repeat_mad_median_ms': 0.004928999999999996, 'paired_instance_median_delta_nearest_minus_input_ms': {'n_instances': 72, 'mean': 0.21968319444444445, 'median': 0.134576, 'bootstrap_95_percentile_ci_for_mean': [0.162609, 0.28742575000000004]}, 'interpretation': 'router-reported times are microsecond-scale; treat differences as descriptive unless repeat spread is small relative to the effect'}. Repetitions are summarized within
each layout; the layout is the unit in paired comparisons. Router-internal
times are short, so runtime claims are descriptive and must be interpreted
against the reported repeat spread, not as evidence of a general speedup.

Search count and expanded nodes include nearest distance probes as well as
the selected production routes. Physical cost is separately validated.

## Per-instance paired results

| Case | k | Layers | Rows×cols | Obstacle mode/density | Distribution | Oracle/status | Optimum | Input success / cost / gap | Nearest success / cost / gap | Paired gap delta | Outcome | Searches input/nearest | Nodes input/nearest | Runtime median ms input/nearest |
|---|---:|---:|---:|---|---|---|---:|---|---|---:|---|---:|---:|---:|
| feasible_000_k3_l1_none_compact_seed202611030000 | 3 | 1 | 13×17 | none/none | compact | optimal | 2 | True / 2 / 0.0 | True / 2 / 0.0 | 0.0 | both_succeeded | 2/5 | 4/17 | 0.03292/0.042658 |
| feasible_001_k3_l1_sparse_widely_separated_seed202611031000 | 3 | 1 | 13×17 | sparse/low_lt_10pct | widely_separated | optimal | 23 | True / 28 / 0.21739130434782608 | True / 28 / 0.21739130434782608 | 0.0 | both_succeeded | 2/5 | 96/683 | 0.068818/0.151727 |
| feasible_002_k3_l1_medium_asymmetric_seed202611032000 | 3 | 1 | 16×16 | medium/moderate_10_to_20pct | asymmetric | optimal | 27 | True / 27 / 0.0 | True / 27 / 0.0 | 0.0 | both_succeeded | 2/5 | 105/514 | 0.065045/0.122034 |
| feasible_003_k3_l1_corridor_branch_heavy_seed202611033000 | 3 | 1 | 12×14 | corridor/low_lt_10pct | branch_heavy | optimal | 25 | True / 25 / 0.0 | True / 25 / 0.0 | 0.0 | both_succeeded | 2/5 | 119/505 | 0.062886/0.129542 |
| feasible_004_k3_l1_chokepoint_barrier_sides_seed202611034000 | 3 | 1 | 9×11 | chokepoint/moderate_10_to_20pct | barrier_sides | optimal | 17 | True / 18 / 0.058823529411764705 | True / 19 / 0.11764705882352941 | 0.058823529411764705 | both_succeeded | 2/5 | 39/240 | 0.069828/0.123283 |
| feasible_005_k3_l2_none_widely_separated_seed202611035000 | 3 | 2 | 11×18 | none/none | widely_separated | optimal | 30 | True / 30 / 0.0 | True / 30 / 0.0 | 0.0 | both_succeeded | 2/5 | 68/887 | 0.071542/0.206819 |
| feasible_006_k3_l2_sparse_asymmetric_seed202611036000 | 3 | 2 | 10×12 | sparse/low_lt_10pct | asymmetric | optimal | 25 | True / 31 / 0.24 | True / 25 / 0.0 | -0.24 | both_succeeded | 2/5 | 183/570 | 0.078976/0.146918 |
| feasible_007_k3_l2_medium_branch_heavy_seed202611037000 | 3 | 2 | 16×16 | medium/moderate_10_to_20pct | branch_heavy | optimal | 33 | True / 38 / 0.15151515151515152 | True / 33 / 0.0 | -0.15151515151515152 | both_succeeded | 2/5 | 107/992 | 0.117081/0.291057 |
| feasible_008_k3_l2_corridor_barrier_sides_seed202611038000 | 3 | 2 | 7×9 | corridor/moderate_10_to_20pct | barrier_sides | optimal | 22 | True / 23 / 0.045454545454545456 | True / 23 / 0.045454545454545456 | 0.0 | both_succeeded | 2/5 | 49/329 | 0.071559/0.165978 |
| feasible_009_k3_l2_chokepoint_compact_seed202611039000 | 3 | 2 | 7×9 | chokepoint/moderate_10_to_20pct | compact | optimal | 7 | True / 7 / 0.0 | True / 7 / 0.0 | 0.0 | both_succeeded | 2/5 | 4/108 | 0.040127/0.059938 |
| feasible_010_k3_l3_none_asymmetric_seed202611040000 | 3 | 3 | 6×8 | none/none | asymmetric | optimal | 17 | True / 18 / 0.058823529411764705 | True / 17 / 0.0 | -0.058823529411764705 | both_succeeded | 2/5 | 82/382 | 0.077117/0.162729 |
| feasible_011_k3_l3_sparse_branch_heavy_seed202611041000 | 3 | 3 | 9×10 | sparse/low_lt_10pct | branch_heavy | optimal | 14 | True / 17 / 0.21428571428571427 | True / 17 / 0.21428571428571427 | 0.0 | both_succeeded | 2/5 | 34/331 | 0.074588/0.156519 |
| feasible_012_k3_l3_medium_barrier_sides_seed202611042000 | 3 | 3 | 12×14 | medium/moderate_10_to_20pct | barrier_sides | optimal | 31 | True / 31 / 0.0 | True / 31 / 0.0 | 0.0 | both_succeeded | 2/5 | 113/1044 | 0.074302/0.257354 |
| feasible_013_k3_l3_corridor_compact_seed202611043000 | 3 | 3 | 6×8 | corridor/moderate_10_to_20pct | compact | optimal | 14 | True / 14 / 0.0 | True / 14 / 0.0 | 0.0 | both_succeeded | 2/5 | 23/224 | 0.038905/0.084387 |
| feasible_014_k3_l3_chokepoint_widely_separated_seed202611044000 | 3 | 3 | 6×8 | chokepoint/moderate_10_to_20pct | widely_separated | optimal | 24 | True / 24 / 0.0 | True / 24 / 0.0 | 0.0 | both_succeeded | 2/5 | 69/292 | 0.066534/0.100302 |
| feasible_015_k4_l1_none_branch_heavy_seed202611045000 | 4 | 1 | 16×16 | none/none | branch_heavy | optimal | 30 | True / 30 / 0.0 | True / 30 / 0.0 | 0.0 | both_succeeded | 3/9 | 82/1279 | 0.105448/0.364487 |
| feasible_016_k4_l1_sparse_barrier_sides_seed202611046000 | 4 | 1 | 12×14 | sparse/low_lt_10pct | barrier_sides | optimal | 26 | True / 27 / 0.038461538461538464 | True / 29 / 0.11538461538461539 | 0.07692307692307693 | both_succeeded | 3/9 | 54/850 | 0.065487/0.177689 |
| feasible_017_k4_l1_medium_compact_seed202611047000 | 4 | 1 | 12×14 | medium/moderate_10_to_20pct | compact | optimal | 3 | True / 3 / 0.0 | True / 3 / 0.0 | 0.0 | both_succeeded | 3/9 | 6/42 | 0.031925/0.051287 |
| feasible_018_k4_l1_corridor_widely_separated_seed202611048000 | 4 | 1 | 12×14 | corridor/low_lt_10pct | widely_separated | optimal | 34 | True / 37 / 0.08823529411764706 | True / 34 / 0.0 | -0.08823529411764706 | both_succeeded | 3/9 | 87/769 | 0.108735/0.212559 |
| feasible_019_k4_l1_chokepoint_asymmetric_seed202611049000 | 4 | 1 | 9×11 | chokepoint/moderate_10_to_20pct | asymmetric | optimal | 16 | True / 16 / 0.0 | True / 16 / 0.0 | 0.0 | both_succeeded | 2/9 | 53/292 | 0.046988/0.13433 |
| feasible_020_k4_l2_none_barrier_sides_seed202611050000 | 4 | 2 | 10×12 | none/none | barrier_sides | optimal | 27 | True / 35 / 0.2962962962962963 | True / 28 / 0.037037037037037035 | -0.25925925925925924 | both_succeeded | 3/9 | 123/1212 | 0.086004/0.263479 |
| feasible_021_k4_l2_sparse_compact_seed202611051000 | 4 | 2 | 10×12 | sparse/moderate_10_to_20pct | compact | optimal | 8 | True / 8 / 0.0 | True / 8 / 0.0 | 0.0 | both_succeeded | 2/9 | 6/229 | 0.036052/0.129856 |
| feasible_022_k4_l2_medium_widely_separated_seed202611052000 | 4 | 2 | 16×16 | medium/moderate_10_to_20pct | widely_separated | optimal | 46 | True / 46 / 0.0 | True / 46 / 0.0 | 0.0 | both_succeeded | 3/9 | 163/2151 | 0.149093/0.695713 |
| feasible_023_k4_l2_corridor_asymmetric_seed202611053000 | 4 | 2 | 10×12 | corridor/low_lt_10pct | asymmetric | optimal | 21 | True / 21 / 0.0 | True / 21 / 0.0 | 0.0 | both_succeeded | 3/9 | 59/677 | 0.058391/0.250036 |
| feasible_024_k4_l2_chokepoint_branch_heavy_seed202611054000 | 4 | 2 | 10×12 | chokepoint/low_lt_10pct | branch_heavy | optimal | 20 | True / 20 / 0.0 | True / 20 / 0.0 | 0.0 | both_succeeded | 3/9 | 23/607 | 0.059166/0.199005 |
| feasible_025_k4_l3_none_compact_seed202611055000 | 4 | 3 | 9×10 | none/none | compact | optimal | 8 | True / 8 / 0.0 | True / 8 / 0.0 | 0.0 | both_succeeded | 3/9 | 6/220 | 0.034123/0.145293 |
| feasible_026_k4_l3_sparse_widely_separated_seed202611056000 | 4 | 3 | 9×10 | sparse/low_lt_10pct | widely_separated | optimal | 41 | True / 42 / 0.024390243902439025 | True / 42 / 0.024390243902439025 | 0.0 | both_succeeded | 3/9 | 91/1314 | 0.112469/0.418762 |
| feasible_027_k4_l3_medium_asymmetric_seed202611057000 | 4 | 3 | 6×8 | medium/moderate_10_to_20pct | asymmetric | optimal | 18 | True / 23 / 0.2777777777777778 | True / 18 / 0.0 | -0.2777777777777778 | both_succeeded | 2/9 | 60/338 | 0.050789/0.160789 |
| feasible_028_k4_l3_corridor_branch_heavy_seed202611058000 | 4 | 3 | 9×10 | corridor/low_lt_10pct | branch_heavy | optimal | 22 | True / 22 / 0.0 | True / 22 / 0.0 | 0.0 | both_succeeded | 3/9 | 61/737 | 0.069255/0.242291 |
| feasible_029_k4_l3_chokepoint_barrier_sides_seed202611059000 | 4 | 3 | 9×10 | chokepoint/moderate_10_to_20pct | barrier_sides | optimal | 37 | True / 39 / 0.05405405405405406 | True / 40 / 0.08108108108108109 | 0.02702702702702703 | both_succeeded | 3/9 | 89/1181 | 0.072517/0.326712 |
| feasible_030_k5_l1_none_widely_separated_seed202611060000 | 5 | 1 | 9×11 | none/none | widely_separated | optimal | 24 | True / 32 / 0.3333333333333333 | True / 27 / 0.125 | -0.20833333333333331 | both_succeeded | 4/14 | 88/940 | 0.109438/0.2365 |
| feasible_031_k5_l1_sparse_asymmetric_seed202611061000 | 5 | 1 | 12×14 | sparse/low_lt_10pct | asymmetric | optimal | 18 | True / 18 / 0.0 | True / 18 / 0.0 | 0.0 | both_succeeded | 4/14 | 78/650 | 0.063744/0.145502 |
| feasible_032_k5_l1_medium_branch_heavy_seed202611062000 | 5 | 1 | 16×16 | medium/moderate_10_to_20pct | branch_heavy | optimal | 33 | True / 33 / 0.0 | True / 34 / 0.030303030303030304 | 0.030303030303030304 | both_succeeded | 3/14 | 59/1650 | 0.071436/0.302943 |
| feasible_033_k5_l1_corridor_barrier_sides_seed202611063000 | 5 | 1 | 9×11 | corridor/low_lt_10pct | barrier_sides | optimal | 25 | True / 26 / 0.04 | True / 26 / 0.04 | 0.0 | both_succeeded | 3/14 | 69/744 | 0.096056/0.257605 |
| feasible_034_k5_l1_chokepoint_compact_seed202611064000 | 5 | 1 | 9×11 | chokepoint/moderate_10_to_20pct | compact | optimal | 4 | True / 4 / 0.0 | True / 4 / 0.0 | 0.0 | both_succeeded | 4/14 | 8/87 | 0.047782/0.097095 |
| feasible_035_k5_l2_none_asymmetric_seed202611065000 | 5 | 2 | 16×16 | none/none | asymmetric | optimal | 30 | True / 30 / 0.0 | True / 30 / 0.0 | 0.0 | both_succeeded | 3/14 | 149/2093 | 0.086067/0.393191 |
| feasible_036_k5_l2_sparse_branch_heavy_seed202611066000 | 5 | 2 | 10×12 | sparse/low_lt_10pct | branch_heavy | optimal | 26 | True / 26 / 0.0 | True / 26 / 0.0 | 0.0 | both_succeeded | 4/14 | 25/1199 | 0.072092/0.313686 |
| feasible_037_k5_l2_medium_barrier_sides_seed202611067000 | 5 | 2 | 7×9 | medium/moderate_10_to_20pct | barrier_sides | optimal | 24 | True / 28 / 0.16666666666666666 | True / 24 / 0.0 | -0.16666666666666666 | both_succeeded | 4/14 | 48/843 | 0.099971/0.225435 |
| feasible_038_k5_l2_corridor_compact_seed202611068000 | 5 | 2 | 16×16 | corridor/low_lt_10pct | compact | optimal | 29 | True / 29 / 0.0 | True / 29 / 0.0 | 0.0 | both_succeeded | 3/14 | 159/2634 | 0.083536/0.483383 |
| feasible_039_k5_l2_chokepoint_widely_separated_seed202611069000 | 5 | 2 | 16×16 | chokepoint/low_lt_10pct | widely_separated | optimal | 58 | True / 63 / 0.08620689655172414 | True / 58 / 0.0 | -0.08620689655172414 | both_succeeded | 4/14 | 234/4358 | 0.13621/1.366159 |
| feasible_040_k5_l3_none_branch_heavy_seed202611070000 | 5 | 3 | 12×14 | none/none | branch_heavy | optimal | 30 | True / 48 / 0.6 | True / 35 / 0.16666666666666666 | -0.43333333333333335 | both_succeeded | 4/14 | 149/2919 | 0.129969/0.94461 |
| feasible_041_k5_l3_sparse_barrier_sides_seed202611071000 | 5 | 3 | 6×8 | sparse/low_lt_10pct | barrier_sides | optimal | 30 | True / 38 / 0.26666666666666666 | True / 35 / 0.16666666666666666 | -0.1 | both_succeeded | 4/14 | 79/1189 | 0.078215/0.393026 |
| feasible_042_k5_l3_medium_compact_seed202611072000 | 5 | 3 | 9×10 | medium/moderate_10_to_20pct | compact | optimal | 13 | True / 13 / 0.0 | True / 13 / 0.0 | 0.0 | both_succeeded | 4/14 | 16/508 | 0.049473/0.157744 |
| feasible_043_k5_l3_corridor_widely_separated_seed202611073000 | 5 | 3 | 6×8 | corridor/moderate_10_to_20pct | widely_separated | optimal | 33 | True / 38 / 0.15151515151515152 | True / 35 / 0.06060606060606061 | -0.09090909090909091 | both_succeeded | 4/14 | 81/1054 | 0.078276/0.375206 |
| feasible_044_k5_l3_chokepoint_asymmetric_seed202611074000 | 5 | 3 | 6×8 | chokepoint/moderate_10_to_20pct | asymmetric | optimal | 24 | True / 25 / 0.041666666666666664 | True / 24 / 0.0 | -0.041666666666666664 | both_succeeded | 4/14 | 51/769 | 0.058074/0.23814 |
| feasible_045_k6_l1_none_barrier_sides_seed202611075000 | 6 | 1 | 9×11 | none/none | barrier_sides | optimal | 27 | True / 27 / 0.0 | True / 27 / 0.0 | 0.0 | both_succeeded | 5/20 | 73/1355 | 0.075995/0.25867 |
| feasible_046_k6_l1_sparse_compact_seed202611076000 | 6 | 1 | 16×16 | sparse/low_lt_10pct | compact | optimal | 5 | True / 5 / 0.0 | True / 5 / 0.0 | 0.0 | both_succeeded | 3/20 | 8/117 | 0.0529/0.134008 |
| feasible_047_k6_l1_medium_widely_separated_seed202611077000 | 6 | 1 | 12×14 | medium/moderate_10_to_20pct | widely_separated | optimal | 39 | True / 49 / 0.2564102564102564 | True / 40 / 0.02564102564102564 | -0.23076923076923075 | both_succeeded | 5/20 | 141/1828 | 0.112079/0.349285 |
| feasible_048_k6_l1_corridor_asymmetric_seed202611078000 | 6 | 1 | 12×14 | corridor/low_lt_10pct | asymmetric | optimal | 21 | True / 21 / 0.0 | True / 21 / 0.0 | 0.0 | both_succeeded | 3/20 | 96/820 | 0.063273/0.179753 |
| feasible_049_k6_l1_chokepoint_branch_heavy_seed202611079000 | 6 | 1 | 13×17 | chokepoint/low_lt_10pct | branch_heavy | optimal | 28 | True / 28 / 0.0 | True / 28 / 0.0 | 0.0 | both_succeeded | 4/20 | 32/2026 | 0.09069/0.55616 |
| feasible_050_k6_l2_none_compact_seed202611080000 | 6 | 2 | 11×18 | none/none | compact | optimal | 10 | True / 10 / 0.0 | True / 10 / 0.0 | 0.0 | both_succeeded | 4/20 | 10/502 | 0.050644/0.279893 |
| feasible_051_k6_l2_sparse_widely_separated_seed202611081000 | 6 | 2 | 7×9 | sparse/low_lt_10pct | widely_separated | optimal | 30 | True / 33 / 0.1 | True / 33 / 0.1 | 0.0 | both_succeeded | 5/20 | 57/1360 | 0.096976/0.323631 |
| feasible_052_k6_l2_medium_asymmetric_seed202611082000 | 6 | 2 | 11×18 | medium/moderate_10_to_20pct | asymmetric | optimal | 31 | True / 32 / 0.03225806451612903 | True / 31 / 0.0 | -0.03225806451612903 | both_succeeded | 5/20 | 65/1439 | 0.122675/0.372255 |
| feasible_053_k6_l2_corridor_branch_heavy_seed202611083000 | 6 | 2 | 7×9 | corridor/moderate_10_to_20pct | branch_heavy | optimal | 25 | True / 25 / 0.0 | True / 25 / 0.0 | 0.0 | both_succeeded | 4/20 | 61/788 | 0.070736/0.234728 |
| feasible_054_k6_l2_chokepoint_barrier_sides_seed202611084000 | 6 | 2 | 10×12 | chokepoint/low_lt_10pct | barrier_sides | optimal | 43 | True / 44 / 0.023255813953488372 | True / 43 / 0.0 | -0.023255813953488372 | both_succeeded | 5/20 | 120/2720 | 0.143111/0.601898 |
| feasible_055_k6_l3_none_widely_separated_seed202611085000 | 6 | 3 | 9×10 | none/none | widely_separated | optimal | 40 | True / 46 / 0.15 | True / 42 / 0.05 | -0.09999999999999999 | both_succeeded | 5/20 | 101/2706 | 0.094774/0.548534 |
| feasible_056_k6_l3_sparse_asymmetric_seed202611086000 | 6 | 3 | 12×14 | sparse/low_lt_10pct | asymmetric | optimal | 35 | True / 36 / 0.02857142857142857 | True / 35 / 0.0 | -0.02857142857142857 | both_succeeded | 4/20 | 237/2820 | 0.144608/0.593552 |
| feasible_057_k6_l3_medium_branch_heavy_seed202611087000 | 6 | 3 | 12×14 | medium/moderate_10_to_20pct | branch_heavy | optimal | 39 | True / 61 / 0.5641025641025641 | True / 44 / 0.1282051282051282 | -0.4358974358974359 | both_succeeded | 5/20 | 138/4131 | 0.112545/1.348634 |
| feasible_058_k6_l3_corridor_barrier_sides_seed202611088000 | 6 | 3 | 12×14 | corridor/low_lt_10pct | barrier_sides | optimal | 60 | True / 66 / 0.1 | True / 62 / 0.03333333333333333 | -0.06666666666666668 | both_succeeded | 5/20 | 159/5839 | 0.126288/1.554459 |
| feasible_059_k6_l3_chokepoint_compact_seed202611089000 | 6 | 3 | 6×8 | chokepoint/moderate_10_to_20pct | compact | optimal | 15 | True / 15 / 0.0 | True / 15 / 0.0 | 0.0 | both_succeeded | 4/20 | 9/574 | 0.052598/0.255237 |
| infeasible_000_k3_l1_seed202612000000 | 3 | 1 | 12×14 | negative_control/low_lt_10pct | compact | infeasible | — | False / — / — | False / — / — | — | negative_control | 2/4 | 114/253 | 0.076728/0.070842 |
| infeasible_001_k4_l1_seed202612000001 | 4 | 1 | 9×11 | negative_control/moderate_10_to_20pct | widely_separated | infeasible | — | False / — / — | False / — / — | — | negative_control | 3/6 | 90/180 | 0.036826/0.046554 |
| infeasible_002_k5_l1_seed202612000002 | 5 | 1 | 9×11 | negative_control/moderate_10_to_20pct | asymmetric | infeasible | — | False / — / — | False / — / — | — | negative_control | 4/11 | 110/380 | 0.065384/0.141494 |
| infeasible_003_k6_l1_seed202612000003 | 6 | 1 | 13×17 | negative_control/low_lt_10pct | branch_heavy | infeasible | — | False / — / — | False / — / — | — | negative_control | 5/14 | 331/1174 | 0.102423/0.196819 |
| infeasible_004_k3_l2_seed202612000004 | 3 | 2 | 16×16 | negative_control/low_lt_10pct | barrier_sides | infeasible | — | False / — / — | False / — / — | — | negative_control | 2/4 | 281/631 | 0.13586/0.151672 |
| infeasible_005_k4_l2_seed202612000005 | 4 | 2 | 7×9 | negative_control/moderate_10_to_20pct | compact | infeasible | — | False / — / — | False / — / — | — | negative_control | 3/6 | 126/274 | 0.0603/0.080967 |
| infeasible_006_k5_l2_seed202612000006 | 5 | 2 | 11×18 | negative_control/low_lt_10pct | widely_separated | infeasible | — | False / — / — | False / — / — | — | negative_control | 4/8 | 618/1319 | 0.168524/0.347484 |
| infeasible_007_k6_l2_seed202612000007 | 6 | 2 | 11×18 | negative_control/low_lt_10pct | asymmetric | infeasible | — | False / — / — | False / — / — | — | negative_control | 5/14 | 561/2041 | 0.155221/0.579717 |
| infeasible_008_k3_l3_seed202612000008 | 3 | 3 | 9×10 | negative_control/moderate_10_to_20pct | branch_heavy | infeasible | — | False / — / — | False / — / — | — | negative_control | 2/4 | 126/260 | 0.07384/0.114999 |
| infeasible_009_k4_l3_seed202612000009 | 4 | 3 | 12×14 | negative_control/low_lt_10pct | barrier_sides | infeasible | — | False / — / — | False / — / — | — | negative_control | 3/6 | 511/1071 | 0.143004/0.212458 |
| infeasible_010_k5_l3_seed202612000010 | 5 | 3 | 6×8 | negative_control/moderate_10_to_20pct | compact | infeasible | — | False / — / — | False / — / — | — | negative_control | 4/11 | 166/544 | 0.075659/0.209534 |
| infeasible_011_k6_l3_seed202612000011 | 6 | 3 | 6×8 | negative_control/moderate_10_to_20pct | widely_separated | infeasible | — | False / — / — | False / — / — | — | negative_control | 4/14 | 228/719 | 0.118859/0.149724 |

## Interpretation and limitations

The paired bootstrap interval and exact sign test use layouts as the
statistical unit. They do not turn hand-generated grid layouts into a
representative industrial workload. Report stratified outcomes and failures
alongside aggregates. Runtime is especially susceptible to clock and process
noise at this scale. This experiment evaluates the frozen existing methods;
it does not tune or introduce a strategy.

Complete raw inputs, candidates and rejection reasons, oracle witnesses,
route JSONs, hashes, raw repetitions, and metadata are stored beside this
report. See `paired_results.csv`, `raw_runs.csv`, `oracle_results.json`, and
`metadata.json`.
