"""Build and run an isolated per-kernel timing diagnostic on Molab."""
from pathlib import Path
import hashlib
import json
import subprocess

from benchmark_photon_batch import api, case


def run(root=Path('/marimo/fly-project')):
    root = Path(root)
    original = (root / 'native/photon.cu').read_text()
    source = original.replace('#include <array>', '#include <array>\n#include <chrono>\n#include <cstdio>')
    source = source.replace('../build/photon_build_id.h', 'photon_profile_build_id.h')
    start = '            check(cudaMemset(counter.p,0,sizeof(int)));'
    source = source.replace(start, '''            auto profile_start=std::chrono::steady_clock::now();
''' + start)
    marker = '            check(cudaGetLastError()); check(cudaDeviceSynchronize());'
    source = source.replace(marker, '''            check(cudaGetLastError()); check(cudaDeviceSynchronize());
            auto profile_trans=std::chrono::steady_clock::now();''')
    marker = '            sum_current<<<n,256>>>(x2.p,counts.p,offsets.p,state.p,current.p,feedback.p);\n            check(cudaGetLastError());'
    source = source.replace(marker, marker + ''' check(cudaDeviceSynchronize());
            auto profile_sum=std::chrono::steady_clock::now();''')
    marker = '            check(cudaGetLastError());\n            update_ns<<<'
    source = source.replace(marker, '''            check(cudaGetLastError()); check(cudaDeviceSynchronize());
            auto profile_hh=std::chrono::steady_clock::now();
            update_ns<<<''')
    marker = '            check(cudaMemcpy(host.data(),state.p,host.size()*sizeof(double),cudaMemcpyDeviceToHost));'
    source = source.replace(marker, '''            check(cudaDeviceSynchronize());
            auto profile_update=std::chrono::steady_clock::now();
''' + marker)
    marker = '            ++tick;\n        }\n        healthy=true;'
    source = source.replace(marker, '''            auto profile_end=std::chrono::steady_clock::now();
            if(step<5) std::fprintf(stderr,"PHOTON_STAGES tick=%u trans_us=%.1f sum_us=%.1f hh_us=%.1f update_us=%.1f validation_us=%.1f\\n",step,
                std::chrono::duration<double,std::micro>(profile_trans-profile_start).count(),
                std::chrono::duration<double,std::micro>(profile_sum-profile_trans).count(),
                std::chrono::duration<double,std::micro>(profile_hh-profile_sum).count(),
                std::chrono::duration<double,std::micro>(profile_update-profile_hh).count(),
                std::chrono::duration<double,std::micro>(profile_end-profile_update).count());
            ++tick;
        }
        healthy=true;''')
    assert source != original
    out = root / 'build/photon_profile_diagnostic.cu'
    header = root / 'build/photon_profile_build_id.h'
    library = root / 'build/libfly_photon_profile_diagnostic.so'
    out.write_text(source)
    build_id = hashlib.sha256(source.encode()).hexdigest()
    header.write_text('#pragma once\n#define FP_BUILD_ID "' + build_id + '"\n')
    nvcc = root / 'build/cuda-13.1.1/bin/nvcc'
    cuda_root = nvcc.parent.parent
    command = [str(nvcc), '-std=c++17', '-O2', '-lineinfo', '-arch=sm_120', '--fmad=false',
               '-shared', '-Xcompiler', '-fPIC', '-I', 'native', '-I', str(cuda_root / 'include'),
               '-L', str(cuda_root / 'lib'), str(out.relative_to(root)), '-o', str(library.relative_to(root))]
    subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    result = case(api(library), 6091, 5, False)
    rec = {'cells': 6091, 'microvilli_per_cell': 30000, 'ticks': 5,
           'elapsed_s': result['elapsed_s'], 'build_id': build_id,
           'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
           'binary_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
           'note': 'Wall timing includes synchronization inserted after each kernel; diagnostic only.'}
    print('PHOTON_STAGE_PROFILE', json.dumps(rec), flush=True)
    return rec


if __name__ == '__main__':
    run()
