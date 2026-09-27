"""Build isolated GPU-batched photoreceptor benchmark without changing equations.

This removes per-tick host synchronization/validation, retaining the same GPU
kernel sequence and validating on fp_advance return. Benchmark-only until
intermediate validity checks are restored on device and checkpoint equivalence
is demonstrated.
"""
from pathlib import Path
import hashlib
import json
import subprocess


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    original = (root / 'native/photon.cu').read_text()
    assert original.count('check(cudaGetLastError()); check(cudaDeviceSynchronize());') == 1
    snippet = '''            check(cudaMemcpy(host.data(),state.p,host.size()*sizeof(double),cudaMemcpyDeviceToHost));
            for(int i=0;i<7*n;++i) if(!std::isfinite(host[i]))
                throw std::runtime_error("Nonfinite photoreceptor state");
            for(int i=n;i<6*n;++i) if(host[i]<0 || host[i]>1)
                throw std::runtime_error("Photoreceptor gate outside [0,1]");
            ++tick;
        }
        healthy=true;'''
    replacement = '''            ++tick;
        }
        check(cudaMemcpy(host.data(),state.p,host.size()*sizeof(double),cudaMemcpyDeviceToHost));
        for(int i=0;i<7*n;++i) if(!std::isfinite(host[i]))
            throw std::runtime_error("Nonfinite photoreceptor state");
        for(int i=n;i<6*n;++i) if(host[i]<0 || host[i]>1)
            throw std::runtime_error("Photoreceptor gate outside [0,1]");
        healthy=true;'''
    assert original.count(snippet) == 1
    modified = original.replace('check(cudaGetLastError()); check(cudaDeviceSynchronize());',
                                'check(cudaGetLastError());').replace(snippet, replacement)
    modified = modified.replace('../build/photon_build_id.h', 'photon_batch_build_id.h')
    assert modified != original
    src = root / 'build/photon_batch_diagnostic.cu'
    header = root / 'build/photon_batch_build_id.h'
    library = root / 'build/libfly_photon_batch_diagnostic.so'
    nvcc = root / 'build/cuda-13.1.1/bin/nvcc'
    assert nvcc.is_file(), 'Molab CUDA toolchain not restored'
    cuda_root = nvcc.parent.parent
    flags = ['-std=c++17', '-O2', '-lineinfo', '-arch=sm_120', '--fmad=false',
             '-shared', '-Xcompiler', '-fPIC', '-I', 'native', '-I', str(cuda_root / 'include'),
             '-L', str(cuda_root / 'lib')]
    spec = {'baseline_source_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'modified_source_sha256': hashlib.sha256(modified.encode()).hexdigest(),
            'baseline_binary_sha256': hashlib.sha256((root / 'build/libfly_photon.so').read_bytes()).hexdigest(),
            'flags': flags, 'nvcc_version': subprocess.check_output([str(nvcc), '--version'], text=True),
            'change': 'Same GPU kernels/order; remove per-tick device sync and host D2H/validation; validate once at end of advance; benchmark-only'}
    identity = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    if src.exists():
        assert src.read_text() == modified
    else:
        src.write_text(modified)
    wanted_header = '#pragma once\n#define FP_BUILD_ID "' + identity + '"\n'
    if header.exists() and header.read_text() != wanted_header:
        assert not library.exists()
    header.write_text(wanted_header)
    command = [str(nvcc), *flags, str(src.relative_to(root)), '-o', str(library.relative_to(root))]
    try:
        subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        print('PHOTON_BATCH_BUILD_STDERR', exc.stderr[-4000:], flush=True)
        raise
    spec['build_identity'] = identity
    spec['binary_sha256'] = hashlib.sha256(library.read_bytes()).hexdigest()
    (root / 'build/photon_batch_build.json').write_text(json.dumps(spec, indent=2))
    print('PHOTON_BATCH_BUILD', json.dumps(spec), flush=True)
    return spec


if __name__ == '__main__':
    run()
