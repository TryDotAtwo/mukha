"""Decoded-artifact negatives for actual004 checker; no new model search."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('checker',Path(__file__).resolve().parents[1]/'tools/check_static_actual.py')
checker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@unittest.skipUnless(os.environ.get('PANG_STATIC_ARCHIVE') and os.environ.get('PANG_STATIC_REVIEWED_DIR'),'set actual archive and reviewed source paths')
class Corruptions(unittest.TestCase):
    def reject(self,mutation):
        original=json.loads
        def decode(*args,**kwargs):
            value=original(*args,**kwargs)
            if isinstance(value,dict) and value.get('schema')=='pang-static-control-result-v1': mutation(value)
            return value
        with patch.object(checker.json,'loads',side_effect=decode):
            with self.assertRaises(ValueError):
                checker.review(os.environ['PANG_STATIC_ARCHIVE'],os.environ['PANG_STATIC_REVIEWED_DIR'])

    def test_coefficient(self):
        self.reject(lambda d:d['training']['L1']['selected'].update(d=0.))

    def test_prediction(self):
        self.reject(lambda d:d['transfers'][0]['prediction'].__setitem__(10,999.))

    def test_support(self):
        self.reject(lambda d:d['transfers'][3]['support'].update(outside_signed_time_fraction=0.))

    def test_frozen_baseline(self):
        self.reject(lambda d:d['transfers'][0]['baselines']['H0'].update(normalized_error=0.))

    def test_summary(self):
        self.reject(lambda d:d['summary'].update(all_six_cubic_better_than_H1=True))


if __name__=='__main__': unittest.main()
