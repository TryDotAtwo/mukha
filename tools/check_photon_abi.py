"""Real GPU C ABI regression against the earlier entity-RNG diagnostic trace."""
import ctypes as ct
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
library=ROOT/'build/fly_photon.dll'
api=ct.CDLL(str(library))
array=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
api.fp_create.argtypes=[ct.c_uint32,ct.c_uint32,ct.c_uint64,ct.c_uint32]
api.fp_create.restype=ct.c_void_p
api.fp_destroy.argtypes=[ct.c_void_p]
api.fp_reset.argtypes=[ct.c_void_p,ct.c_uint64]
api.fp_advance.argtypes=[ct.c_void_p,array,ct.c_size_t,ct.c_uint32]
api.fp_observe.argtypes=[ct.c_void_p,array,ct.c_size_t,ct.POINTER(ct.c_uint64)]
api.fp_last_error.restype=ct.c_char_p
def ok(code):
    assert code==0,api.fp_last_error().decode()
def observe(handle,n):
    state=np.empty(9*n,dtype=np.float64);tick=ct.c_uint64()
    ok(api.fp_observe(handle,state,len(state),ct.byref(tick)))
    return tick.value,state
reference_path=ROOT/'build/phototransduction_entity_repeat_0.csv'
provenance=json.loads((ROOT/'reports/phototransduction_entity_repeatability.json').read_text())
assert hashlib.sha256(reference_path.read_bytes()).hexdigest()==provenance['hashes'][str(Path('build')/'phototransduction_entity_repeat_0.csv')]
reference=np.loadtxt(reference_path,delimiter=',',skiprows=1)
assert reference.shape==(1000,5)
handle=api.fp_create(2,30000,19303,16)
assert handle,api.fp_last_error().decode()
rates=np.array([0.,100000.]); trace=[]
try:
    initial=observe(handle,2)
    assert not api.fp_create(2,30000,19303,16)
    for _ in range(1000):
        ok(api.fp_advance(handle,rates,2,1))
        tick,state=observe(handle,2)
        trace.append([tick,*state[:2],*state[12:14]])
    np.testing.assert_array_equal(np.asarray(trace),reference)
    terminal=state.copy()
    for invalid in (np.array([-1.,0.]),np.array([np.nan,0.]),np.array([np.inf,0.])):
        assert api.fp_advance(handle,invalid,2,1)!=0
        tick,state=observe(handle,2)
        assert tick==1000
        np.testing.assert_array_equal(state,terminal)
    assert api.fp_advance(handle,rates,1,1)!=0
    assert api.fp_advance(handle,rates,2,0)!=0
    ok(api.fp_reset(handle,19303))
    tick,state=observe(handle,2);assert tick==0
    np.testing.assert_array_equal(state,initial[1])
    ok(api.fp_advance(handle,rates,2,1000))
    tick,state=observe(handle,2);assert tick==1000
    np.testing.assert_array_equal(state,terminal)
    # Time-varying external stimulus: split calls preserve the same state.
    ok(api.fp_reset(handle,19303))
    dark=np.zeros(2);reverse=np.array([100000.,0.])
    ok(api.fp_advance(handle,dark,2,250))
    ok(api.fp_advance(handle,reverse,2,750))
    expected=observe(handle,2)
    ok(api.fp_reset(handle,19303))
    for i in range(1000): ok(api.fp_advance(handle,dark if i<250 else reverse,2,1))
    tick,state=observe(handle,2)
    assert tick==expected[0]==1000
    np.testing.assert_array_equal(state,expected[1])
    assert state[0]>state[1]+1.,'Externally addressed lit cell should depolarize'
finally:
    api.fp_destroy(handle)
report={'passed':True,'scope':'Windows RTX 3070 native C ABI, two cells, external photon inputs; not calibrated retina/CNS',
    'reference_trace_exact':True,'single_step_vs_batched_exact':True,
    'time_varying_input_chunking_exact':True,'invalid_inputs_preserve_state':True,
    'reset_reproduces_initial_state':True,'simultaneous_second_instance_rejected':True,
    'binary_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
    'reference_trace_sha256':hashlib.sha256(reference_path.read_bytes()).hexdigest(),
    'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],text=True).strip(),
    'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
        'native/photon.cu','native/photon.h','native/phototransduction_safe.cuh',
        'native/photocurrent_safe.cuh','build/photoreceptor_author_hh.cu',
        'build/photoreceptor_author_adaptation.cu','tools/build_photon.cmd')}}
(ROOT/'reports/photon_abi.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
