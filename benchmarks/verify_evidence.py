"""Read-only verification of CSV summaries, failures, input hashes, and saved evidence."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1]
QUALITY=('total_nets','routed_nets','success_rate','unrouted_nets','invalid_nets',
         'unresolved_conflicts','wirelength','via_count','graph_steps','weighted_cost',
         'search_cost','routing_passes','reroute_iterations','nodes_expanded')


def require(condition,message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open() as file:
        return list(csv.DictReader(file))


def verify_suite(folder, require_current=False):
    rows=read_csv(folder/'results.csv');summaries=read_csv(folder/'summary.csv')
    meta=json.loads((folder/'metadata.json').read_text())
    groups=defaultdict(list)
    for row in rows:
        groups[row['dataset'],row['algorithm']].append(row)
    require(bool(groups),'No observations')
    require(len(summaries)==len(groups),'Summary group count')
    require(len({(s['dataset'],s['algorithm']) for s in summaries})==len(groups),'Duplicate summary group')
    require(set(groups)=={(s['dataset'],s['algorithm']) for s in summaries},'Summary group identities')
    for dataset,_ in groups:
        require({a for d,a in groups if d==dataset}=={'astar','bfs','dijkstra'},'Missing algorithm')
    for s in summaries:
        key=s['dataset'],s['algorithm'];group=groups[key]
        require(len(group)==int(s['repetitions'])==meta['repetitions'],f'{key}: repetitions')
        require(sorted(int(r['repetition']) for r in group)==list(range(meta['repetitions'])),f'{key}: duplicate/missing sample')
        verified=[r for r in group if r['output_verified']=='True']
        require(len(verified)==int(s['verified_runs']),f'{key}: verified count')
        require(len(group)-len(verified)==int(s['execution_errors']),f'{key}: error count')
        require(sum(r['success']=='True' for r in verified)==int(s['successful_runs']),f'{key}: success count')
        for r in group:
            if r['output_verified']!='True':
                require(r['status']=='execution_error' and all(r[k]=='' for k in (*QUALITY,'runtime_ms')),f'{key}: invented error metrics')
                continue
            require(r['status']==('success' if r['success']=='True' else 'routing_failed'),f'{key}: failure classification')
            require(r['returncode']==('0' if r['success']=='True' else '2'),f'{key}: exit status')
            require(int(r['invalid_nets'])==0,f'{key}: invalid nonempty path')
            require(float(r['weighted_cost'])==float(r['wirelength'])+6*float(r['via_count']),f'{key}: physical cost')
            require(int(r['graph_steps'])==int(r['wirelength'])+int(r['via_count']),f'{key}: graph steps')
            require(int(r['routing_passes'])==int(r['reroute_iterations'])+1,f'{key}: passes')
        if verified:
            times=[float(r['runtime_ms']) for r in verified]
            require(all(math.isfinite(v) and v>=0 for v in times),f'{key}: invalid timing')
            for field,fn in [('median_ms',statistics.median),('mean_ms',statistics.mean),
                             ('stdev_ms',lambda a: statistics.stdev(a) if len(a)>1 else 0),
                             ('min_ms',min),('max_ms',max)]:
                require(math.isclose(float(s[field]),fn(times),rel_tol=1e-12,abs_tol=1e-12),f'{key}: {field}')
            for field in QUALITY:
                require(all(r[field]==s[field] for r in verified),f'{key}: nondeterministic/mismatched {field}')
    mismatches=[]
    for name,h in meta['sha256'].items():
        path=ROOT/name
        matches=path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==h
        if path.suffix=='.txt':
            require(matches,f'Input hash mismatch: {name}')
        elif not matches:
            mismatches.append(name)
    if require_current:
        require(not mismatches,f'Current source hashes differ: {mismatches}')
        require(hashlib.sha256((ROOT/'router').read_bytes()).hexdigest()==meta['executable_sha256'],'Executable hash differs')
    print(f'{folder}: {len(rows)} observations, statistics/inputs verified; {len(mismatches)} source differences from current checkout')
    return len(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',type=Path,action='append')
    parser.add_argument('--require-current',action='store_true')
    args=parser.parse_args()
    preserved=ROOT/'docs/verification/preserved-evidence.json'
    if preserved.exists():
        for name,h in json.loads(preserved.read_text()).items():
            require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,f'Historical evidence changed: {name}')
        print('Historical measurements, figures, and original datasets unchanged')
    for folder in args.suite or [ROOT/'benchmarks',ROOT/'benchmarks/single_pass',ROOT/'benchmarks/early_stop']:
        verify_suite(folder,args.require_current)


if __name__ == '__main__':
    main()
