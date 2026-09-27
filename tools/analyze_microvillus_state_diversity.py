"""Measure molecular-state multiplicity before proposing grouped VisTrans."""
from pathlib import Path
import ctypes as c
import hashlib
import json
import statistics

import numpy as np


HEADER=16*8+64


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def snapshot_molecules(lib,model,cells,microvilli):
    size=lib.fp_checkpoint_size(model)
    buffer=(c.c_ubyte*size)()
    if lib.fp_save(model,c.addressof(buffer),size):raise RuntimeError('save failed')
    total=cells*microvilli
    raw=np.frombuffer(buffer,dtype='<u2',count=total*7,offset=HEADER)
    a=raw[:2*total].reshape(total,2)
    b=raw[2*total:4*total].reshape(total,2)
    d=raw[4*total:6*total].reshape(total,2)
    e=raw[6*total:7*total]
    return np.column_stack((e,a,b,d))


def analyze(states,cells,microvilli,time_ms):
    basal=np.array([0,50,0,0,0,0,0],dtype=np.uint16)
    sample=(0,1,2,3,7,15,31,63)
    records=[]
    for cell in sample:
        subset=states[cell*microvilli:(cell+1)*microvilli]
        unique,counts=np.unique(subset,axis=0,return_counts=True)
        basal_count=int(np.count_nonzero(np.all(subset==basal,axis=1)))
        record={'time_ms':time_ms,'cell':cell,'microvilli':microvilli,
                'distinct_states':len(unique),'largest_group':int(counts.max()),
                'basal_fraction':basal_count/microvilli,
                'fraction_in_repeated_states':float(counts[counts>1].sum()/microvilli),
                'simpson_effective_states':float(1/np.sum((counts/microvilli)**2))}
        records.append(record)
        print('MICROVILLUS_DIVERSITY_CELL',json.dumps(record),flush=True)
    return records


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    binary=root/'build/libfly_photon_coupled_current_diagnostic.so'
    lib=c.CDLL(str(binary))
    lib.fp_create.argtypes=[c.c_uint32,c.c_uint32,c.c_uint64,c.c_uint32]
    lib.fp_create.restype=c.c_void_p
    lib.fp_advance.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_uint32]
    lib.fp_advance.restype=c.c_int
    lib.fp_checkpoint_size.argtypes=[c.c_void_p]
    lib.fp_checkpoint_size.restype=c.c_size_t
    lib.fp_save.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t]
    lib.fp_save.restype=c.c_int
    lib.fp_destroy.argtypes=[c.c_void_p]
    cells=64
    m=30000
    model=lib.fp_create(cells,m,19503,1024)
    if not model:raise RuntimeError('fp_create failed')
    rates=np.full(cells,50000.,dtype='<f8')
    records=[]
    try:
        for advance_ticks,time_ms in ((1000,100),(4000,500)):
            if lib.fp_advance(model,rates.ctypes.data,cells,advance_ticks):
                raise RuntimeError('advance failed')
            states=snapshot_molecules(lib,model,cells,m)
            records.extend(analyze(states,cells,m,time_ms))
            del states
    finally:lib.fp_destroy(model)
    summary={str(time):{'median_distinct_states':statistics.median(r['distinct_states'] for r in records if r['time_ms']==time),
                        'median_basal_fraction':statistics.median(r['basal_fraction'] for r in records if r['time_ms']==time),
                        'median_fraction_in_repeated_states':statistics.median(r['fraction_in_repeated_states'] for r in records if r['time_ms']==time)}
             for time in (100,500)}
    report={'scope':'Molecular-state diversity of full-resolution corrected VisTrans; diagnostic for exact grouped-state algorithm',
            'binary_sha256':digest(binary),'cells':cells,'microvilli_each':m,
            'input_rate_photons_s':50000,'seed':19503,'records':records,'summary':summary,
            'limitations':'Eight of 64 independent receptors sampled, one constant light level/seed; state diversity alone does not prove grouped simulation can preserve path laws.'}
    out=root/'data/derived/microvillus_diversity_v1'
    out.mkdir(parents=True,exist_ok=False)
    path=out/'report.json'
    path.write_text(json.dumps(report,indent=2))
    files=[path,root/'tools/analyze_microvillus_state_diversity.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('MICROVILLUS_DIVERSITY_SUMMARY',json.dumps(summary),flush=True)
    print('MICROVILLUS_DIVERSITY_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':run()
