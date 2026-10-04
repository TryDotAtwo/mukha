"""ctypes research harness for the native aggregate Huang reference."""
import ctypes as c
from pathlib import Path
import numpy as np

class Parameters(c.Structure):
    _fields_=[('weights',c.c_double*6),('recurrent',c.c_double*36),('fw0',c.c_double),
              ('fwdt',c.c_double),('tau',c.c_double*3),('adaptation_tau',c.c_double)]
class Event(c.Structure):
    _fields_=[('duration',c.c_double),('odor',c.c_double*2),('punishment',c.c_double),('training',c.c_int32)]

LIBRARY=Path(__file__).resolve().parents[1]/'build/huang_reference.dll'
lib=c.CDLL(str(LIBRARY))
lib.hm_simulate.argtypes=[c.POINTER(Parameters),c.POINTER(Event),c.c_size_t,c.POINTER(c.c_double),c.c_size_t]
lib.hm_simulate.restype=c.c_int

def simulate(params,events):
    if np.asarray(params[0]).size!=6:
        raise ValueError('Select the author odor-pair six weights before native simulation')
    p=Parameters((c.c_double*6)(*params[0].ravel()),(c.c_double*36)(*params[3].ravel()),
                 float(params[1].item()),float(params[2].ravel(order='F')[0]),
                 (c.c_double*3)(*params[4].ravel()),float(params[5].item()))
    e=(Event*len(events))(*[Event(duration,(c.c_double*2)(*odor),punishment,int(name=='training'))
                          for name,duration,odor,punishment,imaging in events])
    out=(c.c_double*(len(events)*6))()
    status=lib.hm_simulate(c.byref(p),e,len(e),out,len(out))
    if status:raise ValueError(f'Native Huang error {status}')
    activity=np.ctypeslib.as_array(out).reshape(len(events),6)
    selected=activity[[i for i,event in enumerate(events) if event[4]]].T
    if not selected.shape[1] or selected.shape[1]%2:
        raise ValueError('Expected complete CS+/CS- imaging pairs')
    return selected.reshape(6,2,selected.shape[1]//2,order='F').copy()
