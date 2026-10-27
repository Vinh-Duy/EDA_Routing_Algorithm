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


def read_layout_with_extras(path):
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
    cells, sources, targets, extras = {}, {}, {}, {}
    for i, row in enumerate(body):
        for y, cell in enumerate(row):
            p = (i // rows, i % rows, y)
            cells[p] = cell
            if cell not in ('.', '#'):
                if cell[0] not in 'STP':
                    raise ValueError('Invalid pin')
                pins = sources if cell[0] == 'S' else targets if cell[0] == 'T' else extras
                name = 'Net' + str(positive_integer(cell[1:]))
                if cell[0] == 'P':
                    extras.setdefault(name, []).append(p)
                elif name in pins:
                    raise ValueError('Duplicate pin')
                else:
                    pins[name] = p
    if not sources or sources.keys() != targets.keys():
        raise ValueError('Incomplete pins')
    if not set(extras).issubset(sources):
        raise ValueError('Additional terminal has no matching S/T pair')
    return dims, cells, sources, targets, extras


def read_layout(path):
    return read_layout_with_extras(path)[:4]


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
    dims, cells, sources, targets, extras = read_layout_with_extras(layout_path)
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
    local, empty, incomplete = {}, 0, 0
    wire, vias, branches, invalid_count, unconnected = 0, 0, 0, 0, 0
    for net in nets:
        check(type(net['valid']) is bool and type(net['local_valid']) is bool, 'Validity flag types')
        check(type(net['search_cost']) is int and net['search_cost'] >= 0, 'Net search cost')
        name = net['name']
        if name not in sources:
            continue
        check(point(net['source']) == sources[name], name + ' source metadata')
        check(point(net['target']) == targets[name], name + ' target metadata')
        expected_terminals = [sources[name], targets[name], *extras.get(name, [])]
        if 'terminals' in net:
            check([point(p) for p in net['terminals']] == expected_terminals, name + ' terminals')
        if len(expected_terminals) > 2:
            edges = net.get('tree_edges')
            if not isinstance(edges, list):
                raise ValueError(name + ' tree_edges must be a list')
            check(net['path'] == [], name + ' tree must not use legacy path field')
            parent, degree, vertices, seen_edges = {}, defaultdict(int), set(), set()
            edge_valid = True

            def find(vertex):
                parent.setdefault(vertex, vertex)
                while parent[vertex] != vertex:
                    parent[vertex] = parent[parent[vertex]]
                    vertex = parent[vertex]
                return vertex

            net_wire, net_vias = 0, 0
            # A net's root is part of its tree even when no edge could be
            # routed; this keeps a partial route a connectivity failure, not
            # a malformed-geometry failure.
            vertices.add(expected_terminals[0])
            owners[expected_terminals[0]].add(name)
            for raw_edge in edges:
                if not isinstance(raw_edge, list) or len(raw_edge) != 2:
                    edge_valid = False
                    continue
                a, b = point(raw_edge[0]), point(raw_edge[1])
                vertices.update((a, b))
                key = tuple(sorted((a, b)))
                if key in seen_edges:
                    edge_valid = False
                    continue
                seen_edges.add(key)
                for p in (a, b):
                    if p not in cells or cells[p] == '#' or (cells[p] != '.' and p not in expected_terminals):
                        edge_valid = False
                    if p in cells:
                        owners[p].add(name)
                if sum(abs(x-y) for x,y in zip(a,b)) != 1:
                    edge_valid = False
                    continue
                degree[a] += 1; degree[b] += 1
                ra, rb = find(a), find(b)
                if ra == rb:
                    edge_valid = False
                else:
                    parent[ra] = rb
                if a[0] == b[0]: net_wire += 1
                else: net_vias += 1
            connected = sum(t in vertices and find(t) == find(expected_terminals[0])
                            for t in expected_terminals)
            disconnected_edges = bool(vertices) and len({find(v) for v in vertices}) != 1
            if disconnected_edges:
                edge_valid = False
            missing = len(expected_terminals) - connected
            incomplete += int(missing > 0)
            unconnected += missing
            geometry_valid = edge_valid and not disconnected_edges
            good = not missing and geometry_valid
            invalid_count += int(not edge_valid or disconnected_edges)
            local[name] = good
            check(net['connected_terminals'] == connected, name + ' connected terminal count')
            check(net['unconnected_terminals'] == missing, name + ' unconnected terminal count')
            check(type(net.get('branch_count')) is int and net['branch_count'] >= 0,
                  name + ' branch count type')
            net_branches = sum(d >= 3 for d in degree.values()) if geometry_valid else 0
            check(net['branch_count'] == net_branches, name + ' branch count')
            if geometry_valid:
                wire += net_wire; vias += net_vias; branches += net_branches
            continue
        path = [point(p) for p in net['path']]
        if not path:
            empty += 1
            missing = max(1, len(expected_terminals)-1)
            unconnected += missing
            if expected_terminals[0] in cells:
                owners[expected_terminals[0]].add(name)
            if 'connected_terminals' in net:
                check(net['connected_terminals'] == len(expected_terminals)-missing,
                      name + ' connected terminal count')
                check(net['unconnected_terminals'] == missing, name + ' unconnected terminal count')
            local[name] = False
            continue
        valid = path[0] == expected_terminals[0] and path[-1] == expected_terminals[1] and len(set(path)) == len(path)
        nw, nv = 0, 0
        for i, p in enumerate(path):
            if p not in cells or cells[p] == '#' or (cells[p] != '.' and p not in expected_terminals):
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
        if 'connected_terminals' in net:
            check(net['connected_terminals'] == (len(expected_terminals) if valid else 0),
                  name + ' connected terminal count')
            check(net['unconnected_terminals'] == (0 if valid else len(expected_terminals)),
                  name + ' unconnected terminal count')
        check(type(net.get('branch_count', 0)) is int and net.get('branch_count', 0) == 0,
              name + ' branch count')
        invalid_count += int(not valid)
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
    expected = dict(total_nets=len(sources), routed_nets=routed, unrouted_nets=empty+incomplete,
                    invalid_nets=invalid_count,
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
    if 'unconnected_terminals' in m:
        check(type(m['unconnected_terminals']) is int and m['unconnected_terminals'] >= 0,
              'Metric unconnected_terminals type')
        check(m['unconnected_terminals'] == unconnected, 'Metric unconnected_terminals')
    if 'branch_count' in m:
        check(type(m['branch_count']) is int and m['branch_count'] >= 0, 'Metric branch_count type')
        check(m['branch_count'] == branches, 'Metric branch_count')
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
            check(empty+incomplete > 0 and not conflicts, 'Unreachable termination mismatch')
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
