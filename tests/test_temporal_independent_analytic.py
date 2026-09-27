"""Independent synthetic-only reviewer controls; no MAT inputs or real fits.

Set PANG_TEMPORAL_RUNNER to exact reviewed runner. Analytic targets do not call
its state updater. All amplitudes/time grids here are synthetic.
"""
import importlib.util
import math
import os
import unittest

import numpy as np

RUNNER = os.environ.get('PANG_TEMPORAL_RUNNER')
if RUNNER:
    spec = importlib.util.spec_from_file_location('reviewed_temporal', RUNNER)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)


@unittest.skipUnless(RUNNER, 'set PANG_TEMPORAL_RUNNER')
class AnalyticControls(unittest.TestCase):
    def setUp(self):
        self.t = np.linspace(0., .25, 63)
        self.tau = float(np.geomspace(np.median(np.diff(self.t)), .25, 32)[12])

    @staticmethod
    def ramp(t, tau, offset, slope):
        x = t-t[0]
        c = offset+slope*x
        r = slope*tau*(-np.expm1(-x/tau))
        return c, r

    def close(self, actual, expected, atol=1e-11):
        np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=atol)

    def test_frozen_policies(self):
        self.assertEqual(runner.RCOND, 1e-12)
        self.assertEqual((runner.ATOL, runner.RTOL), (1e-12, 1e-10))
        self.assertEqual(runner.tolerance(2.), 1e-12+2e-10)

    def test_ramp_exact_irregular_and_sign(self):
        t = np.array([0., .003, .019, .02, .07, .13, .25])
        for offset, slope in ((.4, 3.), (-.7, -2.), (0., 0.)):
            c, r = self.ramp(t, self.tau, offset, slope)
            self.close(runner.memory_state(t, c, self.tau), c-r)

    def test_pure_gain_and_three_transfers(self):
        c, _ = self.ramp(self.t, self.tau, .2, 3.)
        fit = runner.fit_training(self.t, c, 1.7*c)
        self.assertEqual(fit['selected']['model'], 'H0')
        self.close(fit['selected']['a'], 1.7)
        for offset, slope in ((-.3,-2.),(.1,1.),(-.2,-.5)):
            c, _ = self.ramp(self.t, self.tau, offset, slope)
            score = runner.score_transfer(self.t, c, 1.7*c, fit)
            self.assertEqual(score['outcome'], 'numerically_unresolved')
            self.close(score['models']['H0']['prediction'], 1.7*c)

    def test_memory_coefficients_and_frozen_transfers(self):
        c, r = self.ramp(self.t, self.tau, .2, 3.)
        fit = runner.fit_training(self.t, c, .8*c+1.3*r)
        selected = fit['selected']
        self.assertEqual(selected['model'], 'H1')
        self.assertEqual(selected['index'], 12)
        self.close([selected['a'],selected['b'],selected['tau']], [.8,1.3,self.tau])
        for offset, slope in ((-.3,-2.),(.1,1.),(-.2,-.5)):
            c, r = self.ramp(self.t, self.tau, offset, slope)
            score = runner.score_transfer(self.t,c,.8*c+1.3*r,fit)
            self.assertEqual(score['outcome'], 'improved')
            self.close(score['models']['H1_selected']['prediction'], .8*c+1.3*r)
            self.assertEqual(score['models']['H1_selected']['parameters'], selected)

    def test_constant_rank_and_minimum_norm(self):
        c = np.full(63, .7)
        fit = runner.fit_training(self.t,c,2*c)
        self.assertEqual(fit['selected']['model'],'H0')
        for p in fit['profiles']:
            self.assertEqual(p['rank'],1)
            self.assertEqual(p['status'],'nonidentifiable')
            self.close(p['unconstrained_minimum_norm'],[2.,0.])
            self.assertIsNone(p['column_correlation'])
        self.assertIn('nonidentifiable_candidates_excluded',fit['warnings'])

    def test_nearly_constant_rank(self):
        c = 1.+1e-14*self.t
        fit = runner.fit_training(self.t,c,2*c)
        self.assertEqual(fit['selected']['model'],'H0')
        for p in fit['profiles']:
            s = p['singular_values']
            self.assertEqual(p['rank'],sum(v>1e-12*s[0] for v in s))
            self.assertEqual(p['status'],'nonidentifiable')

    def test_zero_training_and_transfer(self):
        with self.assertRaisesRegex(ValueError,'zero_training_control_energy'):
            runner.fit_training(self.t,np.zeros(63),np.ones(63))
        c=np.ones(63)
        fit=runner.fit_training(self.t,c,c)
        score=runner.score_transfer(self.t,np.zeros(63),np.ones(63),fit)
        self.assertEqual(score['status'],'zero_control_energy')
        self.assertIsNone(score['error_improvement'])
        for model in score['models'].values():
            self.assertIsNone(model['normalized_error'])
            self.close(model['sse'],.25)

    def test_constrained_a_boundary(self):
        c,r=self.ramp(self.t,self.tau,.2,3.)
        y=-c+.5*r
        fit=runner.fit_training(self.t,c,y)
        p=fit['profiles'][12]
        self.assertLess(p['unconstrained_minimum_norm'][0],0)
        self.assertEqual(p['a'],0.)
        # Independent trapezoid sum, not runner.weights/error or state.
        numerator=math.fsum(float(d*(u+v)/2) for d,u,v in zip(np.diff(self.t),(r*y)[:-1],(r*y)[1:]))
        denominator=math.fsum(float(d*(u+v)/2) for d,u,v in zip(np.diff(self.t),(r*r)[:-1],(r*r)[1:]))
        self.close(p['b'],numerator/denominator)

    def test_numerical_outcome_deadband(self):
        c=np.ones(63); y=np.ones(63)
        eta=1e-12+1e-10  # H0 a=0 has E0=1 exactly.
        for delta,outcome in ((eta/2,'numerically_unresolved'),(2*eta,'improved'),(-2*eta,'worse')):
            h0=dict(model='H0',a=0.,b=0.,tau=None)
            other=dict(model='H0',a=1-math.sqrt(1-delta),b=0.,tau=None)
            score=runner.score_transfer(self.t,c,y,dict(H0=h0,selected=other))
            self.assertEqual(score['outcome'],outcome)


if __name__ == '__main__':
    unittest.main()
