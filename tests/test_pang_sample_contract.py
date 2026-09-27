import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from audit_pang_sample_contract import boundaries, sampled_areas, source_receipts


class SampleContractTests(unittest.TestCase):
    def test_hand_integrated_signed_areas_and_sample_boundary(self):
        y = [0., 1., 3., 1., -1., -1., 2.]
        r = sampled_areas(y, 3, 2, .04)
        self.assertEqual((r['frame_zero1'], r['frame_zero2'], r['end_phase2']), (1, 5, 6))
        # Unit-spaced trapezoids .5+2+2+0=4.5 and -1; scale 100*.04=4.
        self.assertEqual(r['area1_percent_df_f_seconds'], 18.)
        self.assertEqual(r['area2_percent_df_f_seconds'], -4.)
        self.assertAlmostEqual(r['signed_area_ratio'], -2/9)
        # Geometric crossing at frame 4.5 would assign +.25 more to phase1.
        self.assertNotEqual(r['area1_percent_df_f_seconds'], 19.)

    def test_returning_first_polarity_is_not_rectified(self):
        r = sampled_areas([0., 1., 3., 1., -1., -1., 4., 4.], 3, 2, .03125)
        self.assertEqual(r['signed_area_ratio'], 1.)
        self.assertEqual(r['area2_percent_df_f_seconds'], 14.0625)

    def test_dark_polarity_inverts_areas_preserves_ratio(self):
        y = [0., 1., 3., 1., -1., -1., 2.]
        light = sampled_areas(y, 3, 2, .04)
        dark = sampled_areas([-x for x in y], 3, 1, .04)
        self.assertEqual(dark['area1_percent_df_f_seconds'], -light['area1_percent_df_f_seconds'])
        self.assertEqual(dark['signed_area_ratio'], light['signed_area_ratio'])

    def test_exact_zero_and_missing_crossing(self):
        self.assertEqual(boundaries([0., 1., 3., 0., -1., -1., 2.], 3, 2), (1, 4))
        self.assertEqual(boundaries([0., 1., 3., 2.], 3, 2), (1, None))
        # Source does not reject an absent-polarity trace itself.
        self.assertEqual(boundaries([0., 0., 0., 0.], 2, 2), (2, 2))

    def test_explicit_wrapper_domain(self):
        for y, peak, contrast, ifi in [([0., 1., 2.], 3, 2, .04),
                ([0., 1., -1.], 2, 2, .04), ([0., 1., -1.], 2, 2, 0.),
                ([0., float('nan'), -1.], 2, 2, .1)]:
            with self.subTest(y=y, peak=peak, ifi=ifi), self.assertRaises(ValueError):
                sampled_areas(y, peak, contrast, ifi)

    def test_source_mutation_is_rejected(self):
        from unittest.mock import patch
        with patch.object(Path, 'read_bytes', return_value=b'altered source'):
            with self.assertRaisesRegex(ValueError, 'Git blob mismatch'):
                source_receipts(Path('unused'))


if __name__ == '__main__':
    unittest.main()
