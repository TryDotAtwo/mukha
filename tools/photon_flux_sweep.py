"""Diagnostic VisTrans photoreceptor flash sweep; run only on Molab GPU.

No CNS, camera calibration, or synaptic feedback is included. The tested photon
rates are sensitivity probes, not estimates of the Pang et al. stimulus.
"""
from pathlib import Path
import ctypes as C
import json
import time

import numpy as np


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import digest, publish
    output = root / 'data/derived/photon_flux_sweep_v1'
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
    lib.fp_build_identity.restype = C.c_char_p
    n = 128
    seed = 19503
    scales = [1_000., 10_000., 100_000., 1_000_000.]
    h = lib.fp_create(n, 30_000, seed, 128)
    if not h:
        raise RuntimeError(lib.fp_last_error())
    rate = np.empty(n, dtype=np.float64)
    state = np.empty(n * 9, dtype=np.float64)
    tick = C.c_uint64()
    traces = {}
    measurements = []
    try:
        for scale in scales:
            for mode in ['gray', 'light', 'dark']:
                if lib.fp_reset(h, seed) != 0:
                    raise RuntimeError(lib.fp_last_error())
                sample = np.empty(1020, dtype=np.float64)
                started = time.monotonic()
                for ms in range(1020):
                    photons = scale * (0.5 if ms < 500 or ms >= 520 else
                                       1.0 if mode == 'light' else 0.0)
                    rate.fill(photons)
                    if lib.fp_advance(h, rate.ctypes.data_as(C.POINTER(C.c_double)), n, 10) != 0:
                        raise RuntimeError(lib.fp_last_error())
                    if lib.fp_observe(h, state.ctypes.data_as(C.POINTER(C.c_double)),
                                      len(state), C.byref(tick)) != 0:
                        raise RuntimeError(lib.fp_last_error())
                    if tick.value != (ms + 1) * 10 or not np.isfinite(state[:n]).all():
                        raise AssertionError(('invalid state', tick.value, ms))
                    sample[ms] = state[:n].mean()
                key = f'{int(scale)}_{mode}'
                traces[key] = sample
                measurements.append({'scale_photons_s': scale, 'mode': mode,
                                     'wall_s': time.monotonic() - started,
                                     'preflash_mean_mV': float(sample[499])})
                print('PHOTON_SWEEP_CASE', key, round(measurements[-1]['wall_s'], 2),
                      'baseline', round(sample[499], 4), flush=True)
                if mode != 'gray':
                    assert np.array_equal(traces[f'{int(scale)}_gray'][:500], sample[:500])
        for scale in scales:
            gray = traces[f'{int(scale)}_gray']
            for mode, sign in [('light', 1), ('dark', -1)]:
                x = traces[f'{int(scale)}_{mode}'][500:] - gray[500:]
                peak_index = int(np.argmax(sign * x[:100]))
                initial = float(sign * x[peak_index])
                opposite = float(np.max(-sign * x[100:500]))
                measurements.append({'scale_photons_s': scale, 'mode': mode,
                                     'initial_signed_peak_mV': initial,
                                     'peak_ms': peak_index + 1,
                                     'opposite_101_500ms_mV': opposite,
                                     'opposite_to_initial_ratio': opposite / initial if initial > 0 else None,
                                     'end_response_mV': float(x[-1])})
    finally:
        lib.fp_destroy(h)
    report = {'scope': 'Standalone pinned VisTrans, 128 R1R6-like cells, 30000 microvilli/cell; one seed; no CNS or feedback; 0.1ms ticks, 1ms samples',
              'uncalibrated': True, 'biological_gate_passed': False,
              'seed': seed, 'flash': '500ms gray at half scale; 20ms light at scale or dark at zero; 500ms gray',
              'build_identity': lib.fp_build_identity().decode(),
              'measurements': measurements}
    np.savez_compressed(output / 'mean_voltage_traces.npz', **traces)
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    files = [output / 'mean_voltage_traces.npz', output / 'report.json', root / 'tools/photon_flux_sweep.py']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('PHOTON_SWEEP_REPORT', json.dumps(report), flush=True)
    print('PHOTON_SWEEP_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
