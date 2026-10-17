import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmarks'))
from validate_output import validate, read_layout
from generate_robustness import layout_text, SEEDS
from verify_evidence import verify_suite


class BenchmarkTests(unittest.TestCase):
    def runner(self, directory, *args):
        return subprocess.run([sys.executable,str(ROOT/'benchmarks/run_benchmarks.py'),
            '--skip-build','--repetitions','1','--input',str(ROOT/'benchmarks/layouts/simple_2d.txt'),
            '--results-dir',str(directory),*args],cwd=ROOT,capture_output=True,text=True)

    def test_invalid_output_is_recorded_without_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for i,payload in enumerate([{'nets':None}, [], {'success':False}, 'not json']):
                fake=root/f'fake{i}'
                fake.write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n'
                    +f"Path(sys.argv[sys.argv.index('--output')+1]).write_text({json.dumps(payload)!r})\n")
                fake.chmod(0o755)
                result=root/f'results{i}'
                proc=self.runner(result,'--executable',str(fake))
                self.assertEqual(proc.returncode,1,proc.stderr)
                with (result/'results.csv').open() as file:
                    rows=list(csv.DictReader(file))
                self.assertEqual(len(rows),3)
                self.assertTrue(all(r['status']=='execution_error' and r['runtime_ms']=='' for r in rows))
                meta=json.loads((result/'metadata.json').read_text())
                self.assertEqual(len(meta['errors']),6)  # Warm-ups also fail.
                self.assertEqual(meta['build_provenance'],'unavailable')
                self.assertIsNone(meta['compiler'])

    def test_timeout_and_stale_output_are_not_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);fake=root/'slow'
            fake.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(2)\n');fake.chmod(0o755)
            result=root/'results';routes=result/'routes';routes.mkdir(parents=True)
            (routes/'simple_2d_astar_0.json').write_text((ROOT/'output.json').read_text())
            proc=self.runner(result,'--executable',str(fake),'--timeout','0.01')
            self.assertEqual(proc.returncode,1,proc.stderr)
            with (result/'results.csv').open() as file:
                rows=list(csv.DictReader(file))
            self.assertTrue(all(r['runtime_ms']=='' and r['output_verified']=='False' for r in rows))
            self.assertFalse((routes/'simple_2d_astar_0.json').exists())

    def test_argument_errors_and_existing_results_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for args in [('--timeout','nan'),('--timeout','inf'),('--max-iterations','0'),
                         ('--max-iterations','10001'),('--repetitions','0')]:
                self.assertEqual(self.runner(root/'new',*args).returncode,2)
            duplicate=root/'simple_2d.txt';duplicate.write_text('1 2\nS1 T1\n')
            self.assertEqual(self.runner(root/'new','--input',str(duplicate)).returncode,2)
            record=root/'results.csv';record.write_text('preserve this evidence\n')
            self.assertEqual(self.runner(root).returncode,2)
            self.assertEqual(record.read_text(),'preserve this evidence\n')

    def test_validator_rejects_invalid_geometry_and_metric_types(self):
        with tempfile.TemporaryDirectory() as d:
            layout=Path(d)/'layout.txt';out=Path(d)/'out.json'
            layout.write_text('1 3\nS1 . T1\n')
            subprocess.run([str(ROOT/'router'),'--input',str(layout),'--output',str(out)],check=True,capture_output=True)
            original=json.loads(out.read_text())
            bad=copy.deepcopy(original);bad.pop('termination_reason')
            bad['nets'][0]['path'].pop(1);bad['nets'][0]['valid']=bad['nets'][0]['local_valid']=False
            bad['success']=False
            bad['metrics'].update(routed_nets=0,success_rate=0,invalid_nets=1,wirelength=0,graph_steps=0,weighted_cost=0)
            with self.assertRaises(ValueError):validate(layout,bad)
            for key,value in [('total_nets',True),('nodes_expanded',1.5),('search_cost',-1),('runtime_ms',float('nan'))]:
                bad=copy.deepcopy(original);bad['metrics'][key]=value
                with self.assertRaises(ValueError):validate(layout,bad)
            for bad in [None,[],{'nets':None}]:
                with self.assertRaises(ValueError):validate(layout,bad)

    def test_python_layout_parser_matches_canonical_integer_rules(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'layout.txt'
            for data in ['', '01 2\nS1 T1\n', '1 2\nS01 T01\n', '1 1000001\n',
                         '1 2\nS2147483648 T2147483648\n']:
                path.write_text(data)
                with self.assertRaises(ValueError):read_layout(path)

    def test_robustness_generator_is_deterministic_with_fixed_pins(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'layout.txt';layouts=set();pins=None
            for seed in SEEDS:
                text=layout_text(seed)
                self.assertEqual(text,layout_text(seed));layouts.add(text);path.write_text(text)
                dims,cells,sources,targets=read_layout(path)
                self.assertEqual(dims,[4,40,40]);self.assertEqual(len(sources),12)
                current=(sources,targets)
                if pins is not None:self.assertEqual(current,pins)
                pins=current
            self.assertEqual(len(layouts),5)

    def test_evidence_checker_rejects_corrupted_statistics(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            for name in ('metadata.json','results.csv','summary.csv'):
                (folder/name).write_bytes((ROOT/'benchmarks'/name).read_bytes())
            with (folder/'summary.csv').open() as file:
                rows=list(csv.DictReader(file))
            rows[0]['mean_ms']=str(float(rows[0]['mean_ms'])+1)
            with (folder/'summary.csv').open('w',newline='') as file:
                writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            with self.assertRaisesRegex(ValueError,'mean_ms'):verify_suite(folder)


if __name__ == '__main__':
    unittest.main()
