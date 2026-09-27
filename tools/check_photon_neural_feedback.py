"""Numerical current-injection test; no inferred MaleCNS synaptic calibration."""
import ctypes as ct
import hashlib
import json
from pathlib import Path
import numpy as np
from check_photon_abi_checkpoint import binding,check,snapshot,restore
from check_photoreceptor_membrane import advance as cpu_advance

ROOT=Path(__file__).resolve().parents[1]
api=binding()
api.fp_set_neural_feedback.argtypes=[ct.c_void_p,ct.POINTER(ct.c_double),ct.c_size_t]
p=api.fp_create(2,30000,19303,16);assert p,api.fp_last_error().decode()
rates=(ct.c_double*2)(0.,0.)
state=(ct.c_double*18)();clock=ct.c_uint64()
def feedback(values):check(api,api.fp_set_neural_feedback(p,(ct.c_double*2)(*values),2))
def step():
    check(api,api.fp_advance(p,rates,2,1));check(api,api.fp_observe(p,state,18,ct.byref(clock)))
    return np.array(state)
initial=[-81.9925,.2184,.9653,.0117,.9998,.0017]
cpu=[initial[:],initial[:]];ns=[1.,1.];actual=[];expected=[];middle=None
try:
    for tick in range(1000):
        if tick==250:feedback([10.,-10.])
        if tick==750:feedback([0.,0.])
        if tick==500:middle=snapshot(api,p)
        actual.append(step());assert clock.value==tick+1
        values=[10.,-10.] if 250<=tick<750 else [0.,0.]
        for j in range(2):
            cpu[j]=cpu_advance(cpu[j],values[j]);v=cpu[j][0]
            target=8.5652*(v+53)+5 if v>=-53 else max(1.,.2354*(v+70)+1)
            ns[j]+=(target-ns[j])*.0001
        expected.append(np.concatenate([np.asarray(cpu).T.reshape(-1),ns,[0.,0.,0.,0.]]))
    actual=np.asarray(actual);expected=np.asarray(expected)
    errors=np.max(np.abs(actual-expected),axis=0)
    assert np.all(errors<1e-9),errors
    terminal=snapshot(api,p)
    check(api,restore(api,p,middle))
    np.testing.assert_array_equal(np.frombuffer(middle[-16:],dtype='<f8'),[10.,-10.])
    # Do not reapply feedback at restore: continuation must use serialized current.
    for tick in range(500,1000):
        if tick==750:feedback([0.,0.])
        np.testing.assert_array_equal(step(),actual[tick])
    assert snapshot(api,p)==terminal
    for invalid in ([float('nan'),0.],[0.,float('inf')]):
        assert api.fp_set_neural_feedback(p,(ct.c_double*2)(*invalid),2)!=0
        assert snapshot(api,p)==terminal
    assert api.fp_set_neural_feedback(p,(ct.c_double*1)(0.),1)!=0
    assert snapshot(api,p)==terminal
finally:api.fp_destroy(p)
path=ROOT/'build/photon_neural_feedback_trace.npy';np.save(path,actual)
build=json.loads((ROOT/'reports/photon_build.json').read_text())
report={'passed':True,'scope':'Two-cell dark current injection, not a MaleCNS circuit or calibrated conductance',
        'ticks':1000,'dt_seconds':.0001,'feedback_model_units':'uA/cm^2',
        'protocol':'[0,0] until tick 250; [10,-10] on [250,750); [0,0] afterwards',
        'max_absolute_error_by_state':errors.tolist(),'full_state_restore_with_nonzero_feedback_exact':True,
        'invalid_feedback_preserves_state':True,'build_identity':build['build_identity'],
        'binary_sha256':build['binary_sha256'],'trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'oracle_sha256':hashlib.sha256((ROOT/'tools/check_photoreceptor_membrane.py').read_bytes()).hexdigest()}
(ROOT/'reports/photon_neural_feedback.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
