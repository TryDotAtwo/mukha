"""Physical-GPU continuity and checkpoint checks for persistent CUDA state."""
import argparse
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from check_cuda_reference import Params

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instrumentation', default='none')
    parser.add_argument('--dtype',choices=['float32','float64'],default='float32')
    args = parser.parse_args()
    dll_dir = os.add_dll_directory(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin') if os.name == 'nt' else None
    is64 = args.dtype=='float64'
    scalar = np.float64 if is64 else np.float32
    params_type = type('Params64',(ct.Structure,),{'_fields_':[(name,ct.c_double if typ is ct.c_float else typ) for name,typ in Params._fields_]}) if is64 else Params
    stem = 'fly_cuda64' if is64 else 'fly_cuda_probe'
    path = ROOT / ('build/'+stem+'.dll' if os.name == 'nt' else 'build/lib'+stem+'.so')
    lib = ct.CDLL(str(path))
    if is64:
        for suffix in ('probe_error','create','destroy','advance','reset','checkpoint_size','save','load'):
            setattr(lib,'ff_cuda_'+suffix,getattr(lib,'ff_cuda64_'+suffix))
    lib.ff_cuda_probe_error.restype = ct.c_char_p
    lib.ff_cuda_create.argtypes = [ct.c_uint32, ct.c_uint64] + [ct.c_void_p]*4 + [params_type, ct.c_uint32]
    lib.ff_cuda_create.restype = ct.c_void_p
    lib.ff_cuda_destroy.argtypes = [ct.c_void_p]
    lib.ff_cuda_destroy.restype = None
    lib.ff_cuda_advance.argtypes = [ct.c_void_p, ct.c_uint32] + [ct.c_void_p]*4
    lib.ff_cuda_reset.argtypes = [ct.c_void_p]
    lib.ff_cuda_checkpoint_size.argtypes = [ct.c_void_p]
    lib.ff_cuda_checkpoint_size.restype = ct.c_size_t
    for name in ('ff_cuda_save', 'ff_cuda_load'):
        getattr(lib, name).argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]
    fixture = json.loads((ROOT/'build/brian_fixture.json').read_text())
    n = fixture['n']
    pre, post = np.asarray(fixture['pre']), np.asarray(fixture['post'])
    order = np.lexsort((pre, post))
    row = np.r_[0, np.cumsum(np.bincount(post, minlength=n))].astype(np.uint64)
    col = pre[order].astype(np.uint32)
    weights = np.asarray(fixture['weights_mv'], dtype=scalar)[order]
    sense = np.zeros(n, dtype=np.uint8);sense[fixture['sensory']] = 1
    drive = np.asarray(fixture['stimuli'], dtype=scalar)
    handles = []
    def ok(rc):
        if rc: raise RuntimeError(lib.ff_cuda_probe_error().decode())
    def create(capacity, w=weights):
        model = lib.ff_cuda_create(n, len(col), *[a.ctypes.data for a in (row,col,w,sense)],
                                   params_type(.1,-52,-52,-45,20,5,22,18), capacity)
        if not model: raise RuntimeError(lib.ff_cuda_probe_error().decode())
        handles.append(model)
        return model
    def advance(model, x):
        x = np.ascontiguousarray(x)
        v,g,s = np.empty_like(x),np.empty_like(x),np.empty(x.shape,dtype=np.uint8)
        ok(lib.ff_cuda_advance(model,len(x),*[a.ctypes.data for a in (x,v,g,s)]))
        return v,g,s
    def replay(model, x, cap):
        chunks = [advance(model,x[i:i+cap]) for i in range(0,len(x),cap)]
        return tuple(np.concatenate([chunk[k] for chunk in chunks]) for k in range(3))
    def snapshot(model):
        blob = np.empty(lib.ff_cuda_checkpoint_size(model),dtype=np.uint8)
        ok(lib.ff_cuda_save(model,blob.ctypes.data,len(blob)))
        return blob
    def same(a,b): return all(np.array_equal(x,y) for x,y in zip(a,b))
    checks = {}
    try:
        uninterrupted = advance(create(len(drive)), drive)
        model = create(37)
        prefix = replay(model,drive[:611],37)
        saved = snapshot(model)
        suffix = replay(model,drive[611:],37)
        joined = tuple(np.concatenate([a,b]) for a,b in zip(prefix,suffix))
        checks['chunking_bit_exact'] = same(uninterrupted,joined)
        fresh = create(19)
        ok(lib.ff_cuda_load(fresh,saved.ctypes.data,len(saved)))
        checks['fresh_model_restore_bit_exact'] = same(suffix,replay(fresh,drive[611:],19))
        before = snapshot(fresh)
        corrupt = saved.copy();corrupt[-1] ^= 1
        checks['corrupt_rejected'] = lib.ff_cuda_load(fresh,corrupt.ctypes.data,len(corrupt)) != 0
        checks['truncated_rejected'] = lib.ff_cuda_load(fresh,saved.ctypes.data,len(saved)-1) != 0
        checks['failed_load_preserves_state'] = np.array_equal(before,snapshot(fresh))
        wrong_weights = weights.copy();wrong_weights[0] += 1
        wrong = create(37,wrong_weights)
        checks['wrong_graph_rejected'] = lib.ff_cuda_load(wrong,saved.ctypes.data,len(saved)) != 0
        x = drive[:1].copy();x[0,0] = np.nan
        outv,outg,outs = np.empty_like(x),np.empty_like(x),np.empty(x.shape,dtype=np.uint8)
        checks['nonfinite_rejected'] = lib.ff_cuda_advance(fresh,1,*[a.ctypes.data for a in (x,outv,outg,outs)]) != 0
        checks['over_capacity_rejected'] = lib.ff_cuda_advance(fresh,20,*[a.ctypes.data for a in (x,outv,outg,outs)]) != 0
        checks['failed_advance_preserves_state'] = np.array_equal(before,snapshot(fresh))
        ok(lib.ff_cuda_reset(fresh))
        checks['explicit_reset_bit_exact'] = same(uninterrupted,replay(fresh,drive,19))
        expected = [np.asarray(fixture['expected_'+key]) for key in ('v','g','spikes')]
        checks['brian_spikes_exact'] = np.array_equal(uninterrupted[2],expected[2])
        errors = [float(np.max(np.abs(a-b))) for a,b in zip(uninterrupted[:2],expected[:2])]
        checks['brian_states_within_tolerance'] = max(errors)<.002
        report = dict(passed=all(checks.values()), checks=checks,
                      max_voltage_error_mv=errors[0], max_synapse_error_mv=errors[1],
                      checkpoint_bytes=len(saved), chunk_capacity=37,
                      library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      instrumentation=args.instrumentation,
                      scope='physical GPU fixture; persistence and checkpoint checks only, no full-brain biology')
        suffix = ('64' if is64 else '')+'_state'+('' if args.instrumentation=='none' else '_'+args.instrumentation)
        (ROOT/('reports/cuda'+suffix+'.json')).write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        if not report['passed']: raise SystemExit(1)
    finally:
        for model in handles: lib.ff_cuda_destroy(model)
        if dll_dir: dll_dir.close()


if __name__ == '__main__': main()
