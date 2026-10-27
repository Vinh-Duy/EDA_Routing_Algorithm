"""Run fixed tree-growth cases beside S/T-only two-pin control projections."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/'benchmarks/multiterminal/layouts'
BASELINE=ROOT/'benchmarks/multiterminal/baseline_layouts'


def project_baseline(source, destination):
    """Keep S/T and all obstacles; erase only additional P terminals."""
    lines=source.read_text().splitlines()
    projected=[]
    for line in lines:
        projected.append(' '.join('.' if token.startswith('P') else token
                                  for token in line.split()))
    content='\n'.join(projected)+'\n'
    if destination.exists():
        if destination.read_text()!=content:
            raise ValueError(f'Existing baseline projection differs: {destination}')
    else:
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(content)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repetitions',type=int,default=10)
    parser.add_argument('--results-dir',type=Path,default=ROOT/'benchmarks/multiterminal/experiment')
    parser.add_argument('--skip-build',action='store_true')
    args=parser.parse_args()
    if args.repetitions<1:
        parser.error('repetitions must be positive')
    cases=sorted(CASES.glob('*.txt'))
    if not cases:
        parser.error('no fixed multi-terminal cases found')
    BASELINE.mkdir(parents=True,exist_ok=True)
    controls=[]
    for case in cases:
        control=BASELINE/f'st_baseline_{case.stem}.txt'
        project_baseline(case,control)
        controls.append(control)
    command=[sys.executable,str(ROOT/'benchmarks/run_benchmarks.py'),
             '--repetitions',str(args.repetitions),'--results-dir',str(args.results_dir)]
    if args.skip_build:
        command.append('--skip-build')
    for path in controls+cases:
        command.extend(['--input',str(path)])
    subprocess.run(command,check=True,cwd=ROOT)
    with (args.results_dir/'summary.csv').open() as file:
        rows={(row['dataset'],row['algorithm']):row for row in csv.DictReader(file)}
    lines=['# Multi-terminal routing experiment','',
           'The control is the same fixed layout with each `P<id>` replaced by `.`, leaving only its S/T pair. '
           'It measures the existing two-pin behavior on a reduced-terminal projection; it is not an equal-connectivity '
           'quality comparison. The tree column routes every original terminal. No quality superiority is inferred.', '',
           f"Runs: {args.repetitions} per case/algorithm; warm-up excluded; shuffle seed 20261016; max passes 10.",
           'All inputs are hand-designed fixed fixtures, so there is no obstacle-generation seed. Timings are local and descriptive.', '',
           '| Case | Algorithm | Control success | Tree success | Control length/wire/VIA/branches/cost | Tree length/wire/VIA/branches/cost | Control median ms / expanded | Tree median ms / expanded | Control termination / failed nets | Tree termination / failed nets |',
           '|---|---|---:|---:|---:|---:|---:|---:|---|---|']
    for case in cases:
        for algorithm in ('astar','dijkstra','bfs'):
            base=rows[f'st_baseline_{case.stem}',algorithm]
            tree=rows[case.stem,algorithm]
            base_failures=json.loads(base['net_failures'])
            failures=json.loads(tree['net_failures'])
            lines.append(f"| {case.stem} | {algorithm} | {base['success_rate']} | {tree['success_rate']} | "
                         f"{base['graph_steps']}/{base['wirelength']}/{base['via_count']}/{base['branch_count']}/{base['weighted_cost']} | "
                         f"{tree['graph_steps']}/{tree['wirelength']}/{tree['via_count']}/{tree['branch_count']}/{tree['weighted_cost']} | "
                         f"{base['median_ms']}/{base['nodes_expanded']} | {tree['median_ms']}/{tree['nodes_expanded']} | "
                         f"{base['termination_reason']} / `{json.dumps(base_failures,separators=(',',':'))}` | "
                         f"{tree['termination_reason']} / `{json.dumps(failures,separators=(',',':'))}` |")
    lines.extend(['','The reference result for the five-terminal branch case is independently enumerated in '
                  '[the Python tests](../../../tests/test_multiterminal.py). It proves the 4-edge optimum only for '
                  'that tiny instance; it is not a general Steiner optimality claim. Runtime/search effort include '
                  'the multi-source searches for each attachment. See `results.csv`, `summary.csv`, and `metadata.json` '
                  'for raw observations, per-net failure records, termination reasons, and hashes.'])
    (args.results_dir/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(f'Created comparable S/T-only controls and tree-growth runs in {args.results_dir}')
    print('Inputs are fixed hand-designed layouts; the harness records its shuffle seed and per-net failures.')


if __name__=='__main__':
    main()
