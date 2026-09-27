"""Measure full-resolution corrected VisTrans under different dynamic grids."""
from pathlib import Path
import ctypes as c
import hashlib
import json
import statistics
import time

import numpy as np


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def run_case(lib,blocks):
    cells=3377
    model=lib.fp_create(cells,30000,19503,blocks)
    if not model:raise RuntimeError(f'fp_create failed, blocks={blocks}')
    rates=np.full(cells,50000.,dtype='<f8')
    obs=np.empty(9*cells,dtype='<f8')
    tick=c.c_uint64()
    try:
        start=time.perf_counter()
        if lib.fp_advance(model,rates.ctypes.data,cells,100):raise RuntimeError('fp_advance failed')
        duration=time.perf_counter()-start
        if lib.fp_observe(model,obs.ctypes.data,obs.size,c.byref(tick)):
            raise RuntimeError('fp_observe failed')
        assert tick.value==100 and np.isfinite(obs).all()
        return duration,obs.copy()
    finally:lib.fp_destroy(model)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    binary=root/'build/libfly_photon_coupled_current_diagnostic.so'
    lib=c.CDLL(str(binary))
    lib.fp_create.argtypes=[c.c_uint32,c.c_uint32,c.c_uint64,c.c_uint32]
    lib.fp_create.restype=c.c_void_p
    lib.fp_advance.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_uint32]
    lib.fp_advance.restype=c.c_int
    lib.fp_observe.argtypes=[c.c_void_p,c.c_void_p,c.c_size_t,c.c_void_p]
    lib.fp_observe.restype=c.c_int
    lib.fp_destroy.argtypes=[c.c_void_p]
    order=[1024,256,4096,512,2048,8192,
           1024,8192,2048,512,4096,256,
           1024,256,512,2048,4096,8192]
    reference=None
    trials={str(k):[] for k in sorted(set(order))}
    for index,blocks in enumerate(order):
        elapsed,obs=run_case(lib,blocks)
        if reference is None:reference=obs
        assert np.array_equal(obs,reference),f'observation mismatch at blocks={blocks}'
        trials[str(blocks)].append(elapsed)
        print('PHOTON_GRID_TRIAL',index,blocks,elapsed,flush=True)
    medians={k:statistics.median(v) for k,v in trials.items()}
    best=min(medians,key=medians.get)
    report={'scope':'Dynamic VisTrans warp scheduling grid sweep on corrected full-resolution 3377-receptor model',
            'binary_sha256':digest(binary),'cells':3377,'microvilli_each':30000,
            'ticks':100,'photon_rate_s':50000,'seed':19503,
            'grid_blocks_order':order,'times_s':trials,'medians_s':medians,
            'best_blocks':int(best),'best_vs_1024_speedup':medians['1024']/medians[best],
            'all_observations_exact':True,
            'limitations':'Only isolated retina and one seed/rate; per-case model initialization excluded from timed advance.'}
    folder=root/'data/derived/photon_grid_sweep_v1'
    folder.mkdir(parents=True,exist_ok=False)
    path=folder/'report.json'
    path.write_text(json.dumps(report,indent=2))
    files=[path,root/'tools/sweep_photon_launch_blocks.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('PHOTON_GRID_RESULT',json.dumps({'medians_s':medians,'best_blocks':int(best),'best_vs_1024_speedup':report['best_vs_1024_speedup']}),flush=True)
    print('PHOTON_GRID_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':run()
