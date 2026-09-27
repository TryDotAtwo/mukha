"""Molab comparison of baseline and deferred-host-validation VisTrans builds."""
from pathlib import Path
import ctypes as C
import json
import time

import numpy as np


def api(path):
    lib = C.CDLL(str(path))
    lib.fp_create.argtypes = [C.c_uint32, C.c_uint32, C.c_uint64, C.c_uint32]
    lib.fp_create.restype = C.c_void_p
    lib.fp_destroy.argtypes = [C.c_void_p]
    lib.fp_advance.argtypes = [C.c_void_p, C.POINTER(C.c_double), C.c_size_t, C.c_uint32]
    lib.fp_advance.restype = C.c_int
    lib.fp_observe.argtypes = [C.c_void_p, C.POINTER(C.c_double), C.c_size_t, C.POINTER(C.c_uint64)]
    lib.fp_observe.restype = C.c_int
    lib.fp_checkpoint_size.argtypes = [C.c_void_p]
    lib.fp_checkpoint_size.restype = C.c_size_t
    lib.fp_save.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t]
    lib.fp_save.restype = C.c_int
    lib.fp_last_error.restype = C.c_char_p
    lib.fp_build_identity.restype = C.c_char_p
    return lib


def case(lib, cells, ticks, snapshot=False):
    h = lib.fp_create(cells, 30000, 19503, 128)
    if not h:
        raise RuntimeError(lib.fp_last_error())
    rate = np.full(cells, 50000., np.float64)
    observed = np.empty(9 * cells, np.float64)
    time_tick = C.c_uint64()
    try:
        started = time.perf_counter()
        rc = lib.fp_advance(h, rate.ctypes.data_as(C.POINTER(C.c_double)), cells, ticks)
        elapsed = time.perf_counter() - started
        if rc != 0:
            raise RuntimeError(lib.fp_last_error())
        if lib.fp_observe(h, observed.ctypes.data_as(C.POINTER(C.c_double)),
                          len(observed), C.byref(time_tick)) != 0:
            raise RuntimeError(lib.fp_last_error())
        assert time_tick.value == ticks and np.isfinite(observed).all()
        data = None
        if snapshot:
            size = lib.fp_checkpoint_size(h)
            data = (C.c_ubyte * size)()
            if lib.fp_save(h, data, size) != 0:
                raise RuntimeError(lib.fp_last_error())
            data = bytes(data)
        return {'elapsed_s': elapsed, 'voltage': observed.copy(), 'snapshot': data,
                'build_identity': lib.fp_build_identity().decode()}
    finally:
        lib.fp_destroy(h)


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import digest, publish
    baseline = api(root / 'build/libfly_photon.so')
    batch = api(root / 'build/libfly_photon_batch_diagnostic.so')
    output = root / 'data/derived/photon_batch_benchmark_v1'
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for cells, ticks, snapshot in [(16, 100, True), (128, 1000, False), (6091, 100, False)]:
        a = case(baseline, cells, ticks, snapshot)
        b = case(batch, cells, ticks, snapshot)
        max_voltage_error = float(np.max(np.abs(a['voltage'] - b['voltage'])))
        same_checkpoint_payload = None
        if snapshot:
            assert len(a['snapshot']) == len(b['snapshot'])
            same_checkpoint_payload = a['snapshot'][192:] == b['snapshot'][192:]
        rec = {'cells': cells, 'microvilli_per_cell': 30000, 'ticks': ticks,
               'baseline_elapsed_s': a['elapsed_s'], 'batch_elapsed_s': b['elapsed_s'],
               'speedup': a['elapsed_s'] / b['elapsed_s'],
               'max_observed_state_error': max_voltage_error,
               'checkpoint_payload_exact': same_checkpoint_payload,
               'baseline_build_identity': a['build_identity'],
               'batch_build_identity': b['build_identity']}
        cases.append(rec)
        print('PHOTON_BATCH_CASE', json.dumps(rec), flush=True)
    assert all(r['max_observed_state_error'] == 0 for r in cases)
    assert cases[0]['checkpoint_payload_exact'] is True
    report = {'scope': 'Isolated same-kernel batch-advance diagnostic; 50k photons/s, one seed, 0.1ms ticks',
              'cases': cases, 'benchmark_only': True,
              'limitation': 'Intermediate state validity is not checked every tick in batch build; must add device-side validation before adoption. 100-tick full retina still cannot establish multi-second training throughput.',
              'biological_gate_passed': False}
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    files = [output / 'report.json', root / 'build/photon_batch_diagnostic.cu',
             root / 'build/photon_batch_build_id.h', root / 'build/photon_batch_build.json',
             root / 'build/libfly_photon_batch_diagnostic.so',
             root / 'tools/build_photon_batch_diagnostic.py',
             root / 'tools/benchmark_photon_batch.py']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('PHOTON_BATCH_REPORT', json.dumps(report), flush=True)
    print('PHOTON_BATCH_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
