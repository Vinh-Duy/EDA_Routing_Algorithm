"""Run a serial, paired input-order versus nearest-terminal held-out study."""
import argparse
import csv
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from steiner_oracle import solve
from validate_output import read_layout_with_extras, validate


ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = ('input', 'nearest')
ALGORITHM = 'astar'
MAX_ITERATIONS = 1
BOOTSTRAP_SEED = 20261103
BOOTSTRAP_SAMPLES = 10000


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _median(values):
    return statistics.median(values) if values else None


def _mean(values):
    return statistics.mean(values) if values else None


def _bootstrap_mean_interval(values, seed=BOOTSTRAP_SEED):
    if not values:
        return None
    if len(values) == 1:
        return [values[0], values[0]]
    rng = random.Random(seed)
    means = []
    for _ in range(BOOTSTRAP_SAMPLES):
        means.append(statistics.mean(rng.choices(values, k=len(values))))
    means.sort()
    return [means[int(0.025 * (len(means) - 1))],
            means[int(0.975 * (len(means) - 1))]
            ]


def _sign_test_two_sided(nonzero_differences):
    n = len(nonzero_differences)
    if not n:
        return None
    smaller = min(sum(value > 0 for value in nonzero_differences),
                  sum(value < 0 for value in nonzero_differences))
    tail = sum(math.comb(n, k) for k in range(smaller + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def _layout_metadata(path):
    dimensions, cells, sources, targets, extras = read_layout_with_extras(path)
    if len(sources) != 1:
        raise ValueError(f'Held-out input must contain one net: {path}')
    net = next(iter(sources))
    terminals = [sources[net], targets[net], *extras.get(net, [])]
    obstacles = sum(token == '#' for token in cells.values())
    density = obstacles / len(cells)
    if density == 0:
        density_band = 'none'
    elif density < 0.10:
        density_band = 'low_lt_10pct'
    elif density <= 0.20:
        density_band = 'moderate_10_to_20pct'
    else:
        density_band = 'high_gt_20pct'
    return {
        'dimensions': dimensions,
        'terminal_count': len(set(terminals)),
        'terminals': terminals,
        'obstacle_count': obstacles,
        'obstacle_density': density,
        'obstacle_density_band': density_band,
    }


def _bootstrap_paired(values, seed):
    return _bootstrap_mean_interval(values, seed)


def _group_summary(rows, label):
    feasible = [row for row in rows if row['oracle_status'] == 'optimal']
    summaries = {
        'stratum': label,
        'instance_count': len(rows),
        'oracle_feasible_count': len(feasible),
        'oracle_infeasible_count': sum(row['oracle_status'] == 'infeasible' for row in rows),
        'input_successes_on_infeasible': sum(
            row['oracle_status'] == 'infeasible' and row['input_success'] for row in rows),
        'nearest_successes_on_infeasible': sum(
            row['oracle_status'] == 'infeasible' and row['nearest_success'] for row in rows),
        'input_execution_error_cases': sum(row['input_execution_error_count'] > 0 for row in rows),
        'nearest_execution_error_cases': sum(row['nearest_execution_error_count'] > 0 for row in rows),
    }
    for strategy in STRATEGIES:
        success = [row for row in feasible if row[f'{strategy}_success']]
        gaps = [row[f'{strategy}_relative_gap'] for row in success
                if row[f'{strategy}_relative_gap'] is not None]
        summaries.update({
            f'{strategy}_success_count': len(success),
            f'{strategy}_success_rate': len(success) / len(feasible) if feasible else None,
            f'{strategy}_gap_count': len(gaps),
            f'{strategy}_mean_gap': _mean(gaps),
            f'{strategy}_median_gap': _median(gaps),
            f'{strategy}_mean_nodes': _mean([row[f'{strategy}_nodes_expanded'] for row in feasible
                                             if row[f'{strategy}_nodes_expanded'] is not None]),
            f'{strategy}_mean_searches': _mean([row[f'{strategy}_search_count'] for row in feasible
                                                if row[f'{strategy}_search_count'] is not None]),
            f'{strategy}_median_runtime_ms': _median([
                row[f'{strategy}_runtime_median_ms'] for row in feasible
                if row[f'{strategy}_runtime_median_ms'] is not None
            ]),
        })
    paired = [row for row in feasible if row['paired_gap_delta_nearest_minus_input'] is not None]
    deltas = [row['paired_gap_delta_nearest_minus_input'] for row in paired]
    summaries.update({
        'both_succeeded_count': len(paired),
        'paired_gap_delta_mean': _mean(deltas),
        'paired_gap_delta_median': _median(deltas),
        'nearest_wins': sum(delta < 0 for delta in deltas),
        'ties': sum(delta == 0 for delta in deltas),
        'input_wins': sum(delta > 0 for delta in deltas),
    })
    return summaries


def _summarize(paired_rows, raw_rows):
    feasible = [row for row in paired_rows if row['oracle_status'] == 'optimal']
    infeasible = [row for row in paired_rows if row['oracle_status'] == 'infeasible']
    both_success = [row for row in feasible if row['paired_outcome'] == 'both_succeeded']
    deltas = [row['paired_gap_delta_nearest_minus_input'] for row in both_success]
    nearest_only = sum(row['paired_outcome'] == 'nearest_only_success' for row in feasible)
    input_only = sum(row['paired_outcome'] == 'input_only_success' for row in feasible)
    both_fail = sum(row['paired_outcome'] == 'both_failed' for row in feasible)
    stratifications = {}
    for field in ('terminal_count', 'layers', 'obstacle_mode',
                  'obstacle_density_band', 'terminal_distribution',
                  'oracle_feasibility'):
        values = sorted({row[field] for row in paired_rows}, key=str)
        stratifications[field] = [
            _group_summary([row for row in paired_rows if row[field] == value],
                           value)
            for value in values
        ]
    runtime_pairs = [row for row in paired_rows
                     if row['input_runtime_median_ms'] is not None and
                     row['nearest_runtime_median_ms'] is not None]
    runtime_deltas = [row['nearest_runtime_median_ms'] - row['input_runtime_median_ms']
                      for row in runtime_pairs]
    raw_measured = [row for row in raw_rows if not row['warmup'] and row['runtime_ms'] is not None]
    runtime_values = [row['runtime_ms'] for row in raw_measured]
    repeat_mads = []
    by_case_strategy = {}
    for row in raw_measured:
        by_case_strategy.setdefault((row['case'], row['terminal_strategy']), []).append(row['runtime_ms'])
    for values in by_case_strategy.values():
        if len(values) > 1:
            median = statistics.median(values)
            repeat_mads.append(statistics.median([abs(value - median) for value in values]))

    return {
        'oracle_feasible_instances': len(feasible),
        'oracle_infeasible_negative_controls': len(infeasible),
        'router_success_rates': {
            strategy: sum(row[f'{strategy}_success'] for row in feasible) / len(feasible)
            if feasible else None for strategy in STRATEGIES
        },
        'router_success_counts': {
            strategy: sum(row[f'{strategy}_success'] for row in feasible)
            for strategy in STRATEGIES
        },
        'execution_error_invocations': {
            strategy: sum(row['router_status'] == 'execution_error' and
                          row['terminal_strategy'] == strategy for row in raw_rows)
            for strategy in STRATEGIES
        },
        'successful_route_gap_denominators': {
            strategy: sum(row[f'{strategy}_success'] and row[f'{strategy}_relative_gap'] is not None
                          for row in feasible) for strategy in STRATEGIES
        },
        'mean_relative_gap_among_successes': {
            strategy: _mean([row[f'{strategy}_relative_gap'] for row in feasible
                            if row[f'{strategy}_success'] and
                            row[f'{strategy}_relative_gap'] is not None])
            for strategy in STRATEGIES
        },
        'median_relative_gap_among_successes': {
            strategy: _median([row[f'{strategy}_relative_gap'] for row in feasible
                               if row[f'{strategy}_success'] and
                               row[f'{strategy}_relative_gap'] is not None])
            for strategy in STRATEGIES
        },
        'paired_gap_delta': {
            'definition': 'nearest relative gap minus input relative gap; both strategies must succeed',
            'n_instances': len(deltas),
            'mean': _mean(deltas),
            'median': _median(deltas),
            'bootstrap_95_percentile_ci_for_mean': _bootstrap_paired(deltas, BOOTSTRAP_SEED),
            'nearest_wins': sum(value < 0 for value in deltas),
            'ties': sum(value == 0 for value in deltas),
            'input_wins': sum(value > 0 for value in deltas),
            'exact_two_sided_sign_test_p': _sign_test_two_sided(
                [value for value in deltas if value != 0]),
            'one_sided_only_success_nearest': nearest_only,
            'one_sided_only_success_input': input_only,
            'both_failed': both_fail,
        },
        'negative_control_outcomes': {
            'count': len(infeasible),
            'input_successes': sum(row['input_success'] for row in infeasible),
            'nearest_successes': sum(row['nearest_success'] for row in infeasible),
            'both_reported_unreachable': sum(
                row['input_termination_reason'] == 'unreachable' and
                row['nearest_termination_reason'] == 'unreachable' for row in infeasible),
        },
        'secondary_successful_route_distributions': {
            strategy: {
                'wirelength_mean': _mean([row[f'{strategy}_wirelength'] for row in feasible
                                          if row[f'{strategy}_success']]),
                'wirelength_median': _median([row[f'{strategy}_wirelength'] for row in feasible
                                              if row[f'{strategy}_success']]),
                'via_count_mean': _mean([row[f'{strategy}_via_count'] for row in feasible
                                         if row[f'{strategy}_success']]),
                'via_count_median': _median([row[f'{strategy}_via_count'] for row in feasible
                                             if row[f'{strategy}_success']]),
                'physical_cost_mean': _mean([row[f'{strategy}_physical_cost'] for row in feasible
                                              if row[f'{strategy}_success']]),
                'physical_cost_median': _median([row[f'{strategy}_physical_cost'] for row in feasible
                                                 if row[f'{strategy}_success']]),
            } for strategy in STRATEGIES
        },
        'search_effort': {
            strategy: {
                'mean_search_count': _mean([row[f'{strategy}_search_count'] for row in feasible
                                            if row[f'{strategy}_search_count'] is not None]),
                'median_search_count': _median([row[f'{strategy}_search_count'] for row in feasible
                                                if row[f'{strategy}_search_count'] is not None]),
                'mean_nodes_expanded': _mean([row[f'{strategy}_nodes_expanded'] for row in feasible
                                              if row[f'{strategy}_nodes_expanded'] is not None]),
                'median_nodes_expanded': _median([row[f'{strategy}_nodes_expanded'] for row in feasible
                                                  if row[f'{strategy}_nodes_expanded'] is not None]),
            } for strategy in STRATEGIES
        },
        'runtime': {
            'measured_invocations': len(raw_measured),
            'runtime_value_unique_count': len(set(runtime_values)),
            'runtime_value_count': len(runtime_values),
            'runtime_min_ms': min(runtime_values) if runtime_values else None,
            'runtime_median_ms': _median(runtime_values),
            'within_instance_repeat_mad_median_ms': _median(repeat_mads),
            'paired_instance_median_delta_nearest_minus_input_ms': {
                'n_instances': len(runtime_deltas),
                'mean': _mean(runtime_deltas),
                'median': _median(runtime_deltas),
                'bootstrap_95_percentile_ci_for_mean': _bootstrap_paired(
                    runtime_deltas, BOOTSTRAP_SEED + 1),
            },
            'interpretation': 'router-reported times are microsecond-scale; treat differences as descriptive unless repeat spread is small relative to the effect',
        },
        'stratified_results': stratifications,
        'instance_unit_note': 'All gap and stratum statistics use one row per layout, never repeated invocations.',
    }


def _write_csv(path, rows):
    fields = list(rows[0]) if rows else []
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path, paired_rows, summary, metadata):
    lines = [
        '# Held-out single-net terminal-ordering evaluation',
        '',
        'This frozen evaluation compares only input-order and nearest-next-terminal.',
        'Both use the same A* binary, complete single-net input, numeric net order,',
        'one pass, and planar/VIA costs 1/6. The development split is not scored.',
        '',
        f"Commit `{metadata['git_commit']}`; machine `{metadata['machine']}`; "
        f"compiler `{(metadata['compiler_build'] or {}).get('compiler_version', 'unknown')}`.",
        f"Seed manifest SHA-256: `{metadata['seed_manifest_sha256']}`.",
        f"Generator config SHA-256: `{metadata['generator_config_sha256']}`.",
        f"Measured repetitions per strategy and layout: {metadata['repetitions']}; "
        f"warmups per strategy and layout: {metadata['warmups']}.",
        '',
        '## Overall results',
        '',
        f"- Oracle-feasible held-out instances: {summary['oracle_feasible_instances']}.",
        f"- Negative controls proven infeasible by the oracle: {summary['oracle_infeasible_negative_controls']}.",
        f"- Success counts: input {summary['router_success_counts']['input']}/"
        f"{summary['oracle_feasible_instances']}; nearest "
        f"{summary['router_success_counts']['nearest']}/{summary['oracle_feasible_instances']}.",
        f"- Mean relative gap among successful routes (denominators are explicit): input "
        f"{summary['mean_relative_gap_among_successes']['input']}; nearest "
        f"{summary['mean_relative_gap_among_successes']['nearest']}.",
        f"- Median relative gap among successful routes: input "
        f"{summary['median_relative_gap_among_successes']['input']}; nearest "
        f"{summary['median_relative_gap_among_successes']['nearest']}.",
        f"- Paired gap differences (both routed): {summary['paired_gap_delta']}.",
        f"- Negative controls: {summary['negative_control_outcomes']}.",
        '',
        'A relative gap is `(router physical cost - oracle optimum) / oracle optimum`.',
        'Zero-optimum cases have a null relative gap; they are retained and reported',
        'separately. Failed routes have no physical cost or gap. A one-sided success',
        'or a double failure is counted separately and not silently omitted.',
        '',
        '## Stratified results',
        '',
        'The following strata use layout-level observations. Means of gaps use',
        'successful routes only, with success counts shown in each row; paired gap',
        'deltas require both strategies to succeed.',
        '',
        '| Stratum | Group | Instances | Feasible/infeasible | Input success | Nearest success | Input mean gap | Nearest mean gap | Paired n | Nearest wins | Ties | Input wins | Mean nodes input/nearest |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for field, groups in summary['stratified_results'].items():
        for group in groups:
            lines.append(
                f"| {field} | {group['stratum']} | {group['instance_count']} | "
                f"{group['oracle_feasible_count']}/{group['oracle_infeasible_count']} | "
                f"{group.get('input_success_count', 0)} | {group.get('nearest_success_count', 0)} | "
                f"{group.get('input_mean_gap')} | {group.get('nearest_mean_gap')} | "
                f"{group['both_succeeded_count']} | {group['nearest_wins']} | "
                f"{group['ties']} | {group['input_wins']} | "
                f"{group.get('input_mean_nodes')} / {group.get('nearest_mean_nodes')} |"
            )
    lines.extend([
        '',
        '## Runtime and effort',
        '',
        f"Runtime summary: {summary['runtime']}. Repetitions are summarized within",
        'each layout; the layout is the unit in paired comparisons. Router-internal',
        'times are short, so runtime claims are descriptive and must be interpreted',
        'against the reported repeat spread, not as evidence of a general speedup.',
        '',
        'Search count and expanded nodes include nearest distance probes as well as',
        'the selected production routes. Physical cost is separately validated.',
        '',
        '## Per-instance paired results',
        '',
        '| Case | k | Layers | Rows×cols | Obstacle mode/density | Distribution | Oracle/status | Optimum | Input success / cost / gap | Nearest success / cost / gap | Paired gap delta | Outcome | Searches input/nearest | Nodes input/nearest | Runtime median ms input/nearest |',
        '|---|---:|---:|---:|---|---|---|---:|---|---|---:|---|---:|---:|---:|',
    ])
    for row in paired_rows:
        def display(value):
            return '—' if value is None else str(value)
        lines.append(
            f"| {row['case']} | {row['terminal_count']} | {row['layers']} | "
            f"{row['rows']}×{row['cols']} | {row['obstacle_mode']}/{row['obstacle_density_band']} | "
            f"{row['terminal_distribution']} | "
            f"{row['oracle_status']} | {display(row['oracle_optimal_cost'])} | "
            f"{row['input_success']} / {display(row['input_physical_cost'])} / "
            f"{display(row['input_relative_gap'])} | "
            f"{row['nearest_success']} / {display(row['nearest_physical_cost'])} / "
            f"{display(row['nearest_relative_gap'])} | "
            f"{display(row['paired_gap_delta_nearest_minus_input'])} | "
            f"{row['paired_outcome']} | "
            f"{display(row['input_search_count'])}/{display(row['nearest_search_count'])} | "
            f"{display(row['input_nodes_expanded'])}/{display(row['nearest_nodes_expanded'])} | "
            f"{display(row['input_runtime_median_ms'])}/{display(row['nearest_runtime_median_ms'])} |"
        )
    lines.extend([
        '',
        '## Interpretation and limitations',
        '',
        'The paired bootstrap interval and exact sign test use layouts as the',
        'statistical unit. They do not turn hand-generated grid layouts into a',
        'representative industrial workload. Report stratified outcomes and failures',
        'alongside aggregates. Runtime is especially susceptible to clock and process',
        'noise at this scale. This experiment evaluates the frozen existing methods;',
        'it does not tune or introduce a strategy.',
        '',
        'Complete raw inputs, candidates and rejection reasons, oracle witnesses,',
        'route JSONs, hashes, raw repetitions, and metadata are stored beside this',
        'report. See `paired_results.csv`, `raw_runs.csv`, `oracle_results.json`, and',
        '`metadata.json`.',
    ])
    with path.open('x') as stream:
        stream.write('\n'.join(lines) + '\n')


def run(experiment_dir, repetitions, warmups, executable, skip_build):
    experiment_dir = experiment_dir.resolve()
    output_dir = experiment_dir / 'evaluation'
    if output_dir.exists():
        raise FileExistsError(f'Evaluation directory exists; refusing overwrite: {output_dir}')
    corpus_manifest_path = experiment_dir / 'corpus_manifest.json'
    corpus_manifest = json.loads(corpus_manifest_path.read_text())
    protocol_path = experiment_dir / 'evaluation_protocol.json'
    protocol = json.loads(protocol_path.read_text())
    generation_metadata_path = experiment_dir / 'generation_metadata.json'
    generation_metadata = json.loads(generation_metadata_path.read_text())
    if generation_metadata['generator_sha256'] != digest(
            ROOT / 'benchmarks/generate_steiner_corpus.py'):
        raise ValueError('Corpus generator differs from generation provenance')
    if generation_metadata['evaluation_protocol_sha256'] != digest(protocol_path):
        raise ValueError('Evaluation protocol hash differs from generation provenance')
    if generation_metadata['candidate_manifest_sha256'] != digest(
            experiment_dir / 'candidate_manifest.jsonl'):
        raise ValueError('Candidate manifest hash differs from generation provenance')
    if corpus_manifest['heldout_feasible_count'] != protocol['heldout_feasible_target']:
        raise ValueError('Held-out feasible count differs from the frozen protocol')
    if corpus_manifest['heldout_infeasible_count'] != protocol['negative_control_target']:
        raise ValueError('Negative-control count differs from the frozen protocol')
    if repetitions != protocol['repetitions'] or warmups != protocol['warmups']:
        raise ValueError('Run repetition counts differ from the frozen protocol')
    if protocol['search_algorithm'] != ALGORITHM or \
            protocol['net_order'] != 'numeric' or \
            protocol['routing_passes'] != MAX_ITERATIONS or \
            protocol['methods'] != list(STRATEGIES):
        raise ValueError('Execution settings differ from the frozen evaluation protocol')
    if corpus_manifest['heldout_feasible_count'] < 48:
        raise ValueError('Held-out corpus must contain at least 48 oracle-feasible cases')
    case_specs = (corpus_manifest['cases']['heldout_feasible'] +
                  corpus_manifest['cases']['heldout_infeasible'])
    if not case_specs:
        raise ValueError('No held-out cases in corpus manifest')
    executable = executable.resolve()
    if not skip_build:
        subprocess.run(['make', 'router'], cwd=ROOT, check=True)
    if not executable.is_file():
        raise FileNotFoundError(f'Router executable not found: {executable}')
    build_path = ROOT / 'build/router-build.json'
    build = json.loads(build_path.read_text()) if executable == ROOT / 'router' and build_path.exists() else None
    if executable == ROOT / 'router':
        expected_sources = {str(path.relative_to(ROOT)): digest(path)
                            for path in sorted((ROOT / 'src').glob('*'))}
        if build is None or build['executable_sha256'] != digest(executable) or \
                build['source_sha256'] != expected_sources:
            raise ValueError('Executable/build record is stale; rebuild before evaluation')

    output_dir.mkdir(parents=True)
    raw_dir = output_dir / 'raw'
    raw_dir.mkdir()
    source_files = sorted((ROOT / 'src').glob('*.hpp')) + [ROOT / 'src/main.cpp']
    tracked = source_files + [
        ROOT / 'Makefile', ROOT / 'benchmarks/record_build.py',
        ROOT / 'benchmarks/steiner_oracle.py',
        ROOT / 'benchmarks/generate_steiner_corpus.py',
        ROOT / 'benchmarks/run_steiner_heldout.py',
        ROOT / 'benchmarks/validate_output.py',
        ROOT / 'tests/test_router.cpp', ROOT / 'tests/test_steiner_oracle.py',
        ROOT / 'tests/test_steiner_corpus.py',
    ]
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in tracked}
    config_path = experiment_dir / 'generator_config.json'
    seed_path = experiment_dir / 'seed_manifest.json'
    candidate_manifest_path = experiment_dir / 'candidate_manifest.jsonl'
    corpus_inputs = []
    cases = []
    oracle_records = []
    for spec in case_specs:
        path = experiment_dir / spec['path']
        info = _layout_metadata(path)
        exact = solve(path)
        intended = 'optimal' if spec in corpus_manifest['cases']['heldout_feasible'] else 'infeasible'
        if exact['status'] != intended:
            raise ValueError(f"Corpus/oracle mismatch for {spec['path']}: {exact['status']} != {intended}")
        case = dict(spec)
        case.update(info)
        case['oracle_status'] = exact['status']
        case['oracle_optimal_cost'] = exact['optimal_cost']
        case['input_sha256'] = digest(path)
        case['input_path'] = str(path.relative_to(experiment_dir))
        cases.append(case)
        corpus_inputs.append((path, case))
        oracle_records.append({
            'case': path.stem,
            'input': case['input_path'],
            'input_sha256': case['input_sha256'],
            'oracle': exact,
        })

    metadata = {
        'schema_version': 1,
        'experiment': 'heldout_single_net_terminal_ordering',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'working_tree_dirty': bool(subprocess.check_output(
            ['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        'platform': platform.platform(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python': sys.version,
        'python_perf_counter': {
            'implementation': time.get_clock_info('perf_counter').implementation,
            'monotonic': time.get_clock_info('perf_counter').monotonic,
            'adjustable': time.get_clock_info('perf_counter').adjustable,
            'resolution_seconds': time.get_clock_info('perf_counter').resolution,
        },
        'compiler_build': build,
        'executable_sha256': digest(executable),
        'source_sha256': source_hashes,
        'generator_sha256': digest(ROOT / 'benchmarks/generate_steiner_corpus.py'),
        'runner_sha256': digest(ROOT / 'benchmarks/run_steiner_heldout.py'),
        'generator_config_sha256': digest(config_path),
        'seed_manifest_sha256': digest(seed_path),
        'candidate_manifest_sha256': digest(candidate_manifest_path),
        'corpus_manifest_sha256': digest(corpus_manifest_path),
        'evaluation_protocol_sha256': digest(protocol_path),
        'generation_metadata_sha256': digest(generation_metadata_path),
        'input_sha256': {case['input_path']: case['input_sha256'] for case in cases},
        'algorithm': ALGORITHM,
        'net_order': 'numeric',
        'terminal_strategies': list(STRATEGIES),
        'max_iterations': MAX_ITERATIONS,
        'physical_cost_model': {'planar': 1, 'via': 6},
        'repetitions': repetitions,
        'warmups': warmups,
        'execution_order': 'alternating input/nearest order by measured repetition; warmup input then nearest',
        'timing_scope': 'router-reported runtime_ms; process wall time also retained',
        'statistical_unit': 'one held-out input layout',
        'bootstrap_seed': BOOTSTRAP_SEED,
        'bootstrap_samples': BOOTSTRAP_SAMPLES,
        'corpus_manifest': str(corpus_manifest_path.relative_to(experiment_dir)),
        'case_count': len(cases),
        'cases': [],
    }
    raw_rows = []
    paired_rows = []
    signatures = {}
    for index, (layout, case) in enumerate(corpus_inputs):
        exact = solve(layout)
        strategy_runs = {strategy: [] for strategy in STRATEGIES}
        output_files = {}
        for repetition in range(-warmups, repetitions):
            warmup = repetition < 0
            label = f'w{repetition + warmups:02d}' if warmup else f'r{repetition:03d}'
            if warmup:
                order = STRATEGIES
            else:
                order = STRATEGIES if repetition % 2 == 0 else tuple(reversed(STRATEGIES))
            for strategy in order:
                output_path = raw_dir / f'{layout.stem}_{strategy}_{label}.json'
                command = [
                    str(executable), '--input', str(layout), '--algorithm', ALGORITHM,
                    '--output', str(output_path), '--max-iterations', str(MAX_ITERATIONS),
                    '--net-order', 'numeric', '--terminal-order', strategy,
                ]
                row = {
                    'case': layout.stem, 'input': case['input_path'],
                    'input_sha256': case['input_sha256'], 'seed': case['seed'],
                    'terminal_count': case['terminal_count'], 'layers': case['layers'],
                    'rows': case['dimensions'][1], 'cols': case['dimensions'][2],
                    'obstacle_density_band': case['obstacle_density_band'],
                    'obstacle_mode': case['obstacle_mode'],
                    'terminal_distribution': case['terminal_distribution'],
                    'oracle_status': exact['status'], 'oracle_optimal_cost': exact['optimal_cost'],
                    'terminal_strategy': strategy, 'algorithm': ALGORITHM,
                    'max_iterations': MAX_ITERATIONS, 'repetition': label, 'warmup': warmup,
                    'router_status': 'execution_error', 'success': None,
                    'physical_cost': None, 'absolute_gap': None, 'relative_gap': None,
                    'wirelength': None, 'via_count': None, 'tree_edge_count': None,
                    'search_count': None, 'nodes_expanded': None, 'search_objective_cost': None,
                    'runtime_ms': None, 'process_wall_ms': None,
                    'termination_reason': None, 'output_json': str(output_path.relative_to(output_dir)),
                    'output_sha256': None, 'error': '',
                }
                started = time.perf_counter()
                try:
                    process = subprocess.run(command, cwd=ROOT, capture_output=True,
                                             text=True, timeout=30)
                    row['process_wall_ms'] = (time.perf_counter() - started) * 1000
                    if process.returncode not in (0, 2):
                        raise ValueError(process.stderr.strip() or
                                         f'Router exited {process.returncode}')
                    data = json.loads(output_path.read_text())
                    successful = validate(layout, data)
                    if successful != (process.returncode == 0):
                        raise ValueError('Router exit code contradicts independent validation')
                    if data.get('terminal_order') != strategy or data.get('net_order') != 'numeric':
                        raise ValueError('Output strategy differs from paired command')
                    if data.get('algorithm') != ALGORITHM:
                        raise ValueError('Output search algorithm differs from paired command')
                    stable = json.loads(json.dumps(data))
                    del stable['metrics']['runtime_ms']
                    signature = json.dumps(stable, sort_keys=True)
                    fingerprint = (layout.stem, strategy)
                    if fingerprint in signatures and signatures[fingerprint] != signature:
                        raise ValueError('Route geometry or non-timing metrics changed between repetitions')
                    signatures[fingerprint] = signature
                    if exact['status'] == 'infeasible' and successful:
                        raise ValueError('Router succeeded on oracle-proven-infeasible input')
                    row.update(
                        router_status='success' if successful else 'routing_failure',
                        success=successful,
                        termination_reason=data['termination_reason'],
                        search_count=data['metrics']['search_count'],
                        nodes_expanded=data['metrics']['nodes_expanded'],
                        search_objective_cost=data['metrics']['search_cost'],
                        runtime_ms=data['metrics']['runtime_ms'],
                        output_sha256=digest(output_path),
                    )
                    if successful:
                        physical = data['metrics']['weighted_cost']
                        gap = physical - exact['optimal_cost']
                        if gap < 0:
                            raise ValueError('Router cost is below exact oracle optimum')
                        row.update(
                            physical_cost=physical,
                            absolute_gap=gap,
                            relative_gap=None if exact['optimal_cost'] == 0
                            else gap / exact['optimal_cost'],
                            wirelength=data['metrics']['wirelength'],
                            via_count=data['metrics']['via_count'],
                            tree_edge_count=data['metrics']['graph_steps'],
                        )
                    else:
                        row.update(
                            wirelength=None,
                            via_count=None,
                            tree_edge_count=None,
                        )
                    output_files[f'{strategy}_{label}'] = row['output_json']
                except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
                    row['error'] = str(error)
                    row['router_status'] = 'execution_error'
                raw_rows.append(row)
                strategy_runs[strategy].append(row)

        measured = {
            strategy: [row for row in strategy_runs[strategy] if not row['warmup']]
            for strategy in STRATEGIES
        }
        outcome_row = {}
        for strategy in STRATEGIES:
            rows = measured[strategy]
            verified = [row for row in rows if row['router_status'] in ('success', 'routing_failure')]
            successful = [row for row in verified if row['success']]
            consistent_success = len(successful) == len(rows) and len(rows) == repetitions
            outcome_row[f'{strategy}_success'] = bool(consistent_success)
            outcome_row[f'{strategy}_success_rate'] = len(successful) / repetitions
            outcome_row[f'{strategy}_physical_cost'] = (
                successful[0]['physical_cost'] if consistent_success else None)
            outcome_row[f'{strategy}_relative_gap'] = (
                successful[0]['relative_gap'] if consistent_success else None)
            outcome_row[f'{strategy}_wirelength'] = (
                successful[0]['wirelength'] if consistent_success else None)
            outcome_row[f'{strategy}_via_count'] = (
                successful[0]['via_count'] if consistent_success else None)
            outcome_row[f'{strategy}_tree_edge_count'] = (
                successful[0]['tree_edge_count'] if consistent_success else None)
            outcome_row[f'{strategy}_search_count'] = (
                verified[0]['search_count'] if verified else None)
            outcome_row[f'{strategy}_nodes_expanded'] = (
                verified[0]['nodes_expanded'] if verified else None)
            runtime_values = [row['runtime_ms'] for row in verified if row['runtime_ms'] is not None]
            outcome_row[f'{strategy}_runtime_median_ms'] = _median(runtime_values)
            outcome_row[f'{strategy}_runtime_mad_ms'] = (
                statistics.median([abs(value - statistics.median(runtime_values))
                                   for value in runtime_values]) if runtime_values else None)
            outcome_row[f'{strategy}_termination_reason'] = (
                successful[0]['termination_reason'] if consistent_success else
                verified[0]['termination_reason'] if verified else 'execution_error')
            outcome_row[f'{strategy}_execution_error_count'] = sum(
                row['router_status'] == 'execution_error' for row in rows)
        both_success = outcome_row['input_success'] and outcome_row['nearest_success']
        outcome_row['paired_gap_delta_nearest_minus_input'] = (
            outcome_row['nearest_relative_gap'] - outcome_row['input_relative_gap']
            if both_success and outcome_row['input_relative_gap'] is not None and
            outcome_row['nearest_relative_gap'] is not None else None)
        if exact['status'] == 'infeasible':
            outcome = 'negative_control'
        elif both_success:
            outcome = 'both_succeeded'
        elif outcome_row['nearest_success']:
            outcome = 'nearest_only_success'
        elif outcome_row['input_success']:
            outcome = 'input_only_success'
        else:
            outcome = 'both_failed'
        outcome_row['paired_outcome'] = outcome
        pair = dict(case=layout.stem, input_path=case['input_path'],
                    input_sha256=case['input_sha256'], seed=case['seed'],
                    terminal_count=case['terminal_count'], layers=case['layers'],
                    rows=case['dimensions'][1], cols=case['dimensions'][2],
                    obstacle_mode=case['obstacle_mode'],
                    terminal_distribution=case['terminal_distribution'],
                    obstacle_count=case['obstacle_count'],
                    obstacle_density=case['obstacle_density'],
                    obstacle_density_band=case['obstacle_density_band'],
                    oracle_status=exact['status'],
                    oracle_feasibility='oracle_feasible' if exact['status'] == 'optimal'
                    else 'oracle_infeasible',
                    oracle_optimal_cost=exact['optimal_cost'],
                    **outcome_row)
        paired_rows.append(pair)
        metadata['cases'].append({
            'input': case['input_path'], 'input_sha256': case['input_sha256'],
            'oracle_status': exact['status'], 'oracle_optimal_cost': exact['optimal_cost'],
            'raw_outputs': output_files,
        })
        if index % 10 == 9:
            print(f'Completed {index + 1}/{len(corpus_inputs)} held-out layouts')

    _write_csv(output_dir / 'raw_runs.csv', raw_rows)
    _write_csv(output_dir / 'paired_results.csv', paired_rows)
    with (output_dir / 'oracle_results.json').open('x') as stream:
        json.dump(oracle_records, stream, indent=2)
        stream.write('\n')
    summary = _summarize(paired_rows, raw_rows)
    with (output_dir / 'summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write('\n')
    metadata['summary_sha256'] = digest(output_dir / 'summary.json')
    with (output_dir / 'metadata.json').open('x') as stream:
        json.dump(metadata, stream, indent=2, allow_nan=False)
        stream.write('\n')
    _write_report(output_dir / 'RESULTS.md', paired_rows, summary, metadata)

    if source_hashes != {str(path.relative_to(ROOT)): digest(path) for path in tracked}:
        raise ValueError('Source changed during held-out experiment')
    if any(digest(path) != case['input_sha256'] for path, case in corpus_inputs):
        raise ValueError('Held-out input changed during experiment')
    if digest(executable) != metadata['executable_sha256']:
        raise ValueError('Router executable changed during held-out experiment')
    print(f"Recorded {len(raw_rows)} runs over {len(paired_rows)} held-out cases in {output_dir}")
    print(f"Results: {output_dir / 'RESULTS.md'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment-dir', required=True, type=Path)
    parser.add_argument('--repetitions', type=int, default=11)
    parser.add_argument('--warmups', type=int, default=1)
    parser.add_argument('--executable', type=Path, default=ROOT / 'router')
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_args()
    if args.repetitions < 1 or args.warmups < 0:
        parser.error('repetitions must be positive and warmups nonnegative')
    run(args.experiment_dir, args.repetitions, args.warmups,
        args.executable, args.skip_build)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f'Held-out experiment error: {error}', file=sys.stderr)
        sys.exit(1)
