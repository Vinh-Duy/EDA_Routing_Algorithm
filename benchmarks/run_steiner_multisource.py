"""Compare repeated versus single multi-source nearest-terminal selection."""
import argparse
import csv
import hashlib
import json
import platform
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

from steiner_oracle import solve
from validate_output import read_layout_with_extras, validate

ROOT = Path(__file__).resolve().parents[1]
SOURCE_EXPERIMENT = ROOT / 'benchmarks/steiner/experiment_20261101_heldout_final'
DEFAULT_EXPERIMENT = ROOT / 'benchmarks/steiner/experiment_20261102_multisource'
METHODS = ('repeated', 'multisource')
ALGORITHM = 'astar'
NET_ORDER = 'numeric'
PASSES = 1


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def median(values):
    return statistics.median(values) if values else None


def mad(values):
    if not values:
        return None
    center = median(values)
    return median([abs(value - center) for value in values])


def semantic_output(data):
    metrics = data['metrics']
    return {
        'algorithm': data['algorithm'],
        'success': data['success'],
        'termination_reason': data['termination_reason'],
        'net_order': data['net_order'],
        'terminal_order': data['terminal_order'],
        'dimensions': data['dimensions'],
        'cost_model': data['cost_model'],
        'obstacles': data['obstacles'],
        'conflicts': data['conflicts'],
        'physical_metrics': {
            key: metrics[key] for key in (
                'total_nets', 'routed_nets', 'success_rate', 'unrouted_nets',
                'invalid_nets', 'unresolved_conflicts', 'unconnected_terminals',
                'wirelength', 'via_count', 'branch_count', 'graph_steps',
                'weighted_cost', 'routing_passes', 'reroute_iterations')
        },
        'nets': [{
            key: net[key] for key in (
                'name', 'source', 'target', 'terminals', 'connected_terminals',
                'unconnected_terminals', 'branch_count', 'attached_terminals',
                'valid', 'local_valid', 'path', 'tree_edges')
            if key in net
        } for net in data['nets']],
    }


def stable_run(data):
    result = semantic_output(data)
    metrics = data['metrics']
    result['search'] = {
        'search_count': metrics['search_count'],
        'nodes_expanded': metrics['nodes_expanded'],
        'selection_dijkstra_runs': metrics['selection_dijkstra_runs'],
        'selection_settled_vertices': metrics['selection_settled_vertices'],
        'selection_edges_examined': metrics['selection_edges_examined'],
        'selection_heap_pushes': metrics['selection_heap_pushes'],
        'selection_heap_pops': metrics['selection_heap_pops'],
        'route_searches': metrics['route_searches'],
        'route_nodes_expanded': metrics['route_nodes_expanded'],
    }
    return result


def route_computation(data):
    metrics = data['metrics']
    return {
        'semantic': semantic_output(data),
        'route_searches': metrics['route_searches'],
        'route_nodes_expanded': metrics['route_nodes_expanded'],
    }


def _write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def _write_csv(path, rows):
    if not rows:
        raise ValueError(f'No rows to write: {path}')
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _run_router(executable, layout, output, selector):
    command = [
        str(executable), '--input', str(layout), '--algorithm', ALGORITHM,
        '--output', str(output), '--max-iterations', str(PASSES),
        '--net-order', NET_ORDER, '--terminal-order', 'nearest',
        '--nearest-selector', selector,
    ]
    started = time.perf_counter()
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    wall_ms = (time.perf_counter() - started) * 1000
    if process.returncode not in (0, 2):
        raise RuntimeError(f'{selector} router failed for {layout.name}: {process.stderr.strip()}')
    try:
        data = json.loads(output.read_text())
    except (OSError, ValueError) as error:
        raise RuntimeError(f'Missing/invalid router output for {layout.name}/{selector}: {error}') from error
    if data.get('nearest_selector') != selector:
        raise ValueError(f'Output reports wrong selector for {layout.name}/{selector}')
    successful = validate(layout, data)
    if successful != (process.returncode == 0):
        raise ValueError(f'Exit status contradicts independent validation: {layout.name}/{selector}')
    return data, wall_ms


def _copy_inputs(experiment, source_experiment, corpus_manifest):
    inputs = experiment / 'inputs'
    for split in ('feasible', 'infeasible'):
        destination = inputs / 'heldout' / split
        destination.mkdir(parents=True)
    fixed_dir = inputs / 'fixed'
    fixed_dir.mkdir(parents=True)
    cases = []
    for split, key in (('feasible', 'heldout_feasible'),
                       ('infeasible', 'heldout_infeasible')):
        for item in corpus_manifest['cases'][key]:
            source = source_experiment / item['path']
            destination = inputs / 'heldout' / split / source.name
            shutil.copyfile(source, destination)
            cases.append({
                'case': source.stem,
                'split': split,
                'relative_path': str(destination.relative_to(experiment)),
                'source_path': str(source.relative_to(source_experiment)),
                'input_sha256': digest(destination),
                'seed': item['seed'],
                'terminal_count': item['terminal_count'],
                'layers': item['layers'],
                'obstacle_mode': item['obstacle_mode'],
                'terminal_distribution': item['terminal_distribution'],
            })
    fixed = []
    for source in sorted((ROOT / 'benchmarks/steiner/layouts').glob('*.txt')):
        destination = fixed_dir / source.name
        shutil.copyfile(source, destination)
        fixed.append({
            'case': source.stem,
            'relative_path': str(destination.relative_to(experiment)),
            'input_sha256': digest(destination),
        })
    if len(cases) != 72 or len(fixed) != 6:
        raise ValueError(f'Expected 72 held-out cases and 6 fixed fixtures; got {len(cases)}, {len(fixed)}')
    return cases, fixed


def _compare_fixed_fixtures(experiment, executable, fixed_cases):
    results = []
    output_dir = experiment / 'fixed_outputs'
    output_dir.mkdir()
    for item in fixed_cases:
        layout = experiment / item['relative_path']
        outputs = {}
        for method in METHODS:
            output_path = output_dir / f"{item['case']}_{method}.json"
            data, _ = _run_router(executable, layout, output_path, method)
            outputs[method] = data
        left, right = outputs['repeated'], outputs['multisource']
        if semantic_output(left) != semantic_output(right):
            raise AssertionError(f'Fixed-fixture route semantics differ: {item["case"]}')
        results.append({
            **item,
            'equivalent': True,
            'success': left['success'],
            'termination_reason': left['termination_reason'],
            'physical_cost': left['metrics']['weighted_cost'],
            'attached_terminals': [net['attached_terminals'] for net in left['nets']],
            'tree_edges': [net.get('tree_edges', []) for net in left['nets']],
            'semantic_sha256': hashlib.sha256(
                json.dumps(semantic_output(left), sort_keys=True).encode()).hexdigest(),
            'repeated_output_sha256': digest(output_dir / f"{item['case']}_repeated.json"),
            'multisource_output_sha256': digest(output_dir / f"{item['case']}_multisource.json"),
        })
    return results


def _selection_fields(data):
    metrics = data['metrics']
    return {
        'selection_dijkstra_runs': metrics['selection_dijkstra_runs'],
        'selection_settled_vertices': metrics['selection_settled_vertices'],
        'selection_edges_examined': metrics['selection_edges_examined'],
        'selection_heap_pushes': metrics['selection_heap_pushes'],
        'selection_heap_pops': metrics['selection_heap_pops'],
        'route_searches': metrics['route_searches'],
        'route_nodes_expanded': metrics['route_nodes_expanded'],
        'selection_runtime_ms': metrics['selection_runtime_ms'],
        'route_runtime_ms': metrics['route_runtime_ms'],
        'physical_cost': metrics['weighted_cost'],
        'wirelength': metrics['wirelength'],
        'via_count': metrics['via_count'],
    }


def _summarize(paired, raw):
    feasible = [row for row in paired if row['oracle_status'] == 'optimal']
    fields = (
        'selection_dijkstra_runs', 'selection_settled_vertices',
        'selection_edges_examined', 'selection_heap_pushes',
        'selection_heap_pops', 'route_searches', 'route_nodes_expanded',
    )

    def method_summary(rows):
        result = {}
        for method in METHODS:
            result[method] = {}
            for field in fields:
                values = [row[f'{method}_{field}'] for row in rows]
                result[method][field] = {
                    'total': sum(values),
                    'mean_per_layout': statistics.mean(values) if values else None,
                    'median_per_layout': median(values),
                }
            for field in ('runtime','selection_runtime','route_runtime','wall'):
                values = [row[f'{method}_{field}_median_ms'] for row in rows]
                result[method][f'{field}_median_ms'] = median(values)
                result[method][f'{field}_mad_median_ms'] = median(
                    [row[f'{method}_{field}_mad_ms'] for row in rows])
        return result

    all_method_metrics = method_summary(paired)
    feasible_method_metrics = method_summary(feasible)
    deltas = [row['multisource_minus_repeated_runtime_ms'] for row in paired]
    selection_runs_old = all_method_metrics['repeated']['selection_dijkstra_runs']['total']
    selection_runs_new = all_method_metrics['multisource']['selection_dijkstra_runs']['total']
    settled_old = all_method_metrics['repeated']['selection_settled_vertices']['total']
    settled_new = all_method_metrics['multisource']['selection_settled_vertices']['total']
    return {
        'heldout_instances': len(paired),
        'oracle_feasible_instances': len(feasible),
        'oracle_infeasible_instances': len(paired) - len(feasible),
        'equivalent_route_count': sum(row['equivalent'] for row in paired),
        'method_metrics': all_method_metrics,
        'feasible_method_metrics': feasible_method_metrics,
        'selection_dijkstra_run_reduction': {
            'old_total': selection_runs_old,
            'new_total': selection_runs_new,
            'absolute': selection_runs_old - selection_runs_new,
            'fraction': (selection_runs_old - selection_runs_new) / selection_runs_old
            if selection_runs_old else None,
        },
        'selection_settled_vertex_reduction': {
            'old_total': settled_old,
            'new_total': settled_new,
            'absolute': settled_old - settled_new,
            'fraction': (settled_old - settled_new) / settled_old if settled_old else None,
        },
        'paired_router_runtime_delta_ms_multisource_minus_repeated': {
            'mean_per_layout_median': statistics.mean(deltas) if deltas else None,
            'median_per_layout_median': median(deltas),
            'multisource_faster_layouts': sum(delta < 0 for delta in deltas),
            'ties': sum(delta == 0 for delta in deltas),
            'multisource_slower_layouts': sum(delta > 0 for delta in deltas),
            'all_layout_deltas_ms': deltas,
        },
        'timing_observations': len([row for row in raw if not row['warmup']]),
        'execution_errors': sum(row['router_status'] == 'execution_error' for row in raw),
        'raw_runs_include_warmups': True,
        'statistical_unit': 'layout; repetitions summarized within layout',
    }


def _write_report(path, paired, summary, fixed_results, metadata):
    delta = summary['paired_router_runtime_delta_ms_multisource_minus_repeated']
    run_reduction = summary['selection_dijkstra_run_reduction']
    settled_reduction = summary['selection_settled_vertex_reduction']
    lines = [
        '# Repeated versus multi-source nearest-terminal selection',
        '',
        'This experiment compares the previous repeated-per-candidate Dijkstra selector',
        'with a single multi-source Dijkstra selector. It does not compare the input-order',
        'strategy and does not change A* routing, physical costs, or the default terminal order.',
        '',
        '## Protocol',
        '',
        f"- Held-out cases: {summary['oracle_feasible_instances']} oracle-feasible and "
        f"{summary['oracle_infeasible_instances']} oracle-infeasible controls.",
        f"- Fixed fixtures: {len(fixed_results)}; all route semantics equivalent: "
        f"{all(item['equivalent'] for item in fixed_results)}.",
        f"- Measurements: {metadata['repetitions']} repetitions and {metadata['warmups']} warm-up "
        'per selector and layout; serial execution; paired order alternated by repetition.',
        '- Both methods use the same stored layouts, A* binary, numeric net order, and one pass.',
        '- Runtime comparisons use per-layout medians; repetitions are not independent samples.',
        '',
        '## Correctness',
        '',
        f"- Per-instance held-out route semantic equivalence: "
        f"{summary['equivalent_route_count']}/{summary['heldout_instances']}.",
        '- Compared selected-terminal sequence, physical tree edges, physical cost, wirelength,',
        '  VIA count, routing success/failure, and termination reason.',
        '- The repeated selector was also checked against the archived previous-study route JSON',
        '  for every held-out case (semantic fields and historical search counters).',
        '- Independent route validation ran on every output JSON.',
        '',
        '## Selection work',
        '',
        f"- Dijkstra selection runs: {run_reduction['old_total']} repeated vs. "
        f"{run_reduction['new_total']} multi-source "
        f"({100*run_reduction['fraction']:.2f}% fewer).",
        f"- Settled vertices: {settled_reduction['old_total']} repeated vs. "
        f"{settled_reduction['new_total']} multi-source "
        f"({100*settled_reduction['fraction']:.2f}% fewer).",
        f"- Settled-vertex reduction: {settled_reduction['absolute']}; expanded legal edges,",
        '  heap pushes/pops, A* searches, and A* expanded nodes are included in per-instance CSV.',
        '',
        '## Runtime',
        '',
        f"- Median of per-layout median router time: repeated "
        f"{summary['method_metrics']['repeated']['runtime_median_ms']:.6f} ms; multi-source "
        f"{summary['method_metrics']['multisource']['runtime_median_ms']:.6f} ms.",
        f"- Median paired runtime delta (multi-source minus repeated): "
        f"{delta['median_per_layout_median']:.6f} ms; mean delta "
        f"{delta['mean_per_layout_median']:.6f} ms.",
        f"- Faster / tied / slower layouts: {delta['multisource_faster_layouts']} / "
        f"{delta['ties']} / {delta['multisource_slower_layouts']}.",
        f"- Median within-layout router-time MAD: repeated "
        f"{summary['method_metrics']['repeated']['runtime_mad_median_ms']:.6f} ms; multi-source "
        f"{summary['method_metrics']['multisource']['runtime_mad_median_ms']:.6f} ms.",
        f"- Median selection time: repeated "
        f"{summary['method_metrics']['repeated']['selection_runtime_median_ms']:.6f} ms; multi-source "
        f"{summary['method_metrics']['multisource']['selection_runtime_median_ms']:.6f} ms.",
        f"- Median final routing time: repeated "
        f"{summary['method_metrics']['repeated']['route_runtime_median_ms']:.6f} ms; multi-source "
        f"{summary['method_metrics']['multisource']['route_runtime_median_ms']:.6f} ms.",
        '- Timing is reported rather than inferred from node counts; inspect per-instance and raw',
        '  measurements, including cases where multi-source is slower.',
        '',
        '## Per-instance paired comparison',
        '',
        '| Case | Feasibility | Equivalent | Selection runs old/new | Settled vertices old/new | A* nodes old/new | Runtime median old/new (ms) | Delta new-old (ms) | Faster? |',
        '|---|---|---:|---:|---:|---:|---:|---:|---|',
    ]
    for row in paired:
        lines.append(
            f"| {row['case']} | {row['oracle_status']} | {row['equivalent']} | "
            f"{row['repeated_selection_dijkstra_runs']}/{row['multisource_selection_dijkstra_runs']} | "
            f"{row['repeated_selection_settled_vertices']}/{row['multisource_selection_settled_vertices']} | "
            f"{row['repeated_route_nodes_expanded']}/{row['multisource_route_nodes_expanded']} | "
            f"{row['repeated_runtime_median_ms']:.6f}/{row['multisource_runtime_median_ms']:.6f} | "
            f"{row['multisource_minus_repeated_runtime_ms']:.6f} | "
            f"{'yes' if row['multisource_minus_repeated_runtime_ms'] < 0 else 'no'} |"
        )
    lines += [
        '',
        '## Reproducibility and files',
        '',
        f"- Experiment root: `{metadata['experiment_dir']}`.",
        '- Exact input copies, input SHA-256 values, source/binary hashes, and machine/compiler',
        '  details are recorded in `metadata.json`.',
        '- Raw output JSON and repeated measurements are under `evaluation/raw/` and in',
        '  `raw_runs.csv`; per-layout results are in `paired_results.csv`.',
        '- Fixed fixture outputs and the equivalence audit are retained beside the evaluation.',
        '- Historical experiments are read-only inputs to this run and were not overwritten.',
    ]
    with path.open('x') as stream:
        stream.write('\n'.join(lines) + '\n')


def run(experiment_dir, source_experiment, repetitions, warmups, limit_cases=None):
    experiment_dir = experiment_dir.resolve()
    source_experiment = source_experiment.resolve()
    if experiment_dir.exists():
        raise FileExistsError(f'Refusing to overwrite experiment directory: {experiment_dir}')
    source_evaluation = source_experiment / 'evaluation'
    source_metadata = json.loads((source_evaluation / 'metadata.json').read_text())
    corpus_manifest_path = source_experiment / 'corpus_manifest.json'
    corpus_manifest = json.loads(corpus_manifest_path.read_text())
    expected_names = {Path(item['path']).stem for key in
                      ('heldout_feasible', 'heldout_infeasible')
                      for item in corpus_manifest['cases'][key]}
    if len(expected_names) != 72:
        raise ValueError('Source held-out corpus must contain exactly 72 unique layouts')
    if repetitions < 1 or warmups < 0:
        raise ValueError('Repetitions must be positive and warmups nonnegative')

    subprocess.run(['make', 'router'], cwd=ROOT, check=True)
    executable = ROOT / 'router'
    build = json.loads((ROOT / 'build/router-build.json').read_text())
    if digest(executable) != build['executable_sha256']:
        raise ValueError('Built router does not match the recorded build')

    experiment_dir.mkdir(parents=True)
    evaluation = experiment_dir / 'evaluation'
    evaluation.mkdir()
    raw_dir = evaluation / 'raw'
    raw_dir.mkdir()
    (experiment_dir / 'inputs').mkdir()
    cases, fixed_cases = _copy_inputs(experiment_dir, source_experiment, corpus_manifest)
    if limit_cases is not None:
        if limit_cases < 1:
            raise ValueError('Case limit must be positive')
        cases = cases[:limit_cases]
    _write_json(experiment_dir / 'corpus_manifest.json', {
        'source_experiment': str(source_experiment),
        'source_corpus_manifest_sha256': digest(corpus_manifest_path),
        'heldout_case_count': len(cases),
        'fixed_fixture_count': len(fixed_cases),
        'cases': cases,
        'fixed_fixtures': fixed_cases,
    })
    protocol = {
        'protocol_version': 1,
        'methods': list(METHODS),
        'algorithm': ALGORITHM,
        'net_order': NET_ORDER,
        'routing_passes': PASSES,
        'repetitions': repetitions,
        'warmups': warmups,
        'case_limit_for_runner_validation': limit_cases,
        'execution_order': 'warm-up repeated then multisource; measured repetitions alternate starting selector',
        'statistical_unit': 'one held-out input layout; summarize repetitions per layout',
        'primary_comparison': 'nearest selector repeated probes versus one tree-rooted multisource Dijkstra',
        'source_corpus_manifest_sha256': digest(corpus_manifest_path),
        'source_input_hashes': source_metadata['input_sha256'],
    }
    _write_json(experiment_dir / 'evaluation_protocol.json', protocol)

    tracked = sorted((ROOT / 'src').glob('*.hpp')) + [
        ROOT / 'src/main.cpp', ROOT / 'Makefile', ROOT / 'benchmarks/record_build.py',
        ROOT / 'benchmarks/steiner_oracle.py', ROOT / 'benchmarks/validate_output.py',
        ROOT / 'benchmarks/run_steiner_multisource.py', ROOT / 'tests/test_router.cpp',
        ROOT / 'tests/test_cli.py',
    ]
    source_hashes = {str(path.relative_to(ROOT)): digest(path) for path in tracked}
    metadata = {
        'schema_version': 1,
        'experiment': 'nearest_terminal_repeated_vs_multisource',
        'experiment_dir': str(experiment_dir.relative_to(ROOT)),
        'created_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'git_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'platform': platform.platform(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python': sys.version,
        'compiler_build': build,
        'executable_sha256': digest(executable),
        'source_sha256': source_hashes,
        'runner_sha256': digest(ROOT / 'benchmarks/run_steiner_multisource.py'),
        'source_experiment': str(source_experiment.relative_to(ROOT)),
        'source_metadata_sha256': digest(source_evaluation / 'metadata.json'),
        'source_corpus_manifest_sha256': digest(corpus_manifest_path),
        'source_oracle_summary': {
            'feasible_instances': source_metadata['case_count'] - 12,
            'infeasible_controls': 12,
        },
        'repetitions': repetitions,
        'warmups': warmups,
        'algorithm': ALGORITHM,
        'net_order': NET_ORDER,
        'routing_passes': PASSES,
        'selection_semantics': 'physical planar/via cost plus existing occupancy/history entry penalties',
        'selection_termination': 'settle all candidates at best distance; stop once min unsettled distance is greater',
        'time_measurement': 'router runtime_ms and subprocess wall time; per-layout medians and MADs',
        'inputs': {},
        'fixed_fixtures': {},
    }
    for item in cases:
        path = experiment_dir / item['relative_path']
        metadata['inputs'][item['relative_path']] = digest(path)
    for item in fixed_cases:
        path = experiment_dir / item['relative_path']
        metadata['fixed_fixtures'][item['relative_path']] = digest(path)

    fixed_results = _compare_fixed_fixtures(experiment_dir, executable, fixed_cases)
    _write_json(experiment_dir / 'behavioral_equivalence.json', {
        'fixed_fixture_results': fixed_results,
        'heldout_results': [],
        'candidate_selector_unit_test_scenarios': [
            'unique_nearest', 'equal_distance_tie', 'weighted_via_planar',
            'obstacles', 'multiple_disconnected_candidates', 'all_unreachable',
            'already_connected_terminal', 'multi_branch_tree',
        ],
    })

    raw_rows = []
    paired_rows = []
    oracle_records = []
    for case_number, case in enumerate(cases, 1):
        layout = experiment_dir / case['relative_path']
        exact = solve(layout)
        expected_status = 'optimal' if case['split'] == 'feasible' else 'infeasible'
        if exact['status'] != expected_status:
            raise ValueError(f"Exact oracle disagrees for {case['case']}: {exact['status']}")
        oracle_records.append({
            'case': case['case'],
            'input_path': case['relative_path'],
            'input_sha256': case['input_sha256'],
            'oracle': exact,
        })
        runs = {method: [] for method in METHODS}
        signatures = {}
        for repetition in range(-warmups, repetitions):
            warmup = repetition < 0
            label = f'w{repetition + warmups:02d}' if warmup else f'r{repetition:03d}'
            order = METHODS if warmup or repetition % 2 == 0 else tuple(reversed(METHODS))
            for method in order:
                output_path = raw_dir / f"{case['case']}_{method}_{label}.json"
                row = {
                    'case': case['case'],
                    'input_path': case['relative_path'],
                    'input_sha256': case['input_sha256'],
                    'oracle_status': exact['status'],
                    'oracle_optimal_cost': exact['optimal_cost'],
                    'selector': method,
                    'algorithm': ALGORITHM,
                    'repetition': label,
                    'warmup': warmup,
                    'router_status': 'execution_error',
                    'success': None,
                    'physical_cost': None,
                    'wirelength': None,
                    'via_count': None,
                    'selection_dijkstra_runs': None,
                    'selection_settled_vertices': None,
                    'selection_edges_examined': None,
                    'selection_heap_pushes': None,
                    'selection_heap_pops': None,
                    'route_searches': None,
                    'route_nodes_expanded': None,
                    'search_count': None,
                    'nodes_expanded': None,
                    'runtime_ms': None,
                    'process_wall_ms': None,
                    'termination_reason': None,
                    'output_path': str(output_path.relative_to(experiment_dir)),
                    'output_sha256': None,
                    'semantic_sha256': None,
                    'error': '',
                }
                try:
                    data, wall_ms = _run_router(executable, layout, output_path, method)
                    signature = stable_run(data)
                    if method in signatures and signatures[method] != signature:
                        raise ValueError(f'Non-repeatable route/search metrics for {case["case"]}/{method}')
                    signatures[method] = signature
                    metrics = data['metrics']
                    selection = _selection_fields(data)
                    if not data['success']:
                        selection['physical_cost'] = None
                        selection['wirelength'] = None
                        selection['via_count'] = None
                    row.update(
                        router_status='success' if data['success'] else 'routing_failure',
                        success=data['success'],
                        **selection,
                        search_count=metrics['search_count'],
                        nodes_expanded=metrics['nodes_expanded'],
                        runtime_ms=metrics['runtime_ms'],
                        process_wall_ms=wall_ms,
                        termination_reason=data['termination_reason'],
                        output_sha256=digest(output_path),
                        semantic_sha256=hashlib.sha256(
                            json.dumps(semantic_output(data), sort_keys=True).encode()).hexdigest(),
                    )
                    if exact['status'] == 'infeasible' and data['success']:
                        raise ValueError('Router succeeded on oracle-infeasible input')
                    row['_data'] = data
                except (OSError, ValueError, KeyError, TypeError, RuntimeError,
                        subprocess.SubprocessError) as error:
                    row['error'] = str(error)
                    raise
                raw_rows.append({key: value for key, value in row.items() if key != '_data'})
                runs[method].append(row)

        measured = {
            method: [row for row in runs[method] if not row['warmup']]
            for method in METHODS
        }
        old_first = measured['repeated'][0]
        new_first = measured['multisource'][0]
        if route_computation(old_first['_data']) != route_computation(new_first['_data']):
            raise AssertionError(f'Route semantics differ for {case["case"]}')
        archived_path = (source_evaluation / 'raw' /
                         f"{case['case']}_nearest_r000.json")
        archived_data = json.loads(archived_path.read_text())
        if semantic_output(archived_data) != semantic_output(old_first['_data']):
            raise AssertionError(f'Repeated selector differs from archived route: {case["case"]}')
        archived_metrics = archived_data['metrics']
        current_metrics = old_first['_data']['metrics']
        if any(archived_metrics[field] != current_metrics[field]
               for field in ('search_count', 'nodes_expanded')):
            raise AssertionError(f'Repeated selector changed historical search counters: {case["case"]}')

        paired = {
            'case': case['case'],
            'input_path': case['relative_path'],
            'input_sha256': case['input_sha256'],
            'seed': case['seed'],
            'terminal_count': case['terminal_count'],
            'layers': case['layers'],
            'obstacle_mode': case['obstacle_mode'],
            'terminal_distribution': case['terminal_distribution'],
            'oracle_status': exact['status'],
            'oracle_optimal_cost': exact['optimal_cost'],
            'equivalent': True,
            'success': old_first['success'],
            'termination_reason': old_first['termination_reason'],
            'physical_cost': old_first['physical_cost'] if old_first['success'] else None,
            'wirelength': old_first['wirelength'] if old_first['success'] else None,
            'via_count': old_first['via_count'] if old_first['success'] else None,
            'attached_terminals': json.dumps([
                [point for point in net['attached_terminals']]
                for net in old_first['_data']['nets']], separators=(',', ':')),
            'tree_edges': json.dumps([
                net.get('tree_edges', []) for net in old_first['_data']['nets']],
                separators=(',', ':')),
            'semantic_sha256': old_first['semantic_sha256'],
        }
        for method in METHODS:
            fields = _selection_fields(measured[method][0]['_data'])
            for name, value in fields.items():
                paired[f'{method}_{name}'] = value
            runtimes = [row['runtime_ms'] for row in measured[method]]
            selection_times = [
                row['_data']['metrics']['selection_runtime_ms'] for row in measured[method]]
            route_times = [row['_data']['metrics']['route_runtime_ms']
                           for row in measured[method]]
            walls = [row['process_wall_ms'] for row in measured[method]]
            paired[f'{method}_runtime_median_ms'] = median(runtimes)
            paired[f'{method}_runtime_mad_ms'] = mad(runtimes)
            paired[f'{method}_selection_runtime_median_ms'] = median(selection_times)
            paired[f'{method}_selection_runtime_mad_ms'] = mad(selection_times)
            paired[f'{method}_route_runtime_median_ms'] = median(route_times)
            paired[f'{method}_route_runtime_mad_ms'] = mad(route_times)
            paired[f'{method}_wall_median_ms'] = median(walls)
            paired[f'{method}_wall_mad_ms'] = mad(walls)
        paired['multisource_minus_repeated_runtime_ms'] = (
            paired['multisource_runtime_median_ms'] - paired['repeated_runtime_median_ms'])
        paired_rows.append(paired)
        with (experiment_dir / 'behavioral_equivalence.json').open('r+') as stream:
            audit = json.load(stream)
            audit['heldout_results'].append({
                'case': case['case'],
                'oracle_status': exact['status'],
                'equivalent': True,
                'archived_route_equivalent': True,
                'physical_cost': paired['physical_cost'],
                'wirelength': paired['wirelength'],
                'via_count': paired['via_count'],
                'termination_reason': paired['termination_reason'],
                'attached_terminals': json.loads(paired['attached_terminals']),
                'semantic_sha256': paired['semantic_sha256'],
            })
            stream.seek(0)
            json.dump(audit,stream,indent=2,allow_nan=False)
            stream.write('\n')
            stream.truncate()
        if case_number % 6 == 0:
            print(f'Completed {case_number}/{len(cases)} paired layouts')

    _write_csv(evaluation / 'raw_runs.csv', raw_rows)
    _write_csv(evaluation / 'paired_results.csv', paired_rows)
    _write_json(evaluation / 'oracle_results.json', oracle_records)
    summary = _summarize(paired_rows, raw_rows)
    _write_json(evaluation / 'summary.json', summary)
    metadata['raw_run_count'] = len(raw_rows)
    metadata['paired_layout_count'] = len(paired_rows)
    metadata['fixed_fixture_equivalence_count'] = len(fixed_results)
    metadata['raw_output_hashes'] = {
        row['output_path']: row['output_sha256'] for row in raw_rows
    }
    metadata['input_hashes'] = {
        item['relative_path']: item['input_sha256'] for item in cases + fixed_cases
    }
    _write_json(evaluation / 'metadata.json', metadata)
    _write_report(evaluation / 'RESULTS.md', paired_rows, summary, fixed_results, metadata)

    if source_hashes != {str(path.relative_to(ROOT)): digest(path) for path in tracked}:
        raise ValueError('Source changed during experiment')
    print(f"Recorded {len(raw_rows)} runs over {len(paired_rows)} held-out cases.")
    print(f"Results: {evaluation / 'RESULTS.md'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment-dir', type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument('--source-experiment', type=Path, default=SOURCE_EXPERIMENT)
    parser.add_argument('--repetitions', type=int, default=11)
    parser.add_argument('--warmups', type=int, default=1)
    parser.add_argument('--limit-cases', type=int)
    args = parser.parse_args()
    run(args.experiment_dir,args.source_experiment,args.repetitions,args.warmups,args.limit_cases)


if __name__ == '__main__':
    main()
