"""Small dependency-free CLI/benchmark smoke gate; every unexpected status fails."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmarks'))
from validate_output import validate


def main():
    (ROOT/'build').mkdir(exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix='cli-smoke-',dir=ROOT/'build'))
    for algorithm in ('astar','dijkstra','bfs'):
        for name,expected in [('simple_2d',0),('multilayer',0),('impossible',2),('impossible_overlap',2)]:
            layout=ROOT/f'benchmarks/layouts/{name}.txt';output=directory/f'{name}_{algorithm}.json'
            proc=subprocess.run([str(ROOT/'router'),'--input',str(layout),'--algorithm',algorithm,
                                 '--output',str(output)],capture_output=True,text=True)
            if proc.returncode != expected:
                raise RuntimeError(f'{name}/{algorithm}: expected {expected}, got {proc.returncode}: {proc.stderr}')
            if validate(layout,json.loads(output.read_text())) != (expected==0):
                raise RuntimeError('Independent validation disagrees')
    invalid=directory/'invalid.txt';invalid.write_text('1 2\nS1\n')
    proc=subprocess.run([str(ROOT/'router'),'--input',str(invalid),'--output',str(directory/'bad.json')],capture_output=True)
    if proc.returncode != 1 or (directory/'bad.json').exists():
        raise RuntimeError('Invalid layout did not fail safely')
    proc=subprocess.run([sys.executable,str(ROOT/'benchmarks/validate_output.py'),
                        '--input',str(invalid),'--output',str(directory/'missing.json')],capture_output=True)
    if proc.returncode == 0:
        raise RuntimeError('Validator script accepted invalid input')
    command=[sys.executable,str(ROOT/'benchmarks/run_benchmarks.py'),'--skip-build',
             '--repetitions','2','--results-dir',str(directory/'benchmark')]
    for name in ('simple_2d','multilayer','impossible'):
        command+=['--input',str(ROOT/f'benchmarks/layouts/{name}.txt')]
    subprocess.run(command,check=True,cwd=ROOT)
    with (directory/'benchmark/results.csv').open() as file:
        rows=list(csv.DictReader(file))
    if len(rows)!=18 or any(r['output_verified']!='True' for r in rows):
        raise RuntimeError('Benchmark smoke results incomplete')
    print(f'Smoke passed: 12 routing cases, invalid input/script checks, 18 benchmark observations. Logs: {directory}')


if __name__ == '__main__':
    main()
