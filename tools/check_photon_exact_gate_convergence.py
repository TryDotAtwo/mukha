"""Build fine-voltage-step exact-gate diagnostic and compare full flash traces."""
from pathlib import Path
import ctypes as C
import hashlib
import json
import subprocess

import numpy as np
from benchmark_photon_batch import api


def trace(lib,rate,n=64,seed=19503):
    h=lib.fp_create(n,30000,seed,128)
    if not h:
        raise RuntimeError(lib.fp_last_error())
    stimulus=np.zeros(n,np.float64)
    observation=np.empty(9*n,np.float64)
    tick=C.c_uint64()
    values=np.empty((1010,n),np.float32)
    try:
        for ms in range(1010):
            stimulus.fill(rate if 500<=ms<510 else 0.)
            if lib.fp_advance(h,stimulus.ctypes.data_as(C.POINTER(C.c_double)),n,10):
                raise RuntimeError((ms,lib.fp_last_error()))
            if lib.fp_observe(h,observation.ctypes.data_as(C.POINTER(C.c_double)),len(observation),C.byref(tick)):
                raise RuntimeError(lib.fp_last_error())
            values[ms]=observation[:n]
        return values
    finally:
        lib.fp_destroy(h)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    original=(root/'build/photon_exact_gates_diagnostic.cu').read_text()
    assert original.count(',n,1e-5,10);')==1
    source=original.replace(',n,1e-5,10);',',n,1e-6,100);')
    assert source.count('photon_exact_gates_build_id.h')==1
    source=source.replace('photon_exact_gates_build_id.h','photon_exact_gates_fine_build_id.h')
    source_path=root/'build/photon_exact_gates_fine.cu'
    source_path.write_text(source)
    hh=(root/'build/photoreceptor_hh_exact_gates.cu').read_text()
    identity=hashlib.sha256((source+hh).encode()).hexdigest()
    header=root/'build/photon_exact_gates_fine_build_id.h'
    header.write_text('#pragma once\n#define FP_BUILD_ID "'+identity+'"\n')
    binary=root/'build/libfly_photon_exact_gates_fine.so'
    nvcc=root/'build/cuda-13.1.1/bin/nvcc'
    cuda_root=nvcc.parent.parent
    command=[str(nvcc),'-std=c++17','-O2','-lineinfo','-arch=sm_120','--fmad=false',
             '-shared','-Xcompiler','-fPIC','-I','native','-I','build',
             '-I',str(cuda_root/'include'),'-L',str(cuda_root/'lib'),
             str(source_path.relative_to(root)),'-o',str(binary.relative_to(root))]
    try:
        subprocess.run(command,cwd=root,check=True,capture_output=True,text=True)
    except subprocess.CalledProcessError as exc:
        print('EXACT_GATE_FINE_BUILD_ERROR',exc.stderr[-4000:],flush=True)
        raise
    coarse=api(root/'build/libfly_photon_exact_gates_diagnostic.so')
    fine=api(binary)
    output=root/'data/derived/photon_exact_gate_convergence_v1'
    output.mkdir(parents=True,exist_ok=False)
    cases=[]
    traces={}
    for rate in (10000.,10000000.):
        a=trace(coarse,rate)
        b=trace(fine,rate)
        traces[str(int(rate))+'_coarse']=a
        traces[str(int(rate))+'_fine']=b
        delta=b.astype(np.float64)-a.astype(np.float64)
        pre=float(a[499].mean())
        peak_a=float(a[500:].mean(axis=1).max()-pre)
        peak_b=float(b[500:].mean(axis=1).max()-float(b[499].mean()))
        rec={'photons_s':rate,'coarse_peak_delta_mV':peak_a,'fine_peak_delta_mV':peak_b,
             'peak_difference_mV':peak_b-peak_a,
             'trace_rmse_mV':float(np.sqrt(np.mean(delta**2))),
             'max_abs_voltage_difference_mV':float(np.max(np.abs(delta))),
             'preflash_exact':bool(np.array_equal(a[:500],b[:500]))}
        cases.append(rec)
        print('EXACT_GATE_CONVERGENCE_CASE',json.dumps(rec),flush=True)
    np.savez_compressed(output/'traces.npz',**traces)
    report={'scope':'Voltage Euler convergence sensitivity with exact gate integration; 10x0.01ms versus 100x0.001ms per 0.1ms tick',
            'coarse_identity':coarse.fp_build_identity().decode(),
            'fine_identity':identity,'fine_binary_sha256':digest(binary),
            'cases':cases,'biological_gate_passed':False}
    (output/'report.json').write_text(json.dumps(report,indent=2))
    files=[output/'report.json',output/'traces.npz',source_path,header,binary,
           root/'tools/check_photon_exact_gate_convergence.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('EXACT_GATE_CONVERGENCE_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
