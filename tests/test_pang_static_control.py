"""Synthetic only: no deposited response is fitted."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import run_pang_static_control as m


def archived(c):
    model = dict(prediction=c.tolist(), normalized_error=.25, parameters={'model':'H0','a':1.})
    return {'models': {'H0': copy.deepcopy(model), 'H1_selected': copy.deepcopy(model)}}


class StaticControls(unittest.TestCase):
    def setUp(self):
        self.t = np.linspace(0, .5, 63)
        self.c = np.sin(15*self.t)+.25*np.cos(43*self.t)
        self.y = 1.2*self.c+.4*m.basis(self.c, max(abs(self.c)))

    def test_exact_cubic_and_training_scale(self):
        fit = m.fit_static(self.t, self.c, self.y)
        self.assertEqual(fit['rank'], 2)
        self.assertEqual(fit['selected_model'], 'Hs')
        self.assertAlmostEqual(fit['selected']['a'], 1.2)
        self.assertAlmostEqual(fit['selected']['d'], .4)
        self.assertEqual(fit['scale'], max(abs(self.c)))
        self.assertEqual([p['kind'] for p in fit['candidates']], ['H0','boundary','interior'])

    def test_rank_failure_null_cubic_separate_H0(self):
        c = np.resize(np.array([-1., 0., 1.]), 63)
        fit = m.fit_static(self.t, c, 2*c)
        self.assertEqual(fit['rank'], 1)
        self.assertEqual(fit['status'], 'rank_deficient')
        self.assertIsNone(fit['selected'])
        base = archived(c); original = copy.deepcopy(base)
        result = m.score_static(self.t, c, 2*c, fit, base)
        self.assertIsNone(result['prediction']); self.assertIsNone(result['Es'])
        self.assertEqual(result['fallback_H0'], base['models']['H0'])
        self.assertEqual(result['versus_H1']['outcome'], 'undefined')
        self.assertEqual(base, original)
        self.assertIsNot(result['fallback_H0'], base['models']['H0'])

    def test_full_rank_nested_H0_identity(self):
        fit = m.fit_static(self.t, self.c, 1.7*self.c)
        self.assertEqual(fit['rank'], 2)
        self.assertEqual(fit['selected_model'], 'H0')
        self.assertEqual(fit['status'], 'no_resolved_cubic_increment_on_training')
        result = m.score_static(self.t, self.c, self.c, fit, archived(self.c))
        self.assertEqual(result['status'], 'ok')
        self.assertIsNone(result['fallback_H0'])
        self.assertIsNotNone(result['Es'])

    def test_boundary_solution(self):
        fit = m.fit_static(self.t, self.c, -self.c+3*m.basis(self.c,max(abs(self.c))))
        interior = fit['candidates'][2]
        self.assertLess(interior['a'], 0.)
        self.assertFalse(interior['feasible'])
        self.assertEqual(fit['selected']['kind'], 'boundary')
        self.assertEqual(fit['selected']['a'], 0.)

    def test_signed_and_magnitude_support_time_not_energy(self):
        training = dict(scale=2., training_min=0., training_max=2.)
        t = np.array([0., 1., 3.]); c = np.array([-1., 1., 3.])
        result = m.support(t, c, training)
        self.assertAlmostEqual(result['outside_signed_time_fraction'], .5)
        self.assertAlmostEqual(result['outside_magnitude_time_fraction'], 1/3)
        self.assertEqual(result['max_abs_over_training_scale'], 1.5)
        # Endpoint inclusivity: exact signed/absolute boundary is not outside.
        boundary = m.support(t, np.array([0., 1., 2.]), training)
        self.assertEqual(boundary['outside_signed_time_fraction'], 0.)

    def test_frozen_scale_and_no_target_leakage(self):
        fit = m.fit_static(self.t, self.c, self.y)
        original = copy.deepcopy(fit)
        base = archived(self.c)
        a = m.score_static(self.t, self.c*3, self.y, fit, base)
        b = m.score_static(self.t, self.c*3, self.y+10, fit, base)
        self.assertEqual(fit, original)
        self.assertEqual(a['prediction'], b['prediction'])
        self.assertNotEqual(a['residual'], b['residual'])
        self.assertAlmostEqual(a['support']['max_abs_over_training_scale'], 3.)

    def test_invalid_and_deadband(self):
        with self.assertRaisesRegex(ValueError,'zero_training_control_energy'):
            m.fit_static(self.t, self.c*0, self.y)
        fit = m.fit_static(self.t, self.c, self.y)
        result = m.score_static(self.t,self.c*0,self.y,fit,archived(self.c))
        self.assertEqual(result['status'], 'zero_transfer_control_energy')
        self.assertIsNone(result['Es'])
        result = m.score_static(self.t,self.c,self.y*np.nan,fit,archived(self.c))
        self.assertEqual(result['status'], 'nonfinite_arithmetic')
        self.assertIsNone(result['Es'])
        self.assertEqual(m.compare_score(1., 1.+1e-12)['outcome'], 'numerically_unresolved')
        self.assertEqual(m.compare_score(1., 1.1)['outcome'], 'worse')
        self.assertEqual(m.compare_score(1., .9)['outcome'], 'improved')
        json.dumps(result, allow_nan=False)

    def test_dispatch_six_keys_and_heldout_mutation(self):
        data={name:(self.t,np.array([self.c,self.c*.8])) for name in m.HASHES}
        base=dict(training={c:{'H0':{'a':1.}} for c in ('L1','L2')},
                  transfers=[dict(cell=c,level=l,row=r,**archived(self.c))
                             for c in ('L1','L2') for l,r in m.TESTS],
                  summary={'all_six_improved':False})
        for name in data:
            if '_CDM_' in name:
                data[name]=(self.t,np.array([self.y,self.y*.8]))
        untouched=copy.deepcopy(base)
        with patch.object(m,'fit_static',wraps=m.fit_static) as spy:
            first=m.analyze(data,base)
            self.assertEqual(spy.call_count,2)
            for call in spy.call_args_list:
                np.testing.assert_array_equal(call.args[2], self.y)
        changed=copy.deepcopy(data)
        for cell in ('L1','L2'):
            changed[f'{cell}_CDM_highLum.mat'][1][1] += 10
            changed[f'{cell}_CDM_lowLum.mat'][1][:] += 20
        second=m.analyze(changed,base)
        self.assertEqual(first['training'],second['training'])
        self.assertEqual(len(first['transfers']),6)
        for a,b in zip(first['transfers'],second['transfers']):
            self.assertEqual(a['prediction'],b['prediction'])
        self.assertEqual(base,untouched)
        self.assertIs(first['summary']['prior_temporal003_all_six_improved'],False)

    def test_archive_mutation_rejected_before_fit(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'invalid.tar.gz'; path.write_bytes(b'synthetic wrong bytes')
            with patch.object(m,'fit_static',side_effect=AssertionError('fit must not run')):
                with self.assertRaisesRegex(ValueError,'baseline_archive_hash_mismatch'):
                    m.read_archive(path)


if __name__ == '__main__':
    unittest.main()
