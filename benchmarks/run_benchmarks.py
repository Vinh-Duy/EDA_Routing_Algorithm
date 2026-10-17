"""Run the same instances with all algorithms; retain real failures and raw timings."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

from validate_output import validate

ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = ('astar', 'dijkstra', 'bfs')
METRICS = ('total_nets', 'routed_nets', 'success_rate', 'unrouted_nets', 'invalid_nets',
           'unresolved_conflicts', 'wirelength', 'via_count', 'graph_steps', 'weighted_cost',
           'search_cost', 'routing_passes', 'reroute_iterations', 'runtime_ms', 'nodes_expanded')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repetitions', type=int, default=20)
    parser.add_argument('--max-iterations', type=int, default=10)
    parser.add_argument('--net-order', choices=('numeric','reverse'), default='numeric')
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--executable', type=Path, default=ROOT / 'router')
    parser.add_argument('--results-dir', type=Path, default=ROOT / 'build/benchmarks')
    parser.add_argument('--input', type=Path, action='append', dest='inputs',
                        help='Select a layout; repeat for multiple inputs (default: all original fixtures)')
    args = parser.parse_args()
    if args.repetitions < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('repetitions and finite timeout must be positive')
    if not 1 <= args.max_iterations <= 10000:
        parser.error('max-iterations must be 1..10000')
    datasets = args.inputs if args.inputs is not None else (
        sorted((ROOT / 'data').glob('*.txt')) + sorted((ROOT / 'benchmarks/layouts').glob('*.txt')))
    datasets = [p.resolve() for p in datasets]
    if not datasets or any(not p.is_file() for p in datasets):
        parser.error('Every selected input must be an existing layout file')
    if len({p.stem for p in datasets}) != len(datasets):
        parser.error('Duplicate dataset identifiers; input filenames must have unique stems')
    output_dir = args.results_dir.resolve()
    if any((output_dir/name).exists() for name in ('results.csv','summary.csv','metadata.json')):
        parser.error('Results already exist; choose a fresh results directory')
    if not args.skip_build:
        subprocess.run(['make', '-B', 'router'], cwd=ROOT, check=True)
    executable = args.executable.resolve()
    build = None
    record_path = ROOT/'build/router-build.json'
    if executable == ROOT/'router' and record_path.exists():
        build = json.loads(record_path.read_text())
        current_sources = {str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'src').glob('*'))}
        if build['executable_sha256'] != digest(executable) or build['source_sha256'] != current_sources:
            parser.error('Executable/build record is stale; rebuild before benchmarking')
    route_dir = output_dir / 'routes'
    route_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(path, algorithm) for path in datasets for algorithm in ALGORITHMS]
    tracked = sorted((ROOT/'src').glob('*')) + datasets + [ROOT/'Makefile'] + sorted((ROOT/'benchmarks').glob('*.py'))
    hashes = {os.path.relpath(p,ROOT):digest(p) for p in tracked}
    executable_hash = digest(executable) if executable.is_file() else None
    rows = []
    fingerprints = {}
    errors = []
    rng = random.Random(20261016)

    def execute(path, algorithm, repetition):
        output = route_dir / f'{path.stem}_{algorithm}.json'
        # Unique per invocation avoids reading stale results after a failure.
        output = output.with_name(f'{output.stem}_{repetition}.json')
        command = [str(executable), '--input', str(path), '--algorithm', algorithm,
                   '--output', str(output), '--max-iterations', str(args.max_iterations),
                   '--net-order', args.net_order]
        row = dict(dataset=path.stem, input=os.path.relpath(path,ROOT), algorithm=algorithm,
                   repetition=repetition, status='execution_error', returncode='', success='',
                   output_verified=False, termination_reason='', net_order=args.net_order, error='')
        begin = time.perf_counter()
        try:
            output.unlink(missing_ok=True)
            proc = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout, cwd=ROOT)
            row['process_wall_ms'] = (time.perf_counter()-begin)*1000
            row['returncode'] = proc.returncode
            if proc.returncode not in (0, 2):
                raise ValueError(proc.stderr.strip() or proc.stdout.strip() or f'Exit {proc.returncode}')
            data = json.loads(output.read_text())
            success = validate(path, data)
            if success != (proc.returncode == 0) or data['algorithm'] != algorithm:
                raise ValueError('Exit status or algorithm mismatch')
            if data.get('net_order','numeric') != args.net_order:
                raise ValueError('Net ordering mismatch')
            # Compare every non-timing result across repetitions, including full paths.
            stable = json.loads(json.dumps(data))
            del stable['metrics']['runtime_ms']
            signature = json.dumps(stable, sort_keys=True)
            key = (path.stem, algorithm)
            if key in fingerprints and fingerprints[key] != signature:
                raise ValueError('Nondeterministic route or quality metrics')
            fingerprints[key] = signature
            row.update({key: data['metrics'][key] for key in METRICS})
            row.update(success=success, output_verified=True, status='success' if success else 'routing_failed')
            row['termination_reason'] = data.get('termination_reason', '')
        except (subprocess.TimeoutExpired, ValueError, OSError, KeyError, TypeError, IndexError) as error:
            row['error'] = str(error)
            errors.append(f'{path.stem}/{algorithm}/{repetition}: {error}')
        return row

    # One warm-up per pair, excluded from timing statistics but still checked.
    for path, algorithm in jobs:
        execute(path, algorithm, -1)
    for repetition in range(args.repetitions):
        rng.shuffle(jobs)
        for path, algorithm in jobs:
            rows.append(execute(path, algorithm, repetition))
        print(f'Completed repetition {repetition+1}/{args.repetitions}', flush=True)
    fields = ['dataset', 'input', 'algorithm', 'repetition', 'status', 'returncode', 'success',
              'output_verified', 'termination_reason', 'net_order', *METRICS, 'process_wall_ms', 'error']
    with (output_dir / 'results.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    summaries = []
    for path in datasets:
        for algorithm in ALGORITHMS:
            group = [r for r in rows if r['dataset']==path.stem and r['algorithm']==algorithm]
            verified = [r for r in group if r['output_verified']]
            runtimes = [r['runtime_ms'] for r in verified]
            summary = dict(dataset=path.stem, algorithm=algorithm, repetitions=len(group),
                           verified_runs=len(verified), successful_runs=sum(r['success'] is True for r in group),
                           execution_errors=len(group)-len(verified),
                           termination_reason=verified[0]['termination_reason'] if verified else '',
                           net_order=args.net_order)
            for key, fn in [('median_ms',statistics.median),('mean_ms',statistics.mean),
                            ('stdev_ms',lambda xs: statistics.stdev(xs) if len(xs)>1 else 0),
                            ('min_ms',min),('max_ms',max)]:
                summary[key] = fn(runtimes) if runtimes else ''
            for key in METRICS:
                if key != 'runtime_ms':
                    summary[key] = verified[0][key] if verified else ''
            summaries.append(summary)
    with (output_dir / 'summary.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(summaries[0]))
        writer.writeheader(); writer.writerows(summaries)
    if any(digest(ROOT/p) != h for p,h in hashes.items()) or (
        executable.is_file() and digest(executable) != executable_hash):
        errors.append('Inputs, source files, or executable changed during the experiment')
    git = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
    status = subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True)
    metadata = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                    machine=platform.machine(), processor=platform.processor(), cpu_count=os.cpu_count(),
                    python=sys.version, build=build, build_provenance='recorded' if build else 'unavailable',
                    compiler=build['compiler_version'] if build else None,
                    build_command=build['command'] if build else None,
                    build_flags=build['flags'] if build else None,
                    git_commit=git.stdout.strip() if git.returncode == 0 else None,
                    git_status=status.stdout if status.returncode == 0 else None,
                    argv=sys.argv, repetitions=args.repetitions, warmups=1, shuffle_seed=20261016,
                    max_iterations=args.max_iterations, net_order=args.net_order, timeout_seconds=args.timeout,
                    executable_sha256=executable_hash, sha256=hashes, errors=errors)
    (output_dir/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(f'{len(rows)} observations; {len(errors)} execution/validation errors; CSV: {output_dir}')
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
