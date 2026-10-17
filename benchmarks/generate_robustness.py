"""Five preselected obstacle seeds using the original stress-case dimensions/pins."""
import argparse
import hashlib
import json
from pathlib import Path
import random

SEEDS = (20261017,20261018,20261019,20261020,20261021)


def layout_text(seed):
    rng=random.Random(seed)
    grid=[[['#' if rng.random()<0.18 else '.' for _ in range(40)]
           for _ in range(40)] for _ in range(4)]
    for n in range(1,13):
        z=(n-1)%4;x=2+3*(n-1)
        grid[z][x][0]=f'S{n}'
        grid[(z+2)%4][39-x][39]=f'T{n}'
    return '4 40 40\n'+'\n\n'.join('\n'.join(' '.join(row) for row in layer) for layer in grid)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent/'robustness/layouts')
    args=parser.parse_args()
    contents={f'stress_{seed}.txt':layout_text(seed) for seed in SEEDS}
    manifest=dict(seeds=SEEDS,dimensions=[4,40,40],nets=12,obstacle_probability=0.18,
                  pin_policy='Original stress_seeded coordinates; pins override obstacles',
                  sha256={name:hashlib.sha256(text.encode()).hexdigest() for name,text in contents.items()})
    contents['generation.json']=json.dumps(manifest,indent=2)+'\n'
    for name,text in contents.items():
        path=args.output_dir/name
        if path.exists() and path.read_text()!=text:
            parser.error(f'Refusing to overwrite different fixture: {path}')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for name,text in contents.items():
        (args.output_dir/name).write_text(text)
    print(f'Generated {len(SEEDS)} layouts in {args.output_dir}')


if __name__ == '__main__':
    main()
