# Multi-terminal routing experiment

The control is the same fixed layout with each `P<id>` replaced by `.`, leaving only its S/T pair. It measures the existing two-pin behavior on a reduced-terminal projection; it is not an equal-connectivity quality comparison. The tree column routes every original terminal. No quality superiority is inferred.

Runs: 5 per case/algorithm; warm-up excluded; shuffle seed 20261016; max passes 10.
All inputs are hand-designed fixed fixtures, so there is no obstacle-generation seed. Timings are local and descriptive.

| Case | Algorithm | Control success | Tree success | Control wire/VIA/branches/cost | Tree wire/VIA/branches/cost | Control median ms / expanded | Tree median ms / expanded | Tree termination | Tree failed nets |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| four_terminal_branch | astar | 1 | 1 | 1/0/0/1 | 4/0/1/4 | 0.02935/2 | 0.041633/8 | success | `[]` |
| four_terminal_branch | dijkstra | 1 | 1 | 1/0/0/1 | 4/0/1/4 | 0.027811/2 | 0.045222/24 | success | `[]` |
| four_terminal_branch | bfs | 1 | 1 | 1/0/0/1 | 4/0/1/4 | 0.02957/2 | 0.041775/24 | success | `[]` |
| incomplete_terminal | astar | 0 | 0 | 0/0/0/0 | 1/0/0/1 | 0.02501/2 | 0.029088/4 | unreachable | `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":2,"unconnected_terminals":1}]` |
| incomplete_terminal | dijkstra | 0 | 0 | 0/0/0/0 | 1/0/0/1 | 0.027786/2 | 0.029123/4 | unreachable | `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":2,"unconnected_terminals":1}]` |
| incomplete_terminal | bfs | 0 | 0 | 0/0/0/0 | 1/0/0/1 | 0.028834/2 | 0.030526/4 | unreachable | `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":2,"unconnected_terminals":1}]` |
| multilayer_via | astar | 1 | 1 | 0/1/0/6 | 1/1/0/7 | 0.02767/2 | 0.032087/4 | success | `[]` |
| multilayer_via | dijkstra | 1 | 1 | 0/1/0/6 | 1/1/0/7 | 0.037462/5 | 0.03407/11 | success | `[]` |
| multilayer_via | bfs | 1 | 1 | 0/1/0/6 | 1/1/0/7 | 0.029386/4 | 0.033483/10 | success | `[]` |
| obstacle_detour | astar | 1 | 1 | 2/0/0/2 | 5/0/0/5 | 0.039288/3 | 0.036915/7 | success | `[]` |
| obstacle_detour | dijkstra | 1 | 1 | 2/0/0/2 | 5/0/0/5 | 0.029002/4 | 0.052239/13 | success | `[]` |
| obstacle_detour | bfs | 1 | 1 | 2/0/0/2 | 5/0/0/5 | 0.031137/4 | 0.038778/13 | success | `[]` |

The reference result for the five-terminal branch case is independently enumerated in [the Python tests](../../tests/test_multiterminal.py). It proves the 4-edge optimum only for that tiny instance; it is not a general Steiner optimality claim. Runtime/search effort include the multi-source searches for each attachment. See `results.csv`, `summary.csv`, and `metadata.json` for raw observations, per-net failure records, termination reasons, and hashes.
