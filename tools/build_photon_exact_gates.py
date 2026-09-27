"""Diagnostic HH gate integrator: exact constant-V gate update, original ODEs."""
from pathlib import Path
import hashlib
import json
import subprocess


def replace_one(source, old, new):
    assert source.count(old) == 1, (old, source.count(old))
    return source.replace(old, new)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    original_hh=(root/'build/photoreceptor_author_hh.cu').read_text()
    hh=original_hh
    for name in ('sa','si','dra','dri','nov'):
        old=f'dx = (x_inf - {name})/tau_x;\n            {name} += dt * dx;'
        new=f'{name} = x_inf + ({name} - x_inf) * exp(-dt/tau_x);'
        hh=replace_one(hh,old,new)
    hh_path=root/'build/photoreceptor_hh_exact_gates.cu'
    hh_path.write_text(hh)
    original=(root/'native/photon.cu').read_text()
    source=replace_one(original,'../build/photon_build_id.h','photon_exact_gates_build_id.h')
    source=replace_one(source,'../build/photoreceptor_author_hh.cu',
                       'photoreceptor_hh_exact_gates.cu')
    source_path=root/'build/photon_exact_gates_diagnostic.cu'
    source_path.write_text(source)
    build_id=hashlib.sha256((source+hh).encode()).hexdigest()
    header=root/'build/photon_exact_gates_build_id.h'
    header.write_text('#pragma once\n#define FP_BUILD_ID "'+build_id+'"\n')
    binary=root/'build/libfly_photon_exact_gates_diagnostic.so'
    nvcc=root/'build/cuda-13.1.1/bin/nvcc'
    cuda_root=nvcc.parent.parent
    command=[str(nvcc),'-std=c++17','-O2','-lineinfo','-arch=sm_120','--fmad=false',
             '-shared','-Xcompiler','-fPIC','-I','native','-I','build',
             '-I',str(cuda_root/'include'),'-L',str(cuda_root/'lib'),
             str(source_path.relative_to(root)),'-o',str(binary.relative_to(root))]
    try:
        subprocess.run(command,cwd=root,check=True,capture_output=True,text=True)
    except subprocess.CalledProcessError as exc:
        print('EXACT_GATES_BUILD_ERROR',exc.stderr[-4000:],flush=True)
        raise
    rec={'build_id':build_id,'baseline_hh_sha256':hashlib.sha256(original_hh.encode()).hexdigest(),
         'hh_sha256':hashlib.sha256(hh.encode()).hexdigest(),
         'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
         'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
         'change':'Exact scalar gate solution over each existing 0.01ms substep at frozen V; same author gate ODEs, voltage Euler unchanged'}
    (root/'build/photon_exact_gates_build.json').write_text(json.dumps(rec,indent=2))
    print('EXACT_GATES_BUILD',json.dumps(rec),flush=True)
    return rec


if __name__=='__main__':
    run()
