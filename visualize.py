"""Plot ordered JSON routes, pins, obstacles, conflicts, and explicit VIA segments."""
import argparse
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.colors import qualitative


def build_figure(data):
    fig = go.Figure()
    for idx, net in enumerate(data.get('nets', [])):
        path = net.get('path', [])  # Source-to-target order; never mutate input.
        color = qualitative.Dark24[idx % len(qualitative.Dark24)]
        name = net['name']
        tree_edges = net.get('tree_edges', [])
        status = 'valid' if net.get('valid', bool(path or tree_edges)) else ('unrouted' if not path and not tree_edges else 'conflicted/invalid')
        coords = {axis: [p[axis] for p in path] for axis in ('x','y','z')}
        fig.add_trace(go.Scatter3d(**coords, mode='lines', name=f'{name} ({status})',
                                  line=dict(color=color, width=5, dash='solid' if status=='valid' else 'dash')))
        if tree_edges:
            # One trace with None separators renders each shared tree edge once.
            x, y, z = [], [], []
            for a, b in tree_edges:
                x.extend([a['x'], b['x'], None]); y.extend([a['y'], b['y'], None]); z.extend([a['z'], b['z'], None])
                if a['z'] != b['z']:
                    fig.add_trace(go.Scatter3d(**{k:[a[k],b[k]] for k in ('x','y','z')},
                        mode='lines+markers', name=f'{name} VIA', legendgroup=name, showlegend=False,
                        line=dict(color=color,width=10), marker=dict(size=5,symbol='diamond',color=color),
                        hovertemplate=f'{name} VIA<br>row=%{{x}}, col=%{{y}}, layer=%{{z}}<extra></extra>'))
            fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode='lines', name=f'{name} shared tree',
                                      legendgroup=name, line=dict(color=color,width=5,dash='solid' if status=='valid' else 'dash')))
        for a,b in zip(path,path[1:]):
            if a['z'] != b['z']:
                fig.add_trace(go.Scatter3d(**{k:[a[k],b[k]] for k in ('x','y','z')},
                    mode='lines+markers', name=f'{name} VIA', legendgroup=name, showlegend=False,
                    line=dict(color=color,width=10), marker=dict(size=5,symbol='diamond',color=color),
                    hovertemplate=f'{name} VIA<br>row=%{{x}}, col=%{{y}}, layer=%{{z}}<extra></extra>'))
        terminals = net.get('terminals', [])
        if terminals:
            labels = ['S', 'T'] + ['P'] * max(0, len(terminals)-2)
            pins = list(zip(terminals, labels))
        else:
            source = net.get('source', path[0] if path else None)
            target = net.get('target', path[-1] if path else None)
            pins = [(p,label) for p,label in [(source,'S'),(target,'T')] if p is not None]
        if pins:
            fig.add_trace(go.Scatter3d(**{k:[p[k] for p,_ in pins] for k in ('x','y','z')},
                mode='markers+text', text=[label+name.removeprefix('Net') for _,label in pins],
                textposition='top center', marker=dict(size=6,color=color), showlegend=False, name=name+' pins'))
    for key,color,symbol,size in [('obstacles','#777777','square',3),('conflicts','#ff0000','x',9)]:
        points = [c['cell'] for c in data.get(key,[])] if key=='conflicts' else data.get(key,[])
        if points:
            fig.add_trace(go.Scatter3d(**{k:[p[k] for p in points] for k in ('x','y','z')},
                mode='markers', name=key.title(), marker=dict(size=size,color=color,symbol=symbol,opacity=0.5)))
    status = 'validated success' if data.get('success') else 'incomplete / legacy output'
    fig.update_layout(title=f'Grid routing — {status}',
        scene=dict(xaxis=dict(title='Row (x)',dtick=1), yaxis=dict(title='Column (y)',dtick=1),
                   zaxis=dict(title='Layer (z)',dtick=1)), margin=dict(l=0,r=0,b=0,t=45))
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='output.json')
    parser.add_argument('--html', help='Write a self-contained interactive HTML figure')
    parser.add_argument('--no-show', action='store_true', help='Do not open a browser')
    args = parser.parse_args()
    fig = build_figure(json.loads(Path(args.input).read_text()))
    if args.html:
        fig.write_html(args.html, include_plotlyjs=True)
    if not args.no_show:
        fig.show()


if __name__ == '__main__':
    main()
