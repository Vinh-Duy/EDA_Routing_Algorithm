import json
import plotly.graph_objects as go

def main():
    with open('output.json', 'r') as f:
        data = json.load(f)

    fig = go.Figure()
    colors = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#00FFFF', '#FFA500']

    for idx, net in enumerate(data['nets']):
        name = net['name']
        path = net['path']
        
        path.reverse() 
        
        x_vals = [p['x'] for p in path]
        y_vals = [p['y'] for p in path]
        z_vals = [p['z'] for p in path]
        
        color = colors[idx % len(colors)]

        fig.add_trace(go.Scatter3d(
            x=x_vals, y=y_vals, z=z_vals,
            mode='lines+markers',
            name=name,
            line=dict(color=color, width=6),
            marker=dict(size=4, color=color)
        ))

        fig.add_trace(go.Scatter3d(
            x=[x_vals[0], x_vals[-1]],
            y=[y_vals[0], y_vals[-1]],
            z=[z_vals[0], z_vals[-1]],
            mode='text',
            text=[f'S{name[3:]}', f'T{name[3:]}'],
            textposition="top center",
            textfont=dict(size=14, color=color),
            showlegend=False
        ))

    fig.update_layout(
        title='3D VLSI Routing Visualization',
        scene=dict(
            xaxis=dict(title='Rows (X)', dtick=1),
            yaxis=dict(title='Cols (Y)', dtick=1),
            zaxis=dict(title='Layers (Z)', dtick=1),
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    fig.show()

if __name__ == "__main__":
    main()