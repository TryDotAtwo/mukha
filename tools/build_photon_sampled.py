"""Build diagnostic Monte Carlo sampling of the pinned 30k-microvillus receptor."""
from pathlib import Path
import hashlib
import json
import subprocess


def replace_one(source, old, new):
    assert source.count(old) == 1, (old, source.count(old))
    return source.replace(old, new)


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    trans = (root / 'native/phototransduction_safe.cuh').read_text()
    trans = replace_one(trans, 'int* num_microvilli, int total_microvilli, int* count)',
                        'int* num_microvilli, int total_microvilli, int physical_microvilli, int* count)')
    trans = replace_one(trans, 'lambda = input[ind]/(double)num_microvilli[ind];',
                        'lambda = input[ind]/(double)physical_microvilli;')
    current = (root / 'native/photocurrent_safe.cuh').read_text()
    current = replace_one(current, 'double* I_fb)\n{', 'double* I_fb, double current_scale)\n{')
    current = replace_one(current, 'I_in = total_open_channel * G_TRP * (-Vm);',
                          'I_in = total_open_channel * G_TRP * (-Vm) * current_scale;')
    trans_path = root / 'build/phototransduction_sampled.cuh'
    current_path = root / 'build/photocurrent_sampled.cuh'
    trans_path.write_text(trans)
    current_path.write_text(current)
    source = (root / 'native/photon.cu').read_text()
    source = replace_one(source, '../build/photon_build_id.h', 'photon_sampled_build_id.h')
    source = replace_one(source, '"phototransduction_safe.cuh"',
                         '"phototransduction_sampled.cuh"')
    source = replace_one(source, '"photocurrent_safe.cuh"', '"photocurrent_sampled.cuh"')
    source = replace_one(source, 'counts.p,total,counter.p);',
                         'counts.p,total,30000,counter.p);')
    source = replace_one(source, 'state.p,current.p,feedback.p);',
                         'state.p,current.p,feedback.p,30000.0/double(m));')
    source = replace_one(source, '        cudaDeviceProp properties{};',
                         '        if(m<=0 || m>30000) throw std::invalid_argument("Sampled microvilli must be in [1,30000]");\n        cudaDeviceProp properties{};')
    src_path = root / 'build/photon_sampled_diagnostic.cu'
    header = root / 'build/photon_sampled_build_id.h'
    library = root / 'build/libfly_photon_sampled_diagnostic.so'
    src_path.write_text(source)
    identity = hashlib.sha256((source+trans+current).encode()).hexdigest()
    header.write_text('#pragma once\n#define FP_BUILD_ID "'+identity+'"\n')
    nvcc = root / 'build/cuda-13.1.1/bin/nvcc'
    cuda_root = nvcc.parent.parent
    command = [str(nvcc), '-std=c++17', '-O2', '-lineinfo', '-arch=sm_120', '--fmad=false',
               '-shared', '-Xcompiler', '-fPIC', '-I', 'native', '-I', 'build',
               '-I', str(cuda_root / 'include'), '-L', str(cuda_root / 'lib'),
               str(src_path.relative_to(root)), '-o', str(library.relative_to(root))]
    try:
        subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        print('PHOTON_SAMPLED_BUILD_ERROR', exc.stderr[-4000:], flush=True)
        raise
    record = {'identity': identity, 'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
              'transduction_sha256': hashlib.sha256(trans.encode()).hexdigest(),
              'current_sha256': hashlib.sha256(current.encode()).hexdigest(),
              'binary_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
              'physical_microvilli': 30000,
              'method': 'Monte Carlo subsampling with unchanged per-microvillus reaction law, physical photon hazard, and scaled current; diagnostic only'}
    (root / 'build/photon_sampled_build.json').write_text(json.dumps(record, indent=2))
    print('PHOTON_SAMPLED_BUILD', json.dumps(record), flush=True)
    return record


if __name__ == '__main__':
    run()
