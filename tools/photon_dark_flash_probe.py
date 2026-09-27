"""Exploratory 10-ms dark-adapted R1R6 flash amplitude against published range.

External target: PMID 25673862 / PMC4323538 reports ~40-60 mV for a
saturating 10-ms pulse estimated at ~1e5 effective photons. This model input
is set to 1e7 photons/s for 10 ms; equality of 'effective' units is unproved.
"""
from pathlib import Path
import ctypes as C
import json

import numpy as np


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import digest, publish
    output = root / 'data/derived/photon_dark_flash_v1'
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
    h = lib.fp_create(n, 30000, seed, 128)
    if not h:
        raise RuntimeError(lib.fp_last_error())
    voltage = np.empty(n * 9, dtype=np.float64)
    tick = C.c_uint64()
    traces = {}
    try:
        for condition in ('dark', 'flash'):
            if lib.fp_reset(h, seed) != 0:
                raise RuntimeError(lib.fp_last_error())
            rates = np.zeros(n, np.float64)
            samples = np.empty((steps, n), np.float32)
            for ms in range(steps):
                rates.fill(1e7 if condition == 'flash' and 500 <= ms < 510 else 0)
                if lib.fp_advance(h, rates.ctypes.data_as(C.POINTER(C.c_double)), n, 10) != 0:
                    raise RuntimeError(lib.fp_last_error())
                if lib.fp_observe(h, voltage.ctypes.data_as(C.POINTER(C.c_double)),
                                  len(voltage), C.byref(tick)) != 0:
                    raise RuntimeError(lib.fp_last_error())
                if tick.value != (ms + 1) * 10 or not np.isfinite(voltage[:n]).all():
                    raise AssertionError((condition, ms, tick.value))
                samples[ms] = voltage[:n]
            traces[condition] = samples
            print('DARK_FLASH_CASE', condition, float(samples[499].mean()),
                  float(samples[-1].mean()), flush=True)
    finally:
        lib.fp_destroy(h)
    assert np.array_equal(traces['dark'][:500], traces['flash'][:500])
    response = traces['flash'].astype(np.float64) - traces['dark'].astype(np.float64)
    population = response.mean(axis=1)
    peak_offset = int(np.argmax(population[500:700]))
    peak_index = 500 + peak_offset
    per_cell_peak = response[500:700].max(axis=0)
    report = {'scope': 'Standalone pinned VisTrans; 64 cells x 30000 microvilli; dark-adapted 500ms, then 10ms at 1e7 photons/s, then dark; 0.1ms ticks, 1ms samples; single seed',
              'external_reference': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4323538/',
              'external_reference_statement': 'Typical selected R1-R6: dark resting < -55mV; saturating 10ms pulse estimated ~1e5 effective photons produces ~40-60mV response, at 20 +/- 1 C.',
              'assumed_photon_equivalence': False, 'temperature_matched': False,
              'source_build_identity': lib.fp_build_identity().decode(),
              'seed': seed, 'cells': n, 'preflash_exact': True,
              'baseline_mV': float(traces['flash'][499].mean()),
              'population_peak_delta_mV': float(population[peak_index]),
              'population_peak_time_ms_after_onset': peak_offset + 1,
              'per_cell_peak_delta_mV': {'min': float(per_cell_peak.min()),
                                         'median': float(np.median(per_cell_peak)),
                                         'max': float(per_cell_peak.max())},
              'overlaps_external_amplitude_range': bool(40 <= population[peak_index] <= 60),
              'biological_gate_passed': False}
    np.savez_compressed(output / 'voltage_traces.npz', **traces)
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    files = [output / 'voltage_traces.npz', output / 'report.json', root / 'tools/photon_dark_flash_probe.py']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('DARK_FLASH_REPORT', json.dumps(report), flush=True)
    print('DARK_FLASH_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
