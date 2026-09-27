"""Fresh-process full-state checkpoint continuation and reject-before-mutation."""
import argparse
import ctypes as ct
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/photon-abi-checkpoint'
LIB=ROOT/'build/fly_photon.dll'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def binding():
    api=ct.CDLL(str(LIB))
    api.fp_create.argtypes=[ct.c_uint32,ct.c_uint32,ct.c_uint64,ct.c_uint32]
    api.fp_create.restype=ct.c_void_p
    api.fp_destroy.argtypes=[ct.c_void_p]
    api.fp_advance.argtypes=[ct.c_void_p,ct.POINTER(ct.c_double),ct.c_size_t,ct.c_uint32]
    api.fp_observe.argtypes=[ct.c_void_p,ct.POINTER(ct.c_double),ct.c_size_t,ct.POINTER(ct.c_uint64)]
    api.fp_checkpoint_size.argtypes=[ct.c_void_p];api.fp_checkpoint_size.restype=ct.c_size_t
    api.fp_save.argtypes=[ct.c_void_p,ct.c_void_p,ct.c_size_t]
    api.fp_load.argtypes=[ct.c_void_p,ct.c_void_p,ct.c_size_t]
    api.fp_build_identity.restype=ct.c_char_p
    api.fp_last_error.restype=ct.c_char_p
    return api
def check(api,code): assert code==0,api.fp_last_error().decode()
def snapshot(api,p):
    size=api.fp_checkpoint_size(p);assert size,api.fp_last_error().decode()
    data=(ct.c_ubyte*size)();check(api,api.fp_save(p,data,size))
    return bytes(data)
def restore(api,p,data): return api.fp_load(p,ct.c_char_p(data),len(data))
def advance(api,p,values,ticks): check(api,api.fp_advance(p,(ct.c_double*3)(*values),3,ticks))
def checksum(data):
    value=14695981039346656037
    for i,byte in enumerate(data):
        if not 88<=i<96: value=((value^byte)*1099511628211)&((1<<64)-1)
    return value
def phase(name):
    api=binding()
    build=json.loads((ROOT/'reports/photon_build.json').read_text())
    assert sha(LIB)==build['binary_sha256']
    assert api.fp_build_identity().decode()==build['build_identity']
    p=api.fp_create(3,30001,19303 if name=='baseline' else 999,16)
    assert p,api.fp_last_error().decode()
    try:
        if name=='baseline':
            advance(api,p,[0.,100000.,50000.],250)
            advance(api,p,[100000.,0.,10000.],250)
            (OUT/'midpoint.bin').write_bytes(snapshot(api,p))
        else:
            # Different initial state proves load restores, rather than relying on reset.
            advance(api,p,[12345.,0.,0.],9)
            middle=(OUT/'midpoint.bin').read_bytes()
            check(api,restore(api,p,middle))
            assert snapshot(api,p)==middle,'Full state must restore byte-for-byte'
            if name=='reject':
                rejected=[]
                cases=[('truncated',middle[:-1]),('trailing',middle+b'x')]
                for label,offset in [('tick',64),('seed',72),('population',16),('build',128),('molecular_payload',200),('rng_payload',len(middle)-32)]:
                    bad=bytearray(middle);bad[offset]^=1;cases.append((label,bytes(bad)))
                state_offset=192+3*30001*14
                for label,offset,value in [('nan_voltage',state_offset,float('nan')),
                                            ('gate_out_of_range',state_offset+3*8,2.),
                                            ('nan_feedback',len(middle)-8,float('nan'))]:
                    bad=bytearray(middle);struct.pack_into('<d',bad,offset,value)
                    struct.pack_into('<Q',bad,88,checksum(bad));cases.append((label,bytes(bad)))
                for label,bad in cases:
                    assert restore(api,p,bad)!=0,label
                    assert snapshot(api,p)==middle,label+' mutated live state'
                    rejected.append(label)
                (OUT/'rejected.json').write_text(json.dumps(rejected))
                return
        observation=(ct.c_double*27)();tick=ct.c_uint64()
        check(api,api.fp_observe(p,observation,27,ct.byref(tick)));assert tick.value==500
        advance(api,p,[100000.,0.,10000.],200)
        advance(api,p,[0.,0.,0.],300)
        check(api,api.fp_observe(p,observation,27,ct.byref(tick)));assert tick.value==1000
        (OUT/f'{name}-final.bin').write_bytes(snapshot(api,p))
    finally: api.fp_destroy(p)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['baseline','resumed','reject'])
    args=parser.parse_args()
    if args.phase:
        phase(args.phase);print('PASS',args.phase)
    else:
        OUT.mkdir(exist_ok=True)
        for name in ('baseline','resumed','reject'):
            subprocess.run([sys.executable,__file__,'--phase',name],cwd=ROOT,check=True,timeout=120)
        expected=(OUT/'baseline-final.bin').read_bytes()
        assert expected==(OUT/'resumed-final.bin').read_bytes()
        r={'passed':True,'scope':'Same Windows build and GPU, 3 receptors x 30001 microvilli, trusted checkpoint bytes; no cross-platform equivalence',
           'checkpoint_tick':500,'final_tick':1000,'full_final_bytes_equal':True,
           'snapshot_bytes':len(expected),'final_sha256':hashlib.sha256(expected).hexdigest(),
           'midpoint_sha256':sha(OUT/'midpoint.bin'),'binary_sha256':sha(LIB),
           'build_identity':json.loads((ROOT/'reports/photon_build.json').read_text())['build_identity'],
           'rejected_without_state_mutation':json.loads((OUT/'rejected.json').read_text())}
        (ROOT/'reports/photon_abi_checkpoint.json').write_text(json.dumps(r,indent=2))
        print(json.dumps(r,indent=2))
