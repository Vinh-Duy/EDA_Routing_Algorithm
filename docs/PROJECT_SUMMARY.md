# Project summary

## A. English summary

This independent technical project explores simplified VLSI interconnect routing
through a C++17 implementation of A*, Dijkstra, and breadth-first search. It models
two-pin nets on layered grids with obstacles, layer-transition costs, and limited
cell capacity. A separate validator checks path geometry and shared-cell conflicts,
preventing short but infeasible routes from being reported as successful solutions.
The project combines deterministic oracle tests, sanitizer checks, a command-line
interface, Python visualization, and reproducible benchmark records. Experiments
examine the differences between unweighted and weighted objectives, the effects
of congestion history, and sensitivity to net ordering across additional obstacle
seeds. Results demonstrate engineering trade-offs rather than universal algorithmic
superiority. The model is educational: it does not implement manufacturing design
rules, electrical analysis, multi-terminal routing, or a complete physical-design
workflow.

## B. Four technical contributions

- Implemented established graph-search methods behind a common C++17 interface,
  with consistent weighted costs for A* and Dijkstra and a distinct BFS objective.
- Separated immutable layout data, routing state, and independent validation;
  checked endpoints, obstacle/pin legality, adjacency, VIA accounting, and ownership.
- Built deterministic correctness tests, 200 seeded oracle comparisons, sanitizer
  checks, CLI regression tests, and a GCC/Clang CI configuration.
- Developed reproducible experiments with raw CSV, input/source hashes, measured
  timing variation, explicit failures, and controlled seed/order comparisons.

## C. Problem addressed

Connect every two-pin net on a layered grid while respecting obstacles and
unit-capacity cells. An individually legal path can still conflict with another
net. Success requires every required net to be locally legal and mutually disjoint.

## D. Engineering decisions and trade-offs

A* and Dijkstra share weighted search machinery to isolate the heuristic's effect.
BFS retains a FIFO queue and minimizes graph-edge count. Planar edges cost 1;
layer transitions cost 6. Temporary occupancy costs 100 per occupied destination
cell, and each conflicted cell accumulates 50 history units per reroute.

Full rip-up/reroute is simple to understand, but can repeat work or fail to
converge. Deterministic BFS does not respond to those weights, so it stops after
one pass while retaining its failure status. Numeric net order remains the
default; reverse order is an optional controlled experiment. Paths remain indexed
by their original net identities under either schedule.

## E. Actual experiments completed

- Three historical suites each contain 840 measured invocations: the original
  default-pass suite, its separate one-pass experiment, and the earlier BFS
  early-stop update. Their CSV statistics, input hashes, and preserved files were
  audited; they are not reclassified as measurements of the latest source.
- The new experiment contains 150 measured invocations: five new obstacle seeds,
  three algorithms, two net orders, and five timing repetitions per combination.
  Thirty warm-up invocations are excluded from those statistics.
- The latest local gate passed 17 C++ groups, 16 Python tests with plotting
  dependencies installed, ASan/UBSan, and a small CLI/benchmark smoke test.
- Separately, [EDA validation run #1](https://github.com/Vinh-Duy/EDA_Routing_Algorithm/actions/runs/38993901220)
  passed on October 17, 2026, for `bef67d0`: Ubuntu 24.04 GCC/Clang correctness,
  sanitizer, and headless visualization jobs all succeeded. CI runs a small smoke
  experiment; it does not reproduce or replace the local benchmark measurements above.

## F. What the results show

On the five new layouts, A* and Dijkstra route all 12 nets successfully under both
orders. BFS fails all five layouts under both orders because shared cells remain.
Ordering changes weighted route geometry, cost, and sometimes pass count. For
example, A* on seed 20261021 costs 858 in numeric order and 902 in reverse order;
on seed 20261018, reverse order reduces its cost from 874 to 838. Neither order
is consistently best. See [the robustness appendix](../benchmarks/ROBUSTNESS.md).

## G. What the results do not establish

The project does not establish statistical superiority across real circuits,
industrial EDA performance, global multi-net optimality, or manufacturability.
Five independent obstacle layouts are a small synthetic sample. Repeated timings
measure run-to-run variation, not additional independent designs. These results
are neither a publication nor a completed fabrication workflow.

## H. CV-ready description

Implemented and evaluated C++17 A*, Dijkstra, and BFS routing on multilayer grids,
with independent path validation, congestion rerouting, oracle and sanitizer
tests, and reproducible experiments on routing cost, feasibility, and net order.

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
Empty paths also fail. All required nets must pass before the executable returns
success; a cheaper conflicted candidate is not a better feasible solution.

**4. What do VIA costs and congestion history do?**

A VIA is an adjacent-layer edge costing 6, compared with 1 for a planar edge.
History increases the temporary cost of previously conflicted cells, encouraging
weighted searches to choose alternative paths. Physical cost is planar edges plus
six times VIAs; search cost additionally includes occupancy and history at the
moment of search. BFS ignores these weights while choosing its path.

**5. What is missing compared with industrial VLSI routing?**

The grid lacks real process geometry, wire width and spacing, layer preferences,
timing, parasitics, crosstalk, antenna constraints, multi-pin connectivity, and
manufacturing checks. Its inputs are synthetic educational layouts. A validated
route satisfies this discrete model only; it is not a sign-off-ready chip layout.
