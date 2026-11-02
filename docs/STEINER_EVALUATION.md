# Exact single-net Steiner reference and terminal-order experiment

## What is evaluated

`benchmarks/steiner_oracle.py` independently solves one net's weighted
multilayer-grid Steiner-tree problem. It is not the same problem as
[`benchmarks/exact_oracle.py`](../benchmarks/exact_oracle.py), which exhaustively
combines vertex-disjoint source-to-target paths for multiple two-pin nets. The
latter is still useful for tiny global cell-capacity examples, but it does not
model branching within a multi-terminal net.

The graph is constructed from grid coordinates rather than production router
neighbors or search routines. Obstacles and other pin cells are removed; the
selected net's S/T/P coordinates remain legal vertices. Undirected planar edges
cost 1 and adjacent-layer edges cost 6. Occupancy and history penalties are
excluded because they are search-time costs, not the physical single-net
objective.

The production semantics were checked against this model before corpus
generation. [`Layout::legal`](../src/IRouter3D.hpp) permits empty cells and the
current net's own terminals, but rejects obstacles and foreign-net pins;
[`neighbors`](../src/IRouter3D.hpp) permits only the four planar Manhattan
neighbors and same-coordinate adjacent-layer neighbors. The oracle's
[`build_graph`](../benchmarks/steiner_oracle.py) applies those same vertex and
edge rules, including layout boundaries, and assigns the same planar/VIA costs.
`test_graph_edges_match_independent_production_semantics` independently
enumerates the expected legal vertices and edges for all six fixed layouts and
compares complete weighted edge sets. This is a single-net physical graph:
multi-net occupancy, wire-history penalties, congestion, timing, design rules,
and any non-adjacent layer transition are intentionally outside its objective.

## Dreyfus-Wagner recurrence and witness

For terminal subset `S` and graph vertex `v`, let `D[S,v]` be the minimum cost of
a connected subgraph containing `v` and all terminals in `S`. A singleton state
starts at its terminal with cost zero. For a non-singleton subset, combine
complementary terminal groups at the same vertex:

`B[S,v] = min(D[A,v] + D[S\\A,v])`, for nonempty proper `A subset S`.

Then compute the weighted shortest-path closure:

`D[S,v] = min_u(B[S,u] + shortest_path_cost(u,v))`.

The optimum is `min_v D[all_terminals,v]`. All graph edges have strictly positive
weights, so an optimum can be represented as a tree. The implementation stores
a merge backpointer or a shortest-path predecessor for every finite DP state,
then reconstructs and deduplicates canonical undirected edges. It verifies that
the result is connected, acyclic, and has edge cost exactly equal to the DP
optimum; inconsistency raises an error rather than emitting an uncertified
witness.

The standard running-time bound is `O(3^k V + 2^k E log V)` and the memory bound
is `O(2^k V + E)`, for `k` terminals, `V` legal vertices, and `E` legal edges.
The initial reference caps the instance at six unique terminals and 512 legal
vertices (at most 32,768 DP states, using compact numeric arrays). Larger inputs
return `unknown` with a resource-limit reason; they are never labeled infeasible
and never routed using a heuristic fallback. Disconnected terminals return
`infeasible`. Repeated coordinates are deduplicated; a coincident source/target
is a valid zero-edge, zero-cost instance when the coordinate is legal.

## Correctness evidence

`tests/test_steiner_oracle.py` checks:

- Fixed planar branching and branch-sharing cases, including a tree of cost 4
  where separate source-to-sink routes cost 5.
- Obstacles, an obligatory VIA (cost 6), a VIA-versus-planar-maze case (optimum
  18), and disconnected terminals.
- Witness legality, connectivity, acyclicity, and reconstructed weighted cost.
- Fifty seeded tiny graphs against a separate exhaustive **undirected edge
  subset** enumerator. The brute-force checker does not call or reuse the DP
  recurrence.
- Duplicate/coincident terminals, invalid coordinates, and distinct resource
  limit outcomes.

The fixtures are synthetic and small. These checks validate the implemented
graph model; they do not establish global multi-net routing optimality or
industrial design-rule behavior.

## Terminal-order strategies

`--terminal-order input|nearest` selects the order in which the existing
multi-source tree-growth procedure attaches remaining terminals. `input` is the
default and preserves the existing S, T, then P input sequence.

`nearest` runs weighted Dijkstra distance probes from the current tree to every
remaining in-bounds terminal, using current occupancy/history search costs. It
selects the minimum reachable candidate; ties are broken by `(z, x, y, input
index)`. It then routes that selected target with the requested production
algorithm (A*, Dijkstra, or BFS). If no remaining candidate is reachable, growth
stops and validation marks the tree incomplete. Search count and expanded-node
metrics include all distance probes and selected-route searches; reported
physical tree cost remains separately recomputed by the validator.

## Paired experiment

Run from the repository root with a fresh results path:

```sh
python3 benchmarks/run_steiner_ordering.py \
  --results-dir benchmarks/steiner/experiment_YYYYMMDD \
  --repetitions 3
```

The runner uses all fixed files in `benchmarks/steiner/layouts`, A*, numeric
net scheduling, one pass, the same full terminal set, and identical input bytes
for both terminal strategies. Each exact oracle result is compared only after
the router JSON passes the independent output validator. `raw_runs.csv` retains
per-invocation values and failures; `paired_results.csv` reports per-instance
paired measurements; `raw/` stores raw route JSON; `metadata.json` records
compiler/build, source, executable, and input hashes. One warm-up is retained
but excluded from measured summaries. Repetitions are not counted as independent
instances. Relative cost gap is `(router_cost - optimum) / optimum`; a zero-cost
optimum has a null relative gap. Infeasible and oracle resource-limit results
remain separate from router failures.

The experiment is descriptive evidence on a small hand-designed corpus, not an
unbiased estimate of performance on real circuit designs. No terminal-order
improvement should be claimed without the per-instance results and distributions.

The recorded [November 1 run](../benchmarks/steiner/experiment_20261101_paired/RESULTS.md)
contains six cases: five oracle-feasible and one proven infeasible. Both
strategies match the exact cost on all five feasible cases and both reject the
disconnected case. Paired physical-cost deltas are all zero. Nearest adds
distance-probe work; across the feasible cases it expands 2–68 more nodes and
has higher median router time in this run. These observations support retaining
input order as the default; they do not establish which strategy is better on a
broader or randomly sampled corpus.

## Held-out evaluation

The broader [held-out evaluation](../benchmarks/steiner/experiment_20261101_heldout_final/evaluation/RESULTS.md)
uses a separate 12-case development split, a 60-case held-out feasible corpus,
and 12 sealed-barrier negative controls. The 60 feasible cases are balanced
across 3–6 terminals, 1–3 layers, five obstacle configurations, and five
terminal-spatial classes. Each terminal-count/layer block contains every spatial
class, and obstacle modes are rotated across those classes; two layouts have 512
legal vertices. The deterministic
generator, protocol, configuration, seed manifest, every candidate and rejection,
and all accepted input hashes are retained in the experiment directory. A
temporary regeneration reproduced the manifests and every candidate/layout byte
exactly before routing. Feasible cases are selected by oracle feasibility only,
never by either strategy's result.

Both strategies succeeded on all 60 oracle-feasible cases and neither succeeded
on the 12 infeasible controls. Among the 60 paired feasible outcomes, nearest
had a lower relative gap on 20, tied on 36, and had a higher gap on 4. Mean gap
was 0.0297 for nearest and 0.0784 for input order; the mean paired delta
(nearest minus input) was -0.0488, with a layout-level bootstrap 95% interval
[-0.0765, -0.0241] and an exact two-sided sign-test p-value of 0.00154 over the
24 non-tied pairs. This is evidence within this synthetic, stratified corpus,
not evidence of expected gains on industrial designs. Nearest's mean expanded
nodes were 1,161 versus 77.6, with mean search counts 12.0 versus 3.23.

The runner used 11 measured repetitions and one warm-up per strategy and layout.
Repeated runtimes are summarized within layouts; the 1,584 measured invocations
had a median within-layout repeat MAD of 0.00493 ms. Runtime differences remain
machine- and workload-specific despite the repeated measurements. The earlier
pilot is explicitly marked superseded because it confounded spatial class with
obstacle mode; it is retained for auditability and is not included in this
interpretation. Full per-case
results, strata, all outputs, oracle witnesses, and provenance are in the linked
experiment directory.
