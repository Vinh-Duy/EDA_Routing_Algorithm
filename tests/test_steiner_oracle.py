"""Independent exhaustive checks for the single-net Dreyfus-Wagner reference."""
import itertools
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks'))
import steiner_oracle
from steiner_oracle import MAX_TERMINALS, build_graph, solve, solve_graph
from validate_output import read_layout_with_extras


def edge_subset_optimum(cells, terminals):
    """Enumerate all legal undirected edge subsets; does not use the DP recurrence."""
    legal = sorted(p for p, token in cells.items() if token == '.' or p in terminals)
    index = {p: i for i, p in enumerate(legal)}
    edges = []
    for i, a in enumerate(legal):
        for j in range(i):
            b = legal[j]
            if sum(abs(x - y) for x, y in zip(a, b)) == 1:
                edges.append((i, j, 6 if a[0] != b[0] else 1))
    best = None
    for mask in range(1 << len(edges)):
        cost = sum(weight for bit, (_, _, weight) in enumerate(edges) if mask & (1 << bit))
        if best is not None and cost >= best:
            continue
        parent = list(range(len(legal)))

        def find(vertex):
            while parent[vertex] != vertex:
                parent[vertex] = parent[parent[vertex]]
                vertex = parent[vertex]
            return vertex

        for bit, (a, b, _) in enumerate(edges):
            if mask & (1 << bit):
                parent[find(a)] = find(b)
        roots = {find(index[p]) for p in terminals}
        if len(roots) == 1:
            best = cost
    return best


def load_case(path):
    _, cells, sources, targets, extras = read_layout_with_extras(path)
    net = next(iter(sources))
    terminals = list(dict.fromkeys([sources[net], targets[net], *extras.get(net, [])]))
    return cells, terminals


def production_semantic_edges(cells, terminals):
    """Enumerate the single-net edges implied by Layout::legal and neighbors()."""
    terminal_set = set(terminals)
    legal = {
        point for point, token in cells.items()
        if token == '.' or point in terminal_set
    }
    edges = set()
    for z, x, y in legal:
        for neighbor in ((z, x - 1, y), (z, x + 1, y), (z, x, y - 1),
                         (z, x, y + 1), (z - 1, x, y), (z + 1, x, y)):
            if neighbor not in legal:
                continue
            edge = tuple(sorted(((z, x, y), neighbor)))
            weight = 6 if edge[0][0] != edge[1][0] else 1
            edges.add((edge[0], edge[1], weight))
    return legal, edges


def verify_witness(cells, terminals, result):
    edge_keys = set()
    parent = {}
    cost = 0

    def find(vertex):
        parent.setdefault(vertex, vertex)
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for raw_edge in result['edges']:
        a, b = map(tuple, raw_edge)
        key = tuple(sorted((a, b)))
        if key in edge_keys:
            raise AssertionError('duplicate reconstructed edge')
        edge_keys.add(key)
        if cells[a] == '#' or cells[b] == '#':
            raise AssertionError('edge touches obstacle')
        if sum(abs(x - y) for x, y in zip(a, b)) != 1:
            raise AssertionError('non-adjacent reconstructed edge')
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            raise AssertionError('reconstructed cycle')
        parent[root_a] = root_b
        cost += 6 if a[0] != b[0] else 1
    if terminals:
        root = find(terminals[0])
        if any(find(terminal) != root for terminal in terminals):
            raise AssertionError('terminal disconnected in witness')
        if edge_keys and any(find(a) != root or find(b) != root for a, b in edge_keys):
            raise AssertionError('witness has a disconnected component')
    if cost != result['optimal_cost']:
        raise AssertionError('reconstruction cost differs from claimed optimum')


class SteinerOracleTests(unittest.TestCase):
    def test_graph_edges_match_independent_production_semantics(self):
        folder = ROOT / 'benchmarks/steiner/layouts'
        for path in sorted(folder.glob('*.txt')):
            cells, terminals = load_case(path)
            with self.subTest(layout=path.name):
                expected_vertices, expected_edges = production_semantic_edges(cells, terminals)
                _, points, adjacency, _ = build_graph(cells, terminals)
                actual_edges = set()
                for source, neighbors in enumerate(adjacency):
                    for target, weight in neighbors:
                        if source < target:
                            actual_edges.add((points[source], points[target], weight))
                self.assertEqual(set(points), expected_vertices)
                self.assertEqual(actual_edges, expected_edges)
                for a, b, weight in actual_edges:
                    self.assertEqual(sum(abs(v - w) for v, w in zip(a, b)), 1)
                    self.assertEqual(weight, 6 if a[0] != b[0] else 1)

    def test_analytical_planar_obstacle_and_via_cases(self):
        cases = {
            'planar_branching': (4, 'optimal'),
            'branch_sharing_saves_cost': (4, 'optimal'),
            'obstacle_branch': (7, 'optimal'),
            'required_via': (6, 'optimal'),
            'via_beats_planar_detour': (18, 'optimal'),
            'disconnected': (None, 'infeasible'),
        }
        folder = ROOT / 'benchmarks/steiner/layouts'
        for name, (cost, status) in cases.items():
            with self.subTest(case=name):
                result = solve(folder / f'{name}.txt')
                self.assertEqual((result['status'], result['optimal_cost']), (status, cost))
                if status == 'optimal':
                    cells, terminals = load_case(folder / f'{name}.txt')
                    verify_witness(cells, terminals, result)

    def test_branching_fixture_matches_independent_edge_subset_enumerator(self):
        folder = ROOT / 'benchmarks/steiner/layouts'
        for name in ('planar_branching', 'branch_sharing_saves_cost', 'obstacle_branch'):
            cells, terminals = load_case(folder / f'{name}.txt')
            exact = solve_graph(cells, terminals)
            self.assertEqual(exact['optimal_cost'], edge_subset_optimum(cells, terminals))
            verify_witness(cells, terminals, exact)
        self.assertLess(
            solve(folder / 'branch_sharing_saves_cost.txt')['optimal_cost'],
            5,  # Separate source-to-sink routes cost 2 + 3 without sharing a branch.
        )

    def test_equal_cost_steiner_witness_is_deterministic(self):
        cells = {(0, x, y): '.' for x in range(2) for y in range(2)}
        terminals = [(0, 0, 0), (0, 1, 1)]
        first = solve_graph(cells, terminals)
        second = solve_graph(cells, terminals)
        self.assertEqual(first['optimal_cost'], 2)
        self.assertEqual(first['edges'], second['edges'])
        verify_witness(cells, terminals, first)

    def test_fifty_seeded_tiny_graphs_against_edge_subsets(self):
        rng = random.Random(20261101)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'layout.txt'
            for case in range(50):
                layers, rows, cols = (1, 2, 3) if case < 25 else (2, 2, 2)
                tokens = ['.'] * (layers * rows * cols)
                labels = ('S1', 'T1', 'P1')
                for position, label in zip(rng.sample(range(len(tokens)), len(labels)), labels):
                    tokens[position] = label
                for position, token in enumerate(tokens):
                    if token == '.' and rng.random() < 0.2:
                        tokens[position] = '#'
                path.write_text(
                    f'{layers} {rows} {cols}\n' +
                    '\n'.join(' '.join(tokens[i:i + cols])
                              for i in range(0, len(tokens), cols)) + '\n'
                )
                cells, terminals = load_case(path)
                exact = solve(path)
                self.assertNotEqual(exact['status'], 'unknown')
                self.assertEqual(exact['optimal_cost'], edge_subset_optimum(cells, terminals))
                if exact['status'] == 'optimal':
                    verify_witness(cells, terminals, exact)

    def test_duplicate_and_coincident_terminals_and_invalid_terminals(self):
        cells = {(0, 0, 0): '.', (0, 0, 1): '.', (0, 0, 2): '#'}
        duplicated = solve_graph(cells, [(0, 0, 0), (0, 0, 1), (0, 0, 1)])
        self.assertEqual(duplicated['terminals'], [(0, 0, 0), (0, 0, 1)])
        self.assertEqual(duplicated['optimal_cost'], 1)
        coincident = solve_graph(cells, [(0, 0, 0), (0, 0, 0)])
        self.assertEqual((coincident['status'], coincident['optimal_cost'], coincident['edges']),
                         ('optimal', 0, []))
        for terminals in ([(0, 0, 2)], [(0, 0, 3)]):
            with self.assertRaises(ValueError):
                solve_graph(cells, terminals)

    def test_resource_limits_are_not_reported_as_infeasible(self):
        cells = {(0, 0, i): '.' for i in range(MAX_TERMINALS + 1)}
        too_many = solve_graph(cells, [(0, 0, i) for i in range(MAX_TERMINALS + 1)])
        self.assertEqual((too_many['status'], too_many['reason']), ('unknown', 'terminal_limit'))
        long_cells = {(0, 0, i): '.' for i in range(513)}
        with patch.object(steiner_oracle, 'build_graph',
                          side_effect=AssertionError('oversized graph was allocated')):
            too_large = solve_graph(long_cells, [(0, 0, 0), (0, 0, 512)])
        self.assertEqual((too_large['status'], too_large['reason']), ('unknown', 'graph_limit'))

if __name__ == '__main__':
    unittest.main()
