"""Measure VisTrans waiting hazards on real adapted receptor snapshots.

Diagnostic only: the Python law uses float64 whereas CUDA mixes float/double.
The frozen-rate Poisson tail is not a bound on state-dependent future events.
"""
from pathlib import Path
import ctypes as c
import hashlib
import json

import numpy as np

from reference.grouped_vistrans import LA, DT, reaction_rates


HEADER = 16 * 8 + 64


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def molecules(lib, model, cells, microvilli):
    size = lib.fp_checkpoint_size(model)
    buffer = (c.c_ubyte * size)()
    if lib.fp_save(model, c.addressof(buffer), size):
        raise RuntimeError('fp_save failed')
    total = cells * microvilli
    raw = np.frombuffer(buffer, dtype='<u2', count=total * 7, offset=HEADER)
    a = raw[:2 * total].reshape(total, 2)
    b = raw[2 * total:4 * total].reshape(total, 2)
    d = raw[4 * total:6 * total].reshape(total, 2)
    e = raw[6 * total:7 * total]
    return np.column_stack((e, a, b, d))


def receptor_workload(states, vm_mV, ns, photons_s):
    unique, counts = np.unique(states, axis=0, return_counts=True)
    per_microvillus = photons_s / len(states)
    hazards = np.fromiter(
        (LA + reaction_rates(tuple(int(v) for v in state), vm_mV, ns, per_microvillus).compact
         for state in unique), dtype=np.float64, count=len(unique))
    expected = hazards * DT
    weighted = np.repeat(expected, counts)
    frozen_tail = -np.expm1(-weighted) - weighted * np.exp(-weighted)
    if not np.all(np.isfinite(weighted)) or np.any(weighted < 0):
        raise RuntimeError('nonfinite or negative hazard')
    return {
        'unique_states': int(len(unique)),
        'vm_mV': vm_mV,
        'ns': ns,
        'expected_waiting_events_per_tick': float(weighted.sum()),
        'per_microvillus_lambda_dt_quantiles': {
            label: float(np.quantile(weighted, q))
            for label, q in [('median', .5), ('p90', .9), ('p99', .99), ('p999', .999), ('max', 1.)]
        },
        'microvilli_lambda_dt_above_0_1': int(np.count_nonzero(weighted > .1)),
        'microvilli_lambda_dt_above_1': int(np.count_nonzero(weighted > 1.)),
        'frozen_rate_two_plus_event_expected_microvilli': float(frozen_tail.sum()),
        'scope_note': 'Frozen instantaneous rate diagnostic; not a bound on the true multi-reaction path probability.'
    }


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import publish
    binary = root / 'build/libfly_photon_coupled_current_diagnostic.so'
    lib = c.CDLL(str(binary))
    lib.fp_create.argtypes = [c.c_uint32, c.c_uint32, c.c_uint64, c.c_uint32]
    lib.fp_create.restype = c.c_void_p
    lib.fp_advance.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t, c.c_uint32]
    lib.fp_advance.restype = c.c_int
    lib.fp_observe.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_uint64)]
    lib.fp_observe.restype = c.c_int
    lib.fp_checkpoint_size.argtypes = [c.c_void_p]
    lib.fp_checkpoint_size.restype = c.c_size_t
    lib.fp_save.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t]
    lib.fp_save.restype = c.c_int
    lib.fp_destroy.argtypes = [c.c_void_p]
    cells, m, rate = 8, 30000, 50000.
    model = lib.fp_create(cells, m, 19503, 1024)
    if not model:
        raise RuntimeError('fp_create failed')
    photon_rates = np.full(cells, rate, dtype='<f8')
    records = []
    try:
        for ticks, time_ms in ((1000, 100), (4000, 500)):
            if lib.fp_advance(model, photon_rates.ctypes.data, cells, ticks):
                raise RuntimeError('fp_advance failed')
            state = molecules(lib, model, cells, m)
            observation = np.empty(cells * 9, dtype='<f8')
            tick = c.c_uint64()
            if lib.fp_observe(model, observation.ctypes.data, len(observation), c.byref(tick)):
                raise RuntimeError('fp_observe failed')
            if tick.value != time_ms * 10:
                raise RuntimeError('unexpected observation tick')
            for i in range(cells):
                record = receptor_workload(state[i * m:(i + 1) * m],
                                           float(observation[i]),
                                           float(observation[6 * cells + i]), rate)
                record.update({'time_ms': time_ms, 'receptor': i})
                records.append(record)
                print('VISTRANS_RATE_WORKLOAD', json.dumps(record), flush=True)
    finally:
        lib.fp_destroy(model)
    report = {
        'scope': 'Waiting-hazard workload at 100 and 500 ms on 8 source VisTrans receptors',
        'binary_sha256': digest(binary),
        'cells': cells, 'microvilli_each': m, 'photons_per_receptor_s': rate,
        'seed': 19503, 'records': records,
        'limitations': 'One constant-light seed; float64 rate approximation; frozen-rate tail is not a bound for state-dependent paths; no GPU speed claim.'
    }
    folder = root / 'data/derived/vistrans_rate_workload_v1'
    folder.mkdir(parents=True, exist_ok=False)
    result = folder / 'report.json'
    result.write_text(json.dumps(report, indent=2))
    files = [result, root / 'tools/analyze_vistrans_rate_workload.py',
             root / 'reference/grouped_vistrans.py']
    manifest = {
        'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
        'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size, 'sha256': digest(p)}
                  for p in files}
    }
    receipt = publish(root, manifest)
    print('VISTRANS_RATE_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
