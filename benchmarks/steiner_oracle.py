"""Exact single-net weighted Steiner reference using Dreyfus-Wagner dynamic programming."""
import argparse
from array import array
import heapq
import json
from pathlib import Path
import sys

from validate_output import read_layout_with_extras

PLANAR_COST = 1
VIA_COST = 6
MAX_TERMINALS = 6
MAX_VERTICES = 512
MAX_DP_CELLS = (1 << MAX_TERMINALS) * MAX_VERTICES
INF = (1 << 63) - 1

TERMINAL, MERGE, STEP = 1, 2, 3


def _point(value):
    if not isinstance(value, tuple) or len(value) != 3 or any(type(v) is not int for v in value):
        raise ValueError('Terminals must be integer (z, x, y) coordinate tuples')
    return value


def build_graph(cells, terminals):
    """Build the single-net physical graph independently of the DP resource limits."""
    terminals = list(dict.fromkeys(_point(p) for p in terminals))
    if not terminals:
        raise ValueError('At least one terminal is required')
    if any(p not in cells or cells[p] == '#' for p in terminals):
        raise ValueError('A terminal is outside the graph or on an obstacle')
    terminal_set = set(terminals)
    points = sorted(p for p, token in cells.items() if token == '.' or p in terminal_set)
    if not terminal_set.issubset(points):
        raise ValueError('A terminal is not a legal routing vertex')
    vertex_id = {p: i for i, p in enumerate(points)}
    adjacency = [[] for _ in points]
    for i, p in enumerate(points):
        z, x, y = p
        for q in ((z, x - 1, y), (z, x + 1, y), (z, x, y - 1),
                  (z, x, y + 1), (z - 1, x, y), (z + 1, x, y)):
            j = vertex_id.get(q)
            if j is not None:
                adjacency[i].append((j, VIA_COST if z != q[0] else PLANAR_COST))
        adjacency[i].sort()
    return terminals, points, adjacency, [vertex_id[p] for p in terminals]


def solve_graph(cells, terminals):
    """Solve an undirected cell graph; `cells` maps coordinates to . / # / pin tokens."""
    terminals = list(dict.fromkeys(_point(p) for p in terminals))
    if not terminals:
        raise ValueError('At least one terminal is required')
    if any(p not in cells or cells[p] == '#' for p in terminals):
        raise ValueError('A terminal is outside the graph or on an obstacle')
    if len(terminals) > MAX_TERMINALS:
        return _unknown('terminal_limit', len(terminals), 0)

    terminal_set = set(terminals)
    graph_size = sum(1 for point, token in cells.items()
                     if token == '.' or point in terminal_set)
    if graph_size > MAX_VERTICES:
        return _unknown('graph_limit', len(terminals), graph_size)

    terminals, points, adjacency, terminal_ids = build_graph(cells, terminals)
    if len(points) > MAX_VERTICES:
        return _unknown('graph_limit', len(terminals), len(points))
    if len(points) * (1 << len(terminals)) > MAX_DP_CELLS:
        return _unknown('dp_state_limit', len(terminals), len(points))
    if not _all_terminals_connected(adjacency, terminal_ids):
        return dict(status='infeasible', reason='disconnected_terminals', optimal_cost=None,
                    edges=[], terminals=terminals, graph_vertices=len(points), dp_states=0)

    vertex_count = len(points)
    subset_count = 1 << len(terminals)
    state_count = subset_count * vertex_count
    costs = array('q', [INF]) * state_count
    kinds = array('b', [0]) * state_count
    arguments = array('i', [-1]) * state_count

    for mask in range(1, subset_count):
        offset = mask * vertex_count
        if mask & (mask - 1) == 0:
            terminal_index = mask.bit_length() - 1
            state = offset + terminal_ids[terminal_index]
            costs[state] = 0
            kinds[state] = TERMINAL
        else:
            submask = (mask - 1) & mask
            best_split = [0] * vertex_count
            while submask:
                complement = mask ^ submask
                if complement and submask < complement:
                    left_offset = submask * vertex_count
                    right_offset = complement * vertex_count
                    for vertex in range(vertex_count):
                        left = costs[left_offset + vertex]
                        right = costs[right_offset + vertex]
                        if left == INF or right == INF:
                            continue
                        candidate = left + right
                        state = offset + vertex
                        if candidate < costs[state] or (
                                candidate == costs[state] and
                                (best_split[vertex] == 0 or submask < best_split[vertex])):
                            costs[state] = candidate
                            kinds[state] = MERGE
                            arguments[state] = submask
                            best_split[vertex] = submask
                submask = (submask - 1) & mask

        # Multi-source Dijkstra computes the shortest-path closure for this subset.
        queue = [(costs[offset + vertex], vertex)
                 for vertex in range(vertex_count) if costs[offset + vertex] != INF]
        heapq.heapify(queue)
        while queue:
            distance, vertex = heapq.heappop(queue)
            if distance != costs[offset + vertex]:
                continue
            for neighbor, weight in adjacency[vertex]:
                candidate = distance + weight
                state = offset + neighbor
                if candidate < costs[state]:
                    costs[state] = candidate
                    kinds[state] = STEP
                    arguments[state] = vertex
                    heapq.heappush(queue, (candidate, neighbor))

    full_mask = subset_count - 1
    full_offset = full_mask * vertex_count
    optimum, root = min((costs[full_offset + vertex], vertex)
                        for vertex in range(vertex_count))
    if optimum == INF:
        return dict(status='infeasible', reason='disconnected_terminals', optimal_cost=None,
                    edges=[], terminals=terminals, graph_vertices=vertex_count,
                    dp_states=state_count)

    selected_edges = set()
    visited_states = set()
    active_states = set()

    def reconstruct(mask, vertex):
        state = (mask, vertex)
        if state in visited_states:
            return
        if state in active_states:
            raise RuntimeError('Cycle in Steiner DP reconstruction')
        active_states.add(state)
        index = mask * vertex_count + vertex
        kind = kinds[index]
        if kind == TERMINAL:
            if mask & (mask - 1) or vertex != terminal_ids[mask.bit_length() - 1]:
                raise RuntimeError('Invalid terminal DP backpointer')
        elif kind == MERGE:
            subset = arguments[index]
            if subset <= 0 or subset >= mask or subset & mask != subset:
                raise RuntimeError('Invalid subset DP backpointer')
            reconstruct(subset, vertex)
            reconstruct(mask ^ subset, vertex)
        elif kind == STEP:
            parent = arguments[index]
            if parent < 0 or parent >= vertex_count:
                raise RuntimeError('Invalid shortest-path DP backpointer')
            selected_edges.add(tuple(sorted((parent, vertex))))
            reconstruct(mask, parent)
        else:
            raise RuntimeError('Missing Steiner DP backpointer')
        active_states.remove(state)
        visited_states.add(state)

    reconstruct(full_mask, root)
    edge_cost = sum(weight for a, b in selected_edges
                    for neighbor, weight in adjacency[a] if neighbor == b)
    if edge_cost != optimum:
        raise RuntimeError(f'Reconstructed edge cost {edge_cost} differs from DP optimum {optimum}')
    if not _edge_set_is_tree(selected_edges, adjacency, terminal_ids, vertex_count):
        raise RuntimeError('Reconstructed optimal edge set is not a connected tree')

    edges = [[points[a], points[b]] for a, b in sorted(selected_edges)]
    return dict(status='optimal', reason='dreyfus_wagner', optimal_cost=optimum,
                edges=edges, terminals=terminals, graph_vertices=vertex_count,
                dp_states=state_count)


def solve(layout_path):
    dimensions, cells, sources, targets, extras = read_layout_with_extras(layout_path)
    if len(sources) != 1:
        raise ValueError('The Steiner oracle accepts exactly one net per layout')
    name = next(iter(sources))
    terminals = [sources[name], targets[name], *extras.get(name, [])]
    result = solve_graph(cells, terminals)
    result['input_dimensions'] = dimensions
    result['net'] = name
    return result


def _unknown(reason, terminals, vertices):
    return dict(status='unknown', reason=reason, optimal_cost=None, edges=[],
                terminal_count=terminals, graph_vertices=vertices, dp_states=0)


def _all_terminals_connected(adjacency, terminal_ids):
    reached = {terminal_ids[0]}
    stack = [terminal_ids[0]]
    while stack:
        vertex = stack.pop()
        for neighbor, _ in adjacency[vertex]:
            if neighbor not in reached:
                reached.add(neighbor)
                stack.append(neighbor)
    return all(vertex in reached for vertex in terminal_ids)


def _edge_set_is_tree(edges, adjacency, terminals, vertex_count):
    parent = list(range(vertex_count))

    def find(vertex):
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    used = set()
    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return False
        parent[root_a] = root_b
        used.update((a, b))
    if terminals:
        root = find(terminals[0])
        if any(find(vertex) != root for vertex in terminals):
            return False
    return all(find(vertex) == find(terminals[0]) for vertex in used) if terminals else not used


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = solve(args.input)
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Steiner oracle error: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 3 if result['status'] == 'unknown' else 0


if __name__ == '__main__':
    sys.exit(main())
