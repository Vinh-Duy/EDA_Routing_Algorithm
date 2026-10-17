import copy
import importlib.util
import json
import os
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
                     ('--max-iterations','-1'),('--max-iterations','10001'),('--input','missing.txt'),
                     ('--net-order','unknown')]:
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

    def test_reverse_order_all_datasets(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'
            for path in sorted((ROOT/'data').glob('*.txt'))+sorted((ROOT/'benchmarks/layouts').glob('*.txt')):
                for algorithm in ('astar','dijkstra','bfs'):
                    proc=self.run_router('--input',str(path),'--algorithm',algorithm,
                        '--net-order','reverse','--output',str(out))
                    self.assertIn(proc.returncode,(0,2),proc.stderr)
                    data=json.loads(out.read_text())
                    self.assertEqual(data['net_order'],'reverse')
                    self.assertEqual(validate(path,data),proc.returncode==0)

    def test_python_validator_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'; layout=ROOT/'data/chip_layout_small.txt'
            self.run_router('--input',str(layout),'--output',str(out))
            data=json.loads(out.read_text()); data['nets'][0]['path'][0]['x']=999
            with self.assertRaises(ValueError): validate(layout,data)

    def test_input_cannot_be_overwritten_through_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'layout.txt'
            original = b'1 3\nS1 . T1\n'
            path.write_bytes(original)
            symlink = Path(directory)/'symbolic.txt'
            symlink.symlink_to(path)
            hardlink = Path(directory)/'hard.txt'
            os.link(path, hardlink)
            aliases = [str(path), str(path.parent)+'/./layout.txt', str(symlink), str(hardlink)]
            for alias in aliases:
                with self.subTest(alias=alias):
                    proc = self.run_router('--input',str(path),'--output',alias)
                    self.assertEqual(proc.returncode,1,proc.stdout)
                    self.assertIn('different files',proc.stderr)
                    self.assertEqual(path.read_bytes(),original)
            # Replacing a different existing output must remain supported.
            output = Path(directory)/'output.json'
            output.write_text('old output')
            proc = self.run_router('--input',str(path),'--output',str(output))
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertTrue(validate(path,json.loads(output.read_text())))

    def test_output_cost_model_and_termination_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'
            layout=ROOT/'benchmarks/layouts/congestion.txt'
            proc=self.run_router('--input',str(layout),'--algorithm','bfs',
                                 '--max-iterations','10000','--output',str(out))
            self.assertEqual(proc.returncode,2,proc.stderr)
            original=json.loads(out.read_text())
            self.assertFalse(validate(layout,original))
            self.assertEqual(original['termination_reason'],'congestion_insensitive')
            self.assertEqual(original['metrics']['routing_passes'],1)
            for reason in ['success','unreachable','unknown',None]:
                changed=copy.deepcopy(original)
                changed['termination_reason']=reason
                with self.assertRaises(ValueError): validate(layout,changed)
            changed=copy.deepcopy(original)
            changed['cost_model']['via']=1
            with self.assertRaises(ValueError): validate(layout,changed)
            legacy=copy.deepcopy(original)
            del legacy['termination_reason']
            self.assertFalse(validate(layout,legacy))

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
            for name in ['impossible','multilayer','impossible_overlap','via_sensitive','congestion']:
                out=Path(directory)/'out.json'
                self.run_router('--input',str(ROOT/f'benchmarks/layouts/{name}.txt'),'--output',str(out))
                data=json.loads(out.read_text()); before=copy.deepcopy(data)
                fig=build_figure(data)
                self.assertEqual(data,before)
                html=Path(directory)/f'{name}.html'; fig.write_html(html)
                self.assertGreater(html.stat().st_size,1000)
                self.assertEqual(list(fig.data[0].z),[p['z'] for p in data['nets'][0]['path']])
                for net in data['nets']:
                    trace=next(t for t in fig.data if t.name.startswith(net['name']+' ('))
                    for axis in ('x','y','z'):
                        self.assertEqual(list(getattr(trace,axis)),[p[axis] for p in net['path']])
                    pins=next(t for t in fig.data if t.name==net['name']+' pins')
                    self.assertEqual(list(pins.x),[net['source']['x'],net['target']['x']])
                if data['conflicts']:
                    conflict=next(t for t in fig.data if t.name=='Conflicts')
                    self.assertEqual(list(conflict.z),[c['cell']['z'] for c in data['conflicts']])
                if name=='multilayer':
                    self.assertEqual(sum(t.name.endswith('VIA') for t in fig.data),2)
            legacy={'nets':[{'name':'Net1','path':[]}]}
            self.assertEqual(len(build_figure(legacy).data[0].x),0)


if __name__ == '__main__':
    unittest.main()
