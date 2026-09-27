"""Independently compare derived recordings to every numeric MATLAB array."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
dest = ROOT / 'data/derived/mamiya2018_recordings_v1'
manifest = json.loads((dest / 'manifest.json').read_text())
assert not (dest / 'INCOMPLETE').exists()
archive = ROOT / 'data/reference/mamiya2018/data.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['source_archive_sha256']
totals = dict(files=0, arrays=0, protocol_tables=0, response_rows=0,
              paired_finite_samples=0, missing_response_samples=0, missing_angle_samples=0)
with zipfile.ZipFile(archive) as source:
    for record in manifest['records']:
        payload = source.read(record['source_file'])
        assert hashlib.sha256(payload).hexdigest() == record['source_member_sha256']
        original = {k: v for k, v in loadmat(io.BytesIO(payload), simplify_cells=True).items()
                    if not k.startswith('__')}
        path = dest / (Path(record['source_file']).stem + '.npz')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['files'][path.name]
        with np.load(path, allow_pickle=False) as derived:
            assert set(original) == set(derived.files)
            for key, value in original.items():
                a = np.asarray(value)
                assert a.dtype == derived[key].dtype
                np.testing.assert_array_equal(a, derived[key])
                assert not np.isinf(a).any(), (record['source_file'], key)
                totals['arrays'] += 1
            assert {k[:-4] for k in derived.files if k.endswith('_DFF')} == {
                p['protocol'] for p in record['protocols']}
            for p in record['protocols']:
                response = derived[p['protocol'] + '_DFF']
                angle = derived[p['protocol'] + '_Angle']
                assert response.shape == angle.shape == (p['rows'], p['frames'])
                counts = dict(response_rows=response.shape[0],
                              paired_finite_samples=int((np.isfinite(response) & np.isfinite(angle)).sum()),
                              missing_response_samples=int(np.isnan(response).sum()),
                              missing_angle_samples=int(np.isnan(angle).sum()))
                for key, count in counts.items():
                    if key != 'response_rows':
                        assert count == p[key]
                    totals[key] += count
                totals['protocol_tables'] += 1
        totals['files'] += 1
report = dict(**totals, all_source_arrays_exact=True, infinite_values=0,
              source_archive_sha256=manifest['source_archive_sha256'],
              physiological_fit_performed=False, malecns_mapping_performed=False)
(ROOT / 'reports/mamiya2018_validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
