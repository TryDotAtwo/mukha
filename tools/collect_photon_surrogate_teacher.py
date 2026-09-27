"""Collect full-microvillus teacher trajectories for a sensory surrogate pilot."""
from pathlib import Path
import ctypes as C
import hashlib
import json
import time
import numpy as np

from benchmark_photon_batch import api


def make_rates(ms_count, cells, seed):
    rng = np.random.default_rng(seed)
    rates = np.full((ms_count,cells), 50000., dtype=np.float64)
    levels = np.array([0.,1000.,10000.,50000.,100000.], np.float64)
    for cell in range(cells):
        pos = 500
        while pos < ms_count:
            width = int(rng.integers(5,151))
            rates[pos:min(pos+width,ms_count),cell] = levels[int(rng.integers(len(levels)))]
            pos += width
    return rates


def collect(lib, rates, seed):
    duration,cells = rates.shape
    handle = lib.fp_create(cells,30000,seed,128)
    if not handle:
        raise RuntimeError(lib.fp_last_error())
    state = np.empty(9*cells,np.float64)
    voltage = np.empty((duration,cells),np.float32)
    tick = C.c_uint64()
    begin = time.perf_counter()
    try:
        for ms in range(duration):
            row = np.ascontiguousarray(rates[ms])
            if lib.fp_advance(handle,row.ctypes.data_as(C.POINTER(C.c_double)),cells,10):
                raise RuntimeError((ms,lib.fp_last_error()))
            if lib.fp_observe(handle,state.ctypes.data_as(C.POINTER(C.c_double)),state.size,C.byref(tick)):
                raise RuntimeError(lib.fp_last_error())
            voltage[ms] = state[:cells]
            if (ms+1)%500==0:
                print('SURROGATE_TEACHER_PROGRESS',json.dumps({'ms':ms+1,'of':duration,
                     'elapsed_s':time.perf_counter()-begin}),flush=True)
        assert tick.value==duration*10
        return voltage,time.perf_counter()-begin
    finally:
        lib.fp_destroy(handle)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    output=root/'data/derived/photon_surrogate_teacher_v1'
    output.mkdir(parents=True,exist_ok=False)
    lib=api(root/'build/libfly_photon.so')
    records=[]
    files=[]
    for name,duration,cells,stim_seed,photon_seed in [
        ('train',4000,64,99103,19503),('holdout',2000,64,99104,19504)]:
        rates=make_rates(duration,cells,stim_seed)
        voltage,elapsed=collect(lib,rates,photon_seed)
        file=output/(name+'.npz')
        np.savez_compressed(file,photons_per_s=rates.astype(np.float32),voltage_mV=voltage,
                            dt_ms=np.array(1,dtype=np.int32))
        files.append(file)
        records.append({'name':name,'duration_ms':duration,'cells':cells,
                        'stimulus_seed':stim_seed,'photon_seed':photon_seed,
                        'elapsed_s':elapsed,'path':file.relative_to(root).as_posix()})
        print('SURROGATE_TEACHER_CASE',json.dumps(records[-1]),flush=True)
    report={'scope':'Full 30000-microvillus VisTrans teacher for sensory surrogate pilot; no CNS or body',
            'teacher_build_identity':lib.fp_build_identity().decode(),
            'stimulus':'Independent per-receptor piecewise constant levels 0/1k/10k/50k/100k photons/s, duration 5-150ms; 500ms gray prelude',
            'records':records,'biological_gate_passed':False,
            'limitations':'No measured photon calibration or endogenous feedback; one train and one held-out random stream.'}
    report_file=output/'report.json'
    report_file.write_text(json.dumps(report,indent=2))
    files.extend([report_file,root/'tools/collect_photon_surrogate_teacher.py'])
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('SURROGATE_TEACHER_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
