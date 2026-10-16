# Independent Technical Project — VLSI Routing and Algorithm Evaluation

A C++17 grid-routing project exploring how graph search, layer transitions, and
congestion interact in simplified VLSI interconnect routing. I developed this
independently as an undergraduate Computer Science student to connect algorithm
implementation with semiconductor design concepts.

The project implements established A*, BFS, Dijkstra, and rip-up/reroute methods.
Its engineering work includes explicit routing constraints, independent route
validation, deterministic tests, and reproducible algorithm comparisons. It is an
educational model, not an industrial EDA tool or published research.

## Implemented methods

- **A***: weighted shortest-path search with a consistent 3D Manhattan heuristic.
- **Dijkstra**: the same weighted costs with no heuristic, for controlled comparison.
- **BFS**: shortest unweighted paths; a layer transition counts as one edge.
- **Rip-up/reroute**: sequential net routing, full rip-up, and historical congestion penalties.
- **Validation**: checks ordered paths, endpoints, obstacles, unrelated pins, adjacency,
  VIA accounting, and per-cell net ownership. All nets must pass for success.

Planar moves cost 1; a VIA costs 6. Weighted search additionally charges occupied
cells and historical congestion. A* and BFS optimize different objectives; neither
is claimed universally superior. The C++ Strategy Pattern (`IRouter3D`) separates
search selection from the driver, validation, and visualization.

## Repository structure

```text
src/                         C++ algorithms, parser, validator, driver, JSON writer
  main.cpp                   Command-line entry point
  IRouter3D.hpp               Layout, net, search-result types and strategy interface
  AStar3D.hpp / Dijkstra3D.hpp Weighted-search strategies
  BFS3D.hpp                  Unweighted strategy
  Search3D.hpp               Shared weighted costs and safe reconstruction
  RouteValidation.hpp        Independent geometry and ownership checks
  RoutingEngine.hpp          Rip-up/reroute and timing
  *2D.hpp                    Preserved standalone 2D interfaces/algorithms
data/                       Six original layouts (two documented row repairs)
tests/                      C++ unit/oracle tests and Python integration tests
benchmarks/                 Generator, runner, raw CSV, summaries, report, plots
  layouts/                   Eight deterministic scenarios
  single_pass/               Supplemental one-pass measurements
docs/AUDIT.md               Bugs, dataset repairs, and API compatibility notes
visualize.py                Plotly 3D visualization
output.json                 Generated, validated A* example on chip_layout_hell
Makefile                    Build, tests, sanitizers, benchmarks, figures
```

## Build and run

Requires a C++17 compiler and Make. No third-party C++ dependencies are needed.
Run commands from the repository root:

```sh
make
./router --input data/chip_layout_hell.txt --algorithm astar --output output.json --max-iterations 10
./router --help
```

`--algorithm` accepts `astar`, `bfs`, or `dijkstra`. `--max-iterations` bounds total
routing passes, including the initial attempt. `./router` defaults to the command
above. Exit codes: **0** = all routes validated; **2** = incomplete/conflicted
routing (diagnostic JSON still written); **1** = invalid input/options or I/O error.
An existing output file is replaced after a run; do not use the input layout as
the output filename.

The input header is `rows cols` or `layers rows cols`. Each nonblank following row
must have exactly `cols` whitespace-separated tokens: `.` empty, `#` blocked,
`S1` source, `T1` target, etc. Net IDs may be nonconsecutive; duplicate/missing pins
are rejected. A source and target cannot share a text cell; the C++ API supports
a zero-edge path for coincident endpoints. See [audit notes](docs/AUDIT.md) for
legacy input repairs and the updated 3D C++ interface.

## Test and visualize

Python 3.10+ runs the benchmark and integration tools. Only plotting requires
external Python packages:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make test PYTHON=.venv/bin/python
make sanitize
.venv/bin/python benchmarks/validate_output.py --input data/chip_layout_hell.txt --output output.json
.venv/bin/python visualize.py --input output.json --html benchmarks/figures/routing_example.html --no-show
```

Open the generated HTML to inspect routes and thick VIA segments. Run
`.venv/bin/python visualize.py` to launch Plotly's browser renderer. The original
`nets[].name`/`path` JSON shape remains supported. Unrouted pins and conflicts are
shown explicitly, and path order is preserved. Without plotting dependencies,
`make test` runs core checks and skips the optional Plotly test.

The recorded verification passed **13 C++ test groups and 6 Python tests**, with
no failures or skips in the configured virtual environment. C++ tests also passed
AddressSanitizer and UndefinedBehaviorSanitizer. Coverage includes 200 seeded
graphs checked against an independent Bellman–Ford oracle, every dataset with all
three algorithms, invalid inputs, overlapping VIA cells, empty paths, deterministic
reruns, and benchmark execution failures.

![Validated A* routes on chip_layout_hell](benchmarks/figures/routing_example.png)

## Reproduce the experiments

```sh
# Generation is separate; committed fixture files can be used directly.
.venv/bin/python benchmarks/generate_layouts.py
.venv/bin/python benchmarks/run_benchmarks.py --repetitions 20
.venv/bin/python benchmarks/run_benchmarks.py --repetitions 20 --max-iterations 1 --results-dir benchmarks/single_pass
.venv/bin/python benchmarks/plot_results.py
.venv/bin/python benchmarks/plot_results.py --csv benchmarks/single_pass/results.csv --output-dir benchmarks/single_pass/figures
```

The main suite contains **840 measured runs**: 14 layouts × 3 algorithms × 20
repetitions, plus excluded warm-ups. A separate 840-run one-pass suite helps
separate search behavior from repeated rerouting. Each output is independently
checked against the layout; errors and failed routes are retained. The runner
records actual timings, mean/median/sample standard deviation, geometry, expanded
nodes, validity, and input/source/executable hashes. Avoid running other heavy
work during timing experiments.

Selected **measured** results from the main suite follow. Runtime is median
algorithm milliseconds (including driver/validation, excluding parsing and I/O),
measured on macOS x86_64 with Apple Clang 14, `-O2`. Wirelength counts planar edges;
VIAs are separate; physical weighted cost is `wirelength + 6 × VIAs`.

| Dataset | Algorithm | Valid nets | Wire | VIAs | Physical cost | Median ms |
|---|---|---:|---:|---:|---:|---:|
| `chip_layout_hell` | astar | 10/10 | 86 | 17 | 188 | 0.550117 |
| `chip_layout_hell` | dijkstra | 10/10 | 98 | 15 | 188 | 1.318910 |
| `chip_layout_hell` | bfs | 8/10 | 84 | 15 | 174 † | 10.241392 |
| `via_sensitive` | astar | 1/1 | 10 | 0 | 10 | 0.052457 |
| `via_sensitive` | dijkstra | 1/1 | 10 | 0 | 10 | 0.057272 |
| `via_sensitive` | bfs | 1/1 | 6 | 2 | 18 | 0.040226 |
| `stress_seeded` | astar | 12/12 | 716 | 26 | 872 | 10.258510 |
| `stress_seeded` | dijkstra | 12/12 | 714 | 32 | 906 | 37.030697 |
| `stress_seeded` | bfs | 0/12 | 684 | 26 | 840 † | 188.334152 |

† Failed routing: candidate-path cost, not a feasible solution.

Full measurements and definitions: [technical report](benchmarks/REPORT.md),
[all result rows](benchmarks/RESULTS.md), [raw CSV](benchmarks/results.csv),
[summary CSV](benchmarks/summary.csv), [environment](benchmarks/metadata.json), and
[one-pass results](benchmarks/single_pass/RESULTS.md). Failed routing geometry is
candidate-path data, not the quality of a feasible solution. Local timing results
are not a hardware-independent performance claim.

## Engineering observations and limitations

On the hell layout, A* and Dijkstra both achieve cost 188 but choose different
wirelength/VIA trade-offs. On the VIA-sensitive layout, BFS minimizes 8 graph
edges (cost 18), while weighted search chooses 10 planar edges (cost 10). These
results reflect different objectives. A* expands fewer nodes than Dijkstra on
several recorded cases, but initialization, queue overhead, and measurement noise
also affect runtime.

Some BFS paths overlap. BFS ignores history weights, so repeated passes do not
resolve those conflicts; its ten-pass runtime must not be treated as a pure
single-search comparison. Rip-up/reroute remains heuristic and may fail without
proving infeasibility. Equal-cost early route choices also change constraints for
later nets, so single-net optimality does not imply global multi-net optimality.

This model has unit-capacity cells and two-pin nets. It does not model wire
width/spacing, preferred routing directions, real process rules, timing,
parasitics, or manufacturability. The fixtures are small synthetic layouts, with
one generated random stress seed. Future work includes more seeds and instances,
net-order experiments, selective rip-up, parameter sensitivity, multi-pin nets,
and geometric design-rule constraints. The [report](benchmarks/REPORT.md) explains
these limits and the evidence behind each result.
