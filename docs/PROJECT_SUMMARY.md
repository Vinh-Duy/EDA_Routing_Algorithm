# Project summary

## A. English summary

This independent technical project explores simplified VLSI interconnect routing
through a C++17 implementation of A*, Dijkstra, and breadth-first search. It models
two-terminal nets and deterministic multi-terminal tree growth on layered grids
with obstacles, layer-transition costs, and limited cell capacity. A separate
validator checks path/tree geometry, terminal connectivity, and shared-cell conflicts,
preventing partial or infeasible routes from being reported as successful solutions.
The project combines deterministic oracle tests, sanitizer checks, a command-line
interface, Python visualization, and reproducible benchmark records. Experiments
examine the differences between unweighted and weighted objectives, the effects
of congestion history, and sensitivity to net ordering across additional obstacle
seeds. Results demonstrate engineering trade-offs rather than universal algorithmic
superiority. Multi-terminal growth is a heuristic rather than an exact Steiner
solver. The model is educational: it does not implement manufacturing design rules,
electrical analysis, or a complete physical-design workflow.

## B. Four technical contributions

- Implemented established graph-search methods behind a common C++17 interface,
  with consistent weighted costs for A* and Dijkstra and a distinct BFS objective.
- Separated immutable layout data, routing state, and independent validation;
  checked endpoints, obstacle/pin legality, adjacency, VIA accounting, and ownership.
- Built deterministic correctness tests, 200 seeded oracle comparisons, sanitizer
  checks, CLI regression tests, and a GCC/Clang CI configuration; added a tiny
  multi-net exact reference checked against 60 independent edge-subset cases.
- Developed reproducible experiments with raw CSV, input/source hashes, measured
  timing variation, explicit failures, and controlled seed/order comparisons.
- Added backwards-compatible `P<id>` terminals, multi-source tree growth, edge-tree
  JSON, independent tree validation, and visualization of shared branches. Existing
  two-pin input and JSON paths remain supported.

## C. Problem addressed

Connect all required terminals of each net on a layered grid while respecting
obstacles and unit-capacity cells between different nets. Same-net branches may
share cells and edges. Success requires every terminal to belong to a locally legal,
connected, acyclic route tree and every net to be mutually disjoint from the others.

## D. Engineering decisions and trade-offs

A* and Dijkstra share weighted search machinery to isolate the heuristic's effect.
BFS retains a FIFO queue and minimizes graph-edge count. Planar edges cost 1;
layer transitions cost 6. Temporary occupancy costs 100 per occupied destination
cell, and each conflicted cell accumulates 50 history units per reroute.

Full rip-up/reroute is simple to understand, but can repeat work or fail to
converge. Deterministic BFS does not respond to those weights, so it stops after
one pass while retaining its failure status. Numeric net order remains the
default; reverse order is an optional controlled experiment. Paths remain indexed
by their original net identities under either schedule. For a multi-terminal net,
the router starts at S and attaches T followed by P terminals in row-major input
order. Each attachment is a multi-source search from the existing tree to the new
terminal. This greedy schedule is deterministic but may miss a better branch order
or globally shorter tree. Shared branches are stored as unique undirected edges.

## E. Actual experiments completed

- Three historical suites each contain 840 measured invocations: the original
  default-pass suite, its separate one-pass experiment, and the earlier BFS
  early-stop update. Their CSV statistics, input hashes, and preserved files were
  audited; they are not reclassified as measurements of the latest source.
- The new experiment contains 150 measured invocations: five new obstacle seeds,
  three algorithms, two net orders, and five timing repetitions per combination.
  Thirty warm-up invocations are excluded from those statistics.
- The October 17 local gate passed 17 C++ groups, 16 Python tests with plotting
  dependencies installed, ASan/UBSan, and a small CLI/benchmark smoke test.
- Separately, [EDA validation run #1](https://github.com/Vinh-Duy/EDA_Routing_Algorithm/actions/runs/38993901220)
  passed on October 17, 2026, for `bef67d0`: Ubuntu 24.04 GCC/Clang correctness,
  sanitizer, and headless visualization jobs all succeeded. CI runs a small smoke
  experiment; it does not reproduce or replace the local benchmark measurements above.
- On October 18, six selected tiny layouts supplied 36 exact-quality comparisons,
  separating global infeasibility, heuristic failure, and suboptimal feasible routing.
  The local gate passed 17 C++ groups, 23 Python tests, and ASan/UBSan. Hosted CI
  has not yet verified this addition; it is not covered by the earlier run.
- The multi-terminal extension has 21 C++ test groups and 26 Python tests; two
  plotting tests are skipped in the current local environment because Plotly is
  not installed. The CLI smoke gate validates 24 route executions and 30 benchmark
  observations. A 120-observation fixed-layout experiment compares each tree case
  with its S/T-only projection; all outputs passed independent validation. These
  projections require fewer terminals and are not a like-for-like quality baseline.
  The [raw results and comparison](../benchmarks/multiterminal/experiment_20261026_final/RESULTS.md)
  include per-net failures, termination reasons, and recorded hashes. The updated
  GitHub workflow has not yet run. A separate [compatibility check](../benchmarks/multiterminal/COMPATIBILITY.md)
  matched route geometry and core metrics against the prior source snapshot on all
  42 original two-pin layout/algorithm pairs.

## F. What the results show

On the five new layouts, A* and Dijkstra route all 12 nets successfully under both
orders. BFS fails all five layouts under both orders because shared cells remain.
Ordering changes weighted route geometry, cost, and sometimes pass count. For
example, A* on seed 20261021 costs 858 in numeric order and 902 in reverse order;
on seed 20261018, reverse order reduces its cost from 874 to 838. Neither order
is consistently best. See [the robustness appendix](../benchmarks/ROBUSTNESS.md).

The [exact-reference study](EXACT_ROUTING.md) provides a concrete global-quality
counterexample: numeric A*/Dijkstra return cost 11 where the exact optimum is 7,
while reverse order attains 7. It also shows a feasible layout on which BFS fails.
These intentionally selected tiny examples explain limitations, not their frequency.
For multi-terminal routing, exhaustive edge-subset enumeration confirms that the
five-terminal 3×3 branch fixture has a four-edge optimum, which all three growth
variants attain. This single tiny case is not evidence of general Steiner optimality.

## G. What the results do not establish

The project does not establish statistical superiority across real circuits,
industrial EDA performance, global multi-net or Steiner optimality, or manufacturability.
Five independent obstacle layouts are a small synthetic sample. Repeated timings
measure run-to-run variation, not additional independent designs. These results
are neither a publication nor a completed fabrication workflow.

## H. CV-ready description

Implemented and evaluated C++17 A*, Dijkstra, BFS, and deterministic incremental
multi-terminal tree growth on multilayer grids, with independent route validation,
congestion rerouting, small-instance oracle tests, and reproducible experiments.

## I–J. Five likely interview questions and answers

**1. Why can fewer expanded nodes still take more time?**

Expanded nodes count search work, not all work. Priority-queue operations, memory
allocation, grid initialization, path validation, cache behavior, and operating
system scheduling also contribute. The timer includes routing and validation,
but excludes parsing, output writing, plotting, and process startup. Compare
actual distributions on the same workload rather than assuming a fixed cost per
expanded node.

**2. Does an optimal single-net path produce an optimal multi-net solution?**

No. A* and Dijkstra optimize one net in a fixed occupancy/history context. That
choice changes the costs faced by later nets. Different equal-cost paths and net
orders can yield different aggregate outcomes. The rerouting heuristic has no
global optimality or convergence guarantee.

**3. Why reject a low-cost routing result?**

A low physical cost can describe overlapping candidate paths. The validator
rebuilds cell ownership and marks every net sharing a cell as globally invalid.
Disconnected partial trees also fail. All required terminals must be connected and
all nets conflict-free before the executable returns success; a cheaper partial
candidate is not a feasible solution.

**4. What do VIA costs and congestion history do?**

A VIA is an adjacent-layer edge costing 6, compared with 1 for a planar edge.
History increases the temporary cost of previously conflicted cells, encouraging
weighted searches to choose alternative paths. Physical cost is planar edges plus
six times VIAs; search cost additionally includes occupancy and history at the
moment of search. BFS ignores these weights while choosing its path.

**5. What is missing compared with industrial VLSI routing?**

The grid lacks real process geometry, wire width and spacing, layer preferences,
timing, parasitics, crosstalk, antenna constraints, and manufacturing checks. Its
inputs are synthetic educational layouts. A validated route satisfies this discrete
model only; it is not a sign-off-ready chip layout.
