import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_foreground_export import inspect_export


def receipt(extra=None, bad_manifest=False):
    data = b'{"synthetic_transport_fixture":true}'
    manifest = {'run_id': 'test-run', 'files': {'result.json': {
        'bytes': len(data), 'sha256': 'bad' if bad_manifest else hashlib.sha256(data).hexdigest()}}}
    members = [('test-run/result.json', data),
               ('test-run/manifest.json', json.dumps(manifest).encode())]
    if extra:
        members.append(extra)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name, content in members:
            item = tarfile.TarInfo(name)
            if content is None:
                item.type = tarfile.SYMTYPE
                item.linkname = 'result.json'
                archive.addfile(item)
            else:
                item.size = len(content)
                archive.addfile(item, io.BytesIO(content))
    payload = buffer.getvalue()
    return {'archive_base64': base64.b64encode(payload).decode(),
            'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}


class ExportTests(unittest.TestCase):
    def test_positive(self):
        _, files, report = inspect_export(receipt(), 'test-run')
        self.assertEqual(set(files), {'result.json', 'manifest.json'})
        self.assertEqual(report['manifest_files'], 1)

    def test_unsafe_duplicate_link_and_unlisted(self):
        for member in [('test-run/../escape', b'x'), ('/test-run/x', b'x'),
                       ('test-run/result.json', b'x'), ('test-run/link', None),
                       ('test-run/unlisted', b'x')]:
            with self.subTest(member=member), self.assertRaises(ValueError):
                inspect_export(receipt(extra=member), 'test-run')

    def test_bad_manifest_digest(self):
        with self.assertRaises(ValueError):
            inspect_export(receipt(bad_manifest=True), 'test-run')

    def test_bad_transport_receipt(self):
        for key, value in [('bytes', True), ('bytes', 16_000_001), ('sha256', 'bad')]:
            altered = receipt()
            altered[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                inspect_export(altered, 'test-run')


if __name__ == '__main__':
    unittest.main()
