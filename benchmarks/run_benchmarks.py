"""Run the same instances with all algorithms; retain real failures and raw timings."""
import argparse
import csv
import hashlib
import json
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
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--executable', type=Path, default=ROOT / 'router')
    parser.add_argument('--results-dir', type=Path, default=ROOT / 'benchmarks')
    args = parser.parse_args()
    if args.repetitions < 1 or args.timeout <= 0:
        parser.error('repetitions and timeout must be positive')
    if not args.skip_build:
        subprocess.run(['make', 'router'], cwd=ROOT, check=True)
    executable = args.executable.resolve()
    output_dir = args.results_dir.resolve()
    route_dir = output_dir / 'routes'
    route_dir.mkdir(parents=True, exist_ok=True)
    datasets = sorted((ROOT / 'data').glob('*.txt')) + sorted((ROOT / 'benchmarks/layouts').glob('*.txt'))
    jobs = [(path, algorithm) for path in datasets for algorithm in ALGORITHMS]
    rows = []
    fingerprints = {}
    errors = []
    rng = random.Random(20261016)

    def execute(path, algorithm, repetition):
        output = route_dir / f'{path.stem}_{algorithm}.json'
        # Unique per invocation avoids reading stale results after a failure.
        output = output.with_name(f'{output.stem}_{repetition}.json')
        command = [str(executable), '--input', str(path), '--algorithm', algorithm,
                   '--output', str(output), '--max-iterations', str(args.max_iterations)]
        row = dict(dataset=path.stem, input=str(path.relative_to(ROOT)), algorithm=algorithm,
                   repetition=repetition, status='execution_error', returncode='', success='',
                   output_verified=False, error='')
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
        except (subprocess.TimeoutExpired, ValueError, OSError, KeyError) as error:
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
              'output_verified', *METRICS, 'process_wall_ms', 'error']
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
                           execution_errors=len(group)-len(verified))
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
    compiler = subprocess.run(['c++','--version'], capture_output=True, text=True).stdout.strip()
    tracked = sorted((ROOT/'src').glob('*')) + datasets + [ROOT/'Makefile'] + sorted((ROOT/'benchmarks').glob('*.py'))
    metadata = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                    machine=platform.machine(), processor=platform.processor(), cpu_count=os.cpu_count(),
                    python=sys.version, compiler=compiler, build_command='make router',
                    build_flags='-std=c++17 -O2 -Wall -Wextra -Wpedantic (Makefile default; inspect overrides)',
                    argv=sys.argv, repetitions=args.repetitions, warmups=1, shuffle_seed=20261016,
                    max_iterations=args.max_iterations, timeout_seconds=args.timeout,
                    executable_sha256=digest(executable),
                    sha256={str(p.relative_to(ROOT)):digest(p) for p in tracked}, errors=errors)
    (output_dir/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(f'{len(rows)} observations; {len(errors)} execution/validation errors; CSV: {output_dir}')
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
