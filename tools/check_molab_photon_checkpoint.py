"""Verify exported Molab checkpoint evidence without launching another GPU job."""
import hashlib
import json
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
report = json.loads((root/'reports/molab_photon_checkpoint.json').read_text())
trace = root/'build/molab_photon_checkpoint.csv'
binary = root/'build/molab_photon_probe_linux'
assert hashlib.sha256(trace.read_bytes()).hexdigest() == report['trace_sha256']
assert hashlib.sha256(binary.read_bytes()).hexdigest() == report['binary_sha256']
data = np.genfromtxt(trace, delimiter=',', names=True)
assert len(data) == 1500
assert np.array_equal(data['tick'][:1000], np.arange(1, 1001))
assert np.array_equal(data['tick'][1000:], np.arange(501, 1001))
for name in data.dtype.names:
    assert np.isfinite(data[name]).all()
    assert np.array_equal(data[name][500:1000], data[name][1000:]), name
assert 'Checkpoint continuation exact: 3720160 bytes' in report['native_result']
print('Molab photon trace, clock, replay and native binary hashes verified.')
