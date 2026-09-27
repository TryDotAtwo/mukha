"""Exact split-call and checkpoint replay for the isolated counter RNG receptor."""
from pathlib import Path
import argparse
import ctypes as c
import hashlib
import json
import subprocess
import sys


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def api(root):
    lib = c.CDLL(str(root / 'data/derived/photon_counter_candidate_v2/libfly_photon_counter_diagnostic.so'))
    lib.fp_create.argtypes = [c.c_uint32, c.c_uint32, c.c_uint64, c.c_uint32]
    lib.fp_create.restype = c.c_void_p
    lib.fp_destroy.argtypes = [c.c_void_p]
    lib.fp_reset.argtypes = [c.c_void_p, c.c_uint64]
    lib.fp_advance.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t, c.c_uint32]
    lib.fp_observe.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_uint64)]
    lib.fp_checkpoint_size.argtypes = [c.c_void_p]
    lib.fp_checkpoint_size.restype = c.c_size_t
    lib.fp_save.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t]
    lib.fp_load.argtypes = [c.c_void_p, c.c_void_p, c.c_size_t]
    lib.fp_build_identity.restype = c.c_char_p
    lib.fp_last_error.restype = c.c_char_p
    return lib


def checked(lib, code):
    if code:
        raise RuntimeError(lib.fp_last_error().decode())


def snapshot(lib, model):
    size = lib.fp_checkpoint_size(model)
    if not size:
        raise RuntimeError('checkpoint size is zero')
    buffer = (c.c_ubyte * size)()
    checked(lib, lib.fp_save(model, buffer, size))
    return bytes(buffer)


def advance(lib, model, ticks):
    rate = (c.c_double * 1)(50000.)
    checked(lib, lib.fp_advance(model, c.addressof(rate), 1, ticks))


def exercise(root, phase):
    folder = root / 'data/derived/photon_counter_replay_v1'
    lib = api(root)
    model = lib.fp_create(1, 30000, 19503, 1024)
    if not model:
        raise RuntimeError(lib.fp_last_error().decode())
    try:
        if phase == 'fresh':
            middle = (folder / 'midpoint.bin').read_bytes()
            buffer = (c.c_ubyte * len(middle)).from_buffer_copy(middle)
            checked(lib, lib.fp_load(model, buffer, len(middle)))
            advance(lib, model, 5)
            result = snapshot(lib, model)
            (folder / 'fresh_final.bin').write_bytes(result)
            if result != (folder / 'baseline_final.bin').read_bytes():
                raise RuntimeError('fresh process continuation differed')
            return {'fresh_process_exact': True, 'final_sha256': hashlib.sha256(result).hexdigest()}

        advance(lib, model, 5)
        middle = snapshot(lib, model)
        (folder / 'midpoint.bin').write_bytes(middle)
        if int.from_bytes(middle[8:16], 'little') != 2:
            raise RuntimeError('candidate checkpoint version is not 2')
        advance(lib, model, 5)
        baseline = snapshot(lib, model)
        (folder / 'baseline_final.bin').write_bytes(baseline)
        buffer = (c.c_ubyte * len(middle)).from_buffer_copy(middle)
        checked(lib, lib.fp_load(model, buffer, len(middle)))
        advance(lib, model, 5)
        if snapshot(lib, model) != baseline:
            raise RuntimeError('same-process checkpoint continuation differed')
        checked(lib, lib.fp_reset(model, 19503))
        for _ in range(5):
            advance(lib, model, 1)
        if snapshot(lib, model) != middle:
            raise RuntimeError('split advance calls differed')
        invalid = bytearray(middle)
        invalid[8] = 1
        bad = (c.c_ubyte * len(invalid)).from_buffer_copy(invalid)
        if lib.fp_load(model, bad, len(invalid)) == 0:
            raise RuntimeError('version-1 checkpoint was accepted')
        if snapshot(lib, model) != middle:
            raise RuntimeError('rejected checkpoint mutated model')
        observation = (c.c_double * 9)()
        tick = c.c_uint64()
        checked(lib, lib.fp_observe(model, observation, 9, c.byref(tick)))
        if tick.value != 5:
            raise RuntimeError('wrong tick after split replay')
        return {'same_process_exact': True, 'split_call_exact': True,
                'old_version_rejected_before_mutation': True,
                'checkpoint_bytes': len(middle),
                'midpoint_sha256': hashlib.sha256(middle).hexdigest(),
                'final_sha256': hashlib.sha256(baseline).hexdigest(),
                'tick': tick.value, 'voltage_mV': observation[0],
                'build_id': lib.fp_build_identity().decode()}
    finally:
        lib.fp_destroy(model)


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import publish
    folder = root / 'data/derived/photon_counter_replay_v1'
    folder.mkdir(parents=True, exist_ok=False)
    baseline = exercise(root, 'baseline')
    script = root / 'tools/check_photon_counter_replay.py'
    resumed = subprocess.run([sys.executable, str(script), '--phase', 'fresh',
                              '--root', str(root)], capture_output=True,
                             text=True, timeout=120)
    if resumed.returncode:
        raise RuntimeError(resumed.stderr[-2000:])
    fresh = json.loads(resumed.stdout.split('COUNTER_FRESH_RESULT ')[-1])
    if fresh['final_sha256'] != baseline['final_sha256']:
        raise RuntimeError('fresh-process final digest differs')
    report = {'scope': 'Counter RNG one-receptor exact split-call/checkpoint replay',
              'candidate_binary_sha256': digest(root / 'data/derived/photon_counter_candidate_v2/libfly_photon_counter_diagnostic.so'),
              'baseline': baseline, 'fresh': fresh,
              'limitations': 'One receptor, 10 total ticks, one seed/input; no source-XORWOW distribution or speed claim.'}
    result = folder / 'report.json'
    result.write_text(json.dumps(report, indent=2))
    files = [script, result, folder / 'midpoint.bin', folder / 'baseline_final.bin',
             folder / 'fresh_final.bin']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('COUNTER_REPLAY_RESULT', json.dumps(report), flush=True)
    print('COUNTER_REPLAY_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['fresh'])
    parser.add_argument('--root', type=Path, default=Path('/marimo/fly-project'))
    args = parser.parse_args()
    if args.phase:
        print('COUNTER_FRESH_RESULT ' + json.dumps(exercise(args.root, args.phase)))
    else:
        run(args.root)
