"""Tiny multi-net oracle checks, including an independent edge-subset reference."""
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks'))
from exact_oracle import solve, compare
from validate_output import read_layout


def edge_subset_optimum(layout):
    """Enumerate undirected edge subsets, not per-net paths or path combinations."""
    _, cells, sources, targets = read_layout(layout)
    points = [p for p in cells if cells[p] != '#']
    index = {p: i for i, p in enumerate(points)}
    pins = {index[p] for p in list(sources.values()) + list(targets.values())}
    pairs = [(index[sources[n]], index[targets[n]]) for n in sources]
    edges = [(i, j, 1 if a[0] == b[0] else 6)
             for i, a in enumerate(points) for j, b in enumerate(points[:i])
             if sum(abs(x-y) for x, y in zip(a, b)) == 1]
    best = None
    for selected in itertools.product((False, True), repeat=len(edges)):
        degree = [0] * len(points)
        parent = list(range(len(points)))
        def find(i):
            while parent[i] != i:
                i = parent[i]
            return i
        cost = 0
        for take, (i, j, weight) in zip(selected, edges):
            if take:
                degree[i] += 1; degree[j] += 1
                parent[find(i)] = find(j)
                cost += weight
        if any(degree[i] != 1 if i in pins else degree[i] not in (0, 2)
               for i in range(len(points))):
            continue
        if all(find(s) == find(t) for s, t in pairs):
            best = cost if best is None else min(best, cost)
    return best


class ExactOracleTests(unittest.TestCase):
    def witness(self, layout, exact):
        _, cells, sources, targets = read_layout(layout)
        self.assertEqual(set(exact['paths']), set(sources))
        used = set(); cost = 0
        for name, coords in exact['paths'].items():
            path = [tuple(p[k] for k in ('z', 'x', 'y')) for p in coords]
            self.assertEqual(path[0], sources[name]); self.assertEqual(path[-1], targets[name])
            self.assertEqual(len(path), len(set(path)))
            self.assertFalse(used.intersection(path)); used.update(path)
            for p in path:
                self.assertIn(p, cells); self.assertNotEqual(cells[p], '#')
                self.assertTrue(cells[p] == '.' or p in (sources[name], targets[name]))
            for a, b in zip(path, path[1:]):
                self.assertEqual(sum(abs(x-y) for x,y in zip(a,b)), 1)
                cost += 1 if a[0] == b[0] else 6
        self.assertEqual(cost, exact['optimal_cost'])
        self.assertLessEqual(exact['independent_lower_bound'], cost)

    def test_analytical_costs_and_infeasibility(self):
        fixtures = ROOT/'benchmarks/exact/layouts'
        for name, optimum in [('parallel',4),('via',6),('bottleneck',None),('disconnected',None)]:
            with self.subTest(name=name):
                result = solve(fixtures/f'{name}.txt')
                self.assertEqual(result['optimal_cost'], optimum)
                self.assertEqual(result['status'], 'infeasible' if optimum is None else 'optimal')
                if optimum is not None:self.witness(fixtures/f'{name}.txt', result)
        self.assertEqual(solve(fixtures/'bottleneck.txt')['independent_lower_bound'],4)
        self.assertEqual(solve(fixtures/'bottleneck.txt')['reason'],'no_disjoint_combination')
        self.assertEqual(solve(fixtures/'disconnected.txt')['reason'],'individually_unreachable')

    def test_sixty_seeded_layouts_against_edge_subsets(self):
        rng = random.Random(20261018)
        with tempfile.TemporaryDirectory() as tmp:
            layout = Path(tmp)/'layout.txt'
            for case in range(60):
                layers, rows, cols = (1,2,3) if case < 30 else (2,2,2)
                tokens = ['.'] * (layers*rows*cols)
                for pos, pin in zip(rng.sample(range(len(tokens)),4),('S1','T1','S2','T2')):
                    tokens[pos] = pin
                for i in range(len(tokens)):
                    if tokens[i] == '.' and rng.random() < .2:tokens[i] = '#'
                layout.write_text(f'{layers} {rows} {cols}\n' + '\n'.join(
                    ' '.join(tokens[i:i+cols]) for i in range(0,len(tokens),cols))+'\n')
                with self.subTest(case=case):
                    exact = solve(layout)
                    optimum = edge_subset_optimum(layout)
                    self.assertNotEqual(exact['status'],'unknown')
                    self.assertEqual(exact['optimal_cost'],optimum)
                    if optimum is not None:self.witness(layout,exact)

    def test_budget_limits_and_cli_exit_status(self):
        layout = ROOT/'benchmarks/exact/layouts/parallel.txt'
        exact = solve(layout,1)
        self.assertEqual(exact['status'],'unknown'); self.assertEqual(exact['reason'],'state_limit')
        self.assertIsNone(exact['optimal_cost']); self.assertEqual(exact['paths'],{})
        self.assertEqual(exact['states_examined'],1)
        complete = solve(layout)
        self.assertEqual(complete['status'],'optimal')
        # Exhaustion during combination search must not certify a partial best.
        incomplete = solve(layout,complete['states_examined']-1)
        self.assertEqual(incomplete['status'],'unknown')
        self.assertIsNone(incomplete['optimal_cost']); self.assertEqual(incomplete['paths'],{})
        for budget in (0,-1,True,1.5):
            with self.assertRaises(ValueError):solve(layout,budget)
        for budget, code in [('1',3),('200000',0),('0',1)]:
            proc = subprocess.run([sys.executable,str(ROOT/'benchmarks/exact_oracle.py'),
                                   '--input',str(layout),'--max-states',budget],capture_output=True,text=True)
            self.assertEqual(proc.returncode,code,proc.stderr)
            if code == 3:self.assertEqual(json.loads(proc.stdout)['status'],'unknown')
        with tempfile.TemporaryDirectory() as tmp:
            large=Path(tmp)/'large.txt';large.write_text('1 17\nS1 '+'. '*15+'T1\n')
            with self.assertRaisesRegex(ValueError,'16 traversable'):solve(large)
            large.write_text('1 10\nS1 T1 S2 T2 S3 T3 S4 T4 S5 T5\n')
            with self.assertRaisesRegex(ValueError,'four|4 nets'):solve(large)

    def test_reflection_and_net_renaming_preserve_optimum(self):
        with tempfile.TemporaryDirectory() as tmp:
            layout = Path(tmp)/'layout.txt'
            for original in sorted((ROOT/'benchmarks/exact/layouts').glob('*.txt')):
                expected = solve(original)
                lines = original.read_text().splitlines()
                # Reverse columns and interchange labels without changing geometry.
                body = [' '.join(token.replace('1','X').replace('2','1').replace('X','2')
                                 for token in reversed(line.split())) for line in lines[1:]]
                layout.write_text(lines[0]+'\n'+'\n'.join(body)+'\n')
                actual = solve(layout)
                self.assertEqual((actual['status'],actual['optimal_cost']),
                                 (expected['status'],expected['optimal_cost']))

    def test_router_comparison_validates_and_never_scores_failed_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'route.json'
            for name in ('parallel','bottleneck','via','disconnected'):
                layout=ROOT/'benchmarks/exact/layouts'/f'{name}.txt'
                exact=solve(layout)
                for algorithm in ('astar','dijkstra','bfs'):
                    proc=subprocess.run([str(ROOT/'router'),'--input',str(layout),
                        '--algorithm',algorithm,'--output',str(out)],capture_output=True,text=True)
                    self.assertIn(proc.returncode,(0,2),proc.stderr)
                    candidate=json.loads(out.read_text())
                    result=compare(layout,candidate,exact)
                    self.assertEqual(result['classification'],'optimal' if proc.returncode==0 else 'infeasible_layout')
                    if proc.returncode==2:
                        self.assertIsNone(result['absolute_gap']);self.assertIsNone(result['relative_gap_percent'])
                    unknown=compare(layout,candidate,dict(status='unknown'))
                    self.assertEqual(unknown['classification'],'unresolved')
                    candidate['metrics']['weighted_cost'] += 1
                    with self.assertRaises(ValueError):compare(layout,candidate,exact)


    def test_feasible_failure_and_positive_global_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'route.json'
            for name,algorithm,expected,optimum in [
                ('feasible_conflict','bfs','heuristic_failure',8),
                ('order_sensitive','astar','suboptimal',7)]:
                layout=ROOT/'benchmarks/exact/layouts'/f'{name}.txt'
                exact=solve(layout)
                self.assertEqual(exact['optimal_cost'],optimum)
                self.witness(layout,exact)
                proc=subprocess.run([str(ROOT/'router'),'--input',str(layout),'--algorithm',algorithm,
                    '--output',str(out)],capture_output=True,text=True)
                self.assertIn(proc.returncode,(0,2),proc.stderr)
                candidate=json.loads(out.read_text())
                result=compare(layout,candidate,exact)
                self.assertEqual(result['classification'],expected)
                if expected=='suboptimal':
                    self.assertEqual(result['absolute_gap'],4)
                    self.assertAlmostEqual(result['relative_gap_percent'],400/7)
                    with self.assertRaisesRegex(ValueError,'cheaper'):
                        compare(layout,candidate,dict(status='optimal',optimal_cost=100))
                    with self.assertRaisesRegex(ValueError,'contradicts'):
                        compare(layout,candidate,dict(status='infeasible'))
                else:
                    self.assertIsNone(result['absolute_gap'])

    def test_comparison_runner_preserves_results_and_reports_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'report.json'
            command=[sys.executable,str(ROOT/'benchmarks/check_exact.py'),'--output',str(out)]
            proc=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            original=out.read_bytes();report=json.loads(original)
            fixtures=list((ROOT/'benchmarks/exact/layouts').glob('*.txt'))
            self.assertEqual(len(report['cases']),len(fixtures))
            self.assertTrue(all(len(case['comparisons'])==6 for case in report['cases']))
            proc=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(proc.returncode,2);self.assertEqual(out.read_bytes(),original)
            unknown=root/'unknown.json'
            proc=subprocess.run([*command[:-1],str(unknown),'--max-states','1'],capture_output=True,text=True)
            self.assertEqual(proc.returncode,3,proc.stderr)
            self.assertTrue(any(c['oracle']['status']=='unknown' for c in json.loads(unknown.read_text())['cases']))
            fake=root/'broken'
            fake.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n'
                            'Path(sys.argv[sys.argv.index("--output")+1]).write_text("{}")\n')
            fake.chmod(0o755)
            bad=root/'bad.json'
            proc=subprocess.run([*command[:-1],str(bad),'--executable',str(fake)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,1,proc.stderr);self.assertFalse(bad.exists())


if __name__ == '__main__':
    unittest.main()
