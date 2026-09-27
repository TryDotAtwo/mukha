"""Offline acceptance tests; tiny artificial skeletons are not biology evidence."""
import base64
import hashlib
import importlib.util
import gzip
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

SPEC = importlib.util.spec_from_file_location(
    'swc_audit', Path(__file__).resolve().parents[1] / 'tools/audit_downloaded_malecns_swcs.py')
swc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(swc)


class AuditTests(unittest.TestCase):
    def run_fixture(self, text, population=None):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            inventory = {}
            if text is not None:
                payload = text.encode()
                (source / '1.swc').write_bytes(payload)
                inventory[1] = {'bytes': len(payload), 'md5_base64':
                                base64.b64encode(hashlib.md5(payload).digest()).decode()}
            return swc.audit(source, inventory, {1, 2} if population is None else population, 'fixture')

    def test_partial_valid_is_not_full_coverage(self):
        report = self.run_fixture('1 1 0 0 0 1 -1\n2 3 1 0 0 1 1\n')
        self.assertTrue(report['structural_checks_passed'])
        self.assertEqual(report['downloaded_fraction'], .5)
        self.assertEqual(report['total_swc_nodes'], 2)

    def test_no_files_fails(self):
        self.assertFalse(self.run_fixture(None)['structural_checks_passed'])

    def test_empty_and_comment_only_fail(self):
        for text in ('', '# only a header\n'):
            with self.subTest(text=text):
                report = self.run_fixture(text)
                self.assertFalse(report['structural_checks_passed'])
                self.assertIn('1', report['structural_issue_files'])

    def test_structural_negative_controls(self):
        cases = {
            'malformed': '1 1 0 0 0 1 -1\nbroken\n',
            'missing_parent': '1 1 0 0 0 1 99\n',
            'cycle': '1 1 0 0 0 1 2\n2 3 1 0 0 1 1\n',
            'self_parent': '1 1 0 0 0 1 1\n',
            'duplicate': '1 1 0 0 0 1 -1\n1 3 1 0 0 1 -1\n',
            'nonfinite': '1 1 nan 0 0 1 -1\n',
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                self.assertFalse(self.run_fixture(text)['structural_checks_passed'])

    def test_multi_root_and_zero_length_are_descriptive(self):
        report = self.run_fixture('1 1 0 0 0 1 -1\n2 3 0 0 0 1 1\n3 3 1 0 0 1 -1\n')
        self.assertTrue(report['structural_checks_passed'])
        self.assertEqual(report['multi_root_files'], 1)
        self.assertEqual(report['files_with_zero_length_edges'], 1)

    def test_empty_population_rejected(self):
        with self.assertRaisesRegex(ValueError, 'empty graph'):
            self.run_fixture(None, set())

    def test_outside_population_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside selected'):
            self.run_fixture('1 1 0 0 0 1 -1\n', {2})

    def test_source_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / '1.swc').write_text('1 1 0 0 0 1 -1\n')
            with self.assertRaisesRegex(ValueError, 'source byte mismatch'):
                swc.audit(source, {1: {'bytes': 0, 'md5_base64': ''}}, {1}, 'fixture')

    def test_alias_filename_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            payload = b'1 1 0 0 0 1 -1\n'
            for name in ('1.swc', '01.swc'):
                (source / name).write_bytes(payload)
            inventory = {1: {'bytes': len(payload), 'md5_base64':
                            base64.b64encode(hashlib.md5(payload).digest()).decode()}}
            with self.assertRaisesRegex(ValueError, 'duplicate SWC body'):
                swc.audit(source, inventory, {1}, 'fixture')

    def test_main_exit_contract_and_report(self):
        # Stub only the NPY loader; exercise real inventory hashing, SWC reads,
        # report serialization and main return codes without scientific datasets.
        for payload, expected in ((b'1 1 0 0 0 1 -1\n', 0), (b'', 1),
                                  (b'1 1 0 0 0 1 999\n', 1)):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'reports').mkdir()
                source = root / 'swcs'
                source.mkdir()
                (source / '1.swc').write_bytes(payload)
                digest = base64.b64encode(hashlib.md5(payload).digest()).decode()
                inventory = gzip.compress(
                    f'body_id,bytes,md5_base64\n1,{len(payload)},{digest}\n'.encode())
                (root / 'inventory.csv.gz').write_bytes(inventory)
                (root / 'reports/malecns_swc_bucket_inventory.json').write_text(json.dumps({
                    'inventory_path': 'inventory.csv.gz',
                    'inventory_sha256': hashlib.sha256(inventory).hexdigest()}))
                report_path = root / 'result.json'
                with patch.object(swc, 'ROOT', root), patch.object(swc, 'SOURCE', source), \
                     patch.object(swc, 'REPORT', report_path), \
                     patch.dict('sys.modules', {'numpy': types.SimpleNamespace(load=lambda _: [1, 2])}), \
                     redirect_stdout(io.StringIO()):
                    self.assertEqual(swc.main(), expected)
                report = json.loads(report_path.read_text())
                self.assertEqual(report['structural_checks_passed'], expected == 0)
                self.assertEqual(report['graph_population'], 2)


if __name__ == '__main__':
    unittest.main()
