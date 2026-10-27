# Two-terminal compatibility check

I compiled the pre-extension snapshot `a17dd4e961b6b77c56b7f1e1d91ed25ec81fca62`
from Git's local object database, then ran it and the current router on the same
14 original two-terminal layouts (six under `data/` and eight under
`benchmarks/layouts/`), all three algorithms, default pass limit, and numeric net
order. All **42** exit statuses, ordered per-net paths, and core metrics matched:
success rate, routed/unrouted/invalid nets, conflicts, wirelength, VIAs, graph
steps, weighted and search cost, routing passes, reroute iterations, and expanded
nodes. Runtime was intentionally excluded from equality checks.

This is a deterministic compatibility regression against that recorded source
revision, not a performance experiment. The revision is retained as an ancestor of
this working tree; the check used a temporary archive checkout and did not modify
its files. A rerun can compile the named revision and compare those 42 pairs with
the current `router` using the CLI and metrics listed above.
