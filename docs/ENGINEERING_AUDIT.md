# Engineering quality audit — 2026-10-17

## VERIFIED — Starting point and scope

Initial commit: `62022a05a95c8a9a536586db1b8c6f8b40fbdd1c` (`main`).
There were 13 modified tracked files plus untracked `benchmarks/early_stop/`.
The exact [initial status](verification/initial-status.txt) was recorded before
editing. Those changes already included BFS early termination, input/output alias
protection, additional tests, and a third 840-observation suite. They were treated
as the user's starting work, not discarded or attributed to this audit.

The review covered all source headers/main, tests, Makefile, requirements, ignore
rules, six original datasets, generated fixtures, JSON example, benchmark scripts,
CSV/metadata/report files, and visualization. No separate RTL repository was read
or changed. No commit, push, PR, or remote workflow run was performed during the
initial local audit. The subsequent hosted CI result is recorded separately below.

## VERIFIED — Baseline checks

[Baseline commands and return codes](verification/baseline.json) and the associated
`baseline-*.log` files record the actual execution:

- `make`: exit 0; the existing executable was up to date.
- `make test`: exit 0; 14 C++ groups, seven Python tests passed, one Plotly test skipped.
- `make test PYTHON=.venv/bin/python`: exit 0; 14 C++ groups and all eight Python tests passed.
- `make sanitize`: exit 0; all 14 C++ groups passed ASan/UBSan.
- Compiler: Apple Clang 14.0.3; system and virtualenv Python: 3.10.11.

The normal baseline logs contain no compiler warnings. A separate deliberately
malformed-layout probe exited with signal 6 and an ASan heap-buffer-overflow
report; its symbolizer also emitted environment warnings. That probe confirmed
the API defect below and is not counted as a passing baseline test.

## VERIFIED — Algorithm and termination audit

A* and Dijkstra call the same weighted search function. A* uses
`h = |dx| + |dy| + 6|dz|`, while Dijkstra uses zero. Every legal move costs at least
its planar/VIA component; all occupancy/history additions are nonnegative.
Therefore the heuristic is a lower bound and consistent for a fixed search
context. Both stop at a non-stale goal removal. The queue skips stale g scores,
and guarded predecessor reconstruction returns source-to-target paths. Two
hundred seeded contexts are compared with an independently written Bellman–Ford
oracle; BFS is checked against unit edge costs rather than the weighted objective.

Under parsed layouts, dimensions are positive and total cells are capped at one
million. Bounds checks precede indexing. Search penalties are bounded relative
to the 64-bit maximum and cell count, leaving headroom for base costs and the
heuristic. New tests cover extreme rejection and exact large-cost arithmetic.
The legacy 2D interfaces remain; the executable uses the unified 3D engine even
for one-layer layouts.

The physical grid retains obstacles/pins. Validation rebuilds ownership from
paths and separates locally valid candidates, empty paths, and inter-net
conflicts. Planar wirelength excludes VIA edges; physical cost is `W + 6V`.
Search cost includes temporary occupancy/history and is not a comparable physical
quality objective. Conflicted candidate costs remain explicitly unsuccessful.

A pass with no shared cells can still have empty paths. It returns failure,
not success. Stopping is justified for the built-in searches because occupied
cells carry soft finite costs rather than hard blockage: another history update
cannot make an unreachable target physically reachable. BFS's existing early
stop is also justified under fixed constraints/order, since its geometry ignores
occupancy/history. Weighted searches keep updating history until success or the
pass cap. Repeated geometry alone is not proof of weighted stagnation: costs may
still change. No new convergence rule was introduced.

## FIXED — Confirmed defects and gaps

1. **C++ standalone validator indexing.** A hand-constructed layout declaring two
   cells but storing one could index ownership storage out of bounds before
   checking cells. This was reproduced with ASan. A shared shape guard now runs
   before validation/driver indexing and in search input checks. Parsed CLI
   layouts were already guarded; this fixes the direct API boundary.
2. **Invalid geometry accepted as a verified failure.** The independent Python
   checker could accept a nonempty jumping path when `invalid_nets` and flags
   consistently reported its invalidity. It now rejects any locally invalid
   nonempty path as an output error; ordinary unreachable or conflicted routing
   failures remain accepted and recorded.
3. **Weak JSON/type rejection.** Boolean counts could pass numeric comparison,
   and malformed structures raised uncaught TypeError. Counts/costs now require
   nonnegative integers, numeric fields must be finite, flags must be booleans,
   and structural errors are normalized to ValueError. The Python layout parser
   now matches canonical positive-integer and cell-limit rules.
4. **Benchmark failure recording.** Malformed outputs could abort the harness
   before CSV/metadata were saved. Tests now exercise malformed shapes, missing
   metrics, timeouts, stale output removal, and an always-failing executable.
   Expected process/output failures produce error rows with blank metrics and
   a nonzero harness status; programming errors are not broadly suppressed.
5. **Reproducibility safeguards.** Result-directory reuse is rejected, duplicate
   dataset stems are rejected, timeout/pass arguments are checked, and repeated
   `--input` selection supports small controlled experiments. The default runner
   writes under ignored `build/`, preserving historical results. Hashes are taken
   before execution and checked afterward for changes during measurement.
6. **Compiler provenance.** The old harness queried `c++` and described default
   Make flags even for another executable/build override. Make now records the
   actual compiler invocation/version, flags, source hashes, and executable hash.
   The runner checks that record for the repository executable and explicitly
   marks external/unrecorded binaries as having unavailable provenance.
7. **Static route labels.** The plotting script labeled any representative route
   as `chip_layout_hell`. Representative routing is now explicitly requested and
   labeled with the JSON filename and success state; conflicted paths/cells and
   empty-path pins are visible. CSV-only plots no longer add an unrelated route.
8. **Missing automation.** Added the workflow and dependency-free CLI smoke gate
   described below. Sanitizer execution now makes UBSan findings fatal by default.

No new routing algorithm was added, and the A*/Dijkstra/BFS search implementations
were preserved apart from the shared input-shape guard. Existing local changes
remain included. Default numeric scheduling produces the same routes and
non-timing search/quality metrics as the starting early-stop snapshot; the new
`net_order` JSON field is additive.

## VERIFIED — CI configuration and hosted results

[eda-validation.yml](../.github/workflows/eda-validation.yml) uses Ubuntu 24.04,
read-only repository permission, and independent GCC/Clang core jobs. Each prints
versions, builds C++17, runs C++/Python tests, and executes a smoke gate covering
success, impossible layouts, malformed inputs, validator script failures, and
18 benchmark observations. Core checks need no Plotly/browser. Separate jobs
cover Clang ASan/UBSan and headless Plotly integration. Diagnostic logs and smoke
outputs are uploaded even when a required step fails. Shell pipelines use
`set -euo pipefail`; no required errors are suppressed.

The workflow YAML, matrix/triggers/permissions, and shell blocks were checked
locally. Official action definitions were consulted for
[checkout v6](https://github.com/actions/checkout/blob/v6/action.yml),
[setup-python v6](https://github.com/actions/setup-python/blob/v6/action.yml), and
[upload-artifact v6](https://github.com/actions/upload-artifact/blob/v6/action.yml).
Those initial checks were local syntax/configuration review. Hosted execution and
genuine GNU GCC/Linux tests had not yet run at that stage; `/usr/bin/g++` on the
Mac reports Apple Clang. The original [workflow check](verification/workflow-check.txt)
and [release check](verification/release-check.txt) remain unchanged historical
records. Their **NOT RUN** statements describe the pre-push audit, not current CI
status. Actionlint and manual browser interaction remain unverified.

[EDA validation run #1](https://github.com/Vinh-Duy/EDA_Routing_Algorithm/actions/runs/38993901220)
completed successfully on October 17, 2026, for commit
`bef67d03dd14c6ad89de2c44f9e35134e24edc24`. The public run summary and
[job results](https://api.github.com/repos/Vinh-Duy/EDA_Routing_Algorithm/actions/runs/38993901220/jobs)
confirm success for all four Ubuntu 24.04 jobs: `correctness (g++)`,
`correctness (clang++)`, `sanitizers`, and `visualization`.

This verifies the configured hosted checks for that commit, including the small
CLI/benchmark smoke gate. It does not rerun the three archived 840-observation
suites or the 150-observation robustness experiment. Their local measurements,
source snapshots, compiler records, and timing claims remain separate and unchanged.

## VERIFIED — Benchmark integrity and new experiments

The original default-pass and one-pass suites each contain 840 observations.
All their recorded source/input hashes match commit `62022a0`; their statistics
recompute from the raw CSV. Their success counts are 640 and 600 respectively.
The earlier local `early_stop` suite contains another 840 observations and 640
successes; all its source hashes matched the initial working tree.

The initial early-stop source differences are saved in
[early-stop-source.patch](verification/early-stop-source.patch). Applying this to
files from `62022a0` in a temporary directory reproduced every recorded source
and input hash. This preserves a reproducible source snapshot rather than
silently assigning those timings to today's source. Historical build flags were
self-reported; the new build record provides stronger provenance for new runs.

All **2,646 archived per-invocation JSONs**, including 126 excluded warm-ups,
passed the stricter current checker. Fifty-two saved file hashes protect original
datasets, CSVs, metadata, result tables, figures, and early-stop notes. The
read-only [evidence checker](../benchmarks/verify_evidence.py) recomputes sample
counts, failure accounting, physical costs, medians, means, sample standard
deviations, minima/maxima, repeatability, and input hashes. It reports historical
source differences rather than pretending archived binaries are current.

[ROBUSTNESS.md](../benchmarks/ROBUSTNESS.md) records 150 new measured invocations
on five preselected seeds with numeric/reverse order and five timing repetitions.
There were 100 complete routing successes, 50 correctly reported routing failures,
and zero execution/validation errors. All new source/input/executable hashes match
the measured build. A*/Dijkstra solve all five layouts under both orders; BFS
solves none because shared cells remain. Reverse can help or hurt weighted cost
and pass count. Five layouts are not 25 independent designs, and no statistical
or universal performance superiority is claimed.

## VERIFIED — Final local gate

[Exact commands, exit codes, and logs](verification/final.json):

- Clean build: `make clean`, then `make`, both exit 0.
- `make test`: 17 C++ groups and 15 Python tests passed; one optional Plotly skip.
- `make test PYTHON=.venv/bin/python`: 17 C++ groups and all 16 Python tests passed.
- `make sanitize`: all 17 C++ groups passed ASan/UBSan.
- `python3 tests/smoke_cli.py`: 12 routing cases, invalid-input/script checks, and
  18 benchmark observations passed.
- Preserved evidence and newly measured summary/hash checks passed.
- Headless Plotly tests verify complete path coordinates, endpoint traces, VIAs,
  empty and legacy paths, and conflicts without mutating source JSON.
- Ten new PNG plots were generated from measured CSV; figure/data checks and
  documentation checks are recorded in the release-check log.

No failures remain in the executed final gate. The deliberate malformed-output,
timeout, invalid-layout, impossible-route, and pre-fix ASan cases are expected
negative tests, not omitted observations. Browser interaction was not manually
verified. The final logs contain no compiler warnings or ResourceWarnings.

## REMAINING LIMITATION — Release assessment

The project is suitable as an undergraduate educational engineering portfolio,
provided its scope and measured failures are explained honestly. This is not an
admissions prediction. Hosted Ubuntu 24.04 GCC/Clang checks passed for `bef67d0`;
this does not establish portability across every compiler or platform. Rerouting has no
convergence/global-optimality guarantee, inputs are synthetic, and no process
geometry/electrical/fabrication validation is implemented. The public API expects
valid net semantics when bypassing the parser. CLI output writes are not atomic
and alias checks do not address concurrent filesystem changes.

Plot regeneration writes its selected destinations; use fresh output/report paths
for archived CSVs. Source hashes describe snapshots and can legitimately differ
from a later checkout. No full 840-run historical suite was regenerated or
silently replaced. Further algorithm changes should receive a new experiment
folder and independent validation.

## VERIFIED — Before committing

Run from the repository root; no command below commits or pushes:

```sh
make clean
make test PYTHON=.venv/bin/python
make sanitize
python3 tests/smoke_cli.py
python3 benchmarks/verify_evidence.py
python3 benchmarks/verify_evidence.py --suite benchmarks/robustness/numeric --suite benchmarks/robustness/reverse
git diff --check -- . ':!*.svg' ':!*.csv' ':!*.patch'
git diff -- data/
git status --short
```

Review [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for the 123-word English summary,
four contributions, CV description, and five interview questions with answers.
