# Multi-terminal routing experiment

The control is the same fixed layout with each `P<id>` replaced by `.`, leaving only its S/T pair. It measures the existing two-pin behavior on a reduced-terminal projection; it is not an equal-connectivity quality comparison. The tree column routes every original terminal. No quality superiority is inferred.

Runs: 5 per case/algorithm; warm-up excluded; shuffle seed 20261016; max passes 10.
All inputs are hand-designed fixed fixtures, so there is no obstacle-generation seed. Timings are local and descriptive.

| Case | Algorithm | Control success | Tree success | Control length/wire/VIA/branches/cost | Tree length/wire/VIA/branches/cost | Control median ms / expanded | Tree median ms / expanded | Control termination / failed nets | Tree termination / failed nets |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| four_terminal_branch | astar | 1 | 1 | 1/1/0/0/1 | 4/4/0/1/4 | 0.027817/2 | 0.040679/8 | success / `[]` | success / `[]` |
| four_terminal_branch | dijkstra | 1 | 1 | 1/1/0/0/1 | 4/4/0/1/4 | 0.028424/2 | 0.044155/24 | success / `[]` | success / `[]` |
| four_terminal_branch | bfs | 1 | 1 | 1/1/0/0/1 | 4/4/0/1/4 | 0.027613/2 | 0.055426/24 | success / `[]` | success / `[]` |
| incomplete_terminal | astar | 0 | 0 | 0/0/0/0/0 | 1/1/0/0/1 | 0.023717/2 | 0.029755/4 | unreachable / `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":1,"unconnected_terminals":1}]` | unreachable / `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":2,"unconnected_terminals":1}]` |
| incomplete_terminal | dijkstra | 0 | 0 | 0/0/0/0/0 | 1/1/0/0/1 | 0.024478/2 | 0.027978/4 | unreachable / `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":1,"unconnected_terminals":1}]` | unreachable / `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":2,"unconnected_terminals":1}]` |
| incomplete_terminal | bfs | 0 | 0 | 0/0/0/0/0 | 1/1/0/0/1 | 0.026566/2 | 0.029341/4 | unreachable / `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":1,"unconnected_terminals":1}]` | unreachable / `[{"name":"Net1","reason":"unconnected_terminals","connected_terminals":2,"unconnected_terminals":1}]` |
| multilayer_via | astar | 1 | 1 | 1/0/1/0/6 | 2/1/1/0/7 | 0.026874/2 | 0.031015/4 | success / `[]` | success / `[]` |
| multilayer_via | dijkstra | 1 | 1 | 1/0/1/0/6 | 2/1/1/0/7 | 0.036755/5 | 0.041256/11 | success / `[]` | success / `[]` |
| multilayer_via | bfs | 1 | 1 | 1/0/1/0/6 | 2/1/1/0/7 | 0.030467/4 | 0.041997/10 | success / `[]` | success / `[]` |
| obstacle_detour | astar | 1 | 1 | 2/2/0/0/2 | 5/5/0/0/5 | 0.027674/3 | 0.052129/7 | success / `[]` | success / `[]` |
| obstacle_detour | dijkstra | 1 | 1 | 2/2/0/0/2 | 5/5/0/0/5 | 0.030761/4 | 0.050032/13 | success / `[]` | success / `[]` |
| obstacle_detour | bfs | 1 | 1 | 2/2/0/0/2 | 5/5/0/0/5 | 0.029838/4 | 0.041675/13 | success / `[]` | success / `[]` |

The reference result for the five-terminal branch case is independently enumerated in [the Python tests](../../tests/test_multiterminal.py). It proves the 4-edge optimum only for that tiny instance; it is not a general Steiner optimality claim. Runtime/search effort include the multi-source searches for each attachment. See `results.csv`, `summary.csv`, and `metadata.json` for raw observations, per-net failure records, termination reasons, and hashes.

The current implementation also matched the prior committed router's paths and core metrics on all 42 original two-pin layout/algorithm pairs; see the [compatibility check](../COMPATIBILITY.md).
