# Correctness audit and compatibility notes

The audit covered every original C++ header and `main.cpp`, all six layouts, the
tracked JSON example, `visualize.py`, README, and ignore rules before editing.
The original C++ program compiled with Apple Clang 14 (an unused BFS penalty
parameter warning). The following findings are based on code inspection; no
before/after speed improvement is claimed.

| Finding | Consequence | Change / evidence |
|---|---|---|
| `main.cpp` ignored `route()` return values and tested only `X` cells | Empty paths could produce a “100% Routed” message | Independently validate every required net; unreachable regression |
| `V` was treated as free, and a single display token replaced ownership | Overlaps at layer transitions could be hidden | Immutable physical cells; per-cell lists of net owners; VIA overlap regression |
| Reconstruction started at the destination's parent | Source equal to target accessed a sentinel predecessor | Reconstruction includes endpoints, has bounds and cycle guards; singleton path tests |
| Grid dimensions and cell reads were unchecked | Truncated inputs shifted pin positions or left cells unset | Strict header, row, token, count, dimension, and pin validation |
| Pins were stored by assignment, and net discovery stopped at the first missing ID | Duplicate pins overwritten; later or incomplete nets omitted | Reject duplicates and missing pairs; accept nonconsecutive positive numeric IDs |
| Destination special case could allow a blocked endpoint through direct API calls | Invalid search endpoints | Check endpoint legality before searching |
| VIA display marks were used as geometry | Final transition and shared VIA cells were ambiguous | Count consecutive layer-changing edges independently of display |
| Search did not skip stale A* queue entries | Repeated, unnecessary processing | Skip outdated g scores; count only non-stale removals |
| Timing included JSON and console output | Timing was not algorithm-only | `steady_clock` around driver/search/validation; all I/O outside |
| Visualizer reversed an already ordered path and indexed empty lists | Swapped source/target labels and exceptions | Preserve traversal order; explicit endpoint metadata; empty-path rendering tests |
| Console padding subtracted token length from unsigned 4 | Long labels could cause huge output loops | Replace grid dump with a concise validated summary |

## Dataset repairs

Two existing files had one missing token. The old whitespace-stream parser
silently shifted all subsequent cells. The following minimal repairs append an
empty cell to the short row, preserving every explicitly written token's column
within that row. This is an engineering interpretation of the intended layout,
not a recovered ground truth. Benchmarks use these repaired versions and record
their SHA-256 hashes.

| File | Physical file line (1-based) | Grid coordinate of added `.` |
|---|---:|---|
| `data/chip_layout_complex.txt` | 10 | `(z=0, x=8, y=9)` |
| `data/chip_layout_hell.txt` | 20 | `(z=1, x=6, y=9)` |

A trailing newline was also added to these two files. The other four original
layouts are byte-for-byte unchanged. All six are covered by executable regression
tests; A* and Dijkstra produce valid complete solutions on each in the recorded
suite. BFS's conflicts on `chip_layout_test` and `chip_layout_hell` are reported,
not hidden. The old tracked `output.json` was stale relative to the intended
layout rows; it has been replaced by a generated, independently checked example.

## Architecture and compatibility

The C++17 Strategy Pattern remains: `AStar3D`, `BFS3D`, and `Dijkstra3D` implement
`IRouter3D`. Full rip-up/reroute with a historical penalty grid remains the
multi-net strategy. A* and Dijkstra share queue/reconstruction/cost machinery to
avoid accidental objective differences. BFS keeps its FIFO frontier.

The 3D C++ method signature intentionally changed: it now receives a const
`Layout`, net, occupancy counts, and history, and returns a `SearchResult`. Code
that called the old mutable-grid signature must migrate. This change separates
routing from display and makes net identity explicit in the driver/validator.
The legacy 2D classes and their public interfaces remain, with endpoint and grid
shape safeguards. The executable uses the unified 3D implementation for 2D data.

CLI defaults preserve `./router` behavior (hell input, A*, `output.json`). The
JSON retains `nets[].name` and ordered `nets[].path`, adding schema version,
endpoints, obstacles, conflict owners, validity, and metrics. The visualizer also
accepts legacy name/path-only JSON, including empty paths.

Source-equals-target is supported by the C++ API as a one-cell, zero-edge path.
The text format has one token per cell and cannot encode two co-located pin
labels; no ambiguous text extension was added. Positive dimensions, canonical
positive numeric pin IDs, at most 1,000,000 cells, and 1–10,000 routing passes are
explicit implementation limits.
