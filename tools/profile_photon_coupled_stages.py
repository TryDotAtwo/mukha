"""Diagnostic CUDA stage timing for the full-resolution corrected retina."""
from pathlib import Path
import ctypes as c
import hashlib
import json
import subprocess
import time

import numpy as np


def replace_one(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def run_library(path,cells,microvilli,ticks):
    lib=c.CDLL(str(path))
    lib.fp_create.argtypes=[c.c_uint32,c.c_uint32,c.c_uint64,c.c_uint32]
    lib.fp_create.restype=c.c_void_p
    lib.fp_advance.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_uint32]
    lib.fp_advance.restype=c.c_int
    lib.fp_observe.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_void_p]
    lib.fp_observe.restype=c.c_int
    lib.fp_destroy.argtypes=[c.c_void_p]
    start=time.perf_counter()
    model=lib.fp_create(cells,microvilli,19503,1024)
    if not model:raise RuntimeError('fp_create failed')
    init_s=time.perf_counter()-start
    rates=np.full(cells,50000.,dtype='<f8')
    obs=np.empty(cells*9,dtype='<f8')
    tick=c.c_uint64()
    try:
        start=time.perf_counter()
        if lib.fp_advance(model,rates.ctypes.data,cells,ticks):raise RuntimeError('fp_advance failed')
        advance_s=time.perf_counter()-start
        if lib.fp_observe(model,obs.ctypes.data,obs.size,c.byref(tick)):
            raise RuntimeError('fp_observe failed')
        assert tick.value==ticks and np.isfinite(obs).all()
        return {'init_s':init_s,'advance_s':advance_s,'tick':tick.value},obs.copy()
    finally:lib.fp_destroy(model)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    original=root/'build/photon_coupled_current_diagnostic.cu'
    text=original.read_text()
    text=replace_one(text,'#include <cmath>','#include <cmath>\n#include <chrono>')
    lo=text.index('    void advance(const double* rates,uint32_t ticks) {')
    hi=text.index('    void set_feedback(',lo)
    old=text[lo:hi]
    new='''    void advance(const double* rates,uint32_t ticks) {
        healthy=false;
        check(cudaSetDevice(device));
        using Clock=std::chrono::steady_clock;
        double total_ms[6]{};
        auto stamp=[](){return Clock::now();};
        auto millis=[](Clock::time_point a,Clock::time_point b){
            return std::chrono::duration<double,std::milli>(b-a).count();};
        auto t0=stamp();
        upload(state.p+7*n,rates,n);
        auto t1=stamp();total_ms[0]+=millis(t0,t1);
        for(uint32_t step=0;step<ticks;++step) {
            t0=stamp();
            check(cudaMemset(counter.p,0,sizeof(int)));
            transduction<<<blocks,128>>>(rng.p,1e-4f,state.p,state.p+6*n,state.p+7*n,
                                          counts.p,total,counter.p);
            check(cudaGetLastError()); check(cudaDeviceSynchronize());
            t1=stamp();total_ms[1]+=millis(t0,t1);
            t0=stamp();
            sum_current<<<n,256>>>(x2.p,counts.p,offsets.p,state.p,current.p,feedback.p);
            check(cudaGetLastError()); check(cudaDeviceSynchronize());
            t1=stamp();total_ms[2]+=millis(t0,t1);
            t0=stamp();
            hh<<<(n+31)/32,32>>>(current.p,feedback.p,state.p,state.p+n,state.p+2*n,state.p+3*n,
                                state.p+4*n,state.p+5*n,n,1e-5,10);
            check(cudaGetLastError()); check(cudaDeviceSynchronize());
            t1=stamp();total_ms[3]+=millis(t0,t1);
            t0=stamp();
            update_ns<<<(n+127)/128,128>>>(state.p+6*n,n,state.p,1e-4);
            check(cudaGetLastError()); check(cudaDeviceSynchronize());
            t1=stamp();total_ms[4]+=millis(t0,t1);
            t0=stamp();
            check(cudaMemcpy(host.data(),state.p,host.size()*sizeof(double),cudaMemcpyDeviceToHost));
            for(int i=0;i<7*n;++i) if(!std::isfinite(host[i]))
                throw std::runtime_error("Nonfinite photoreceptor state");
            for(int i=n;i<6*n;++i) if(host[i]<0 || host[i]>1)
                throw std::runtime_error("Photoreceptor gate outside [0,1]");
            ++tick;
            t1=stamp();total_ms[5]+=millis(t0,t1);
        }
        fprintf(stdout,"PHOTON_STAGE_MS h2d=%.6f transduction=%.6f current=%.6f hh=%.6f update=%.6f readback_check=%.6f ticks=%u\\n",
                total_ms[0],total_ms[1],total_ms[2],total_ms[3],total_ms[4],total_ms[5],ticks);
        fflush(stdout);
        healthy=true;
    }
'''
    text=replace_one(text,old,new)
    out=root/'data/derived/photon_stage_profile_v1'
    out.mkdir(parents=True,exist_ok=False)
    source=out/'photon_stage_profile.cu'
    source.write_text(text)
    binary=out/'libfly_photon_stage_profile.so'
    nvcc=root/'build/cuda-13.1.1/bin/nvcc'
    cuda=nvcc.parent.parent
    command=[str(nvcc),'-std=c++17','-O2','-lineinfo','-arch=sm_120','--fmad=false',
             '-shared','-Xcompiler','-fPIC','-I','native','-I','build',
             '-I',str(cuda/'include'),'-L',str(cuda/'lib'),str(source.relative_to(root)),
             '-o',str(binary.relative_to(root))]
    subprocess.run(command,cwd=root,check=True,capture_output=True,text=True,timeout=120)
    trials={}
    observations={}
    for name,path in (('reference',root/'build/libfly_photon_coupled_current_diagnostic.so'),
                      ('profile',binary)):
        print('PHOTON_PROFILE_START',name,flush=True)
        trial,obs=run_library(path,3377,30000,100)
        trials[name]=trial
        observations[name]=obs
        print('PHOTON_PROFILE_CASE',name,json.dumps(trial),flush=True)
    equal=bool(np.array_equal(observations['reference'],observations['profile']))
    max_abs=float(np.max(np.abs(observations['reference']-observations['profile'])))
    report={'scope':'Full-resolution 3377-receptor 100-tick CUDA stage profile; instrumented build adds synchronization',
            'cells':3377,'microvilli_each':30000,'ticks':100,'rates_photons_s':50000,
            'seed':19503,'source_sha256':digest(source),'reference_binary_sha256':digest(root/'build/libfly_photon_coupled_current_diagnostic.so'),
            'profile_binary_sha256':digest(binary),'build_command':command,
            'trials':trials,'observation_exact':equal,'max_abs_observation_difference':max_abs,
            'limitations':'Instrumented timing includes synchronization and Python call overhead; no neural/body stages.'}
    assert equal,'Instrumentation changed observations'
    report_path=out/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[source,binary,report_path,root/'tools/profile_photon_coupled_stages.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('PHOTON_PROFILE_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':run()
