"""Test deterministic warp assignment in VisTrans without changing chemistry."""
from pathlib import Path
import ctypes as c
import hashlib
import json
import subprocess
import time

import numpy as np


HEADER_BYTES=16*8+64


def replace_one(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def run_library(path,cells,microvilli,ticks,save):
    lib=c.CDLL(str(path))
    lib.fp_create.argtypes=[c.c_uint32,c.c_uint32,c.c_uint64,c.c_uint32]
    lib.fp_create.restype=c.c_void_p
    lib.fp_advance.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_uint32]
    lib.fp_advance.restype=c.c_int
    lib.fp_observe.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_void_p]
    lib.fp_observe.restype=c.c_int
    lib.fp_checkpoint_size.argtypes=[c.c_void_p]
    lib.fp_checkpoint_size.restype=c.c_size_t
    lib.fp_save.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t]
    lib.fp_save.restype=c.c_int
    lib.fp_destroy.argtypes=[c.c_void_p]
    model=lib.fp_create(cells,microvilli,19503,1024)
    if not model:raise RuntimeError('fp_create failed')
    rates=np.full(cells,50000.,dtype='<f8')
    obs=np.empty(9*cells,dtype='<f8')
    tick=c.c_uint64()
    try:
        start=time.perf_counter()
        if lib.fp_advance(model,rates.ctypes.data,cells,ticks):raise RuntimeError('advance failed')
        advance_s=time.perf_counter()-start
        if lib.fp_observe(model,obs.ctypes.data,obs.size,c.byref(tick)):
            raise RuntimeError('observe failed')
        assert tick.value==ticks and np.isfinite(obs).all()
        state_hash=None
        if save:
            size=lib.fp_checkpoint_size(model)
            snapshot=(c.c_ubyte*size)()
            if lib.fp_save(model,c.addressof(snapshot),size):raise RuntimeError('save failed')
            state_hash=hashlib.sha256(memoryview(snapshot).cast('B')[HEADER_BYTES:]).hexdigest()
        return {'advance_s':advance_s,'tick':tick.value,'state_payload_sha256':state_hash},obs.copy()
    finally:lib.fp_destroy(model)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    original_kernel=(root/'native/phototransduction_safe.cuh').read_text()
    kernel=replace_one(original_kernel,
        '''    int start=0;
    if(wid==0) start=atomicAdd(count,32);
    start=__shfl_sync(0xffffffffu,start,0);
    int mid=start+wid;''',
        '''    // Static warp-stride assignment. Every microvillus keeps its own RNG.
    int start=blockIdx.x*blockDim.x + (tid & ~31);
    int mid=start+wid;''')
    kernel=replace_one(kernel,
        '''      if(wid==0) start=atomicAdd(count,32);
      start=__shfl_sync(0xffffffffu,start,0);
      mid=start+wid;''',
        '''      start += gridDim.x*blockDim.x;
      mid=start+wid;''')
    original_source=(root/'build/photon_coupled_current_diagnostic.cu').read_text()
    source=replace_one(original_source,'phototransduction_safe.cuh','phototransduction_static.cuh')
    source=replace_one(source,'photon_coupled_current_build_id.h','photon_static_build_id.h')
    out=root/'data/derived/photon_static_schedule_v1'
    out.mkdir(parents=True,exist_ok=False)
    kernel_path=root/'build/phototransduction_static.cuh'
    source_path=root/'build/photon_static_schedule.cu'
    header=root/'build/photon_static_build_id.h'
    kernel_path.write_text(kernel)
    source_path.write_text(source)
    identity=hashlib.sha256((source+kernel).encode()).hexdigest()
    header.write_text('#pragma once\n#define FP_BUILD_ID "'+identity+'"\n')
    binary=root/'build/libfly_photon_static_schedule.so'
    nvcc=root/'build/cuda-13.1.1/bin/nvcc'
    cuda=nvcc.parent.parent
    command=[str(nvcc),'-std=c++17','-O2','-lineinfo','-arch=sm_120','--fmad=false',
             '-shared','-Xcompiler','-fPIC','-I','native','-I','build',
             '-I',str(cuda/'include'),'-L',str(cuda/'lib'),
             str(source_path.relative_to(root)),'-o',str(binary.relative_to(root))]
    subprocess.run(command,cwd=root,check=True,capture_output=True,text=True,timeout=120)
    ref=root/'build/libfly_photon_coupled_current_diagnostic.so'
    cases=[]
    for cells,ticks,save in ((64,100,True),(3377,100,False)):
        data={}
        observations={}
        for name,path in (('dynamic',ref),('static',binary)):
            print('STATIC_SCHEDULE_CASE_START',cells,ticks,name,flush=True)
            result,obs=run_library(path,cells,30000,ticks,save)
            data[name]=result
            observations[name]=obs
            print('STATIC_SCHEDULE_CASE_DONE',cells,ticks,name,json.dumps(result),flush=True)
        equality=bool(np.array_equal(observations['dynamic'],observations['static']))
        state_equality=data['dynamic']['state_payload_sha256']==data['static']['state_payload_sha256'] if save else None
        case={'cells':cells,'microvilli_each':30000,'ticks':ticks,'seed':19503,
              'rates_photons_s':50000,'trials':data,'observation_exact':equality,
              'max_abs_observation_difference':float(np.max(np.abs(observations['dynamic']-observations['static']))),
              'state_payload_exact':state_equality,
              'advance_speedup':data['dynamic']['advance_s']/data['static']['advance_s']}
        cases.append(case)
        print('STATIC_SCHEDULE_COMPARISON',json.dumps(case),flush=True)
    report={'scope':'Static warp-stride scheduling for original per-microvillus chemistry/RNG, corrected receptor current variant',
            'build_id':identity,'source_sha256':digest(source_path),
            'kernel_sha256':digest(kernel_path),'binary_sha256':digest(binary),
            'reference_binary_sha256':digest(ref),'build_command':command,
            'cases':cases,'biological_gate_passed':False,
            'candidate_acceptance':all(case['observation_exact'] for case in cases) and cases[0]['state_payload_exact'],
            'limitations':'One light level and seed; 64-cell full-state and 3377-cell observed-state comparisons only. No full-CNS regression.'}
    report_path=out/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[kernel_path,source_path,header,binary,report_path,root/'tools/check_photon_static_schedule.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('STATIC_SCHEDULE_ARCHIVE',json.dumps(receipt),flush=True)
    if not report['candidate_acceptance']:raise RuntimeError('Static schedule changed receptor state')
    return receipt


if __name__=='__main__':run()
