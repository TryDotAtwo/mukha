import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from check_pang_measurement_result import (EXPECTED_PEAK_POLICY, EXPECTED_SCHEMA,
                                          FILES, validate_contract)


class ContractTests(unittest.TestCase):
    def setUp(self):
        # Only the header/index contract is exercised; these are not curve data.
        self.report = {'schema': EXPECTED_SCHEMA, 'peak_policy': EXPECTED_PEAK_POLICY,
                       'rows': [{'file': name, 'row': row, 'supplied_peak_frame': 4,
                                 'sampled': {'frame_zero1': 2, 'frame_zero2': 8,
                                             'end_phase2': 30}}
                                for name in FILES for row in (0, 1)]}

    def test_declared_header_and_integer_fields(self):
        validate_contract(self.report)

    def test_schema_and_policy_mutations(self):
        for field, value in [('schema', 'physiology-validated-v999'),
                             ('peak_policy', 'author computeFramePeaks over entire supplied vector')]:
            r = copy.deepcopy(self.report)
            r[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_contract(r)

    def test_fractional_boolean_out_of_range_frames(self):
        for field in ('frame_zero1', 'frame_zero2', 'end_phase2', 'supplied_peak_frame'):
            for value in (2+5e-13, 2.0, True, 0, 64):
                r = copy.deepcopy(self.report)
                target = r['rows'][0] if field == 'supplied_peak_frame' else r['rows'][0]['sampled']
                target[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_contract(r)

    def test_boolean_duplicate_and_missing_rows(self):
        for change in ('boolean', 'duplicate', 'missing'):
            r = copy.deepcopy(self.report)
            if change == 'boolean':
                r['rows'][0]['row'] = False
            elif change == 'duplicate':
                r['rows'][0] = copy.deepcopy(r['rows'][1])
            else:
                r['rows'].pop()
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_contract(r)


if __name__ == '__main__':
    unittest.main()
