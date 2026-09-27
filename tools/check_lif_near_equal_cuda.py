"""Exercise the compiled CUDA64 LIF recurrence at near-equal time constants."""
import ctypes as ct
import hashlib
import json
import math
import os
from pathlib import Path

import mpmath as mp
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DLL=ROOT/'build/fly_cuda64.dll'
REPORT=ROOT/'reports/lif_near_equal_cuda.json'
os.add_dll_directory(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin')


class Params(ct.Structure):
    _fields_=[(name,ct.c_double) for name in
              ('dt_ms','rest_mv','reset_mv','threshold_mv','membrane_ms','synapse_ms')]
    _fields_ += [('refractory_ticks',ct.c_uint32),('delay_ticks',ct.c_uint32)]


def main():
    lib=ct.CDLL(str(DLL))
    lib.ff_cuda64_create.argtypes=[ct.c_uint32,ct.c_uint64,ct.c_void_p,ct.c_void_p,
                                    ct.c_void_p,ct.c_void_p,Params,ct.c_uint32]
    lib.ff_cuda64_create.restype=ct.c_void_p
    lib.ff_cuda64_advance.argtypes=[ct.c_void_p,ct.c_uint32,ct.c_void_p,
                                     ct.c_void_p,ct.c_void_p,ct.c_void_p]
    lib.ff_cuda64_destroy.argtypes=[ct.c_void_p]
    lib.ff_cuda64_checkpoint_size.argtypes=[ct.c_void_p]
    lib.ff_cuda64_checkpoint_size.restype=ct.c_size_t
    lib.ff_cuda64_save.argtypes=[ct.c_void_p,ct.c_void_p,ct.c_size_t]
    lib.ff_cuda64_load.argtypes=[ct.c_void_p,ct.c_void_p,ct.c_size_t]
    lib.ff_cuda64_probe_error.restype=ct.c_char_p
    row=np.array([0,0,1],np.uint64)
    col=np.array([0],np.uint32)
    weight=np.array([1.0],np.float64)
    sensory=np.array([1,0],np.uint8)
    drive=np.zeros((3,2),np.float64)
    drive[0,0]=10.0
    mp.mp.dps=80
    results=[]
    for name,ts in [('below',math.nextafter(20.0,-math.inf)),
                    ('equal',20.0),('above',math.nextafter(20.0,math.inf)),
                    ('ordinary',5.0)]:
        params=Params(0.1,-60.0,-60.0,-53.0,20.0,ts,0,0)
        handle=lib.ff_cuda64_create(2,1,row.ctypes.data,col.ctypes.data,
                                     weight.ctypes.data,sensory.ctypes.data,params,3)
        assert handle,lib.ff_cuda64_probe_error()
        v=np.empty_like(drive);g=np.empty_like(drive);spikes=np.empty(drive.shape,np.uint8)
        try:
            rc=lib.ff_cuda64_advance(handle,3,drive.ctypes.data,v.ctypes.data,
                                      g.ctypes.data,spikes.ctypes.data)
            assert rc==0,lib.ff_cuda64_probe_error()
            if name=='above':
                size=lib.ff_cuda64_checkpoint_size(handle)
                checkpoint=(ct.c_ubyte*size)()
                assert lib.ff_cuda64_save(handle,checkpoint,size)==0
                original=bytes(checkpoint)
                old_identity=14695981039346656037
                for blob in (ct.string_at(ct.byref(params),ct.sizeof(params)),
                             row.tobytes(),col.tobytes(),weight.tobytes(),sensory.tobytes()):
                    for value in blob:
                        old_identity=((old_identity^value)*1099511628211)&((1<<64)-1)
                assert int.from_bytes(original[40:48],'little') != old_identity
                old_header=bytearray(original)
                old_header[40:48]=old_identity.to_bytes(8,'little')
                incompatible=(ct.c_ubyte*size).from_buffer_copy(old_header)
                assert lib.ff_cuda64_load(handle,incompatible,size)!=0
                unchanged=(ct.c_ubyte*size)()
                assert lib.ff_cuda64_save(handle,unchanged,size)==0
                assert bytes(unchanged)==original
        finally:
            lib.ff_cuda64_destroy(handle)
        assert spikes[:,0].tolist()==[0,1,0] and not np.any(spikes[:,1])
        assert abs(g[1,1]-1.0)<1e-15
        d=mp.mpf(0.1);tm=mp.mpf(20.0);syn=mp.mpf(ts)
        reference=mp.quad(lambda s:mp.exp(-(d-s)/tm)*mp.exp(-s/syn)/tm,[0,d])
        observed=float(v[2,1]+60.0)
        error=abs(observed-float(reference))
        assert error<2e-14,(name,observed,reference)
        results.append({'case':name,'observed_c':observed,
                        'reference_c':float(reference),'absolute_error':error})
    REPORT.write_text(json.dumps({'passed':True,'near_equal_old_identity_rejected_without_state_mutation':True,
                                  'dll_sha256':hashlib.sha256(DLL.read_bytes()).hexdigest(),
                                  'scope':'Two-cell CUDA64 spike-to-synapse recurrence, not full-graph biology',
                                  'cases':results},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'cases':len(results),
                      'max_absolute_error':max(x['absolute_error'] for x in results)}))


if __name__=='__main__':
    main()
