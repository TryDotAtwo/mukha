"""Synthetic controls only, no fitting of deposited means."""
import copy
import json
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import run_pang_temporal_transfer as m


class TemporalControls(unittest.TestCase):
    def setUp(self):
        self.t = np.arange(63)/120
        self.c = np.sin(17*self.t)+.2*np.cos(43*self.t)

    def test_constant_and_rank(self):
        c = np.ones(63)*.7
        np.testing.assert_array_equal(m.memory_state(self.t, c, .07), c)
        fit = m.fit_training(self.t, c, 2*c)
        self.assertEqual(fit['selected']['model'], 'H0')
        self.assertAlmostEqual(fit['H0']['a'], 2.)
        self.assertTrue(all(p['rank'] == 1 and p['status'] == 'nonidentifiable' for p in fit['profiles']))
        self.assertEqual(len(fit['profiles']), 32)

    def test_ramp_exact_state(self):
        t = np.r_[0., .002, .01, .03, .11, .19]
        c = .4+2*t; tau = .04
        expected = c-2*tau*(1-np.exp(-t/tau))
        np.testing.assert_allclose(m.memory_state(t, c, tau), expected, atol=1e-15, rtol=1e-13)

    def test_pure_gain_nested_and_roundoff(self):
        fit = m.fit_training(self.t, self.c, 1.7*self.c)
        self.assertEqual(fit['selected']['model'], 'H0')
        self.assertAlmostEqual(fit['H0']['a'], 1.7)
        scored = m.score_transfer(self.t, self.c, 1.7*self.c, fit)
        self.assertEqual(scored['outcome'], 'numerically_unresolved')

    def test_memory_recovery_and_no_transfer_tuning(self):
        tau = np.geomspace(1/120, .25, 32)[13]
        target = 1.2*self.c+.6*(self.c-m.memory_state(self.t, self.c, tau))
        fit = m.fit_training(self.t, self.c, target)
        self.assertEqual(fit['selected']['model'], 'H1')
        self.assertAlmostEqual(fit['selected']['a'], 1.2, places=8)
        self.assertAlmostEqual(fit['selected']['b'], .6, places=8)
        frozen = copy.deepcopy(fit)
        first = m.score_transfer(self.t, self.c, target, fit)
        changed = m.score_transfer(self.t, self.c, target+100, fit)
        self.assertEqual(fit, frozen)
        self.assertEqual(first['models']['H1_selected']['prediction'], changed['models']['H1_selected']['prediction'])
        self.assertNotEqual(first['models']['H1_selected']['residual'], changed['models']['H1_selected']['residual'])

    def test_zero_and_invalid(self):
        with self.assertRaisesRegex(ValueError, 'zero_training_control_energy'):
            m.fit_training(self.t, self.c*0, self.c)
        fit = m.fit_training(self.t, self.c, self.c)
        result = m.score_transfer(self.t, self.c*0, self.c, fit)
        self.assertEqual(result['status'], 'zero_control_energy')
        self.assertIsNone(result['error_improvement'])
        for t, c in [(self.t[::-1], self.c), (self.t, self.c*float('nan'))]:
            with self.assertRaises(ValueError):
                m.fit_training(t, c, self.c)
        for tau in (0., -1., float('inf')):
            with self.assertRaises(ValueError):
                m.memory_state(self.t, self.c, tau)

    def test_positive_gain_boundary(self):
        fit = m.fit_training(self.t, self.c, -self.c)
        self.assertEqual(fit['H0']['a'], 0.)
        self.assertTrue(all(p['a'] >= 0 for p in fit['profiles']))
        json.dumps(fit, allow_nan=False)

    def test_complete_unique_typed_keys(self):
        rows = [dict(cell=c, level=l, row=r) for c in ('L1','L2') for l,r in m.TESTS]
        m.validate_keys(rows[::-1])
        for bad in (rows[:-1], rows+[rows[0]], rows[:-1]+[rows[0]],
                    rows[:-1]+[dict(cell='L2', level='lowLum', row=True)]):
            with self.assertRaisesRegex(ValueError, 'transfer_key_mismatch'):
                m.validate_keys(bad)


if __name__ == '__main__':
    unittest.main()
