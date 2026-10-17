"""Record the compiler invocation and inputs for the executable built by Make."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--flags', required=True)
    args = parser.parse_args()
    compiler = shlex.split(args.compiler)
    version = subprocess.run(compiler+['--version'], capture_output=True, text=True, check=True)
    record = dict(command=compiler+shlex.split(args.flags)+['src/main.cpp','-o','router'],
                  compiler_version=version.stdout.strip(), flags=args.flags,
                  executable_sha256=digest(ROOT/'router'),
                  source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'src').glob('*'))})
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/router-build.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__ == '__main__':
    main()
