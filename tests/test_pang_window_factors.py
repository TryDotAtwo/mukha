"""Synthetic-only controls; no archived curve factorial evaluation."""
import sys
import copy
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from run_pang_window_factors import evaluate_cube, contrasts, invariants, grid, integrate, CONDITIONS, analyze_curve, compare
import run_pang_window_factors as runner


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

    def test_missing_crossing_and_typed_row(self):
        t = np.arange(63, dtype=float)/120
        y = np.ones(63)
        for row in (True, 1.5, 2):
            with self.assertRaisesRegex(ValueError, 'invalid_curve_domain'):
                analyze_curve(t, y, row, {})
        with self.assertRaisesRegex(ValueError, 'missing_crossing'):
            analyze_curve(t, y, 1, {})

    def test_nonfinite_comparison_serializable(self):
        import json
        value = compare(float('inf'), 0.)
        self.assertFalse(value['passed'])
        json.dumps(value, allow_nan=False)

    def test_cube_keys_before_aggregation(self):
        original = self.cube()
        malformed = [original + [copy.deepcopy(original[0])], original[:-1]]
        for label in ('HHH', 'XYZ', None, True, [], 1):
            cells = copy.deepcopy(original)
            cells[-1]['condition'] = label
            malformed.append(cells)
        cells = copy.deepcopy(original)
        del cells[-1]['condition']
        malformed.append(cells)
        for helper in (contrasts, invariants, runner.validate_cells):
            for cells in malformed:
                with self.subTest(helper=helper.__name__, cells=cells):
                    with self.assertRaisesRegex(ValueError, '^condition_key_mismatch$'):
                        helper(cells)
        self.assertEqual(contrasts(original), contrasts(original[::-1]))
        self.assertEqual(invariants(original), invariants(original[::-1]))

    def test_analyze_rejects_boundary_drift_and_duplicate(self):
        # Astra3's independent synthetic reproducer; not an archived mean.
        t = np.arange(63, dtype=float)/120
        y = np.zeros(63)
        y[2:6] = [2, 1, -1, -1]
        dt = float(np.median(np.diff(t)))
        reference = {'supplied_peak_frame': 3, 'sampled': {
            'frame_zero1': 2, 'frame_zero2': 5, 'end_phase2': 30,
            'area1_percent_df_f_seconds': 2.5*dt*100,
            'area2_percent_df_f_seconds': -1.5*dt*100},
            'historical_area1_df_f_seconds': 1.75/120,
            'historical_area2_df_f_seconds': -1.75/120,
            'historical_negative_signed_ratio': 1.,
            'sampled_negative_signed_ratio': .6}
        baseline = analyze_curve(t, y, 1, reference)
        self.assertEqual(baseline['status'], 'ok')
        for index, condition in enumerate(CONDITIONS):
            for field in ('start', 'end', 'split'):
                for replacement in (None, True, float('nan'), float('inf'),
                                    baseline['cells'][index][field]+.001,
                                    float(np.nextafter(baseline['cells'][index][field], np.inf))):
                    cells = copy.deepcopy(baseline['cells'])
                    cells[index][field] = replacement
                    with self.subTest(condition=condition, field=field, value=replacement):
                        with patch.object(runner, 'evaluate_cube', return_value=cells):
                            with self.assertRaisesRegex(ValueError, '^frozen_boundary_mismatch:'):
                                analyze_curve(t, y, 1, reference)
        malformed = copy.deepcopy(baseline['cells'])
        malformed[-1] = copy.deepcopy(malformed[0])
        with patch.object(runner, 'evaluate_cube', return_value=malformed):
            with self.assertRaisesRegex(ValueError, '^condition_key_mismatch$'):
                analyze_curve(t, y, 1, reference)
        with patch.object(runner, 'evaluate_cube', return_value=baseline['cells'][::-1]):
            self.assertEqual(analyze_curve(t, y, 1, reference)['status'], 'ok')


if __name__ == '__main__':
    unittest.main()
