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
    parser.add_argument('--route', type=Path, default=ROOT/'output.json')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(args.csv.open()))
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
        fig.savefig(args.output_dir/f'{filename}.png',dpi=170)
        fig.savefig(args.output_dir/f'{filename}.svg')
        plt.close(fig)
    table = ['# Recorded benchmark measurements', '',
             'Generated from `results.csv`. Runtime is median / mean / sample standard deviation in ms. '
             'Quality is deterministic across verified repetitions. Failed runs retain partial-path quality; '
             'it is not a complete routing solution.', '',
             '| Dataset | Algorithm | Runs verified | Successful runs | Valid nets | Conflicts | Wire | VIAs | Cost | Passes | Expanded | Runtime ms (median / mean / SD) |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for dataset in datasets:
        for algorithm in ALGORITHMS:
            group = grouped[dataset,algorithm]
            verified = [r for r in group if r['output_verified']=='True']
            if not verified:
                table.append(f'| {dataset} | {algorithm} | 0 | 0 | — | — | — | — | — | — | — | execution failure |')
                continue
            r=verified[0]; times=[float(x['runtime_ms']) for x in verified]
            success=sum(x['success']=='True' for x in verified)
            sd=statistics.stdev(times) if len(times)>1 else 0
            table.append(f"| {dataset} | {algorithm} | {len(verified)}/{len(group)} | {success} | "
                         f"{r['routed_nets']}/{r['total_nets']} | {r['unresolved_conflicts']} | {r['wirelength']} | "
                         f"{r['via_count']} | {r['weighted_cost']} | {r['routing_passes']} | {r['nodes_expanded']} | "
                         f"{statistics.median(times):.6f} / {statistics.mean(times):.6f} / {sd:.6f} |")
    (args.csv.parent/'RESULTS.md').write_text('\n'.join(table)+'\n')
    # A static, shareable route view complements the interactive Plotly HTML.
    if args.route.exists():
        data=json.loads(args.route.read_text())
        fig=plt.figure(figsize=(10,8)); ax=fig.add_subplot(111,projection='3d')
        for i,net in enumerate(data['nets']):
            path=net['path']; color=plt.get_cmap('tab20')(i%20)
            if not path:
                continue
            ax.plot([p['x'] for p in path],[p['y'] for p in path],[p['z'] for p in path],color=color,label=net['name'])
            for a,b in zip(path,path[1:]):
                if a['z']!=b['z']:
                    ax.plot([a['x'],b['x']],[a['y'],b['y']],[a['z'],b['z']],color=color,linewidth=4)
            for p,label in [(net['source'],'S'),(net['target'],'T')]:
                ax.scatter(p['x'],p['y'],p['z'],color=color,s=20)
                ax.text(p['x'],p['y'],p['z'],label+net['name'][3:],fontsize=7)
        ax.set(xlabel='Row (x)',ylabel='Column (y)',zlabel='Layer (z)',title=f"{data['algorithm']}: chip_layout_hell (thick segments = VIAs)")
        ax.legend(loc='upper left',fontsize=8)
        fig.tight_layout(); fig.savefig(args.output_dir/'routing_example.png',dpi=170); plt.close(fig)
    print(f'Figures: {args.output_dir}; table: {args.csv.parent / "RESULTS.md"}')


if __name__ == '__main__':
    main()
