"""Compare HH 100-substep diagnostic to preserved baseline receptor traces."""
from pathlib import Path
import ctypes as C
import json

import numpy as np


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import digest, publish
    output = root / 'data/derived/photon_substep100_diagnostic_v1'
    output.mkdir(parents=True, exist_ok=False)
    build = json.loads((root / 'build/photon_substep100_build.json').read_text())
    library = root / 'build/libfly_photon_substep100.so'
    assert digest(library) == build['binary_sha256']
    lib = C.CDLL(str(library))
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
    assert lib.fp_build_identity().decode() == build['build_identity']
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
            completed, failure = 0, None
            for ms in range(steps):
                input_rate.fill(photons_s if 500 <= ms < 510 else 0)
                if lib.fp_advance(h, input_rate.ctypes.data_as(C.POINTER(C.c_double)), n, 10) != 0:
                    failure = {'sample_ms': ms + 1,
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
            record = {'photons_s': photons_s, 'completed_samples_ms': completed,
                      'failure': failure,
                      'peak_delta_from_preflash_mV': float(values[500:completed].mean(axis=1).max() - values[499].mean()) if completed > 500 else None,
                      'max_cell_voltage_mV': float(values[:completed].max()) if completed else None}
            records.append(record)
            print('SUBSTEP100_CASE', json.dumps(record), flush=True)
    finally:
        lib.fp_destroy(h)
    baseline_path = root / 'data/derived/photon_dark_flash_range_v1/partial_voltage_traces.npz'
    comparisons = []
    with np.load(baseline_path) as baseline:
        for photons_s in rates:
            key = str(int(photons_s))
            old = baseline[key]
            new = traces[key]
            shared = min(len(old), len(new))
            delta = new[:shared].astype(np.float64) - old[:shared].astype(np.float64)
            comparisons.append({'photons_s': photons_s, 'baseline_samples': len(old),
                                'substep100_samples': len(new),
                                'max_abs_voltage_difference_mV_on_shared_prefix': float(np.abs(delta).max()),
                                'rms_voltage_difference_mV_on_shared_prefix': float(np.sqrt(np.mean(delta**2))),
                                'preflash_exact': bool(np.array_equal(old[:500], new[:500]))})
    report = {'scope': 'Numerical sensitivity only: author HH Euler equations integrated as 100x0.001ms vs 10x0.01ms per 0.1ms neural tick; other equations unchanged',
              'build_identity': build['build_identity'],
              'baseline_build_identity': '8f3eae84b1b13162b068dc72b6dc3ea1bcc42e017addd3c1be5e1174c5a12e16',
              'seed': seed, 'results': records, 'comparisons': comparisons,
              'adopted_as_biological_model': False, 'biological_gate_passed': False}
    np.savez_compressed(output / 'voltage_traces.npz', **traces)
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    files = [output / 'voltage_traces.npz', output / 'report.json',
             root / 'build/photon_substep100.cu', root / 'build/photon_substep100_build_id.h',
             root / 'build/photon_substep100_build.json', library,
             root / 'tools/build_photon_substep_diagnostic.py',
             root / 'tools/check_photon_substep_diagnostic.py',
             root / 'build/photoreceptor_author_hh.cu',
             root / 'build/photoreceptor_author_adaptation.cu']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('SUBSTEP100_REPORT', json.dumps(report), flush=True)
    print('SUBSTEP100_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
