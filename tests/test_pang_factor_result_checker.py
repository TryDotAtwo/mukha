"""Targeted oracle negatives; mutate decoded result, not the pinned archive."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('factor_check', Path(__file__).resolve().parents[1]/'tools/check_pang_factor_result.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
ARCHIVE = os.environ.get('PANG_FACTOR_ARCHIVE')


@unittest.skipUnless(ARCHIVE, 'set PANG_FACTOR_ARCHIVE to retrieved archive')
class ResultNegatives(unittest.TestCase):
    def reject(self, mutation):
        original = json.loads
        def decode(*args, **kwargs):
            value = original(*args, **kwargs)
            if isinstance(value, dict) and value.get('schema') == 'pang-window-factors-v1':
                mutation(value)
            return value
        with patch.object(checker.json, 'loads', side_effect=decode):
            with self.assertRaises(ValueError):
                checker.review(ARCHIVE)

    def test_sign(self):
        self.reject(lambda d: d['records'][0].update(Q=-d['records'][0]['Q']))

    def test_area(self):
        self.reject(lambda d: d['records'][1].update(A2=d['records'][1]['A2']+1e-5))

    def test_boundary(self):
        self.reject(lambda d: d['records'][3].update(end=d['records'][3]['end']+.001))

    def test_duplicate(self):
        self.reject(lambda d: d['records'].__setitem__(1,d['records'][0]))

    def test_triple(self):
        self.reject(lambda d: d['curves'][0]['contrasts']['Q']['terms']['OEC'].update(baseline=.01))

    def test_average(self):
        self.reject(lambda d: d['curves'][0]['contrasts']['Q']['terms']['O'].update(averaged=.01))

    def test_conditional(self):
        self.reject(lambda d: d['curves'][0]['contrasts']['Q']['terms']['OE']['conditional'].update(S=.01))

    def test_corner(self):
        self.reject(lambda d: d['curves'][0]['corner_closure']['SSS']['A1'].update(residual=.01))


if __name__ == '__main__':
    unittest.main()
