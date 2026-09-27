"""Feedback and full-state checkpoint regression for coupled-current receptor."""
from pathlib import Path
import ctypes as C
import hashlib
import json

import numpy as np

from benchmark_photon_batch import api


def save(lib, handle):
    size=lib.fp_checkpoint_size(handle)
    assert size>0
    buf=(C.c_ubyte*size)()
    if lib.fp_save(handle,buf,size):
        raise RuntimeError(lib.fp_last_error())
    return bytes(buf)


def load(lib,handle,data):
    buf=C.create_string_buffer(data)
    rc=lib.fp_load(handle,C.cast(buf,C.c_void_p),len(data))
    if rc:
        raise RuntimeError(lib.fp_last_error())


def feedback(lib,handle,values):
    array=np.ascontiguousarray(values,dtype=np.float64)
    rc=lib.fp_set_neural_feedback(handle,array.ctypes.data_as(C.POINTER(C.c_double)),len(array))
    if rc:
        raise RuntimeError(lib.fp_last_error())


def observe(lib,handle,n):
    state=np.empty(9*n,np.float64)
    tick=C.c_uint64()
    rc=lib.fp_observe(handle,state.ctypes.data_as(C.POINTER(C.c_double)),len(state),C.byref(tick))
    if rc:
        raise RuntimeError(lib.fp_last_error())
    return state,tick.value


def advance(lib,handle,n,ticks):
    rates=np.zeros(n,np.float64)
    rc=lib.fp_advance(handle,rates.ctypes.data_as(C.POINTER(C.c_double)),n,ticks)
    if rc:
        raise RuntimeError(lib.fp_last_error())


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    lib=api(root/'build/libfly_photon_coupled_current_diagnostic.so')
    lib.fp_load.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t]
    lib.fp_load.restype=C.c_int
    lib.fp_set_neural_feedback.argtypes=[C.c_void_p,C.POINTER(C.c_double),C.c_size_t]
    lib.fp_set_neural_feedback.restype=C.c_int
    n=4
    handle=lib.fp_create(n,30000,19503,128)
    if not handle:
        raise RuntimeError(lib.fp_last_error())
    output=root/'data/derived/photon_coupled_feedback_checkpoint_v1'
    output.mkdir(parents=True,exist_ok=False)
    try:
        advance(lib,handle,n,200)
        baseline_checkpoint=save(lib,handle)
        feedback(lib,handle,[10.,-10.,0.,0.])
        advance(lib,handle,n,250)
        midpoint=save(lib,handle)
        np.testing.assert_array_equal(np.frombuffer(midpoint[-n*8:],dtype='<f8'),[10.,-10.,0.,0.])
        advance(lib,handle,n,250)
        injected_state,injected_tick=observe(lib,handle,n)
        injected_final=save(lib,handle)
        assert injected_tick==700
        load(lib,handle,midpoint)
        advance(lib,handle,n,250)
        replay_state,replay_tick=observe(lib,handle,n)
        replay_final=save(lib,handle)
        assert replay_tick==700 and np.array_equal(injected_state,replay_state)
        assert injected_final==replay_final

        load(lib,handle,baseline_checkpoint)
        feedback(lib,handle,[0.,0.,0.,0.])
        advance(lib,handle,n,500)
        zero_state,zero_tick=observe(lib,handle,n)
        assert zero_tick==700
        voltage_delta=(injected_state[:n]-zero_state[:n]).tolist()
        assert voltage_delta[0]>0 and voltage_delta[1]<0
        assert voltage_delta[2]==0 and voltage_delta[3]==0

        terminal=save(lib,handle)
        nan=np.array([float('nan'),0.,0.,0.],np.float64)
        assert lib.fp_set_neural_feedback(handle,nan.ctypes.data_as(C.POINTER(C.c_double)),n)!=0
        wrong=np.zeros(3,np.float64)
        assert lib.fp_set_neural_feedback(handle,wrong.ctypes.data_as(C.POINTER(C.c_double)),3)!=0
        corrupt=bytearray(terminal)
        corrupt[200]^=1
        buf=C.create_string_buffer(bytes(corrupt))
        assert lib.fp_load(handle,C.cast(buf,C.c_void_p),len(corrupt))!=0
        assert save(lib,handle)==terminal
    finally:
        lib.fp_destroy(handle)
    for name,data in [('pre-feedback.bin',baseline_checkpoint),('feedback-midpoint.bin',midpoint),
                      ('feedback-final.bin',injected_final)]:
        (output/name).write_bytes(data)
    report={'scope':'Four-receptor dark signed-feedback and full-state snapshot regression for isolated coupled-current diagnostic',
            'binary_identity':lib.fp_build_identity().decode(),
            'ticks':700,'microvilli_per_receptor':30000,
            'feedback_uA_per_cm2':[10.,-10.,0.,0.],
            'terminal_voltage_delta_mV':voltage_delta,
            'midpoint_feedback_serialized':True,'replay_state_exact':True,
            'replay_checkpoint_exact':True,'invalid_feedback_and_corruption_rejected_without_mutation':True,
            'biological_gate_passed':False,
            'limitations':'Diagnostic current injection, not calibrated MaleCNS synaptic input; same build/GPU snapshot replay.'}
    report_path=output/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[report_path,output/'pre-feedback.bin',output/'feedback-midpoint.bin',
           output/'feedback-final.bin',root/'tools/check_coupled_photon_feedback_checkpoint.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('COUPLED_FEEDBACK_CHECKPOINT_REPORT',json.dumps(report),flush=True)
    print('COUPLED_FEEDBACK_CHECKPOINT_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
