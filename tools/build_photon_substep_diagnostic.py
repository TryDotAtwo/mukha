"""Build isolated photoreceptor HH-substep diagnostic without replacing baseline.

Changes only the existing HH Euler call from 10 x 0.01 ms to 100 x 0.001 ms.
Both integrate the same author equations over each 0.1 ms photoreceptor tick.
This is a numerical sensitivity experiment, not a validated replacement.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    source = (root / 'native/photon.cu').read_text()
    old_call = ',n,1e-5,10);'
    old_header = '../build/photon_build_id.h'
    assert source.count(old_call) == 1 and source.count(old_header) == 1
    modified = source.replace(old_call, ',n,1e-6,100);').replace(
        old_header, 'photon_substep100_build_id.h')
    src = root / 'build/photon_substep100.cu'
    header = root / 'build/photon_substep100_build_id.h'
    library = root / 'build/libfly_photon_substep100.so'
    nvcc = shutil.which('nvcc') or '/marimo/fly-project/build/cuda-13.1.1/bin/nvcc'
    assert Path(nvcc).is_file()
    cuda_root = Path(nvcc).parent.parent
    flags = ['-std=c++17', '-O2', '-lineinfo', '-arch=sm_120', '--fmad=false',
             '-shared', '-Xcompiler', '-fPIC', '-I', 'native', '-I', str(cuda_root / 'include'),
             '-L', str(cuda_root / 'lib')]
    nvcc_version = subprocess.check_output([nvcc, '--version'], text=True)
    build_spec = {'source_sha256': hashlib.sha256(modified.encode()).hexdigest(),
                  'baseline_source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                  'baseline_binary_sha256': hashlib.sha256((root / 'build/libfly_photon.so').read_bytes()).hexdigest(),
                  'flags': flags, 'nvcc_version': nvcc_version,
                  'change': 'HH Euler 10x0.01ms -> 100x0.001ms; no other equation or input change'}
    identity = hashlib.sha256(json.dumps(build_spec, sort_keys=True).encode()).hexdigest()
    if src.exists():
        assert src.read_text() == modified
    else:
        src.write_text(modified)
    wanted_header = '#pragma once\n#define FP_BUILD_ID "' + identity + '"\n'
    if header.exists() and header.read_text() != wanted_header:
        assert not library.exists(), 'Refusing to retag an existing diagnostic binary'
    header.write_text(wanted_header)
    command = [nvcc, *flags, str(src.relative_to(root)), '-o', str(library.relative_to(root))]
    try:
        subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        print('PHOTON_SUBSTEP_BUILD_STDERR', exc.stderr[-4000:], flush=True)
        raise
    build_spec['build_identity'] = identity
    build_spec['binary_sha256'] = hashlib.sha256(library.read_bytes()).hexdigest()
    (root / 'build/photon_substep100_build.json').write_text(json.dumps(build_spec, indent=2))
    print('PHOTON_SUBSTEP100_BUILD', json.dumps(build_spec), flush=True)
    return build_spec


if __name__ == '__main__':
    run()
