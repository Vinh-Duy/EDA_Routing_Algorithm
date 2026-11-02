import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks'))
from run_steiner_ordering import compare_cost


class SteinerEvaluationTests(unittest.TestCase):
    def test_gap_classification_handles_zero_optimum_and_failure(self):
        zero = {'status': 'optimal', 'optimal_cost': 0}
        self.assertEqual(compare_cost(zero, {'metrics': {'weighted_cost': 0}}, True),
                         ('optimal', 0, None))
        self.assertEqual(compare_cost({'status': 'optimal', 'optimal_cost': 4}, {}, False),
                         ('router_failure', None, None))
        self.assertEqual(compare_cost({'status': 'infeasible'}, {}, False),
                         ('proven_infeasible', None, None))
        self.assertEqual(compare_cost({'status': 'unknown'}, {}, True),
                         ('oracle_resource_limited', None, None))


if __name__ == '__main__':
    unittest.main()
