"""Run the native CUDA replay on the Brian2 fixture; Python is only a test host."""
import ctypes as ct
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class Params(ct.Structure):
    _fields_ = [(k, ct.c_float) for k in ('dt', 'rest', 'reset', 'threshold', 'membrane', 'synapse')] + [
        ('refractory', ct.c_uint32), ('delay', ct.c_uint32)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instrumentation', choices=['none', 'memcheck', 'racecheck', 'initcheck', 'synccheck'], default='none')
    parser.add_argument('--author',choices=['shiu','dallmann'],default='shiu')
    args = parser.parse_args()
    dll_dir = os.add_dll_directory(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin') if os.name == 'nt' else None
    library = ROOT / ('build/fly_cuda_probe.dll' if os.name == 'nt' else 'build/libfly_cuda_probe.so')
    lib = ct.CDLL(str(library))
    lib.ff_cuda_probe_error.restype = ct.c_char_p
    lib.ff_cuda_probe.argtypes = [ct.c_uint32, ct.c_uint64] + [ct.c_void_p] * 4 + [Params, ct.c_uint32] + [ct.c_void_p] * 4
    lib.ff_cuda_probe.restype = ct.c_int
    prefix='' if args.author=='shiu' else 'dallmann_'
    fixture_path = ROOT / ('build/'+prefix+'brian_fixture.json')
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    n = fixture['n']
    pre, post = np.asarray(fixture['pre']), np.asarray(fixture['post'])
    order = np.lexsort((pre, post))
    ptr = np.concatenate(([0], np.cumsum(np.bincount(post, minlength=n)))).astype(np.uint64)
    col = pre[order].astype(np.uint32)
    weights = np.asarray(fixture['weights_mv'], dtype=np.float32)[order]
    sensory = np.zeros(n, dtype=np.uint8)
    sensory[fixture['sensory']] = 1
    drive = np.asarray(fixture['stimuli'], dtype=np.float32)
    params = Params(0.1, -52, -52, -45, 20, 5, 22, 18)
    outputs = []
    started = time.monotonic()
    for _ in range(2):
        v, g, s = np.empty_like(drive), np.empty_like(drive), np.empty(drive.shape, dtype=np.uint8)
        pointers = [ct.c_void_p(a.ctypes.data) for a in (ptr, col, weights, sensory)]
        result = lib.ff_cuda_probe(n, len(col), *pointers, params, len(drive),
                                  *[ct.c_void_p(a.ctypes.data) for a in (drive, v, g, s)])
        if result:
            raise RuntimeError(lib.ff_cuda_probe_error().decode())
        outputs.append((v, g, s))
    elapsed = time.monotonic() - started
    v, g, s = outputs[0]
    dv = float(np.max(np.abs(v - np.asarray(fixture['expected_v']))))
    dg = float(np.max(np.abs(g - np.asarray(fixture['expected_g']))))
    mismatch = int(np.count_nonzero(s != np.asarray(fixture['expected_spikes'])))
    repeat = all(np.array_equal(a, b) for a, b in zip(*outputs))
    passed = bool(np.isfinite(v).all() and np.isfinite(g).all() and dv < 0.002 and dg < 0.002 and mismatch == 0 and repeat)
    hardware = subprocess.check_output(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'], text=True).strip()
    report = dict(backend='native-cuda-fp32-cusparse-csr-alg2', hardware=hardware,
                  fixture_sha256=hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
                  library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
                  neurons=n, steps=len(drive), max_voltage_error_mv=dv, max_synapse_error_mv=dg,
                  spike_mismatches=mismatch, repeated_run_bit_exact=repeat, passed=passed,
                  two_replays_wall_seconds=elapsed, instrumentation=args.instrumentation,
                  scope='physical GPU numerical fixture only; no full-graph or biological validation; no checkpoint API yet')
    suffix = '' if args.instrumentation == 'none' else '_' + args.instrumentation
    (ROOT / ('reports/'+prefix+'cuda_brian_equivalence' + suffix + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if dll_dir:
        dll_dir.close()
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
