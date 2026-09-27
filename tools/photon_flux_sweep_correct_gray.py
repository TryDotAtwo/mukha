"""Correct the gray control of photon_flux_sweep v1 without altering its raw flashes.

The v1 gray condition accidentally presented darkness in the 20 ms flash
window. Both original light and dark traces used the intended input. This
script reruns gray only, at half-scale photon rate for all 1020 ms.
"""
from pathlib import Path
import ctypes as C
import json

import numpy as np


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import digest, publish
    original = root / 'data/derived/photon_flux_sweep_v1'
    output = root / 'data/derived/photon_flux_sweep_v2'
    output.mkdir(parents=True, exist_ok=False)
    lib = C.CDLL(str(root / 'build/libfly_photon.so'))
    lib.fp_create.argtypes = [C.c_uint32, C.c_uint32, C.c_uint64, C.c_uint32]
    lib.fp_create.restype = C.c_void_p
    lib.fp_destroy.argtypes = [C.c_void_p]
    lib.fp_reset.argtypes = [C.c_void_p, C.c_uint64]
    lib.fp_reset.restype = C.c_int
    lib.fp_advance.argtypes = [C.c_void_p, C.POINTER(C.c_double), C.c_size_t, C.c_uint32]
    lib.fp_advance.restype = C.c_int
    lib.fp_observe.argtypes = [C.c_void_p, C.POINTER(C.c_double), C.c_size_t, C.POINTER(C.c_uint64)]
    lib.fp_observe.restype = C.c_int
    lib.fp_last_error.restype = C.c_char_p
    n = 128
    seed = 19503
    scales = [1_000, 10_000, 100_000, 1_000_000]
    with np.load(original / 'mean_voltage_traces.npz') as recorded:
        traces = {k: recorded[k].copy() for k in recorded.files if not k.endswith('_gray')}
        wrong_gray = {scale: recorded[f'{scale}_gray'].copy() for scale in scales}
    h = lib.fp_create(n, 30_000, seed, 128)
    if not h:
        raise RuntimeError(lib.fp_last_error())
    state = np.empty(n * 9, dtype=np.float64)
    tick = C.c_uint64()
    try:
        for scale in scales:
            if lib.fp_reset(h, seed) != 0:
                raise RuntimeError(lib.fp_last_error())
            rate = np.full(n, scale * 0.5, np.float64)
            sample = np.empty(1020, np.float64)
            for ms in range(1020):
                if lib.fp_advance(h, rate.ctypes.data_as(C.POINTER(C.c_double)), n, 10) != 0:
                    raise RuntimeError(lib.fp_last_error())
                if lib.fp_observe(h, state.ctypes.data_as(C.POINTER(C.c_double)),
                                  len(state), C.byref(tick)) != 0:
                    raise RuntimeError(lib.fp_last_error())
                if tick.value != (ms + 1) * 10 or not np.isfinite(state[:n]).all():
                    raise AssertionError(('invalid state', tick.value, ms))
                sample[ms] = state[:n].mean()
            assert np.array_equal(sample[:500], wrong_gray[scale][:500])
            assert np.array_equal(sample[:500], traces[f'{scale}_light'][:500])
            assert np.array_equal(sample[:500], traces[f'{scale}_dark'][:500])
            assert not np.array_equal(sample[500:520], wrong_gray[scale][500:520])
            traces[f'{scale}_gray'] = sample
            print('CORRECT_GRAY', scale, float(sample[499]), float(sample[519]), flush=True)
    finally:
        lib.fp_destroy(h)
    results = []
    for scale in scales:
        gray = traces[f'{scale}_gray']
        for mode, sign in [('light', 1), ('dark', -1)]:
            response = traces[f'{scale}_{mode}'][500:] - gray[500:]
            peak = int(np.argmax(sign * response[:100]))
            initial = float(sign * response[peak])
            opposite = float(np.max(-sign * response[100:500]))
            results.append({'scale_photons_s': scale, 'mode': mode,
                            'initial_signed_peak_mV': initial, 'peak_ms': peak + 1,
                            'opposite_101_500ms_mV': opposite,
                            'opposite_to_initial_ratio': opposite / initial if initial > 0 else None,
                            'end_response_mV': float(response[-1])})
    report = {'scope': 'Standalone pinned VisTrans; 128 R1R6-like cells; 30000 microvilli/cell; 0.1ms ticks, 1ms samples; one seed, no CNS or feedback',
              'correction': 'V1 gray control presented zero photons for 20ms; V2 reruns all four gray controls at half-scale continuously. Light and dark raw traces are reused unchanged.',
              'original_v1_hf_revision': '9277edd43d1c2f978f2f5d43dbcda4ce5f2737d5',
              'uncalibrated': True, 'biological_gate_passed': False,
              'seed': seed, 'results': results}
    np.savez_compressed(output / 'mean_voltage_traces.npz', **traces)
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    files = [output / 'mean_voltage_traces.npz', output / 'report.json', root / 'tools/photon_flux_sweep_correct_gray.py']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('CORRECTED_PHOTON_SWEEP_REPORT', json.dumps(report), flush=True)
    print('CORRECTED_PHOTON_SWEEP_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
