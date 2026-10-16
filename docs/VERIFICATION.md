# Final verification record

Completed locally on 2026-10-16.

- C++17 release build: passed, with `-O2 -Wall -Wextra -Wpedantic`.
- C++ correctness suite: 13 test groups passed, including 200 seeded graph/oracle cases.
- Python integration suite: 6 tests passed, none skipped in the configured virtual environment.
- AddressSanitizer and UndefinedBehaviorSanitizer: all 13 C++ groups passed.
- Main benchmark: 840 measured runs; 640 complete routing successes, 200 reported routing failures.
- One-pass benchmark: 840 measured runs; 600 successes, 240 reported routing failures.
- Both suites: zero execution errors, zero output-verification errors, zero locally invalid paths.
- Failures include impossible inputs and BFS conflicts; they are represented in CSV and plots.
- Every pair has 20 measurements plus an excluded warm-up; paths and non-timing metrics repeat exactly.
- SHA-256 hashes of the final executable, source inputs, and recorded source files match metadata.
- Before committing, rebuilt the release executable and rechecked all 1,680 stored
  routes against their layouts, CSV metrics, summary timing statistics, and recorded hashes.
- All six original datasets are exercised. Two short rows were repaired as described in AUDIT.md.
- Eight generated fixtures reproduce byte-for-byte with the documented generator.
- Five benchmark plots were exported as PNG and SVG for each suite; the representative route PNG
  and self-contained Plotly HTML were generated. Runtime, success-rate, and route PNGs were visually inspected.
- Plotly tests cover ordered paths, endpoint labels, empty paths, VIA traces, and conflicts.
  Browser interaction was not manually tested.
- README/report tables were populated from real summary CSV values. Relative document links resolve.
- Source and documentation whitespace checks passed with `git diff --check`;
  generated CSV and SVG files retain their exporters' formatting.

Exact reproduction commands are in [README](../README.md) and the
[experimental setup](../benchmarks/REPORT.md#7-experimental-setup).
Raw observations, runtime variation, and failed routing statistics are retained in
[main results](../benchmarks/RESULTS.md) and [one-pass results](../benchmarks/single_pass/RESULTS.md).
Timing remains machine/load dependent; route quality and ownership are deterministic.

## Changed tracked files

- `.gitignore`
- `README.md`
- `data/chip_layout_complex.txt`
- `data/chip_layout_hell.txt`
- `output.json`
- `src/AStar2D.hpp`
- `src/AStar3D.hpp`
- `src/BFS2D.hpp`
- `src/BFS3D.hpp`
- `src/IRouter3D.hpp`
- `src/main.cpp`
- `visualize.py`

## Added project files

- `Makefile`
- `benchmarks/REPORT.md`
- `benchmarks/RESULTS.md`
- `benchmarks/figures/nodes_expanded.png`
- `benchmarks/figures/nodes_expanded.svg`
- `benchmarks/figures/routing_example.png`
- `benchmarks/figures/runtime.png`
- `benchmarks/figures/runtime.svg`
- `benchmarks/figures/success_rate.png`
- `benchmarks/figures/success_rate.svg`
- `benchmarks/figures/vias.png`
- `benchmarks/figures/vias.svg`
- `benchmarks/figures/wirelength.png`
- `benchmarks/figures/wirelength.svg`
- `benchmarks/generate_layouts.py`
- `benchmarks/layouts/README.md`
- `benchmarks/layouts/congestion.txt`
- `benchmarks/layouts/impossible.txt`
- `benchmarks/layouts/impossible_overlap.txt`
- `benchmarks/layouts/multilayer.txt`
- `benchmarks/layouts/obstacles_2d.txt`
- `benchmarks/layouts/simple_2d.txt`
- `benchmarks/layouts/stress_seeded.txt`
- `benchmarks/layouts/via_sensitive.txt`
- `benchmarks/metadata.json`
- `benchmarks/plot_results.py`
- `benchmarks/results.csv`
- `benchmarks/run_benchmarks.py`
- `benchmarks/single_pass/RESULTS.md`
- `benchmarks/single_pass/figures/nodes_expanded.png`
- `benchmarks/single_pass/figures/nodes_expanded.svg`
- `benchmarks/single_pass/figures/routing_example.png`
- `benchmarks/single_pass/figures/runtime.png`
- `benchmarks/single_pass/figures/runtime.svg`
- `benchmarks/single_pass/figures/success_rate.png`
- `benchmarks/single_pass/figures/success_rate.svg`
- `benchmarks/single_pass/figures/vias.png`
- `benchmarks/single_pass/figures/vias.svg`
- `benchmarks/single_pass/figures/wirelength.png`
- `benchmarks/single_pass/figures/wirelength.svg`
- `benchmarks/single_pass/metadata.json`
- `benchmarks/single_pass/results.csv`
- `benchmarks/single_pass/summary.csv`
- `benchmarks/summary.csv`
- `benchmarks/validate_output.py`
- `docs/AUDIT.md`
- `docs/VERIFICATION.md`
- `requirements.txt`
- `src/Dijkstra3D.hpp`
- `src/JsonOutput.hpp`
- `src/LayoutIO.hpp`
- `src/RouteValidation.hpp`
- `src/RoutingEngine.hpp`
- `src/Search3D.hpp`
- `tests/test_cli.py`
- `tests/test_router.cpp`

Ignored generated files include the executable, build/test binaries, virtual environment,
per-invocation route JSONs, and interactive HTML. These remain in the local workspace
and can be regenerated using the documented commands.
