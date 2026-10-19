# Exact reference for tiny multi-net routing

## Purpose and scope

The existing 200 seeded Bellman–Ford checks establish single-net correctness in a
fixed cost context. They do not establish that a complete multi-net routing is
globally optimal, or that a failed heuristic run proves a layout infeasible.

[exact_oracle.py](../benchmarks/exact_oracle.py) supplies a separate, exhaustive
reference for **at most 16 traversable cells and four two-pin nets**. It minimizes
total physical cost, planar edges plus six times VIAs, subject to the same
obstacle, pin, and unit-cell-capacity constraints. It is a verification tool for
tiny examples, not an alternative production router. The C++ algorithms,
default ordering, and historical experimental data are unchanged.

## Why the answer is exact

1. For each net, construct the legal graph directly from coordinate adjacency,
   excluding obstacles and all other nets' terminals. The Python oracle does not
   call the C++ search, predecessor reconstruction, or congestion implementation.
2. Enumerate every simple source-to-target path with depth-first search. Cycles
   are prohibited by this model; positive edge costs also make them unnecessary
   for a minimum-cost solution. A bit mask records each path's occupied cells.
3. If several paths occupy exactly the same set of cells, retain one with minimum
   physical cost. Their interactions with all other nets are identical because
   this model's inter-net constraint depends only on shared cells.
4. Explore disjoint combinations of one retained path per net. Memoization uses
   the next net index and union of occupied cells; future feasibility and cost
   depend only on that state. Return the minimum sum over complete combinations.

This covers every feasible solution up to a cost-preserving or cost-improving
replacement of equivalent cell sets. A completed search therefore yields an
optimum and explicit witness paths, or proves infeasibility. Exactness depends on
this discrete model; it would not automatically extend to spacing or electrical
constraints absent from the state.

The independent lower bound is the sum of per-net shortest physical costs,
computed with Floyd–Warshall while ignoring competition for cells. Each feasible
solution must cost at least this sum. The bound may be unattainable: the bottleneck
example has a finite bound but no disjoint solution.

## Resource limits and output meaning

Both simple-path enumeration and path-combination search are exponential. Their
shared budget defaults to 200,000 counted work units: path prefixes, combination
states, and attempted candidate combinations. Fixed-size graph preprocessing is
outside that counter. The limit is deterministic, not a wall-clock guarantee.
Inputs exceeding the size/net caps are rejected rather than truncated.

- `optimal`: exhaustive search finished; `optimal_cost` and witness paths are present.
- `infeasible`: a terminal is individually unreachable, or exhaustive combination
  search proves there is no disjoint solution.
- `unknown`: the work budget was exhausted; no optimum or infeasibility is claimed.
  The independent lower bound remains valid, but no incumbent is certified.

The oracle CLI returns 0 for a completed exact verdict (including infeasibility),
3 for unknown, and 1 for input/output errors. Argument syntax errors return 2.
These are separate from the router's 0/2/1 success/routing-failure/error codes.

[check_exact.py](../benchmarks/check_exact.py) validates every router JSON before
comparison. It assigns `optimal`, `suboptimal`, `heuristic_failure`,
`infeasible_layout`, or `unresolved`. Cost gaps are computed **only** for successful
routing with an established optimum:

- Absolute gap = feasible physical cost − exact optimum.
- Relative gap (%) = 100 × absolute gap / exact optimum.

Failed routes have null physical costs and gaps in the comparison record. A
validated solution cheaper than the claimed optimum, or a validated solution to
a supposedly infeasible layout, raises an error rather than becoming a result.

## Recorded examples — October 18, 2026

[results.json](../benchmarks/exact/results.json) records six layouts, three existing
algorithms, and numeric/reverse scheduling: **36 quality comparisons**, with ten
passes allowed per router invocation. All JSONs passed independent validation.
The record contains exact witnesses, router paths, costs, conflicts, pass counts,
work budgets, source/input/executable hashes, and Git base/dirty state. It contains
no runtime measurements or timing aggregates. The Git base alone does not identify
the added, initially uncommitted verification tools; source hashes identify them.

- **Parallel paths:** exact cost 4; all algorithms/orders attain it.
- **One VIA:** exact cost 6; all algorithms/orders attain it.
- **Disconnected terminals:** independently unreachable; every router reports failure.
- **Shared bottleneck:** each net individually costs 2, giving lower bound 4,
  but every path needs the same central cell. No disjoint solution exists.
- **Feasible conflict:** lower bound 6, exact cost 8. Both weighted methods attain
  8 in either order. BFS fails in both orders although a solution exists.
- **Order-sensitive layout:** lower bound 5, exact cost 7. Numeric A*/Dijkstra each
  return cost 11: gap 4, approximately 57.14%. Reverse order attains 7 for both.
  BFS fails under both orders.

For the order-sensitive example, the layout is:

```text
4 4
. . . .
. T1 S2 .
. . . S1
. . T2 .
```

Numeric order lets Net1 reserve a route before Net2 searches. The local occupancy
penalty can make a longer physical detour preferable for Net2. A conflict-free
result then stops rerouting; it has no subsequent global cost minimization step.
Reversing the schedule changes those reservations. This explains why individually
optimal weighted searches can produce a globally suboptimal physical solution.

Across these selected examples the classifications are 18 optimal, two suboptimal,
four heuristic failures, and 12 invocations on proven-infeasible layouts. These
are **illustrative case counts, not estimated success rates**. Four fixtures were
chosen for analytical checks. The feasible-conflict example was selected at
zero-based index 46 from a 150-instance exploratory 3×4 stream with Python seed
20261018; the order-sensitive example was selected at index 89 from a 4×4 stream
with seed 20261019. Each stream sampled four distinct terminals, then added
obstacles with probability 0.12 on remaining cells. Their literal fixture files
are the reproduction inputs. Selection was intentional to expose failure modes,
not representative sampling. No ordering or algorithm superiority is inferred.

## Independent checks and reproduction

[The tests](../tests/test_exact_oracle.py) compare oracle costs with a second exact
formulation on **60 deterministic layouts**: 30 single-layer 2×3 and 30 two-layer
2×2 grids, each with two nets. That reference enumerates undirected edge subsets
and checks terminal/internal degrees and paired connectivity; it does not enumerate
per-net paths. This exercises feasibility, global cost, and VIA weights through a
different implementation. Witness paths are separately checked for endpoint,
obstacle/pin, adjacency, disjointness, and cost correctness.

Other checks cover analytical cases, net renaming and reflection, exhaustion in
both search phases, rejection of oversized inputs, tampered candidate metrics,
positive gaps, real heuristic failures, process status, and output preservation.

The October 18 local gate passed **17 C++ groups and 23 Python tests**, with no
skips in the configured virtualenv, plus ASan/UBSan and the CLI smoke gate.
[Command records and logs](verification/exact/checks.json) retain actual exit codes.
[A second comparison run](verification/exact/reproduction.txt) reproduced all
36 deterministic comparisons; source/input/binary hashes were checked. Historical
benchmark statistics and preservation checks also passed unchanged.

From the repository root:

```sh
make
python3 -m unittest discover -s tests -p test_exact_oracle.py -v
python3 benchmarks/exact_oracle.py --input benchmarks/exact/layouts/order_sensitive.txt
./router --input benchmarks/exact/layouts/order_sensitive.txt --algorithm astar --output build/exact-route.json
python3 benchmarks/exact_oracle.py --input benchmarks/exact/layouts/order_sensitive.txt --candidate build/exact-route.json
python3 benchmarks/check_exact.py --output build/exact-reproduction.json
```

Choose a fresh comparison output filename; existing records are never overwritten.
To compare the deterministic evidence with the archived record (creation date,
Git metadata, and binary hashes may differ across builds):

```sh
python3 - <<'PY'
import json
from pathlib import Path
old = json.loads(Path('benchmarks/exact/results.json').read_text())
new = json.loads(Path('build/exact-reproduction.json').read_text())
assert old['input_sha256'] == new['input_sha256']
assert old['cases'] == new['cases']
print('Exact verdicts, witnesses, and router comparisons reproduce')
PY
```

The existing CI core jobs discover this test module automatically through
`make test`. The earlier successful hosted run for `bef67d0` predates this addition
and is not evidence that these new tests have run on GitHub. The full historical
benchmark suites remain separate from this tiny exact-quality study.
