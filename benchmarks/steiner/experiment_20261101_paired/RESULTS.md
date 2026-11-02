# Paired single-net terminal-ordering experiment

Each pair uses identical layout bytes, terminal coordinates, obstacles, planar/VIA weights, A* search, numeric net scheduling, and one routing pass. Only the terminal attachment strategy changes. The input-order strategy is the existing default; nearest is opt-in. The exact reference is the single-net Dreyfus-Wagner oracle. No multi-net optimality claim is made.

Commit `a319f25b29dd00b9bb51f00696b23a9c4fea6bfa`; machine `x86_64`; compiler `Apple clang version 14.0.3 (clang-1403.0.22.14.1)
Target: x86_64-apple-darwin22.6.0
Thread model: posix
InstalledDir: /Library/Developer/CommandLineTools/usr/bin`; build flags `-std=c++17 -O2 -Wall -Wextra -Wpedantic`.
Measured repetitions per strategy/case: 3; one warm-up retained but excluded. Runtime is router-reported milliseconds; process wall time is separately retained.
All layouts are fixed, hand-designed fixtures (no random seed). Raw route JSONs, per-invocation metrics, SHA-256 hashes, and exact oracle witnesses are retained beside this report.

| Case | Oracle | Optimum | Input success/cost/gap | Nearest success/cost/gap | Input wire/VIA/edges/branches | Nearest wire/VIA/edges/branches | Input searches/nodes/median ms | Nearest searches/nodes/median ms | Termination (input / nearest) | Paired deltas (nearest minus input): cost/searches/nodes/median ms |
|---|---|---:|---|---|---|---|---|---|---|---|
| branch_sharing_saves_cost | optimal | 4 | 1.0/4/0 | 1.0/4/0 | 4/0/4/1 | 4/0/4/1 | 2/6/0.028791 | 5/27/0.036449 | success / success | 0/3/21/0.007658000000000002 |
| disconnected | infeasible | — | 0.0/—/— | 0.0/—/— | 0/0/0/0 | 0/0/0/0 | 1/1/0.019316 | 1/1/0.019669 | unreachable / unreachable | —/0/0/0.00035299999999999915 |
| obstacle_branch | optimal | 7 | 1.0/7/0 | 1.0/7/0 | 7/0/7/1 | 7/0/7/1 | 2/11/0.039357 | 5/34/0.048484 | success / success | 0/3/23/0.009126999999999996 |
| planar_branching | optimal | 4 | 1.0/4/0 | 1.0/4/0 | 4/0/4/1 | 4/0/4/1 | 4/8/0.046575 | 14/63/0.087204 | success / success | 0/10/55/0.040629000000000005 |
| required_via | optimal | 6 | 1.0/6/0 | 1.0/6/0 | 0/1/1/0 | 0/1/1/0 | 1/2/0.0226 | 2/4/0.024242 | success / success | 0/1/2/0.001642000000000001 |
| via_beats_planar_detour | optimal | 18 | 1.0/18/0 | 1.0/18/0 | 6/2/8/0 | 6/2/8/0 | 1/24/0.033844 | 2/92/0.046943 | success / success | 0/1/68/0.013099 |

Paired feasible cost differences (nearest minus input): [0, 0, 0, 0, 0].
Per-instance search-count differences: [3, 0, 3, 10, 1, 1]; expanded-node differences: [21, 0, 23, 55, 2, 68].
Per-instance median-runtime differences (nearest minus input, ms): [0.007658000000000002, 0.00035299999999999915, 0.009126999999999996, 0.040629000000000005, 0.001642000000000001, 0.013099]; median across these fixed cases: 0.008392499999999999.
The fixed execution order alternates strategy order between repetitions; these small local runtime differences remain descriptive and noisy.
Recorded invocation count: 48; measured rows exclude 12 warm-ups.
A zero-cost optimum uses a null relative gap; infeasible and failed-router cases do not receive a physical-cost gap. Repeated timings are repeated measurements of these layouts, not additional independent instances.

See `raw_runs.csv`, `paired_results.csv`, `metadata.json`, and `raw/` for the complete record.
