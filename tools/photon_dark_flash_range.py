"""Bounded failure characterization for dark-adapted 10-ms photon pulse."""
from pathlib import Path
import ctypes as C
import json

import numpy as np


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import digest, publish
    output = root / 'data/derived/photon_dark_flash_range_v1'
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
    n, seed, steps = 64, 19503, 1010
    rates = [10_000., 100_000., 1_000_000., 10_000_000.]
    h = lib.fp_create(n, 30000, seed, 128)
    if not h:
        raise RuntimeError(lib.fp_last_error())
    voltage = np.empty(n * 9, dtype=np.float64)
    tick = C.c_uint64()
    traces, records = {}, []
    try:
        for photons_s in rates:
            if lib.fp_reset(h, seed) != 0:
                raise RuntimeError(lib.fp_last_error())
            input_rate = np.zeros(n, np.float64)
            values = np.empty((steps, n), np.float32)
            completed = 0
            failure = None
            for ms in range(steps):
                input_rate.fill(photons_s if 500 <= ms < 510 else 0)
                if lib.fp_advance(h, input_rate.ctypes.data_as(C.POINTER(C.c_double)), n, 10) != 0:
                    failure = {'sample_ms': ms + 1, 'phase': 'pulse' if ms < 510 else 'recovery',
                               'message': lib.fp_last_error().decode(errors='replace')}
                    break
                if lib.fp_observe(h, voltage.ctypes.data_as(C.POINTER(C.c_double)),
                                  len(voltage), C.byref(tick)) != 0:
                    raise RuntimeError(lib.fp_last_error())
                if tick.value != (ms + 1) * 10 or not np.isfinite(voltage[:n]).all():
                    raise AssertionError((photons_s, ms, tick.value))
                values[ms] = voltage[:n]
                completed += 1
            traces[str(int(photons_s))] = values[:completed]
            peak = float(np.max(values[500:completed].mean(axis=1) - values[499].mean())) if completed > 500 else None
            record = {'photons_s': photons_s, 'estimated_pulse_photons': photons_s * 0.01,
                      'completed_samples_ms': completed, 'failure': failure,
                      'baseline_mV': float(values[499].mean()) if completed > 499 else None,
                      'peak_delta_from_preflash_mV': peak}
            records.append(record)
            print('DARK_FLASH_RANGE_CASE', json.dumps(record), flush=True)
    finally:
        lib.fp_destroy(h)
    report = {'scope': 'Standalone VisTrans, 64 receptors x 30000 microvilli; 500ms dark, 10ms pulse, 500ms dark; 0.1ms neural ticks; one seed',
              'reason': 'Previous 1e7 photons/s case failed with Photoreceptor gate outside [0,1]',
              'build_identity': lib.fp_build_identity().decode(), 'seed': seed,
              'external_reference': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4323538/',
              'target_stimulus_estimate': 'approximately 1e5 effective photons in a 10ms pulse; equivalence to model photon input is unverified',
              'results': records, 'biological_gate_passed': False}
    np.savez_compressed(output / 'partial_voltage_traces.npz', **traces)
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    files = [output / 'partial_voltage_traces.npz', output / 'report.json',
             root / 'tools/photon_dark_flash_range.py', root / 'tools/photon_dark_flash_probe.py']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('DARK_FLASH_RANGE_REPORT', json.dumps(report), flush=True)
    print('DARK_FLASH_RANGE_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
