"""Count exact per-tick molecular-state changes after visual adaptation."""
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


def molecules(lib,model,cells,microvilli):
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
    cells=8
    m=30000
    model=lib.fp_create(cells,m,19503,1024)
    if not model:raise RuntimeError('fp_create failed')
    rates=np.full(cells,50000.,dtype='<f8')
    records=[]
    try:
        if lib.fp_advance(model,rates.ctypes.data,cells,5000):raise RuntimeError('prelude failed')
        previous=molecules(lib,model,cells,m)
        for step in range(20):
            if lib.fp_advance(model,rates.ctypes.data,cells,1):raise RuntimeError('step failed')
            current=molecules(lib,model,cells,m)
            changed=np.any(previous!=current,axis=1).reshape(cells,m)
            record={'tick_after_500ms':step+1,'changed_per_receptor':[int(x) for x in changed.sum(axis=1)],
                    'mean_changed_fraction':float(changed.mean())}
            records.append(record)
            print('MICROVILLUS_TURNOVER_STEP',json.dumps(record),flush=True)
            previous=current
    finally:lib.fp_destroy(model)
    fractions=[r['mean_changed_fraction'] for r in records]
    report={'scope':'Exact molecular-state change fraction for 8 corrected VisTrans receptors after 500ms constant gray',
            'binary_sha256':digest(binary),'cells':cells,'microvilli_each':m,
            'prelude_ms':500,'measured_ticks':20,'photon_rate_s':50000,'seed':19503,
            'records':records,'median_changed_fraction':statistics.median(fractions),
            'min_changed_fraction':min(fractions),'max_changed_fraction':max(fractions),
            'limitations':'State changes are a lower bound on reaction events; paths can react multiple times or return to an earlier state. One seed and light level.'}
    folder=root/'data/derived/microvillus_turnover_v1'
    folder.mkdir(parents=True,exist_ok=False)
    path=folder/'report.json'
    path.write_text(json.dumps(report,indent=2))
    files=[path,root/'tools/analyze_microvillus_turnover.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('MICROVILLUS_TURNOVER_RESULT',json.dumps({'median':report['median_changed_fraction'],'min':min(fractions),'max':max(fractions)}),flush=True)
    print('MICROVILLUS_TURNOVER_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':run()
