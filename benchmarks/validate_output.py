"""Independent Python route and metric checker against the source layout."""
from collections import defaultdict
from pathlib import Path
import argparse
import json
import math
import re


def positive_integer(text):
    if not re.fullmatch(r'[1-9][0-9]*', text) or int(text) > 2147483647:
        raise ValueError('Invalid positive integer')
    return int(text)


def read_layout(path):
    lines = Path(path).read_text().splitlines()
    if not lines:
        raise ValueError('Missing header')
    dims = [positive_integer(v) for v in lines[0].split()]
    if len(dims) == 2:
        dims.insert(0, 1)
    if len(dims) != 3 or min(dims) < 1:
        raise ValueError('Invalid dimensions')
    layers, rows, cols = dims
    if layers * rows * cols > 1000000:
        raise ValueError('Layout exceeds cell limit')
    body = [line.split() for line in lines[1:] if line.strip()]
    if len(body) != layers * rows or any(len(row) != cols for row in body):
        raise ValueError('Invalid row lengths')
    cells, sources, targets = {}, {}, {}
    for i, row in enumerate(body):
        for y, cell in enumerate(row):
            p = (i // rows, i % rows, y)
            cells[p] = cell
            if cell not in ('.', '#'):
                if cell[0] not in 'ST':
                    raise ValueError('Invalid pin')
                pins = sources if cell[0] == 'S' else targets
                name = 'Net' + str(positive_integer(cell[1:]))
                if name in pins:
                    raise ValueError('Duplicate pin')
                pins[name] = p
    if not sources or sources.keys() != targets.keys():
        raise ValueError('Incomplete pins')
    return dims, cells, sources, targets


def point(p):
    result = tuple(p[k] for k in ('z', 'x', 'y'))
    if any(type(v) is not int for v in result):
        raise ValueError('Non-integer coordinate')
    return result


def validate(layout_path, data):
    try:
        return _validate(layout_path, data)
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError) as error:
        raise ValueError(f'Malformed routing output: {error}') from error


def _validate(layout_path, data):
    dims, cells, sources, targets = read_layout(layout_path)
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    check(type(data['success']) is bool, 'Success must be boolean')
    check(data['algorithm'] in ('astar', 'dijkstra', 'bfs'), 'Unknown algorithm')
    check(data.get('net_order','numeric') in ('numeric','reverse'), 'Unknown net order')
    check(type(data['schema_version']) is int, 'Schema version type')
    check(all(type(v) is int for v in data['dimensions']), 'Dimension types')
    check(all(type(v) is int for v in data['cost_model'].values()), 'Cost model types')
    check(data.get('schema_version') == 2, 'Schema version')
    check(data.get('dimensions') == dims, 'Dimensions mismatch')
    check(data.get('cost_model') == dict(planar=1, via=6, occupied_cell=100, history_increment=50),
          'Cost model mismatch')
    nets = data['nets']
    if not isinstance(nets,list):
        raise ValueError('Nets must be a list')
    check(len(nets) == len(sources), 'Net count')
    check({n['name'] for n in nets} == set(sources), 'Net identities')
    owners = defaultdict(set)
    local, empty = {}, 0
    wire, vias = 0, 0
    for net in nets:
        check(type(net['valid']) is bool and type(net['local_valid']) is bool, 'Validity flag types')
        check(type(net['search_cost']) is int and net['search_cost'] >= 0, 'Net search cost')
        name = net['name']
        if name not in sources:
            continue
        check(point(net['source']) == sources[name], name + ' source metadata')
        check(point(net['target']) == targets[name], name + ' target metadata')
        path = [point(p) for p in net['path']]
        if not path:
            empty += 1
            local[name] = False
            continue
        valid = path[0] == sources[name] and path[-1] == targets[name] and len(set(path)) == len(path)
        nw, nv = 0, 0
        for i, p in enumerate(path):
            if p not in cells or cells[p] == '#' or (cells[p] != '.' and p not in (sources[name], targets[name])):
                valid = False
            if p in cells:
                owners[p].add(name)
            if i:
                prev = path[i-1]
                if sum(abs(a-b) for a,b in zip(p, prev)) != 1:
                    valid = False
                elif p[0] == prev[0]:
                    nw += 1
                else:
                    nv += 1
        local[name] = valid
        check(valid, name + ' invalid nonempty path')
        if valid:
            wire += nw
            vias += nv
    conflicts = {p: names for p, names in owners.items() if len(names) > 1}
    conflicting_nets = set().union(*conflicts.values()) if conflicts else set()
    routed = sum(ok and name not in conflicting_nets for name, ok in local.items())
    for net in nets:
        check(net['local_valid'] == local.get(net['name'], False), net['name'] + ' local validity')
        check(net['valid'] == (local.get(net['name'], False) and net['name'] not in conflicting_nets), net['name'] + ' validity')
    actual_conflicts = {point(c['cell']): set(c['nets']) for c in data['conflicts']}
    check(actual_conflicts == conflicts, 'Conflict ownership')
    check({point(p) for p in data['obstacles']} == {p for p,c in cells.items() if c == '#'}, 'Obstacles')
    expected = dict(total_nets=len(sources), routed_nets=routed, unrouted_nets=empty,
                    invalid_nets=sum(not x for x in local.values())-empty,
                    unresolved_conflicts=len(conflicts), wirelength=wire, via_count=vias,
                    graph_steps=wire+vias, weighted_cost=wire+6*vias,
                    success_rate=routed/len(sources))
    m = data['metrics']
    integer_metrics = ('total_nets', 'routed_nets', 'unrouted_nets', 'invalid_nets',
                       'unresolved_conflicts', 'wirelength', 'via_count', 'graph_steps',
                       'weighted_cost', 'search_cost', 'routing_passes', 'reroute_iterations',
                       'nodes_expanded')
    for key in integer_metrics:
        check(type(m[key]) is int and m[key] >= 0, 'Nonnegative integer metric ' + key)
    for key in ('runtime_ms','success_rate'):
        check(type(m[key]) in (int,float) and math.isfinite(m[key]), 'Finite numeric metric ' + key)
    for key, value in expected.items():
        check(math.isclose(m[key], value, rel_tol=1e-10, abs_tol=1e-10), 'Metric ' + key)
    check(data['success'] == (routed == len(sources)), 'Overall success')
    check(m['routing_passes'] >= 1 and m['reroute_iterations'] == m['routing_passes']-1, 'Iteration count')
    check(m['runtime_ms'] >= 0 and math.isfinite(m['runtime_ms']), 'Runtime')
    check(m['nodes_expanded'] >= 0, 'Expanded nodes')
    check(m['search_cost'] == sum(n['search_cost'] for n in nets), 'Search cost sum')
    # Additive schema-v2 field: historical benchmark outputs may omit it.
    reason = data.get('termination_reason')
    if 'termination_reason' in data:
        check(reason in ('success', 'unreachable', 'congestion_insensitive', 'iteration_limit'),
              'Unknown termination reason')
        check((reason == 'success') == (routed == len(sources)), 'Termination success mismatch')
        if reason == 'unreachable':
            check(empty > 0 and not conflicts, 'Unreachable termination mismatch')
        elif reason in ('congestion_insensitive', 'iteration_limit'):
            check(bool(conflicts), 'Conflicted termination without conflicts')
        if reason == 'congestion_insensitive':
            check(data.get('algorithm') == 'bfs' and m['routing_passes'] == 1,
                  'Congestion-insensitive termination mismatch')
    if errors:
        raise ValueError('; '.join(errors))
    return data['success']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    success = validate(args.input, json.loads(Path(args.output).read_text()))
    print('Output verified; routing ' + ('successful' if success else 'incomplete (correctly reported)'))


if __name__ == '__main__':
    main()
