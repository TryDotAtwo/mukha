"""Diagnostic: cache receptor-voltage exponential shared by its microvilli."""
from pathlib import Path
import hashlib
import json
import subprocess


def once_replace(source, old, new):
    assert source.count(old) == 1, (old, source.count(old))
    return source.replace(old, new)


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    original_kernel = (root / 'native/phototransduction_safe.cuh').read_text()
    kernel = original_kernel
    kernel = once_replace(kernel, 'float compute_ca(int Tstar, float cstar_cc, float Vm)',
                          'float compute_ca(int Tstar, float cstar_cc, float Vm, float exp_vm)')
    kernel = once_replace(kernel, '179.0952 * expf(-39.60793*Vm)', '179.0952 * exp_vm')
    kernel = once_replace(kernel, 'double* g_ns, double* input,\n             int* num_microvilli',
                          'double* g_ns, double* input, float* exp_vm,\n             int* num_microvilli')
    kernel = kernel.replace('num_to_mM(X[tid][5]), Vm)', 'num_to_mM(X[tid][5]), Vm, exp_vm[ind])')
    assert kernel.count('exp_vm[ind])') == 2
    kernel_path = root / 'build/phototransduction_exp_cache.cuh'
    kernel_path.write_text(kernel)

    original = (root / 'native/photon.cu').read_text()
    source = original.replace('../build/photon_build_id.h', 'photon_exp_cache_build_id.h')
    source = once_replace(source, '"phototransduction_safe.cuh"',
                          '"phototransduction_exp_cache.cuh"')
    source = once_replace(source, 'struct Model {', '''__global__ void cache_exp_vm(const double* voltage, float* output, int n) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<n) {
        float vm=voltage[i]*1e-3;
        output[i]=expf(-39.60793*vm);
    }
}
struct Model {''')
    source = once_replace(source, 'DeviceArray<double> state,current,feedback;',
                          'DeviceArray<double> state,current,feedback;\n    DeviceArray<float> exp_vm;')
    source = once_replace(source, 'state(9*n),current(n),feedback(n),rng(total),host(9*n)',
                          'state(9*n),current(n),feedback(n),exp_vm(n),rng(total),host(9*n)')
    source = once_replace(source, '            transduction<<<blocks,128>>>',
                          '''            cache_exp_vm<<<(n+127)/128,128>>>(state.p,exp_vm.p,n);
            check(cudaGetLastError());
            transduction<<<blocks,128>>>''')
    source = once_replace(source, 'state.p+6*n,state.p+7*n,\n                                          counts.p',
                          'state.p+6*n,state.p+7*n,exp_vm.p,\n                                          counts.p')
    src_path = root / 'build/photon_exp_cache_diagnostic.cu'
    header_path = root / 'build/photon_exp_cache_build_id.h'
    library = root / 'build/libfly_photon_exp_cache_diagnostic.so'
    src_path.write_text(source)
    build_id = hashlib.sha256((source + kernel).encode()).hexdigest()
    header_path.write_text('#pragma once\n#define FP_BUILD_ID "' + build_id + '"\n')
    nvcc = root / 'build/cuda-13.1.1/bin/nvcc'
    cuda_root = nvcc.parent.parent
    command = [str(nvcc), '-std=c++17', '-O2', '-lineinfo', '-arch=sm_120', '--fmad=false',
               '-shared', '-Xcompiler', '-fPIC', '-I', 'native', '-I', 'build',
               '-I', str(cuda_root / 'include'), '-L', str(cuda_root / 'lib'),
               str(src_path.relative_to(root)), '-o', str(library.relative_to(root))]
    try:
        subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        print('PHOTON_EXP_BUILD_ERROR', exc.stderr[-4000:], flush=True)
        raise
    rec = {'build_id': build_id,
           'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
           'kernel_sha256': hashlib.sha256(kernel.encode()).hexdigest(),
           'binary_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
           'change': 'Precompute expf(-39.60793*Vm) per receptor and tick; otherwise same equations and RNG.'}
    (root / 'build/photon_exp_cache_build.json').write_text(json.dumps(rec, indent=2))
    print('PHOTON_EXP_BUILD', json.dumps(rec), flush=True)
    return rec


if __name__ == '__main__':
    run()
