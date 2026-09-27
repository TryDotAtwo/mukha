"""Analytic oracle check and decoded-result negatives for actual003 review."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

spec=importlib.util.spec_from_file_location('checker',Path(__file__).resolve().parents[1]/'tools/check_temporal_actual.py')
checker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ConvolutionOracle(unittest.TestCase):
    def test_independent_closed_form(self):
        t=np.array([0.,.003,.02,.06,.13,.25]); tau=.017
        c=.2-3*t
        expected=c+3*tau*(-np.expm1(-t/tau))
        np.testing.assert_allclose(checker.state(t,c,tau),expected,rtol=1e-12,atol=1e-14)


@unittest.skipUnless(os.environ.get('PANG_TEMPORAL_ARCHIVE') and os.environ.get('PANG_TEMPORAL_RUNNER'), 'set archive/runner paths')
class DecodedNegatives(unittest.TestCase):
    def reject(self, mutate):
        original=json.loads
        def decode(*args,**kwargs):
            obj=original(*args,**kwargs)
            if isinstance(obj,dict) and obj.get('schema')=='pang-temporal-transfer-result-v1': mutate(obj)
            return obj
        with patch.object(checker.json,'loads',side_effect=decode):
            with self.assertRaises(ValueError):
                checker.review(os.environ['PANG_TEMPORAL_ARCHIVE'],os.environ['PANG_TEMPORAL_RUNNER'])

    def test_unselected_tau_score(self):
        self.reject(lambda d:d['training']['L1']['profiles'][31].update(score=999.))

    def test_selected_parameter(self):
        self.reject(lambda d:d['training']['L2']['selected'].update(b=999.))

    def test_prediction(self):
        self.reject(lambda d:d['transfers'][0]['models']['H1_selected']['prediction'].__setitem__(10,999.))

    def test_residual(self):
        self.reject(lambda d:d['transfers'][0]['models']['H0']['residual'].__setitem__(10,999.))

    def test_error(self):
        self.reject(lambda d:d['transfers'][3]['models']['H1_selected'].update(normalized_error=0.))

    def test_aggregate(self):
        self.reject(lambda d:d['summary'].update(all_six_improved=True))


if __name__=='__main__': unittest.main()
