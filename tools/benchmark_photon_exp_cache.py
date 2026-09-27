"""Compare original and cached-exponential phototransduction on Molab."""
from pathlib import Path
import hashlib
import json
import numpy as np

from benchmark_photon_batch import api, case


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import digest, publish
    baseline = api(root / 'build/libfly_photon.so')
    modified = api(root / 'build/libfly_photon_exp_cache_diagnostic.so')
    output = root / 'data/derived/photon_exp_cache_benchmark_v1'
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for cells, ticks, snapshot in [(16, 100, True), (128, 1000, False), (6091, 100, False)]:
        a = case(baseline, cells, ticks, snapshot)
        b = case(modified, cells, ticks, snapshot)
        max_error = float(np.max(np.abs(a['voltage'] - b['voltage'])))
        exact_payload = a['snapshot'][192:] == b['snapshot'][192:] if snapshot else None
        rec = {'cells': cells, 'microvilli_per_cell': 30000, 'ticks': ticks,
               'baseline_elapsed_s': a['elapsed_s'], 'exp_cache_elapsed_s': b['elapsed_s'],
               'speedup': a['elapsed_s']/b['elapsed_s'], 'max_observed_state_error': max_error,
               'checkpoint_payload_exact': exact_payload}
        cases.append(rec)
        print('PHOTON_EXP_CASE', json.dumps(rec), flush=True)
    report = {'scope': 'Same chemistry and RNG, cached voltage exponential per receptor/tick; 50k photons/s, seed 19503',
              'cases': cases, 'benchmark_only': True, 'biological_gate_passed': False,
              'limitation': 'Single seed and stimulus; even exact short-run agreement is not biological validation.'}
    report_path = output / 'report.json'
    report_path.write_text(json.dumps(report, indent=2))
    files = [report_path, root / 'tools/build_photon_exp_cache.py',
             root / 'tools/benchmark_photon_exp_cache.py',
             root / 'build/phototransduction_exp_cache.cuh',
             root / 'build/photon_exp_cache_diagnostic.cu',
             root / 'build/photon_exp_cache_build_id.h',
             root / 'build/photon_exp_cache_build.json',
             root / 'build/libfly_photon_exp_cache_diagnostic.so']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                          'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('PHOTON_EXP_REPORT', json.dumps(report), flush=True)
    print('PHOTON_EXP_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
