import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmarks'))
sys.path.insert(0,str(ROOT))
from validate_output import validate


class CLITests(unittest.TestCase):
    def run_router(self, *args):
        return subprocess.run([str(ROOT/'router'),*args],capture_output=True,text=True,cwd=ROOT)

    def test_help_and_bad_options(self):
        self.assertEqual(self.run_router('--help').returncode,0)
        for args in [('--unknown',),('--input',),('--algorithm','bogus'),('--max-iterations','0'),
                     ('--max-iterations','-1'),('--max-iterations','10001'),('--input','missing.txt')]:
            self.assertEqual(self.run_router(*args).returncode,1,args)

    def test_all_original_and_generated_datasets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'route.json'
            for path in sorted((ROOT/'data').glob('*.txt'))+sorted((ROOT/'benchmarks/layouts').glob('*.txt')):
                for algorithm in ('astar','dijkstra','bfs'):
                    with self.subTest(path=path.name,algorithm=algorithm):
                        proc=self.run_router('--input',str(path),'--algorithm',algorithm,'--output',str(output))
                        self.assertIn(proc.returncode,(0,2),proc.stderr)
                        data=json.loads(output.read_text())
                        self.assertEqual(validate(path,data),proc.returncode==0)
                        again=self.run_router('--input',str(path),'--algorithm',algorithm,'--output',str(output))
                        other=json.loads(output.read_text())
                        data['metrics'].pop('runtime_ms'); other['metrics'].pop('runtime_ms')
                        self.assertEqual(data,other)
                        self.assertEqual(proc.returncode,again.returncode)

    def test_invalid_layout_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.txt'
            for text in ['1 2\nS1\n','1 2\nS1 S1\n','1 2\nS1 T3\n','1 2\nS1 T1\n. .\n']:
                path.write_text(text)
                self.assertEqual(self.run_router('--input',str(path)).returncode,1)
            self.assertEqual(self.run_router('--output',str(Path(directory)/'missing'/'out.json')).returncode,1)

    def test_python_validator_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'; layout=ROOT/'data/chip_layout_small.txt'
            self.run_router('--input',str(layout),'--output',str(out))
            data=json.loads(out.read_text()); data['nets'][0]['path'][0]['x']=999
            with self.assertRaises(ValueError): validate(layout,data)

    def test_benchmark_execution_errors_have_no_invented_metrics(self):
        import csv
        with tempfile.TemporaryDirectory() as directory:
            proc = subprocess.run([sys.executable, str(ROOT/'benchmarks/run_benchmarks.py'),
                '--skip-build', '--executable', '/usr/bin/false', '--repetitions', '1',
                '--results-dir', directory], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(proc.returncode, 1)
            with (Path(directory)/'results.csv').open() as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 42)
            self.assertTrue(all(r['status']=='execution_error' and r['runtime_ms']==''
                                and r['success']=='' for r in rows))

    @unittest.skipUnless(importlib.util.find_spec('plotly'), 'Plotly optional; install requirements.txt to test rendering')
    def test_visualizer_empty_vias_and_order(self):
        from visualize import build_figure
        with tempfile.TemporaryDirectory() as directory:
            for name in ['impossible','multilayer','impossible_overlap']:
                out=Path(directory)/'out.json'
                self.run_router('--input',str(ROOT/f'benchmarks/layouts/{name}.txt'),'--output',str(out))
                data=json.loads(out.read_text()); before=copy.deepcopy(data)
                fig=build_figure(data)
                self.assertEqual(data,before)
                html=Path(directory)/f'{name}.html'; fig.write_html(html)
                self.assertGreater(html.stat().st_size,1000)
                self.assertEqual(list(fig.data[0].z),[p['z'] for p in data['nets'][0]['path']])
                if name=='multilayer':
                    self.assertEqual(sum(t.name.endswith('VIA') for t in fig.data),2)


if __name__ == '__main__':
    unittest.main()
