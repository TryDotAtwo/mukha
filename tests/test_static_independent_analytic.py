"""Independent polynomial/rational controls, synthetic data only.

PANG_STATIC_RUNNER points to exact reviewed implementation, imported as subject
under test, never used to generate expected values or fit an oracle model.
"""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import unittest

import numpy as np

TARGET=os.environ.get('PANG_STATIC_RUNNER')
if TARGET:
    sys.path.insert(0,str(Path(TARGET).parent))
    spec=importlib.util.spec_from_file_location('static_subject',TARGET)
    subject=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)


@unittest.skipUnless(TARGET,'set PANG_STATIC_RUNNER')
class IndependentCubic(unittest.TestCase):
    def setUp(self):
        self.t=np.array([0.,1.,3.,4.])
        self.c=np.array([-2.,-1.,1.,2.])
        self.y=2*self.c+3*self.c**3/4
        # Synthetic archived objects are markers, not refitted baselines.
        self.archived={'models':{'H0':{'prediction':[9.,8.,7.], 'normalized_error':4.,
                                      'parameters':{'model':'H0','a':2.}},
                                  'H1_selected':{'prediction':[6.,5.,4.], 'normalized_error':5.}}}

    def close(self,a,b):
        np.testing.assert_allclose(a,b,atol=1e-12,rtol=1e-10)

    def test_coefficients_and_scale(self):
        # Exact nested gain <c,y>/<c,c>=(2*7+3*19/4)/7=113/28.
        fit=subject.fit_static(self.t,self.c,self.y,h0_a=113/28)
        self.assertEqual(fit['rank'],2)
        self.assertEqual(fit['selected_model'],'Hs')
        self.assertEqual(fit['selected']['kind'],'interior')
        self.close([fit['selected']['a'],fit['selected']['d'],fit['scale']],[2.,3.,2.])
        self.close(fit['training_prediction'],self.y)
        self.close(fit['training_residual'],np.zeros(4))

    def test_gain_only_nested_tie(self):
        fit=subject.fit_static(self.t,self.c,1.7*self.c,h0_a=1.7)
        self.assertEqual(fit['selected_model'],'H0')
        self.assertEqual(fit['status'],'no_resolved_cubic_increment_on_training')
        self.assertEqual(fit['selected']['kind'],'H0')
        self.close(fit['selected']['a'],1.7)
        self.assertEqual(fit['selected']['d'],0.)

    def test_a_boundary_rational_solution(self):
        fit=subject.fit_static(self.t,self.c,-self.c+3*self.c**3/4)
        # w=(1/2,3/2,3/2,1/2), <v,c>=19/4, <v,v>=67/16.
        self.assertEqual(fit['selected']['kind'],'boundary')
        self.assertEqual(fit['selected']['a'],0.)
        self.close(fit['selected']['d'],125/67)
        interior=next(p for p in fit['candidates'] if p['kind']=='interior')
        self.assertFalse(interior['feasible'])
        self.close([interior['a'],interior['d']],[-1.,3.])

    def test_rank_deficient_not_pseudoinverse_extrapolation(self):
        t=np.array([0.,1.,3.]); c=np.array([-2.,0.,2.])
        fit=subject.fit_static(t,c,5*c)
        self.assertEqual(fit['rank'],1)
        self.assertEqual(fit['status'],'rank_deficient')
        self.assertIsNone(fit['selected'])
        self.assertIsNone(fit['training_prediction'])
        baseline=copy.deepcopy(self.archived)
        score=subject.score_static(t,np.array([-1.,1.,3.]),np.zeros(3),fit,baseline)
        self.assertEqual(score['status'],'rank_deficient')
        self.assertEqual(score['selected_model'],'H0')
        for key in ('prediction','residual','Es','sse'):
            self.assertIsNone(score[key])
        self.assertEqual(score['fallback_H0'],baseline['models']['H0'])
        self.assertEqual(score['baselines']['H1'],baseline['models']['H1_selected'])
        self.assertIsNone(score['versus_H0']['delta'])
        self.assertEqual(score['versus_H1']['outcome'],'undefined')
        score['fallback_H0']['prediction'][0]=123.
        self.assertEqual(baseline,self.archived)

    def test_distinct_magnitudes_restore_rank(self):
        t=np.array([0.,1.,3.]); c=np.array([0.,1.,2.])
        fit=subject.fit_static(t,c,2*c+3*c**3/4)
        self.assertEqual(fit['rank'],2)
        self.close([fit['selected']['a'],fit['selected']['d']],[2.,3.])

    def test_extrapolation_time_weights_and_frozen_scale(self):
        t=np.array([0.,1.,3.]); c=np.array([0.,1.,2.])
        fit=subject.fit_static(t,c,2*c+3*c**3/4)
        transfer=np.array([-1.,1.,3.])
        expected=np.array([-11/4,11/4,105/4])
        score=subject.score_static(t,transfer,expected,fit,self.archived)
        self.assertEqual(score['status'],'ok')
        self.close(score['prediction'],expected)
        self.close(score['Es'],0.)
        self.assertIsNone(score['fallback_H0'])
        # Time weights (.5,1.5,1), signed outside at indices0,2, magnitude at2.
        self.close(score['support']['outside_signed_time_fraction'],1/2)
        self.close(score['support']['outside_magnitude_time_fraction'],1/3)
        self.close(score['support']['max_abs_over_training_scale'],3/2)
        self.close([score['support']['transfer_min'],score['support']['transfer_max']],[-1.,3.])
        self.assertEqual(fit['scale'],2.)
        self.assertEqual(score['versus_H0']['outcome'],'improved')

    def test_zero_energy_and_invalid_training(self):
        with self.assertRaisesRegex(ValueError,'zero_training_control_energy'):
            subject.fit_static(self.t,np.zeros(4),np.ones(4))
        fit=subject.fit_static(self.t,self.c,self.y)
        scored=subject.score_static(self.t,np.zeros(4),np.ones(4),fit,self.archived)
        self.assertEqual(scored['status'],'zero_transfer_control_energy')
        self.assertIsNone(scored['Es'])
        self.assertEqual(scored['versus_H1']['outcome'],'undefined')
        invalid={'status':'zero_training_control_energy','selected_model':None}
        scored=subject.score_static(self.t,self.c,self.y,invalid,self.archived)
        self.assertEqual(scored['status'],'invalid_training')
        self.assertIsNone(scored['prediction'])
        self.assertEqual(scored['baselines']['H0'],self.archived['models']['H0'])

    def test_frozen_deadband(self):
        eta=1e-12+1e-10*2
        for difference,label in ((eta/2,'numerically_unresolved'),(2*eta,'improved'),(-2*eta,'worse')):
            self.assertEqual(subject.compare_score(2.,2.-difference)['outcome'],label)
        self.assertEqual(subject.compare_score(2.,None),{'delta':None,'outcome':'undefined'})


if __name__=='__main__': unittest.main()
