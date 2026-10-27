"""Exact vertex-disjoint routing oracle for tiny layouts, independent of C++ search.

Enumerates simple paths, then minimizes total physical cost over disjoint path
combinations. Exponential by design: at most 16 traversable cells and four nets.
A deterministic work budget bounds enumeration and combination search. Exhausting
it returns unknown, never infeasible or an uncertified optimum.
"""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import sys

from validate_output import read_layout_with_extras, validate

MAX_CELLS = 16
MAX_NETS = 4
DEFAULT_MAX_STATES = 200_000


class BudgetExceeded(Exception):
    pass


def solve(layout_path, max_states=DEFAULT_MAX_STATES):
    if type(max_states) is not int or max_states < 1:
        raise ValueError('max_states must be a positive integer')
    _, cells, sources, targets, extras = read_layout_with_extras(layout_path)
    if extras:
        raise ValueError('The two-terminal exact oracle does not accept multi-terminal nets')
    points = sorted(p for p, token in cells.items() if token != '#')
    names = sorted(sources, key=lambda name: int(name[3:]))
    if len(points) > MAX_CELLS or len(names) > MAX_NETS:
        raise ValueError(f'Exact oracle supports at most {MAX_CELLS} traversable cells and {MAX_NETS} nets')
    index = {p: i for i, p in enumerate(points)}
    used_states = 0
    result = dict(status='unknown', optimal_cost=None, independent_lower_bound=None,
                  paths={}, states_examined=0, candidate_paths={}, reason=None)

    def tick():
        nonlocal used_states
        if used_states == max_states:
            raise BudgetExceeded
        used_states += 1

    # Build each net's graph directly from coordinates. Other nets' pins are
    # forbidden even before any path is selected. No C++ neighbor/cost code reused.
    graphs = []
    bounds = []
    for name in names:
        allowed = [i for i, p in enumerate(points)
                   if cells[p] == '.' or p in (sources[name], targets[name])]
        adj = {i: [] for i in allowed}
        dist = {(i, j): (0 if i == j else float('inf')) for i in allowed for j in allowed}
        for i in allowed:
            for j in allowed:
                if sum(abs(a-b) for a, b in zip(points[i], points[j])) == 1:
                    cost = 1 if points[i][0] == points[j][0] else 6
                    adj[i].append((j, cost))
                    dist[i, j] = cost
        # Floyd-Warshall lower bounds ignore competition for cells, not obstacles.
        for k in allowed:
            for i in allowed:
                for j in allowed:
                    dist[i, j] = min(dist[i, j], dist[i, k] + dist[k, j])
        src, dst = index[sources[name]], index[targets[name]]
        if dist[src, dst] == float('inf'):
            result.update(status='infeasible', reason='individually_unreachable')
            return result
        bounds.append(dist[src, dst])
        graphs.append((src, dst, adj))
    result['independent_lower_bound'] = sum(bounds)

    try:
        candidates = []
        for name, (src, dst, adj) in zip(names, graphs):
            by_mask = {}

            def visit(node, mask, cost, path):
                tick()
                if node == dst:
                    # Equal occupied-cell sets have identical effects on other
                    # nets; only their cheapest realization can be globally best.
                    if mask not in by_mask or cost < by_mask[mask][0]:
                        by_mask[mask] = (cost, path)
                    return
                for nxt, weight in adj[node]:
                    if not mask & (1 << nxt):
                        visit(nxt, mask | (1 << nxt), cost + weight, path + (nxt,))

            visit(src, 1 << src, 0, (src,))
            choices = sorted((cost, mask, path) for mask, (cost, path) in by_mask.items())
            result['candidate_paths'][name] = len(choices)
            candidates.append(choices)

        @lru_cache(maxsize=None)
        def combine(net, occupied):
            tick()
            if net == len(names):
                return 0, ()
            best_cost, best_paths = float('inf'), ()
            for cost, mask, path in candidates[net]:
                tick()
                if mask & occupied:
                    continue
                tail_cost, tail_paths = combine(net + 1, occupied | mask)
                if cost + tail_cost < best_cost:
                    best_cost, best_paths = cost + tail_cost, (path,) + tail_paths
            return best_cost, best_paths

        best_cost, best_paths = combine(0, 0)
        if best_cost == float('inf'):
            result.update(status='infeasible', reason='no_disjoint_combination')
        else:
            result.update(status='optimal', optimal_cost=best_cost, reason='exhaustive_search',
                          paths={name: [dict(zip(('z', 'x', 'y'), points[i])) for i in path]
                                 for name, path in zip(names, best_paths)})
    except BudgetExceeded:
        result['reason'] = 'state_limit'
    result['states_examined'] = used_states
    return result


def compare(layout_path, candidate, exact):
    """Validate the router output before comparing any physical-quality metric."""
    success = validate(layout_path, candidate)
    status = exact['status']
    comparison = dict(router_success=success, classification='unresolved',
                      absolute_gap=None, relative_gap_percent=None)
    if status == 'infeasible':
        if success:
            raise ValueError('Validated solution contradicts oracle infeasibility')
        comparison['classification'] = 'infeasible_layout'
    elif status == 'optimal':
        if not success:
            comparison['classification'] = 'heuristic_failure'
        else:
            optimum = exact['optimal_cost']
            gap = candidate['metrics']['weighted_cost'] - optimum
            if gap < 0:
                raise ValueError('Validated solution is cheaper than oracle optimum')
            comparison.update(classification='optimal' if gap == 0 else 'suboptimal',
                              absolute_gap=gap, relative_gap_percent=100 * gap / optimum)
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--candidate', type=Path, help='Optional existing router JSON to validate and compare')
    parser.add_argument('--max-states', type=int, default=DEFAULT_MAX_STATES)
    args = parser.parse_args()
    try:
        result = solve(args.input, args.max_states)
        if args.candidate:
            result['comparison'] = compare(args.input, json.loads(args.candidate.read_text()), result)
    except (ValueError, OSError) as error:
        print(f'Exact oracle error: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 3 if result['status'] == 'unknown' else 0


if __name__ == '__main__':
    sys.exit(main())
