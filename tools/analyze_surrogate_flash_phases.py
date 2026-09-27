"""Compute sign-aware post-flash opposite phases from archived teacher/pilot traces."""
from pathlib import Path
import json
import numpy as np


def phases(light, gray):
    response=light.mean(axis=1)-gray.mean(axis=1)
    initial=response[500:620]
    offset=int(np.argmax(np.abs(initial)))
    initial_peak=float(initial[offset])
    sign=1. if initial_peak>=0 else -1.
    tail=response[620:]
    opposite=float(max(0.,np.max(-sign*tail)))
    return {'initial_signed_mV':initial_peak,'initial_ms':500+offset,
            'opposite_abs_mV':opposite,
            'opposite_to_initial_ratio':opposite/max(abs(initial_peak),1e-12)}


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    data=np.load(root/'data/derived/photon_surrogate_flash_v1/traces.npz')
    result={}
    for pulse in ('light','dark'):
        result[pulse]={kind:phases(data[f'{pulse}_{kind}'],data[f'gray_{kind}'])
                       for kind in ('teacher','prediction')}
    path=root/'data/derived/photon_surrogate_flash_v1/signed_phases.json'
    path.write_text(json.dumps(result,indent=2))
    print('SURROGATE_SIGNED_PHASES',json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    run()
