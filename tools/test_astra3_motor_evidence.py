"""Negative controls for the exported motor evidence audit (no simulation)."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from audit_astra3_motor_evidence import audit, indexed

ROOT = Path(__file__).resolve().parents[1]


class EvidenceTests(unittest.TestCase):
    def test_complete_groups(self):
        result = audit(ROOT)
        self.assertEqual(result['candidate_count'], 815)
        self.assertEqual(sum(map(len, result['curated_group_members'].values())), 4)
        self.assertFalse(result['gate_D_passed'])

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            indexed([{'bodyId': '815344'}, {'bodyId': '815344'}])

    def test_edited_export_rejected(self):
        original = Path.read_bytes
        def read(path):
            data = original(path)
            if path.name == 'malecns_manc_motor_targets.csv':
                return data.replace(b'Tergotr.', b'Ti extensor')
            return data
        with patch.object(Path, 'read_bytes', read):
            with self.assertRaisesRegex(ValueError, 'predicted table hash mismatch'):
                audit(ROOT)

    def test_enabled_or_calibrated_draft_rejected(self):
        original = Path.read_bytes
        for field, value in [('enabled', True), ('gain', 0.1), ('activation_time_constant_ms', 20)]:
            def read(path):
                data = original(path)
                if path.name == 'knee_interface_draft.json':
                    obj = json.loads(data)
                    obj['entries'][0][field] = value
                    return json.dumps(obj).encode()
                return data
            with self.subTest(field=field), patch.object(Path, 'read_bytes', read):
                with self.assertRaisesRegex(ValueError, 'active or calibrated'):
                    audit(ROOT)

    def test_unpinned_publisher_bytes_rejected(self):
        original = Path.read_bytes
        def read(path):
            return b'altered publisher bytes' if path.name == 'supp3.csv' else original(path)
        with patch.object(Path, 'read_bytes', read):
            with self.assertRaisesRegex(ValueError, 'publisher hash mismatch'):
                audit(ROOT, Path('synthetic-publisher-fixture'))


if __name__ == '__main__':
    unittest.main()
