"""Compare pinned CUDA Philox with independent CPU vectors on Molab."""
from pathlib import Path
import hashlib
import json
import subprocess

from reference.philox_counter import words, draw, uniform_bits


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    from hf_artifact_archive import publish
    cuda = root / 'build/cuda-13.1.1'
    source = root / 'native/philox_counter_probe.cu'
    folder = root / 'data/derived/philox_counter_mapping_v2'
    folder.mkdir(parents=True, exist_ok=False)
    binary = folder / 'philox_counter_probe'
    command = [str(cuda / 'bin/nvcc'), '-std=c++17', '-O2', '-arch=sm_120',
               '-I', str(cuda / 'include'), '-L', str(cuda / 'lib'),
               str(source), '-o', str(binary)]
    built = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if built.returncode:
        raise RuntimeError(built.stderr[-3000:])
    cases = [
        (0, 0, 0, 0),
        (19503, 0, 0, 0),
        (19503, 1, 0, 0),
        (19503, 0, 1, 0),
        (19503, 0, 1, 1),
        (19503, 101309999, 1 << 32 | 7, 0),
        ((1 << 64) - 1, 101309999, (1 << 64) - 1, (1 << 32) - 1),
    ]
    vectors = []
    for case in cases:
        raw = words(*case)
        expected = raw + tuple(uniform_bits(value) for value in raw)
        observed = []
        for _ in range(2):
            p = subprocess.run([str(binary), *map(str, case)],
                               capture_output=True, text=True, timeout=30)
            if p.returncode:
                raise RuntimeError(p.stderr[-1000:])
            observed.append(tuple(map(int, p.stdout.split())))
        if observed != [expected, expected]:
            raise RuntimeError(f'Philox vector mismatch: {case}, {expected}, {observed}')
        vectors.append({'seed': case[0], 'id': case[1], 'tick': case[2],
                        'draw_block': case[3], 'words': list(raw),
                        'uniform_fp32_bits': list(expected[4:])})
    if words(0, 0, 0, 0) != (0x6627e8d5, 0xe169c58d, 0xbc57ac4c, 0x9b00dbd8):
        raise RuntimeError('known-answer vector mismatch')
    for seed, entity, tick, _ in cases:
        for index in range(8):
            if draw(seed, entity, tick, index) != words(seed, entity, tick, index >> 2)[index & 3]:
                raise RuntimeError('draw block/lane mismatch')
    report = {
        'scope': 'Pinned CUDA Philox counter/key and FP32 uniform mapping against independent CPU oracle',
        'mapping': 'key=[seed_lo32,seed_hi32], counter=[entity_id,tick_lo32,tick_hi32,draw_block], draw_lane=index%4',
        'source_sha256': digest(source), 'binary_sha256': digest(binary),
        'cuda_header_sha256': digest(cuda / 'include/curand_philox4x32_x.h'),
        'cuda_uniform_header_sha256': digest(cuda / 'include/curand_uniform.h'),
        'build_command': command, 'vectors': vectors,
        'all_vectors_passed': True,
        'limitations': 'Mapping/deterministic replay vectors only; no retina distribution, checkpoint, statistical-quality or speed test.'
    }
    result = folder / 'report.json'
    result.write_text(json.dumps(report, indent=2))
    files = [source, binary, result, root / 'reference/philox_counter.py',
             root / 'tools/check_philox_counter_mapping.py']
    manifest = {'schema': 'faithful-fly-artifacts-v1', 'scope': report['scope'],
                'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                                                           'sha256': digest(p)} for p in files}}
    receipt = publish(root, manifest)
    print('PHILOX_MAPPING_RESULT', json.dumps({'vectors': len(vectors), 'passed': True}), flush=True)
    print('PHILOX_MAPPING_ARCHIVE', json.dumps(receipt), flush=True)
    return receipt


if __name__ == '__main__':
    run()
