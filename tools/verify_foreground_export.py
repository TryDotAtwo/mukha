"""Verify a bounded foreground archive/export without executing its contents."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

LIMIT = 16_000_000


def inspect_export(receipt, run_id):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', run_id):
        raise ValueError('Invalid run ID')
    if type(receipt.get('bytes')) is not int or not 0 < receipt['bytes'] <= LIMIT:
        raise ValueError('Invalid archive byte count')
    encoded = receipt.get('archive_base64')
    if not isinstance(encoded, str) or len(encoded) > 4 * ((LIMIT + 2) // 3):
        raise ValueError('Invalid encoded archive size')
    payload = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != receipt['bytes'] or digest != receipt.get('sha256'):
        raise ValueError('Transport receipt mismatch')
    files, names, expanded = {}, set(), 0
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        for member in archive:
            name = member.name
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or path.parts[0] != run_id or str(path) != name.rstrip('/')
                    or '\\' in name or name in names or len(names) >= 128):
                raise ValueError('Unsafe, duplicate or excessive archive member')
            names.add(name)
            if member.isdir():
                continue
            if not member.isfile() or member.size < 0:
                raise ValueError('Nonregular archive member')
            expanded += member.size
            if expanded > LIMIT:
                raise ValueError('Expanded archive exceeds bound')
            relative = str(path.relative_to(run_id))
            files[relative] = archive.extractfile(member).read()
    manifest = json.loads(files['manifest.json'])
    if manifest.get('run_id') != run_id or not isinstance(manifest.get('files'), dict):
        raise ValueError('Manifest run or shape mismatch')
    if set(files) != {'manifest.json'} | set(manifest['files']):
        raise ValueError('Manifest member set mismatch')
    if 'result.json' not in manifest['files']:
        raise ValueError('Result absent from manifest')
    for name, expected in manifest['files'].items():
        data = files[name]
        if (type(expected.get('bytes')) is not int or expected['bytes'] != len(data)
                or expected.get('sha256') != hashlib.sha256(data).hexdigest()):
            raise ValueError('Manifest content mismatch')
    return payload, files, {'run_id': run_id, 'archive_sha256': digest,
                            'archive_bytes': len(payload), 'manifest_files': len(manifest['files']),
                            'scope': 'Transport integrity only; independent scientific review required'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    payload, files, report = inspect_export(json.loads(args.receipt.read_text()), args.run_id)
    # A dedicated new root prevents accidental overwrite of any previous run.
    args.output_root.mkdir(parents=True, exist_ok=False)
    (args.output_root / (args.run_id + '.tar.gz')).write_bytes(payload)
    target = args.output_root / args.run_id
    target.mkdir()
    for name, data in files.items():
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as handle:
            handle.write(data)
    (args.output_root / 'export-integrity.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
