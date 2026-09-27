"""Decode and verify the bounded Molab fresh-process checkpoint artifact bundle."""
import base64
import gzip
import hashlib
import io
import json
import tarfile
import argparse
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--bundle', default='build/molab_file_checkpoint_bundle.txt')
parser.add_argument('--destination', default='build/molab_file_checkpoint_artifacts')
args = parser.parse_args()
lines = (root/args.bundle).read_text(encoding='utf-8-sig').splitlines()
parts = []
offset = 0
for line in lines:
    if line.startswith('BUNDLE_PART '):
        _, position, part = line.split(' ', 2)
        assert int(position) == offset
        parts.append(part)
        offset += len(part)
end = next(line.split() for line in lines if line.startswith('BUNDLE_END '))
assert offset == int(end[1])
data = base64.b64decode(''.join(parts), validate=True)
assert hashlib.sha256(data).hexdigest() == end[2]
destination = (root/args.destination).resolve()
assert destination.is_relative_to((root/'build').resolve())
destination.mkdir(exist_ok=True)
allowed = {'report.json', 'probe'} | {
    name for onset in (250,750) for name in (
        f'checkpoint-{onset}.bin', f'checkpoint-{onset}.bin.final',
        f'full-{onset}.csv', f'resume-{onset}.csv')}
seen = set()
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    for member in archive:
        assert member.isfile() and member.name in allowed and member.name not in seen
        seen.add(member.name)
        (destination/member.name).write_bytes(archive.extractfile(member).read())
assert seen == allowed
report = json.loads((destination/'report.json').read_text())
assert hashlib.sha256((destination/'probe').read_bytes()).hexdigest() == report['binary_sha256']
for case in report['cases']:
    onset = case['onset_tick']
    snapshot = (destination/f'checkpoint-{onset}.bin').read_bytes()
    final = (destination/f'checkpoint-{onset}.bin.final').read_bytes()
    assert len(snapshot) == case['snapshot_bytes']
    assert hashlib.sha256(snapshot).hexdigest() == case['snapshot_sha256']
    assert hashlib.sha256(final).hexdigest() == case['final_sha256']
    full = (destination/f'full-{onset}.csv').read_text().splitlines()
    resumed = (destination/f'resume-{onset}.csv').read_text().splitlines()
    assert len(full) == 1001 and len(resumed) == 501
    assert full[501:] == resumed[1:]
print('Verified exported snapshots, final states, traces and executable for both onset cases.')
