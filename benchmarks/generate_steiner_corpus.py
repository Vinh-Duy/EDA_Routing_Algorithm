"""Generate deterministic development and held-out single-net Steiner layouts."""
import argparse
import hashlib
import itertools
import json
import random
import shutil
from pathlib import Path

from steiner_oracle import solve


ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    'schema_version': 1,
    'development_seed_base': 912000,
    'heldout_seed_base': 202611030000,
    'negative_seed_base': 202612000000,
    'max_replacement_attempts_per_stratum': 100,
    'terminal_counts': [3, 4, 5, 6],
    'layers': [1, 2, 3],
    'feasible_obstacle_modes': ['none', 'sparse', 'medium', 'corridor', 'chokepoint'],
    'terminal_distributions': [
        'compact', 'widely_separated', 'asymmetric', 'branch_heavy', 'barrier_sides',
    ],
    'terminal_distribution_assignment': (
        '(stratum_slot // obstacle_mode_count + stratum_slot % obstacle_mode_count) '
        'mod terminal_distribution_count; fixed across feasibility replacement attempts'
    ),
    'negative_controls': 12,
    'development_instances': 12,
    'dimensions': {
        'one_layer': [[9, 11], [12, 14], [13, 17], [16, 16]],
        'two_layers': [[7, 9], [10, 12], [11, 18], [16, 16]],
        'three_layers': [[6, 8], [9, 10], [12, 14]],
    },
    'obstacle_probability': {'sparse': 0.06, 'medium': 0.16},
    'barrier_openings': {
        'corridor': ['first_column', 'last_column'],
        'chokepoint': 'middle_column',
        'negative_control': 'none',
    },
}
PROTOCOL = {
    'protocol_version': 1,
    'methods': ['input', 'nearest'],
    'search_algorithm': 'astar',
    'net_order': 'numeric',
    'routing_passes': 1,
    'physical_cost': {'planar': 1, 'via': 6},
    'terminal_limit': 6,
    'oracle_legal_vertex_limit': 512,
    'heldout_feasible_target': 60,
    'terminal_distribution_balance': (
        'Orthogonal rotated assignment: every terminal-count/layer block contains '
        'each distribution once; each obstacle mode is paired with all distributions '
        'across blocks.'
    ),
    'negative_control_target': 12,
    'development_target': 12,
    'feasibility_selection': (
        'Accept the first candidate in each predeclared terminal-count/layer/obstacle '
        'stratum that the exact oracle reports optimal; retain every attempted seed '
        'and rejection in candidate_manifest.jsonl. Selection does not inspect either router.'
    ),
    'negative_control_rule': (
        'Place a fully blocked row across every layer and select terminals on both sides; '
        'accept only when the exact oracle proves infeasible.'
    ),
    'repetitions': 11,
    'warmups': 1,
    'execution_order': 'warmup input then nearest; alternate strategy order by measured repetition',
    'primary_metrics': [
        'oracle_optimal_physical_cost', 'router_success', 'router_physical_cost',
        'relative_optimality_gap', 'paired_gap_delta_nearest_minus_input',
    ],
    'relative_gap': '(router_physical_cost - oracle_optimal_cost) / oracle_optimal_cost',
    'zero_optimum_rule': 'relative gap is null; absolute gap and route success remain recorded',
    'failure_rule': 'Failed routes receive no physical cost or optimality gap and are counted separately.',
    'paired_significance': 'Layout is the unit; bootstrap paired mean-gap CI and exact two-sided sign test.',
    'runtime_rule': (
        'Record router-internal and process wall times; summarize repetitions within layout; '
        'report within-layout repeat spread and treat microsecond-scale timing as descriptive.'
    ),
    'strata': [
        'terminal_count', 'layer_count', 'obstacle_density_band',
        'obstacle_configuration', 'terminal_spatial_distribution', 'oracle_feasibility',
    ],
    'no_tuning': (
        'No held-out case may be used to change terminal ordering, tie-breaking, search settings, '
        'or routing parameters.'
    ),
}


def choose_dimensions(rng, layers):
    pool = CONFIG['dimensions'][{
        1: 'one_layer', 2: 'two_layers', 3: 'three_layers',
    }[layers]]
    rows, cols = rng.choice(pool)
    if layers * rows * cols > 512:
        raise ValueError('Configured layout exceeds the oracle legal-vertex limit')
    return rows, cols


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def _choose_terminals(rng, free, count, distribution, rows, cols, layers):
    if len(free) < count:
        raise ValueError('Not enough legal cells for requested terminals')
    center = (layers // 2, rows // 2, cols // 2)
    if distribution == 'compact':
        return sorted(free, key=lambda p: (_manhattan(p, center), p))[:count]
    if distribution == 'widely_separated':
        chosen = [rng.choice(free)]
        while len(chosen) < count:
            choices = [p for p in free if p not in chosen]
            chosen.append(max(choices, key=lambda p: (min(_manhattan(p, q) for q in chosen),
                                                      rng.random(), p)))
        return chosen
    if distribution == 'asymmetric':
        corner = (0, 0, 0)
        anchor_pool = [p for p in free if p[1] <= rows // 3 and p[2] <= cols // 3]
        chosen = [rng.choice(anchor_pool or free)]
        while len(chosen) < count:
            choices = [p for p in free if p not in chosen]
            chosen.append(max(choices, key=lambda p: (_manhattan(p, corner),
                                                      min(_manhattan(p, q) for q in chosen),
                                                      rng.random())))
        return chosen
    if distribution == 'branch_heavy':
        arms = [
            (center[0], 0, center[2]), (center[0], rows - 1, center[2]),
            (center[0], center[1], 0), (center[0], center[1], cols - 1),
            (0, center[1], center[2]), (layers - 1, center[1], center[2]),
        ]
        chosen = []
        for arm in arms:
            available = [p for p in free if p not in chosen]
            if available:
                chosen.append(min(available, key=lambda p: (_manhattan(p, arm), p)))
            if len(chosen) == count:
                break
        while len(chosen) < count:
            available = [p for p in free if p not in chosen]
            chosen.append(max(available, key=lambda p: (min(_manhattan(p, q) for q in chosen),
                                                        rng.random(), p)))
        return chosen
    if distribution == 'barrier_sides':
        middle = rows // 2
        left = [p for p in free if p[1] < middle]
        right = [p for p in free if p[1] > middle]
        if not left or not right:
            return _choose_terminals(rng, free, count, 'widely_separated', rows, cols, layers)
        chosen = [rng.choice(left), rng.choice(right)]
        while len(chosen) < count:
            available = [p for p in free if p not in chosen]
            chosen.append(max(available, key=lambda p: (min(_manhattan(p, q) for q in chosen),
                                                        rng.random(), p)))
        return chosen
    raise ValueError(f'Unknown terminal distribution: {distribution}')


def make_candidate(seed, terminal_count, layers, obstacle_mode, distribution):
    rng = random.Random(seed)
    rows, cols = choose_dimensions(rng, layers)
    cells = {(z, x, y): '.' for z in range(layers)
             for x in range(rows) for y in range(cols)}
    middle = rows // 2
    if obstacle_mode in ('corridor', 'chokepoint', 'negative_control'):
        openings = ({0, cols - 1} if obstacle_mode == 'corridor'
                    else ({cols // 2} if obstacle_mode == 'chokepoint' else set()))
        for z in range(layers):
            for y in range(cols):
                if y not in openings:
                    cells[z, middle, y] = '#'
    elif obstacle_mode in ('sparse', 'medium'):
        probability = CONFIG['obstacle_probability'][obstacle_mode]
        for point in sorted(cells):
            if rng.random() < probability:
                cells[point] = '#'
    elif obstacle_mode != 'none':
        raise ValueError(f'Unknown obstacle mode: {obstacle_mode}')

    free = [p for p, token in cells.items() if token == '.']
    if obstacle_mode == 'negative_control':
        left = [p for p in free if p[1] < middle]
        right = [p for p in free if p[1] > middle]
        chosen = [rng.choice(left), rng.choice(right)]
        while len(chosen) < terminal_count:
            side = left if len(chosen) % 2 == 0 else right
            available = [p for p in side if p not in chosen]
            chosen.append(rng.choice(available))
    else:
        chosen = _choose_terminals(rng, free, terminal_count, distribution, rows, cols, layers)

    rng.shuffle(chosen)
    labels = ['S1', 'T1'] + ['P1'] * (terminal_count - 2)
    for point, label in zip(chosen, labels):
        cells[point] = label
    lines = [f'{layers} {rows} {cols}']
    for z in range(layers):
        for x in range(rows):
            lines.append(' '.join(cells[z, x, y] for y in range(cols)))
    return '\n'.join(lines) + '\n'


def _write_candidate(root, candidate_id, text):
    path = root / 'candidates' / f'{candidate_id}.txt'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _append_record(records, **record):
    records.append(record)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accept_candidate(root, source, relative_destination):
    destination = root / relative_destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


def generate(output_dir):
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f'Output directory already exists: {output_dir}')
    output_dir.mkdir(parents=True)
    (output_dir / 'development' / 'layouts').mkdir(parents=True)
    (output_dir / 'heldout' / 'layouts').mkdir(parents=True)
    records = []
    cases = {'development': [], 'heldout_feasible': [], 'heldout_infeasible': []}
    slot = 0
    stratum_specs = list(itertools.product(CONFIG['terminal_counts'], CONFIG['layers'],
                                           CONFIG['feasible_obstacle_modes']))
    for terminal_count, layers, obstacle_mode in stratum_specs:
        accepted = False
        for attempt in range(CONFIG['max_replacement_attempts_per_stratum']):
            seed = CONFIG['heldout_seed_base'] + slot * 1000 + attempt
            obstacle_count = len(CONFIG['feasible_obstacle_modes'])
            distribution_index = (slot // obstacle_count + slot % obstacle_count) % \
                len(CONFIG['terminal_distributions'])
            distribution = CONFIG['terminal_distributions'][distribution_index]
            text = make_candidate(seed, terminal_count, layers, obstacle_mode, distribution)
            candidate_id = f'heldout_{slot:03d}_attempt_{attempt:03d}_seed_{seed}'
            source = _write_candidate(output_dir, candidate_id, text)
            result = solve(source)
            candidate = dict(
                split='heldout_feasible', stratum=slot, attempt=attempt, seed=seed,
                terminal_count=terminal_count, layers=layers, obstacle_mode=obstacle_mode,
                terminal_distribution=distribution, candidate=str(source.relative_to(output_dir)),
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                oracle_status=result['status'], oracle_reason=result['reason'],
                oracle_cost=result['optimal_cost'], accepted=False,
                rejection_reason=None,
            )
            if result['status'] == 'optimal':
                filename = (f'feasible_{slot:03d}_k{terminal_count}_l{layers}_'
                            f'{obstacle_mode}_{distribution}_seed{seed}.txt')
                destination = _accept_candidate(
                    output_dir, source, Path('heldout/layouts') / filename)
                candidate.update(accepted=True, accepted_input=str(destination.relative_to(output_dir)),
                                 accepted_sha256=hashlib.sha256(
                                     destination.read_bytes()).hexdigest())
                cases['heldout_feasible'].append({
                    'path': str(destination.relative_to(output_dir)),
                    'seed': seed, 'stratum': slot, 'terminal_count': terminal_count,
                    'layers': layers, 'obstacle_mode': obstacle_mode,
                    'terminal_distribution': distribution,
                })
                accepted = True
            else:
                candidate['rejection_reason'] = f'oracle_{result["status"]}:{result["reason"]}'
            _append_record(records, **candidate)
            if accepted:
                break
        if not accepted:
            raise RuntimeError(f'Could not fill held-out stratum {slot} after configured attempts')
        slot += 1

    for index in range(CONFIG['negative_controls']):
        terminal_count = CONFIG['terminal_counts'][index % len(CONFIG['terminal_counts'])]
        layers = CONFIG['layers'][(index // len(CONFIG['terminal_counts'])) % len(CONFIG['layers'])]
        seed = CONFIG['negative_seed_base'] + index
        distribution = CONFIG['terminal_distributions'][index % len(CONFIG['terminal_distributions'])]
        text = make_candidate(seed, terminal_count, layers, 'negative_control', distribution)
        candidate_id = f'negative_{index:03d}_seed_{seed}'
        source = _write_candidate(output_dir, candidate_id, text)
        result = solve(source)
        if result['status'] != 'infeasible':
            raise RuntimeError(f'Negative-control seed {seed} was not proven infeasible')
        filename = f'infeasible_{index:03d}_k{terminal_count}_l{layers}_seed{seed}.txt'
        destination = _accept_candidate(output_dir, source, Path('heldout/layouts') / filename)
        records.append(dict(
            split='heldout_infeasible', stratum=index, attempt=0, seed=seed,
            terminal_count=terminal_count, layers=layers, obstacle_mode='negative_control',
            terminal_distribution=distribution, candidate=str(source.relative_to(output_dir)),
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            oracle_status=result['status'], oracle_reason=result['reason'],
            oracle_cost=None, accepted=True, rejection_reason=None,
            accepted_input=str(destination.relative_to(output_dir)),
            accepted_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        ))
        cases['heldout_infeasible'].append({
            'path': str(destination.relative_to(output_dir)), 'seed': seed,
            'terminal_count': terminal_count, 'layers': layers,
            'obstacle_mode': 'negative_control', 'terminal_distribution': distribution,
        })

    for index in range(CONFIG['development_instances']):
        terminal_count = CONFIG['terminal_counts'][index % len(CONFIG['terminal_counts'])]
        layers = CONFIG['layers'][(index // len(CONFIG['terminal_counts'])) % len(CONFIG['layers'])]
        seed = CONFIG['development_seed_base'] + index
        obstacle_mode = CONFIG['feasible_obstacle_modes'][index % len(CONFIG['feasible_obstacle_modes'])]
        distribution = CONFIG['terminal_distributions'][(index * 3) %
                                                         len(CONFIG['terminal_distributions'])]
        accepted = False
        for attempt in range(CONFIG['max_replacement_attempts_per_stratum']):
            candidate_seed = seed + attempt * 1000
            text = make_candidate(candidate_seed, terminal_count, layers,
                                  obstacle_mode, distribution)
            candidate_id = f'development_{index:03d}_attempt_{attempt:03d}_seed_{candidate_seed}'
            source = _write_candidate(output_dir, candidate_id, text)
            result = solve(source)
            record = dict(
                split='development', stratum=index, attempt=attempt, seed=candidate_seed,
                terminal_count=terminal_count, layers=layers, obstacle_mode=obstacle_mode,
                terminal_distribution=distribution, candidate=str(source.relative_to(output_dir)),
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                oracle_status=result['status'], oracle_reason=result['reason'],
                oracle_cost=result['optimal_cost'], accepted=False, rejection_reason=None,
            )
            if result['status'] == 'optimal':
                filename = f'development_{index:03d}_seed{candidate_seed}.txt'
                destination = _accept_candidate(
                    output_dir, source, Path('development/layouts') / filename)
                record.update(accepted=True, accepted_input=str(destination.relative_to(output_dir)),
                              accepted_sha256=hashlib.sha256(
                                  destination.read_bytes()).hexdigest())
                cases['development'].append({
                    'path': str(destination.relative_to(output_dir)), 'seed': candidate_seed,
                    'terminal_count': terminal_count, 'layers': layers,
                    'obstacle_mode': obstacle_mode, 'terminal_distribution': distribution,
                })
                accepted = True
            else:
                record['rejection_reason'] = f'oracle_{result["status"]}:{result["reason"]}'
            records.append(record)
            if accepted:
                break
        if not accepted:
            raise RuntimeError(f'Could not fill development stratum {index}')

    (output_dir / 'generator_config.json').write_text(json.dumps(CONFIG, indent=2) + '\n')
    (output_dir / 'evaluation_protocol.json').write_text(json.dumps(PROTOCOL, indent=2) + '\n')
    (output_dir / 'candidate_manifest.jsonl').write_text(
        ''.join(json.dumps(record, sort_keys=True) + '\n' for record in records))
    seed_manifest = {
        'heldout_feasible_strata': [
            {'slot': slot, 'terminal_count': k, 'layers': layers, 'obstacle_mode': obstacle}
            for slot, (k, layers, obstacle) in enumerate(stratum_specs)
        ],
        'heldout_seed_rule': 'seed_base + stratum_slot * 1000 + replacement_attempt',
        'heldout_distribution_rule': CONFIG['terminal_distribution_assignment'],
        'heldout_seed_base': CONFIG['heldout_seed_base'],
        'negative_seed_rule': 'negative_seed_base + negative_control_index',
        'negative_seed_base': CONFIG['negative_seed_base'],
        'development_seed_rule': 'development_seed_base + development_index + attempt * 1000',
        'development_seed_base': CONFIG['development_seed_base'],
        'cases': cases,
    }
    (output_dir / 'seed_manifest.json').write_text(json.dumps(seed_manifest, indent=2) + '\n')
    corpus_manifest = {
        'schema_version': 1,
        'heldout_feasible_count': len(cases['heldout_feasible']),
        'heldout_infeasible_count': len(cases['heldout_infeasible']),
        'development_count': len(cases['development']),
        'cases': cases,
    }
    (output_dir / 'corpus_manifest.json').write_text(json.dumps(corpus_manifest, indent=2) + '\n')
    generator_files = [
        Path(__file__).resolve(),
        ROOT / 'benchmarks/steiner_oracle.py',
        ROOT / 'benchmarks/validate_output.py',
    ]
    generation_metadata = {
        'generator_sha256': _sha256(generator_files[0]),
        'oracle_sha256': _sha256(generator_files[1]),
        'layout_parser_sha256': _sha256(generator_files[2]),
        'generator_config_sha256': _sha256(output_dir / 'generator_config.json'),
        'evaluation_protocol_sha256': _sha256(output_dir / 'evaluation_protocol.json'),
        'candidate_manifest_sha256': _sha256(output_dir / 'candidate_manifest.jsonl'),
        'seed_manifest_sha256': _sha256(output_dir / 'seed_manifest.json'),
        'corpus_manifest_sha256': _sha256(output_dir / 'corpus_manifest.json'),
        'candidate_file_count': sum(1 for _ in (output_dir / 'candidates').glob('*.txt')),
        'candidate_input_sha256': {
            str(path.relative_to(output_dir)): _sha256(path)
            for path in sorted((output_dir / 'candidates').glob('*.txt'))
        },
        'accepted_input_sha256': {
            str(path.relative_to(output_dir)): _sha256(path)
            for path in sorted(output_dir.glob('**/layouts/*.txt'))
        },
    }
    (output_dir / 'generation_metadata.json').write_text(
        json.dumps(generation_metadata, indent=2) + '\n')
    print(f"Generated {len(cases['development'])} development, "
          f"{len(cases['heldout_feasible'])} held-out feasible, and "
          f"{len(cases['heldout_infeasible'])} infeasible cases.")
    print(f"Retained {len(records)} candidate records at {output_dir / 'candidate_manifest.jsonl'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    generate(args.output_dir)


if __name__ == '__main__':
    main()
