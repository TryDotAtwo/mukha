"""Diagnostic ptxas register-cap sweep for full-resolution VisTrans."""
from pathlib import Path
import ctypes as c
import hashlib
import json
import statistics
import subprocess
import time

import numpy as np


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def run_case(path):
    lib=c.CDLL(str(path))
    lib.fp_create.argtypes=[c.c_uint32,c.c_uint32,c.c_uint64,c.c_uint32]
    lib.fp_create.restype=c.c_void_p
    lib.fp_advance.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_uint32]
    lib.fp_advance.restype=c.c_int
    lib.fp_observe.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_void_p]
    lib.fp_observe.restype=c.c_int
    lib.fp_destroy.argtypes=[c.c_void_p]
    n=3377
    model=lib.fp_create(n,30000,19503,1024)
    if not model:raise RuntimeError('fp_create failed')
    rates=np.full(n,50000.,dtype='<f8')
    obs=np.empty(9*n,dtype='<f8')
    tick=c.c_uint64()
    try:
        start=time.perf_counter()
        if lib.fp_advance(model,rates.ctypes.data,n,100):raise RuntimeError('advance failed')
        elapsed=time.perf_counter()-start
        if lib.fp_observe(model,obs.ctypes.data,obs.size,c.byref(tick)):
            raise RuntimeError('observe failed')
        assert tick.value==100 and np.isfinite(obs).all()
        return elapsed,obs.copy()
    finally:lib.fp_destroy(model)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    ref=root/'build/libfly_photon_coupled_current_diagnostic.so'
    out=root/'data/derived/photon_register_sweep_v1'
    out.mkdir(parents=True,exist_ok=False)
    nvcc=root/'build/cuda-13.1.1/bin/nvcc'
    cuda=nvcc.parent.parent
    builds={}
    for cap in (64,56,48):
        binary=out/f'libfly_photon_r{cap}.so'
        command=[str(nvcc),'-std=c++17','-O2','-lineinfo','-arch=sm_120','--fmad=false',
                 '-maxrregcount='+str(cap),'-Xptxas=-v','-shared','-Xcompiler','-fPIC',
                 '-I','native','-I','build','-I',str(cuda/'include'),'-L',str(cuda/'lib'),
                 'build/photon_coupled_current_diagnostic.cu','-o',str(binary.relative_to(root))]
        result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=120)
        if result.returncode:raise RuntimeError(f'build r{cap}: {result.stderr[-2000:]}')
        lines=result.stderr.splitlines()
        found=[i for i,line in enumerate(lines) if "entry function 'transduction'" in line]
        assert len(found)==1
        ptxas=lines[found[0]:found[0]+5]
        builds[str(cap)]={'binary':str(binary.relative_to(root)),'sha256':digest(binary),
                          'command':command,'ptxas_transduction':ptxas}
        print('REG_CAP_BUILD',cap,json.dumps(ptxas),flush=True)
    paths={'reference':ref,**{str(cap):out/f'libfly_photon_r{cap}.so' for cap in (64,56,48)}}
    order=['reference','64','56','48','48','56','64','reference']
    trials={name:[] for name in paths}
    reference=None
    exact={name:True for name in paths}
    max_abs={name:0. for name in paths}
    for index,name in enumerate(order):
        elapsed,obs=run_case(paths[name])
        if reference is None:reference=obs
        equal=bool(np.array_equal(obs,reference))
        exact[name]&=equal
        max_abs[name]=max(max_abs[name],float(np.max(np.abs(obs-reference))))
        trials[name].append(elapsed)
        print('REG_CAP_TRIAL',index,name,elapsed,'exact',equal,flush=True)
    medians={name:statistics.median(times) for name,times in trials.items()}
    report={'scope':'Register-cap sweep of unchanged full-resolution corrected VisTrans source on RTX PRO 6000 Blackwell',
            'reference_binary_sha256':digest(ref),'source_sha256':digest(root/'build/photon_coupled_current_diagnostic.cu'),
            'cells':3377,'microvilli_each':30000,'ticks':100,'seed':19503,'rate_photons_s':50000,
            'builds':builds,'order':order,'trials_s':trials,'medians_s':medians,
            'observations_exact':exact,'max_abs_observation_difference':max_abs,
            'limitations':'Compiler-only candidates; two timing repetitions, one input/seed, isolated retina.'}
    report_path=out/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[report_path,root/'tools/sweep_photon_register_cap.py',*paths.values()]
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('REG_CAP_RESULT',json.dumps({'medians_s':medians,'observations_exact':exact,'max_abs':max_abs}),flush=True)
    print('REG_CAP_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':run()
