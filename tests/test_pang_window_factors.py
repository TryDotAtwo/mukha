"""Synthetic-only controls; no archived curve factorial evaluation."""
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from run_pang_window_factors import evaluate_cube, contrasts, invariants, grid, integrate, CONDITIONS


class FactorControls(unittest.TestCase):
    def setUp(self):
        self.t = np.array([0., 1., 2., 3., 4., 5.])
        self.y = np.array([0., 2., 0., -2., 0., 2.])
        self.levels = [{'H': 0., 'S': .5}, {'H': 4., 'S': 5.}, {'H': 2., 'S': 2.5}]

    def cube(self):
        return evaluate_cube(self.t, self.y, 1., self.levels)

    def test_analytic_integrals(self):
        self.assertEqual(integrate(self.t, self.y, 0., 2.), 2.)
        self.assertEqual(integrate(self.t, self.y, .5, 2.5), 1.5)
        self.assertEqual(integrate(self.t, self.y, 2., 4.), -2.)

    def test_isolation_and_conservation(self):
        cells = self.cube()
        self.assertEqual({c['condition'] for c in cells}, set(CONDITIONS))
        self.assertEqual(len(cells), 8)
        self.assertTrue(all(c['conservation']['passed'] for c in cells))
        self.assertTrue(all(c['passed'] for c in invariants(cells)))
        self.assertEqual(cells[0]['Q'], 1.)

    def test_interaction_expansion(self):
        result = contrasts(self.cube())
        for metric in result.values():
            self.assertAlmostEqual(metric['baseline_expansion_residual'], 0.)
        self.assertNotEqual(result['Q']['terms']['OEC']['baseline'], 0.)
        self.assertEqual(result['A1']['terms']['E']['averaged'], 0.)
        self.assertEqual(result['A2']['terms']['O']['averaged'], 0.)

    def test_coincident_split(self):
        self.levels[2]['S'] = 2.
        for metric in contrasts(self.cube()).values():
            self.assertEqual(metric['terms']['C']['averaged'], 0.)

    def test_zero_and_small_denominator(self):
        cells = evaluate_cube(self.t, self.y*0, 1., self.levels)
        self.assertTrue(all(c['status'] == 'zero_first_area' and c['Q'] is None for c in cells))
        tiny = evaluate_cube(self.t, self.y*1e-100, 1., self.levels)
        self.assertTrue(all(c['status'] == 'ok' for c in tiny))
        self.assertAlmostEqual(tiny[0]['Q'], 1.)

    def test_invalid_retained(self):
        self.levels[0]['S'] = 3.
        cells = self.cube()
        self.assertEqual(len(cells), 8)
        self.assertEqual(sum(c['status'] == 'invalid_interval' for c in cells), 4)
        self.assertEqual(contrasts(cells)['Q']['status'], 'undefined_metric')

    def test_grid_guards(self):
        for t, y in [([0, 0], [1, 2]), ([0, 1], [1, float('nan')]), ([1, 0], [1, 2])]:
            with self.assertRaises(ValueError):
                grid(t, y)


if __name__ == '__main__':
    unittest.main()
