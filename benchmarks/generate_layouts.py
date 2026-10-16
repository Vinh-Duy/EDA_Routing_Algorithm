"""Generate deterministic educational fixtures; separate from benchmark execution."""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent / 'layouts'
SEED = 20261016


def write(name, grid):
    layers, rows, cols = len(grid), len(grid[0]), len(grid[0][0])
    text = f'{layers} {rows} {cols}\n' + '\n\n'.join(
        '\n'.join(' '.join(row) for row in layer) for layer in grid) + '\n'
    (ROOT / f'{name}.txt').write_text(text)


def main():
    ROOT.mkdir(exist_ok=True)
    write('simple_2d', [[['S1', '.', '.', '.', 'T1'], ['.'] * 5, ['.'] * 5]])
    write('obstacles_2d', [[['S1', '#', 'T1'], ['.', '#', '.'], ['.', '.', '.']]])
    write('multilayer', [[['S1']], [['.']], [['T1']]])
    write('impossible', [[['S1', '#', 'T1']]])
    write('impossible_overlap', [[['#', 'S1', '#'], ['S2', '.', 'T2'], ['#', 'T1', '#']]])
    # Net1 initially takes row 3; Net2 can only enter its target from (0,3,3).
    # History makes Net1 use the longer bottom detour on a subsequent pass.
    g = [[['.'] * 7 for _ in range(7)]]
    for x, y, value in [(3,0,'S1'),(3,6,'T1'),(0,3,'S2'),(4,3,'T2'),
                         (4,2,'#'),(4,4,'#'),(5,3,'#')]:
        g[0][x][y] = value
    for x in range(3):
        g[0][x][2] = g[0][x][4] = '#'
    write('congestion', g)
    # Same-layer detour: 10 planar steps. Upper shortcut: 6 planar + 2 VIAs.
    g = [[['.'] * 7 for _ in range(5)] for _ in range(2)]
    g[0][2][0], g[0][2][6] = 'S1', 'T1'
    for x in range(1, 4):
        g[0][x][3] = '#'
    write('via_sensitive', g)
    rng = random.Random(SEED)
    g = [[['#' if rng.random() < 0.18 else '.' for _ in range(40)]
          for _ in range(40)] for _ in range(4)]
    for n in range(1, 13):
        z = (n - 1) % 4
        x = 2 + 3 * (n - 1)
        g[z][x][0], g[(z+2)%4][39-x][39] = f'S{n}', f'T{n}'
    write('stress_seeded', g)


if __name__ == '__main__':
    main()
