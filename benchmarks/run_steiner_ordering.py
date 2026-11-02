"""Paired single-net input-order versus nearest-terminal evaluation."""
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

from steiner_oracle import solve
from validate_output import read_layout_with_extras, validate

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'benchmarks/steiner/layouts'
STRATEGIES = ('input', 'nearest')
ALGORITHM = 'astar'
MAX_ITERATIONS = 1
PHYSICAL_COST_MODEL = {'planar': 1, 'via': 6}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def terminal_coordinates(layout):
    _, _, sources, targets, extras = read_layout_with_extras(layout)
    name = next(iter(sources))
    return [sources[name], targets[name], *extras.get(name, [])]


def compare_cost(exact, data, success):
    if exact['status'] == 'unknown':
        return 'oracle_resource_limited', None, None
    if exact['status'] == 'infeasible':
        if success:
            raise ValueError('Validated router success contradicts exact infeasibility')
        return 'proven_infeasible', None, None
    if not success:
        return 'router_failure', None, None
    physical = data['metrics']['weighted_cost']
    gap = physical - exact['optimal_cost']
    if gap < 0:
        raise ValueError('Validated router cost is below the exact optimum')
    relative = None if exact['optimal_cost'] == 0 else gap / exact['optimal_cost']
    return ('optimal' if gap == 0 else 'suboptimal'), gap, relative


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path,
                        default=ROOT / 'benchmarks/steiner/experiment_20261101_paired')
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--executable', type=Path, default=ROOT / 'router')
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error('repetitions must be positive')
    output_dir = args.results_dir.resolve()
    if output_dir.exists():
        parser.error(f'Results directory already exists; choose a fresh directory: {output_dir}')
    inputs = sorted(CORPUS.glob('*.txt'))
    if not inputs:
        parser.error(f'No deterministic Steiner fixtures found in {CORPUS}')
    executable = args.executable.resolve()
    if not args.skip_build:
        subprocess.run(['make', 'router'], cwd=ROOT, check=True)
    if not executable.is_file():
        parser.error(f'Router executable does not exist: {executable}')
    build_path = ROOT / 'build/router-build.json'
    build = json.loads(build_path.read_text()) if executable == (ROOT / 'router') and build_path.exists() else None
    if executable == (ROOT / 'router'):
        expected_sources = {str(path.relative_to(ROOT)): digest(path)
                            for path in sorted((ROOT / 'src').glob('*'))}
        if build is None or build['executable_sha256'] != digest(executable) or \
                build['source_sha256'] != expected_sources:
            parser.error('Executable/build record is stale; rebuild before benchmarking')
    source_files = sorted((ROOT / 'src').glob('*.hpp')) + [ROOT / 'src/main.cpp']
    tracked_files = source_files + [
        ROOT / 'Makefile',
        ROOT / 'benchmarks/record_build.py',
        ROOT / 'benchmarks/steiner_oracle.py',
        ROOT / 'benchmarks/run_steiner_ordering.py',
        ROOT / 'benchmarks/validate_output.py',
        ROOT / 'tests/test_router.cpp',
        ROOT / 'tests/test_steiner_oracle.py',
    ]
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in tracked_files}
    input_hashes = {str(path.relative_to(ROOT)): digest(path) for path in inputs}
    executable_hash = digest(executable)
    record = dict(
        schema_version=1,
        experiment='paired_single_net_terminal_ordering',
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        python=sys.version,
        compiler_build=build,
        executable_sha256=executable_hash,
        source_sha256=source_hashes,
        input_sha256=input_hashes,
        algorithm=ALGORITHM,
        net_order='numeric',
        terminal_strategies=list(STRATEGIES),
        max_iterations=MAX_ITERATIONS,
        physical_cost_model=PHYSICAL_COST_MODEL,
        repetitions=args.repetitions,
        warmups=1,
        timing_scope='router-reported runtime_ms; process wall time retained separately',
        execution_order='alternating strategy order by repetition; warmup input then nearest',
        seed=None,
        corpus='fixed deterministic fixtures; no stochastic generation',
        cases=[],
    )
    output_dir.mkdir(parents=True)
    raw_dir = output_dir / 'raw'
    raw_dir.mkdir()
    rows = []
    paired_rows = []
    fingerprints = {}
    for layout in inputs:
        exact = solve(layout)
        terminals = terminal_coordinates(layout)
        input_hash = input_hashes[str(layout.relative_to(ROOT))]
        case_results = {strategy: [] for strategy in STRATEGIES}
        output_files = {}
        for repetition in range(-1, args.repetitions):
            is_warmup = repetition == -1
            strategy_order = STRATEGIES if repetition % 2 else tuple(reversed(STRATEGIES))
            for strategy in strategy_order:
                label = 'warmup' if is_warmup else f'r{repetition:02d}'
                output_path = raw_dir / f'{layout.stem}_{strategy}_{label}.json'
                command = [
                    str(executable), '--input', str(layout), '--algorithm', ALGORITHM,
                    '--output', str(output_path), '--max-iterations', str(MAX_ITERATIONS),
                    '--net-order', 'numeric', '--terminal-order', strategy,
                ]
                row = dict(
                    case=layout.stem, input=str(layout.relative_to(ROOT)), input_sha256=input_hash,
                    terminals=json.dumps(terminals, separators=(',', ':')),
                    algorithm=ALGORITHM, terminal_strategy=strategy, net_order='numeric',
                    max_iterations=MAX_ITERATIONS, repetition=label, warmup=is_warmup,
                    oracle_status=exact['status'], oracle_reason=exact['reason'],
                    oracle_optimal_cost=exact['optimal_cost'], router_status='execution_error',
                    success=None, classification=None, physical_cost=None, absolute_gap=None,
                    relative_gap=None, wirelength=None, via_count=None, tree_edges=None,
                    branch_count=None, nodes_expanded=None, search_count=None,
                    search_objective_cost=None, runtime_ms=None, process_wall_ms=None,
                    termination_reason=None, output_json=str(output_path.relative_to(output_dir)),
                    output_sha256=None, stdout='', error='',
                )
                started = time.perf_counter()
                try:
                    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
                    row['process_wall_ms'] = (time.perf_counter() - started) * 1000
                    row['stdout'] = process.stdout.strip()
                    if process.returncode not in (0, 2):
                        raise ValueError(process.stderr.strip() or f'Router exited {process.returncode}')
                    data = json.loads(output_path.read_text())
                    successful = validate(layout, data)
                    if successful != (process.returncode == 0):
                        raise ValueError('Exit code contradicts independently validated output')
                    if data.get('terminal_order') != strategy or data.get('net_order') != 'numeric':
                        raise ValueError('Output strategy does not match the paired command')
                    stable = json.loads(json.dumps(data))
                    del stable['metrics']['runtime_ms']
                    signature = json.dumps(stable, sort_keys=True)
                    key = (layout.stem, strategy)
                    if key in fingerprints and fingerprints[key] != signature:
                        raise ValueError('Route geometry or non-timing metrics changed between repetitions')
                    fingerprints[key] = signature
                    classification, gap, relative = compare_cost(exact, data, successful)
                    row.update(
                        router_status='success' if successful else 'routing_failure',
                        success=successful,
                        classification=classification,
                        physical_cost=data['metrics']['weighted_cost'] if successful else None,
                        absolute_gap=gap,
                        relative_gap=relative,
                        wirelength=data['metrics']['wirelength'],
                        via_count=data['metrics']['via_count'],
                        tree_edges=data['metrics']['graph_steps'],
                        branch_count=data['metrics']['branch_count'],
                        nodes_expanded=data['metrics']['nodes_expanded'],
                        search_count=data['metrics']['search_count'],
                        search_objective_cost=data['metrics']['search_cost'],
                        runtime_ms=data['metrics']['runtime_ms'],
                        termination_reason=data['termination_reason'],
                        output_sha256=digest(output_path),
                    )
                    output_files[f'{strategy}_{label}'] = row['output_json']
                except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
                    row['error'] = str(error)
                    row['router_status'] = 'execution_error'
                case_results[strategy].append(row)
                rows.append(row)
        case_results = {
            strategy: [row for row in strategy_runs if not row['warmup']]
            for strategy, strategy_runs in case_results.items()
        }
        pair = dict(case=layout.stem, input=str(layout.relative_to(ROOT)), input_sha256=input_hash,
                    oracle_status=exact['status'], oracle_reason=exact['reason'],
                    oracle_optimal_cost=exact['optimal_cost'])
        for strategy in STRATEGIES:
            measured = case_results[strategy]
            verified = [row for row in measured if row['router_status'] in ('success', 'routing_failure')]
            successful = [row for row in verified if row['success']]
            observed = verified[0] if verified else None
            pair.update({
                f'{strategy}_success_rate': (len(successful) / len(measured)) if measured else None,
                f'{strategy}_physical_cost': successful[0]['physical_cost'] if successful else None,
                f'{strategy}_absolute_gap': successful[0]['absolute_gap'] if successful else None,
                f'{strategy}_relative_gap': successful[0]['relative_gap'] if successful else None,
                f'{strategy}_wirelength': observed['wirelength'] if observed else None,
                f'{strategy}_via_count': observed['via_count'] if observed else None,
                f'{strategy}_tree_edges': observed['tree_edges'] if observed else None,
                f'{strategy}_branch_count': observed['branch_count'] if observed else None,
                f'{strategy}_nodes_expanded': observed['nodes_expanded'] if observed else None,
                f'{strategy}_search_count': observed['search_count'] if observed else None,
                f'{strategy}_runtime_median_ms': statistics.median(
                    row['runtime_ms'] for row in verified if row['runtime_ms'] is not None
                ) if any(row['runtime_ms'] is not None for row in verified) else None,
                f'{strategy}_termination_reason': successful[0]['termination_reason']
                if successful else (verified[0]['termination_reason'] if verified else 'execution_error'),
            })
        if pair['input_success_rate'] is not None and pair['nearest_success_rate'] is not None:
            pair['paired_physical_cost_difference_nearest_minus_input'] = (
                pair['nearest_physical_cost'] - pair['input_physical_cost']
                if pair['input_physical_cost'] is not None and pair['nearest_physical_cost'] is not None else None
            )
            pair['paired_search_count_difference_nearest_minus_input'] = (
                pair['nearest_search_count'] - pair['input_search_count']
                if pair['nearest_search_count'] is not None and pair['input_search_count'] is not None else None
            )
            pair['paired_nodes_difference_nearest_minus_input'] = (
                pair['nearest_nodes_expanded'] - pair['input_nodes_expanded']
                if pair['nearest_nodes_expanded'] is not None and pair['input_nodes_expanded'] is not None else None
            )
            pair['paired_median_runtime_difference_nearest_minus_input_ms'] = (
                pair['nearest_runtime_median_ms'] - pair['input_runtime_median_ms']
                if pair['nearest_runtime_median_ms'] is not None and
                pair['input_runtime_median_ms'] is not None else None
            )
        paired_rows.append(pair)
        record['cases'].append(dict(
            input=str(layout.relative_to(ROOT)), input_sha256=input_hash, oracle=exact,
            raw_outputs=output_files,
        ))

    fields = list(rows[0])
    with (output_dir / 'raw_runs.csv').open('x', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    pair_fields = list(paired_rows[0])
    with (output_dir / 'paired_results.csv').open('x', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=pair_fields)
        writer.writeheader()
        writer.writerows(paired_rows)
    with (output_dir / 'metadata.json').open('x') as file:
        json.dump(record, file, indent=2, allow_nan=False)
        file.write('\n')
    write_report(output_dir, paired_rows, rows, record)
    if source_hashes != {str(path.relative_to(ROOT)): digest(path) for path in tracked_files} or \
            input_hashes != {str(path.relative_to(ROOT)): digest(path) for path in inputs} or \
            executable_hash != digest(executable):
        raise ValueError('Source, input, or executable changed during the experiment')
    print(f"Recorded {len(rows)} raw runs for {len(inputs)} identical single-net cases in {output_dir}")
    print(f"Oracle statuses: {', '.join(case['oracle']['status'] for case in record['cases'])}")
    print(f"Results: {output_dir / 'RESULTS.md'}")
    return 0


def write_report(output_dir, paired_rows, raw_rows, record):
    lines = [
        '# Paired single-net terminal-ordering experiment', '',
        'Each pair uses identical layout bytes, terminal coordinates, obstacles, planar/VIA weights, '
        'A* search, numeric net scheduling, and one routing pass. Only the terminal attachment strategy '
        'changes. The input-order strategy is the existing default; nearest is opt-in. The exact reference '
        'is the single-net Dreyfus-Wagner oracle. No multi-net optimality claim is made.', '',
        f"Commit `{record['git_commit']}`; machine `{record['machine']}`; "
        f"compiler `{(record['compiler_build'] or {}).get('compiler_version', 'unrecorded')}`; "
        f"build flags `{(record['compiler_build'] or {}).get('flags', 'unrecorded')}`.",
        f"Measured repetitions per strategy/case: {record['repetitions']}; one warm-up retained but excluded. "
        'Runtime is router-reported milliseconds; process wall time is separately retained.',
        'All layouts are fixed, hand-designed fixtures (no random seed). Raw route JSONs, per-invocation '
        'metrics, SHA-256 hashes, and exact oracle witnesses are retained beside this report.', '',
        '| Case | Oracle | Optimum | Input success/cost/gap | Nearest success/cost/gap | Input wire/VIA/edges/branches | Nearest wire/VIA/edges/branches | Input searches/nodes/median ms | Nearest searches/nodes/median ms | Termination (input / nearest) | Paired deltas (nearest minus input): cost/searches/nodes/median ms |',
        '|---|---|---:|---|---|---|---|---|---|---|---|',
    ]
    for row in paired_rows:
        def display(strategy, field, fallback='—'):
            value = row.get(f'{strategy}_{field}')
            return fallback if value is None else str(value)
        def display_delta(field):
            value = row.get(field)
            return '—' if value is None else str(value)
        lines.append(
            f"| {row['case']} | {row['oracle_status']} | {row['oracle_optimal_cost'] if row['oracle_optimal_cost'] is not None else '—'} "
            f"| {display('input','success_rate')}/{display('input','physical_cost')}/{display('input','absolute_gap')} "
            f"| {display('nearest','success_rate')}/{display('nearest','physical_cost')}/{display('nearest','absolute_gap')} "
            f"| {display('input','wirelength')}/{display('input','via_count')}/{display('input','tree_edges')}/{display('input','branch_count')} "
            f"| {display('nearest','wirelength')}/{display('nearest','via_count')}/{display('nearest','tree_edges')}/{display('nearest','branch_count')} "
            f"| {display('input','search_count')}/{display('input','nodes_expanded')}/{display('input','runtime_median_ms')} "
            f"| {display('nearest','search_count')}/{display('nearest','nodes_expanded')}/{display('nearest','runtime_median_ms')} "
            f"| {row['input_termination_reason']} / {row['nearest_termination_reason']} "
            f"| {display_delta('paired_physical_cost_difference_nearest_minus_input')}/"
            f"{display_delta('paired_search_count_difference_nearest_minus_input')}/"
            f"{display_delta('paired_nodes_difference_nearest_minus_input')}/"
            f"{display_delta('paired_median_runtime_difference_nearest_minus_input_ms')} |"
        )
    deltas = [row.get('paired_physical_cost_difference_nearest_minus_input')
              for row in paired_rows if row.get('paired_physical_cost_difference_nearest_minus_input') is not None]
    search_deltas = [row['paired_search_count_difference_nearest_minus_input']
                     for row in paired_rows
                     if row.get('paired_search_count_difference_nearest_minus_input') is not None]
    node_deltas = [row['paired_nodes_difference_nearest_minus_input']
                   for row in paired_rows
                   if row.get('paired_nodes_difference_nearest_minus_input') is not None]
    runtime_deltas = [row['paired_median_runtime_difference_nearest_minus_input_ms']
                      for row in paired_rows
                      if row.get('paired_median_runtime_difference_nearest_minus_input_ms') is not None]
    lines.extend(['', f'Paired feasible cost differences (nearest minus input): {deltas or "not available"}.',
                  f'Per-instance search-count differences: {search_deltas or "not available"}; '
                  f'expanded-node differences: {node_deltas or "not available"}.',
                  f'Per-instance median-runtime differences (nearest minus input, ms): {runtime_deltas or "not available"}; '
                  f'median across these fixed cases: '
                  f'{statistics.median(runtime_deltas) if runtime_deltas else "not available"}.',
                  'The fixed execution order alternates strategy order between repetitions; these small local '
                  'runtime differences remain descriptive and noisy.',
                  f"Recorded invocation count: {len(raw_rows)}; measured rows exclude "
                  f"{sum(row['warmup'] for row in raw_rows)} warm-ups.",
                  'A zero-cost optimum uses a null relative gap; infeasible and failed-router cases do not receive '
                  'a physical-cost gap. Repeated timings are repeated measurements of these layouts, not additional '
                  'independent instances.', '',
                  'See `raw_runs.csv`, `paired_results.csv`, `metadata.json`, and `raw/` for the complete record.'])
    with (output_dir / 'RESULTS.md').open('x') as file:
        file.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Paired experiment error: {error}', file=sys.stderr)
        sys.exit(1)
