"""Determinism and bound checks for the held-out corpus generator."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks'))
from generate_steiner_corpus import make_candidate
from validate_output import read_layout_with_extras


class SteinerCorpusGeneratorTests(unittest.TestCase):
    def test_seeded_candidate_is_reproducible_and_within_oracle_bounds(self):
        first = make_candidate(202611010017, 6, 3, 'chokepoint', 'branch_heavy')
        second = make_candidate(202611010017, 6, 3, 'chokepoint', 'branch_heavy')
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'layout.txt'
            path.write_text(first)
            dimensions, cells, sources, targets, extras = read_layout_with_extras(path)
        layers, rows, cols = dimensions
        self.assertLessEqual(layers * rows * cols, 512)
        net = next(iter(sources))
        terminals = [sources[net], targets[net], *extras[net]]
        self.assertEqual(len(terminals), 6)
        self.assertEqual(len(set(terminals)), 6)
        self.assertTrue(all(cells[point] != '#' for point in terminals))


if __name__ == '__main__':
    unittest.main()
