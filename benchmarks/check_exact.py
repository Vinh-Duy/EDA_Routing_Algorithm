"""Compare the existing router with exhaustive tiny-layout optima (not a timing benchmark)."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from exact_oracle import DEFAULT_MAX_STATES, compare, solve

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(executable, inputs, max_states):
    source_paths = sorted((ROOT/'src').glob('*.hpp')) + [ROOT/'src/main.cpp']
    source_paths += [ROOT/'benchmarks'/name for name in
                     ('exact_oracle.py','check_exact.py','validate_output.py')]
    source_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in source_paths}
    input_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in inputs}
    binary_hash = sha256(executable)
    report = dict(schema_version=1, experiment='tiny_exact_quality',
                  created_at_utc=datetime.now(timezone.utc).isoformat(),
                  git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                  source_sha256=source_hashes, input_sha256=input_hashes,
                  executable_sha256=binary_hash, max_states=max_states, max_iterations=10,
                  physical_cost_model=dict(planar=1,via=6), cases=[])
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)/'route.json'
        for layout in inputs:
            exact = solve(layout, max_states)
            case = dict(input=str(layout.relative_to(ROOT)), oracle=exact, comparisons=[])
            for order in ('numeric','reverse'):
                for algorithm in ('astar','dijkstra','bfs'):
                    output.unlink(missing_ok=True)
                    proc = subprocess.run([str(executable),'--input',str(layout),'--output',str(output),
                        '--algorithm',algorithm,'--net-order',order,'--max-iterations','10'],
                        cwd=ROOT,capture_output=True,text=True,timeout=30)
                    if proc.returncode not in (0,2):
                        raise ValueError(f'{layout.name}/{algorithm}/{order}: exit {proc.returncode}: {proc.stderr}')
                    candidate = json.loads(output.read_text())
                    comparison = compare(layout,candidate,exact)
                    if comparison['router_success'] != (proc.returncode == 0):
                        raise ValueError('Router exit status contradicts validated output')
                    if candidate['algorithm'] != algorithm or candidate.get('net_order') != order:
                        raise ValueError('Router output does not match requested algorithm/order')
                    metrics = candidate['metrics']
                    # No timing observations retained or aggregated in this study.
                    case['comparisons'].append(dict(algorithm=algorithm,net_order=order,
                        **comparison, physical_cost=metrics['weighted_cost'] if candidate['success'] else None,
                        routing_passes=metrics['routing_passes'],conflicting_cells=metrics['unresolved_conflicts'],
                        paths={n['name']:n['path'] for n in candidate['nets']}))
            report['cases'].append(case)
    if source_hashes != {str(p.relative_to(ROOT)):sha256(p) for p in source_paths} or \
       input_hashes != {str(p.relative_to(ROOT)):sha256(p) for p in inputs} or sha256(executable) != binary_hash:
        raise ValueError('Source, inputs, or executable changed during the comparison')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path,help='New JSON file; existing files are never overwritten')
    parser.add_argument('--executable',type=Path,default=ROOT/'router')
    parser.add_argument('--max-states',type=int,default=DEFAULT_MAX_STATES)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a fresh file')
    if args.max_states < 1:
        parser.error('max-states must be positive')
    try:
        inputs = sorted((ROOT/'benchmarks/exact/layouts').glob('*.txt'))
        if not inputs:
            raise ValueError('No exact-oracle fixtures found')
        report = run(args.executable.resolve(),inputs,args.max_states)
        serialized = json.dumps(report,indent=2,allow_nan=False)+'\n'
        with args.output.open('x') as file:
            file.write(serialized)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print(f'Exact comparison error: {error}',file=sys.stderr)
        return 1
    unknown = any(c['oracle']['status']=='unknown' for c in report['cases'])
    print(f'Checked {len(report["cases"])} layouts; saved {args.output}')
    return 3 if unknown else 0


if __name__ == '__main__':
    sys.exit(main())
