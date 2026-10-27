"""Tiny edge-subset reference for a one-net rectilinear Steiner instance."""
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def tiny_exact_cost(layout):
    """Enumerate legal edge subsets; independent of production search code."""
    lines=Path(layout).read_text().splitlines()
    rows,cols=map(int,lines[0].split())
    cells=[token for line in lines[1:] for token in line.split()]
    terminals=[]
    for x in range(rows):
        for y in range(cols):
            token=cells[x*cols+y]
            if token.startswith(('S','T','P')):
                terminals.append((x,y))
    edges=[]
    for x in range(rows):
        for y in range(cols):
            if cells[x*cols+y]=='#':
                continue
            for dx,dy in ((1,0),(0,1)):
                q=(x+dx,y+dy)
                if q[0]<rows and q[1]<cols and cells[q[0]*cols+q[1]]!='#':
                    edges.append(((x,y),q))
    best=None
    for mask in range(1<<len(edges)):
        cost=mask.bit_count()
        if best is not None and cost>=best:
            continue
        parent={}
        def find(v):
            parent.setdefault(v,v)
            while parent[v]!=v:
                parent[v]=parent[parent[v]]
                v=parent[v]
            return v
        for i,(a,b) in enumerate(edges):
            if mask>>i&1:
                ra,rb=find(a),find(b)
                parent[ra]=rb
        if all(find(t)==find(terminals[0]) for t in terminals):
            best=cost
    return best


class MultiTerminalReferenceTests(unittest.TestCase):
    def test_five_terminal_grid_matches_independent_exact_tiny_optimum(self):
        layout=ROOT/'benchmarks/multiterminal/layouts/four_terminal_branch.txt'
        optimum=tiny_exact_cost(layout)
        self.assertEqual(optimum,4)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'route.json'
            for algorithm in ('astar','dijkstra','bfs'):
                proc=subprocess.run([str(ROOT/'router'),'--input',str(layout),'--algorithm',algorithm,
                                     '--output',str(output)],capture_output=True,text=True,cwd=ROOT)
                self.assertEqual(proc.returncode,0,proc.stderr)
                data=json.loads(output.read_text())
                self.assertEqual(data['metrics']['weighted_cost'],optimum)


if __name__=='__main__':
    unittest.main()
