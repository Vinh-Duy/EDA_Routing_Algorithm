# Multi-terminal routing design

## Scope

Add multi-terminal support to the existing grid router while retaining the
current two-terminal file format, algorithms, return codes, and JSON `path`
representation for legacy nets. This is a deterministic incremental tree-growth
heuristic; it is **not** a Rectilinear Steiner Minimum Tree solver and makes no
global optimality claim.

## Input and in-memory model

Keep `S<id>` and `T<id>` as the required first two terminals. Add `P<id>` tokens
for zero or more additional terminals of that same net. A valid net therefore
has exactly one `S`, one `T`, and may have any number of `P` terminals. Each P
token names its owning net, so repeated `P<id>` tokens are expected while
duplicate S or T tokens are rejected. Every P ID needs a complete S/T pair.
The parser retains deterministic order `S`, `T`, then `P` in row-major
layout order. Existing files contain no P tokens and parse to exactly the same
two-terminal nets.

Extend `Net3D` with the ordered terminal list while retaining `src` and `dst` for
existing two-terminal search APIs. Represent a completed route as an undirected
set of adjacent grid edges (`RouteTree`). Edge endpoints are canonicalized and
deduplicated within a net, so branches may meet or share existing tree edges
without charging or claiming the same edge twice. Different nets may not share
any route cell, including a terminal cell. A route tree must be connected,
acyclic, and contain every terminal.

## Incremental deterministic growth

Start each net's tree at its S terminal. Visit remaining terminals in the
deterministic order T then P row-major. For each terminal outside the current
tree, run a multi-source shortest-path search initialized with every current
tree vertex at distance zero; stop when the requested terminal is removed from
the queue. Add the recovered path's edges to the tree. If a terminal was already
incorporated by an earlier branch, skip it. Fixed neighbor ordering and the
existing stable queue tie-breaks make results repeatable.

A* and Dijkstra use the existing planar/VIA base costs (1/6), plus the existing
nonnegative occupancy and history penalties for cells owned by other nets. Cells
already in the current tree are free seeds and do not incur an occupancy penalty.
The A* Manhattan/VIA lower bound remains admissible for the requested terminal.
BFS uses a multi-source FIFO search, minimizes edge count, and remains explicitly
congestion-insensitive. It is not ranked as a weighted optimizer. Rip-up/reroute
still rebuilds all trees each pass, updates history at cross-net conflict cells,
and stops on full validated success, no-conflict incomplete connectivity,
congestion-insensitive BFS failure, or pass limit. Any missing terminal makes
the whole layout unsuccessful.

## Validation, metrics, and output compatibility

Add an independent tree validator. It checks edge endpoints, bounds, adjacency,
obstacles, foreign pins, duplicate/cyclic edges, terminal connectivity, and
cross-net cell ownership. It recomputes unique planar edges, unique VIAs,
physical cost `wirelength + 6 * via_count`, and branch points (tree vertices of
degree at least three). Same-net shared vertices/edges are legal and counted
once; any cross-net shared cell invalidates every owner. Partial trees remain
visible in output but cannot count as routed or successful.

Keep the schema version and existing `source`, `target`, and ordered `path` fields
for two-terminal nets. Add an ordered `terminals` field. Two-terminal nets keep
their existing source-to-target `path` and metrics. Multi-terminal nets use an
empty `path` plus an undirected, deduplicated `tree_edges` list, each edge an
endpoint pair. Add `branch_count` to run/per-net metrics. The independent Python
validator accepts historical two-terminal JSON without the additive fields and
validates the new tree form when present.

The Plotly view draws each unique tree edge once and marks every terminal. Raw
historical benchmark archives, metadata, and hashes remain untouched. Fixed
multi-pin fixtures have a separate experiment folder and are compared with
S/T-only projections made from the same obstacle layouts. This projection control
has fewer required terminals, so it measures legacy two-pin behavior and added
work, not equal-connectivity routing quality. The experiment records runtime,
expanded nodes, graph length, planar wire, VIAs, branch points, termination reasons,
and per-net failures. A separate independent tiny edge-subset reference checks the
five-terminal 3×3 case; it is not a general optimality claim.

## Verification and known limits

Tests cover old files and P groups, malformed/missing/duplicate pins, multi-source
weighted and BFS search, obstacle/VIA handling, shared same-net branches,
foreign-net conflicts, disconnected terminals, exact tree metrics, JSON round-trip
validation, visualization, repeated-run equality, and an independent tiny exact
reference. `make test` and the CLI smoke workflow now exercise multi-terminal cases.
The current local run passed 21 C++ test groups and 26 Python tests (two optional
Plotly tests skipped because Plotly is not installed locally); the updated GitHub
workflow has not yet run. The fixed-layout experiment recorded 120 observations
with no execution or validation errors, plus 24 excluded warm-ups.

Grid-cell capacity remains the only geometric spacing rule. This work adds no
industrial DRC, timing, parasitic, multi-layer process rules, or convergence or
optimality guarantee. The greedy terminal order can produce nonminimal trees.
