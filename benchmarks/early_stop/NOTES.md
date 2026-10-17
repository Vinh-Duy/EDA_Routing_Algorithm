# Early termination and input protection

This update removes repeated, unchanged BFS searches and prevents output paths
from destroying the input layout. The baseline is commit `62022a0`; its measured
results remain in `benchmarks/` and `benchmarks/single_pass/`. Current observations,
source/executable hashes, and figures are kept separately in this directory.

## Changes

- The routing strategy advertises whether congestion changes can affect its paths.
  BFS returns false; other strategies default to true. With fixed inputs and net
  order, BFS ignores both occupancy and history, so rerouting cannot change its
  paths. The driver stops after the first conflicted BFS pass. A* and Dijkstra
  continue to use the configured pass budget and history updates.
- JSON records `termination_reason`, also retained in raw and summary CSV files.
  Conflicted early stops remain unsuccessful and return exit code 2. A failure
  does not prove general infeasibility. `search_cost` describes the pass actually
  executed, so it no longer includes history from skipped BFS passes.
- CLI input/output equivalence checks reject the same file through direct paths,
  relative aliases, symlinks, or hardlinks before opening the output stream.
  Replacing a distinct output file remains supported. This guards ordinary path
  mistakes; it does not implement atomic writes or protect against concurrent
  filesystem changes between checking and writing.
- The independent checker now rejects incorrect cost-model metadata and
  inconsistent termination reasons. Schema-v2 historical outputs without the
  new reason field remain accepted.

## Measured outcome

The current suite contains 840 measured invocations: 14 layouts, three algorithms,
20 repetitions each, plus 42 excluded warm-ups. There are 640 routing successes,
200 correctly reported routing failures, zero execution/verification errors, and
zero locally invalid paths. Every pair has deterministic non-timing output.

All 42 dataset/algorithm pairs retain the baseline route geometry, validity,
physical cost, and conflict counts. A* and Dijkstra retain all prior non-timing
outputs except the new reason field. Five conflicted BFS instances go from ten
passes to one, reducing expanded nodes by exactly 90%:

- `chip_layout_hell`: 26,890 → 2,689 expanded nodes; current median 0.645570 ms.
- `chip_layout_test`: 480 → 48 expanded nodes; current median 0.037672 ms.
- `congestion`: 310 → 31 expanded nodes; current median 0.034328 ms.
- `impossible_overlap`: 60 → 6 expanded nodes; current median 0.025284 ms.
- `stress_seeded`: 589,700 → 58,970 expanded nodes; current median 10.910001 ms.

This is a reduction in redundant work, not an improvement in route feasibility.
The BFS conflicts remain. These measurements were collected in a separate run
from the baseline, so wall-clock ratios are not controlled paired speedups.
The exact node counts and unchanged paths are the evidence for the improvement.
Full runtime medians, means, sample deviations, minima, and maxima are in
[summary.csv](summary.csv); all observations are in [results.csv](results.csv).
[RESULTS.md](RESULTS.md) and [figures/](figures/) retain failed cases explicitly.

## Verification

- Release build passed with C++17 and warnings enabled.
- All 14 C++ test groups and eight Python tests passed, with no skips.
- All 14 C++ groups passed AddressSanitizer and UndefinedBehaviorSanitizer.
- A regression verifies BFS stops even with a budget of 10,000 passes, preserving
  conflicts, geometry, expanded nodes, and first-pass search costs.
- Weighted-search regressions verify that A* and Dijkstra still resolve the
  congestion fixture with multiple passes.
- Input/output alias tests verify original layout bytes survive every rejection.
  The original overwrite was reproduced with the saved baseline binary using a
  temporary fixture before testing the fix.
- All six original and eight generated layouts run under all three algorithms.
- Current source and executable SHA-256 hashes were checked against metadata.
- All 42 first measured route outputs were compared against baseline paths;
  the harness checks all repetitions for independent validity and determinism.

## Reproduction

From the repository root, with the README's Python dependencies installed:

```sh
make test PYTHON=.venv/bin/python
make sanitize
.venv/bin/python benchmarks/run_benchmarks.py --repetitions 20 --results-dir benchmarks/early_stop
.venv/bin/python benchmarks/plot_results.py --csv benchmarks/early_stop/results.csv --output-dir benchmarks/early_stop/figures
```

To reproduce the historical behavior, use a separate checkout of `62022a0`.
Timing varies with machine load; regenerated results replace this directory's
measurements. The fixed net order, two-pin model, and weighted rerouting heuristic
remain limitations. Selective rip-up and alternate net orders require separate
experiments before making routing-quality claims.
