"""Paired Molab speed and impulse-response validation for sampled receptors."""
from pathlib import Path
import ctypes as C
import json
import time

import numpy as np
from benchmark_photon_batch import api, case


def trace(lib, cells, microvilli, seed, pulse_rate):
    handle = lib.fp_create(cells, microvilli, seed, 128)
    if not handle:
        raise RuntimeError(lib.fp_last_error())
    observation = np.empty(9*cells, np.float64)
    tick = C.c_uint64()
    output = []
    elapsed = 0.0
    try:
        # Gray, 20-ms contrast pulse, gray. One observation per simulated ms.
        for ms in range(320):
            rate = 50000.0 if ms < 100 or ms >= 120 else pulse_rate
            stimulus = np.full(cells, rate, np.float64)
            start = time.perf_counter()
            rc = lib.fp_advance(handle, stimulus.ctypes.data_as(C.POINTER(C.c_double)), cells, 10)
            elapsed += time.perf_counter() - start
            if rc:
                raise RuntimeError((ms, microvilli, seed, lib.fp_last_error()))
            if lib.fp_observe(handle, observation.ctypes.data_as(C.POINTER(C.c_double)),
                              observation.size, C.byref(tick)):
                raise RuntimeError(lib.fp_last_error())
            output.append(observation[:cells].copy())
        assert tick.value == 3200
        return np.stack(output), elapsed
    finally:
        lib.fp_destroy(handle)


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import digest, publish
    baseline = api(root / 'build/libfly_photon.so')
    sampled = api(root / 'build/libfly_photon_sampled_diagnostic.so')
    output = root / 'data/derived/photon_sampled_benchmark_v1'
    output.mkdir(parents=True, exist_ok=False)
    exact_a = case(baseline, 16, 100, True)
    exact_b = case(sampled, 16, 100, True)
    exact = {'same_observation': bool(np.array_equal(exact_a['voltage'], exact_b['voltage'])),
             'same_checkpoint_payload': exact_a['snapshot'][192:] == exact_b['snapshot'][192:]}
    print('SAMPLED_FULL_COUNT_REGRESSION', json.dumps(exact), flush=True)
    assert exact['same_observation'] and exact['same_checkpoint_payload']
    seeds = [19503, 19504, 19505]
    rows = []
    traces = {}
    for pulse_name, pulse_rate in [('light', 100000.), ('dark', 0.)]:
        for seed in seeds:
            reference, reference_s = trace(baseline, 32, 30000, seed, pulse_rate)
            traces[f'{pulse_name}_reference_{seed}'] = reference.astype(np.float32)
            print('SAMPLED_REFERENCE', json.dumps({'pulse': pulse_name, 'seed': seed,
                                                    'elapsed_s': reference_s}), flush=True)
            for m in [256, 1024, 4096]:
                candidate, duration = trace(sampled, 32, m, seed, pulse_rate)
                traces[f'{pulse_name}_{m}_{seed}'] = candidate.astype(np.float32)
                # Evaluate population mean dynamics and cell-level error separately.
                ref_mean = reference.mean(axis=1)
                cand_mean = candidate.mean(axis=1)
                response_ref = ref_mean[100:] - ref_mean[99]
                response_cand = cand_mean[100:] - cand_mean[99]
                peak_ref = float(np.max(np.abs(response_ref)))
                rmse = float(np.sqrt(np.mean((response_ref-response_cand)**2)))
                cell_rmse = float(np.sqrt(np.mean((reference[100:]-candidate[100:])**2)))
                row = {'pulse': pulse_name, 'seed': seed, 'microvilli_sampled': m,
                       'reference_elapsed_s': reference_s, 'sampled_elapsed_s': duration,
                       'response_peak_ref_mV': peak_ref, 'mean_response_rmse_mV': rmse,
                       'mean_response_rmse_fraction_of_peak': rmse/max(peak_ref, 1e-12),
                       'cell_voltage_rmse_mV': cell_rmse}
                rows.append(row)
                print('SAMPLED_RESPONSE_CASE', json.dumps(row), flush=True)
    speed_rows = []
    for m in [256, 1024, 4096]:
        handle = sampled.fp_create(6091, m, 19503, 128)
        if not handle:
            raise RuntimeError(sampled.fp_last_error())
        stimulus = np.full(6091, 50000., np.float64)
        try:
            start = time.perf_counter()
            rc = sampled.fp_advance(handle, stimulus.ctypes.data_as(C.POINTER(C.c_double)), 6091, 100)
            duration = time.perf_counter()-start
            if rc:
                raise RuntimeError(sampled.fp_last_error())
        finally:
            sampled.fp_destroy(handle)
        speed_rows.append({'microvilli_sampled': m, 'cells': 6091, 'ticks': 100,
                           'elapsed_s': duration, 'baseline_elapsed_s': 6.57168,
                           'speedup_vs_previous_baseline': 6.57168/duration})
        print('SAMPLED_SPEED_CASE', json.dumps(speed_rows[-1]), flush=True)
    np.savez_compressed(output/'traces.npz', **traces)
    report = {'scope': 'Diagnostic Monte Carlo sampling of VisTrans microvilli; physical count fixed at 30000, same per-microvillus chemistry',
              'seeds': seeds, 'pulse_protocol_ms': {'gray_before': 100, 'pulse': 20, 'gray_after': 200},
              'gray_photons_per_s': 50000, 'light_photons_per_s': 100000,
              'exact_full_count_regression': exact, 'response_cases': rows,
              'full_retina_speed_cases': speed_rows, 'biological_gate_passed': False,
              'limitation': 'Uncalibrated input and one temporal protocol; population mean comparison cannot establish biological fidelity or closed-loop equivalence.'}
    (output/'report.json').write_text(json.dumps(report, indent=2))
    files = [output/'report.json', output/'traces.npz',
             root/'tools/build_photon_sampled.py', root/'tools/benchmark_photon_sampled.py',
             root/'build/phototransduction_sampled.cuh', root/'build/photocurrent_sampled.cuh',
             root/'build/photon_sampled_diagnostic.cu', root/'build/photon_sampled_build_id.h',
             root/'build/photon_sampled_build.json', root/'build/libfly_photon_sampled_diagnostic.so']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                          'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('SAMPLED_REPORT', json.dumps(report), flush=True)
    print('SAMPLED_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
