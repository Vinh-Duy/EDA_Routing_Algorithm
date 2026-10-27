"""Generate figures and a table directly from recorded observations (including failures)."""
import argparse
from collections import defaultdict
import csv
import json
import os
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'build/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ALGORITHMS = ('astar', 'dijkstra', 'bfs')
COLORS = ('#2874a6', '#e67e22', '#26865b')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=ROOT/'benchmarks/results.csv')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'benchmarks/figures')
    parser.add_argument('--route', type=Path, help='Optional route JSON for a separate representative figure')
    parser.add_argument('--format', choices=('png','svg','both'), default='both')
    parser.add_argument('--report', type=Path, help='Summary Markdown destination (default: beside CSV)')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with args.csv.open() as file:
        rows = list(csv.DictReader(file))
    if not rows:
        parser.error('CSV has no observations')
    if args.route is not None and not args.route.is_file():
        parser.error('Route JSON does not exist')
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row['dataset'], row['algorithm'])].append(row)
    datasets = list(dict.fromkeys(r['dataset'] for r in rows))
    datasets.sort()
    plots = [('runtime_ms', 'Algorithm execution time (ms, median; bars: IQR)', 'runtime'),
             ('wirelength', 'Planar wirelength (grid edges)', 'wirelength'),
             ('via_count', 'VIA count (adjacent layer transitions)', 'vias'),
             ('success_rate', 'Conflict-free valid nets (%)', 'success_rate'),
             ('nodes_expanded', 'Search nodes expanded (all routing passes)', 'nodes_expanded')]
    if all('branch_count' in row for row in rows):
        plots.append(('branch_count', 'Unique degree-three-or-more branch vertices', 'branch_count'))
    for metric, ylabel, filename in plots:
        fig, ax = plt.subplots(figsize=(15, 6.5))
        for a, (algorithm, color) in enumerate(zip(ALGORITHMS, COLORS)):
            for d, dataset in enumerate(datasets):
                group = grouped[dataset, algorithm]
                verified = [r for r in group if r['output_verified']=='True']
                x = d + (a-1)*0.25
                if not verified:
                    ax.text(x, 0, 'ERR', rotation=90, color='red', ha='center')
                    continue
                values = [float(r[metric])*(100 if metric=='success_rate' else 1) for r in verified]
                median = statistics.median(values)
                failed = any(r['success']!='True' for r in verified)
                error = None
                if metric=='runtime_ms' and len(values)>1:
                    q = statistics.quantiles(values, n=4, method='inclusive')
                    error = [[median-q[0]],[q[2]-median]]
                ax.bar(x, median, width=0.24, color=color, edgecolor='#333333', linewidth=0.3,
                       hatch='///' if failed else '', yerr=error, capsize=2)
                if failed:
                    # Marks failures even when quality values are zero.
                    ax.annotate('×', (x,median), ha='center', va='bottom', fontsize=10)
                if len(verified)!=len(group):
                    ax.annotate('ERR', (x,median), rotation=90, ha='center', color='red')
        if metric in ('runtime_ms','nodes_expanded'):
            ax.set_yscale('log')
        if metric=='success_rate':
            ax.set_ylim(0,115)
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(len(datasets)), [d.removeprefix('chip_layout_') for d in datasets], rotation=35, ha='right')
        ax.set_xlabel('Dataset (same inputs and pass limits for all algorithms)')
        ax.grid(axis='y', alpha=0.2)
        ax.set_axisbelow(True)
        handles = [Patch(facecolor=c,label=a) for a,c in zip(ALGORITHMS,COLORS)]
        handles.append(Patch(facecolor='white',edgecolor='black',hatch='///',label='Routing failed (×); partial quality only'))
        ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(0,1.16), ncol=4, frameon=False)
        fig.tight_layout()
        for extension in (('png','svg') if args.format=='both' else (args.format,)):
            fig.savefig(args.output_dir/f'{filename}.{extension}',dpi=170)
        plt.close(fig)
    table = ['# Recorded benchmark measurements', '',
             'Generated from `results.csv`. Runtime is median / mean / sample standard deviation in ms. '
             'Quality is deterministic across verified repetitions. Failed runs retain partial-path quality; '
             'it is not a complete routing solution.', '',
             '| Dataset | Algorithm | Runs verified | Successful runs | Valid nets | Conflicts | Wire | VIAs | Branches | Cost | Passes | Expanded | Runtime ms (median / mean / SD) |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for dataset in datasets:
        for algorithm in ALGORITHMS:
            group = grouped[dataset,algorithm]
            verified = [r for r in group if r['output_verified']=='True']
            if not verified:
                table.append(f'| {dataset} | {algorithm} | 0 | 0 | — | — | — | — | — | — | — | — | execution failure |')
                continue
            r=verified[0]; times=[float(x['runtime_ms']) for x in verified]
            success=sum(x['success']=='True' for x in verified)
            sd=statistics.stdev(times) if len(times)>1 else 0
            table.append(f"| {dataset} | {algorithm} | {len(verified)}/{len(group)} | {success} | "
                         f"{r['routed_nets']}/{r['total_nets']} | {r['unresolved_conflicts']} | {r['wirelength']} | "
                         f"{r['via_count']} | {r.get('branch_count','—')} | {r['weighted_cost']} | {r['routing_passes']} | {r['nodes_expanded']} | "
                         f"{statistics.median(times):.6f} / {statistics.mean(times):.6f} / {sd:.6f} |")
    report = args.report or args.csv.parent/'RESULTS.md'
    report.write_text('\n'.join(table)+'\n')
    # A static, shareable route view complements the interactive Plotly HTML.
    if args.route is not None:
        data=json.loads(args.route.read_text())
        fig=plt.figure(figsize=(10,8)); ax=fig.add_subplot(111,projection='3d')
        for i,net in enumerate(data['nets']):
            path=net['path']; edges=net.get('tree_edges', []); color=plt.get_cmap('tab20')(i%20)
            ax.plot([p['x'] for p in path],[p['y'] for p in path],[p['z'] for p in path],
                    color=color,label=net['name'],linestyle='-' if net.get('valid') else '--')
            segments=edges if edges else list(zip(path,path[1:]))
            for a,b in segments:
                if a['z']!=b['z']:
                    ax.plot([a['x'],b['x']],[a['y'],b['y']],[a['z'],b['z']],color=color,linewidth=4)
                else:
                    ax.plot([a['x'],b['x']],[a['y'],b['y']],[a['z'],b['z']],color=color,linewidth=2)
            terminals=net.get('terminals', [])
            pins=list(zip(terminals,['S','T']+['P']*max(0,len(terminals)-2))) if terminals else [(net['source'],'S'),(net['target'],'T')]
            for p,label in pins:
                ax.scatter(p['x'],p['y'],p['z'],color=color,s=20)
                ax.text(p['x'],p['y'],p['z'],label+net['name'][3:],fontsize=7)
        conflicts=[c['cell'] for c in data.get('conflicts',[])]
        if conflicts:
            ax.scatter([p['x'] for p in conflicts],[p['y'] for p in conflicts],
                       [p['z'] for p in conflicts],color='red',marker='x',label='Conflicts')
        status='validated success' if data.get('success') else 'incomplete routing'
        ax.set(xlabel='Row (x)',ylabel='Column (y)',zlabel='Layer (z)',
               title=f"{data['algorithm']}: {args.route.name} — {status} (thick segments = VIAs)")
        ax.legend(loc='upper left',fontsize=8)
        fig.tight_layout(); fig.savefig(args.output_dir/'routing_example.png',dpi=170); plt.close(fig)
    print(f'Figures: {args.output_dir}; table: {report}')


if __name__ == '__main__':
    main()
