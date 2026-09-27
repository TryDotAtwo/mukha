"""Out-of-distribution flash and online-throughput check for sensory GRU pilot."""
from pathlib import Path
import hashlib
import json
import time

import numpy as np
import torch

from benchmark_photon_batch import api
from collect_photon_surrogate_teacher import collect
from train_photon_surrogate_pilot_v2 import ReceptorGRU


def model_predict(model, rates, device):
    x = (np.log1p(rates)/np.log1p(100000.)).astype(np.float32)
    with torch.inference_mode():
        prediction,_ = model(torch.from_numpy(x[...,None]).to(device))
    return (prediction[...,0].cpu().numpy()*100.-81.9925)


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    output=root/'data/derived/photon_surrogate_flash_v1'
    output.mkdir(parents=True,exist_ok=False)
    device=torch.device('cuda')
    model=ReceptorGRU(24).to(device)
    checkpoint=torch.load(root/'data/derived/photon_surrogate_pilot_v2/model.pt',
                          map_location=device,weights_only=True)
    model.load_state_dict(checkpoint['state_dict'])
    model.eval()
    teacher=api(root/'build/libfly_photon.so')
    records=[]
    arrays={}
    for name,flash_rate in [('gray',50000.),('light',100000.),('dark',0.)]:
        rates=np.full((1020,64),50000.,np.float64)
        rates[500:520,:]=flash_rate
        voltage,elapsed=collect(teacher,rates,19506)
        prediction=model_predict(model,rates,device)
        arrays[name+'_teacher']=voltage
        arrays[name+'_prediction']=prediction.astype(np.float32)
        arrays[name+'_rate']=rates.astype(np.float32)
        rec={'stimulus':name,'teacher_elapsed_s':elapsed,
             'cell_voltage_rmse_mV':float(np.sqrt(np.mean((prediction-voltage)**2))),
             'population_voltage_rmse_mV':float(np.sqrt(np.mean((prediction.mean(axis=1)-voltage.mean(axis=1))**2)))}
        records.append(rec)
        print('SURROGATE_FLASH_CASE',json.dumps(rec),flush=True)
    for name in ('light','dark'):
        teacher_response=arrays[name+'_teacher'].mean(axis=1)-arrays['gray_teacher'].mean(axis=1)
        prediction_response=arrays[name+'_prediction'].mean(axis=1)-arrays['gray_prediction'].mean(axis=1)
        values={'stimulus':name,
                'mean_response_rmse_mV':float(np.sqrt(np.mean((teacher_response[500:]-prediction_response[500:])**2))),
                'teacher_peak_abs_mV':float(np.max(np.abs(teacher_response[500:620]))),
                'prediction_peak_abs_mV':float(np.max(np.abs(prediction_response[500:620]))),
                'teacher_opposite_abs_mV':float(np.max(np.abs(teacher_response[620:]))),
                'prediction_opposite_abs_mV':float(np.max(np.abs(prediction_response[620:])))}
        records.append(values)
        print('SURROGATE_FLASH_RESPONSE',json.dumps(values),flush=True)
    np.savez_compressed(output/'traces.npz',**arrays)
    # Sequential calls, one simulated ms per call. Includes Python/PyTorch dispatch.
    one=torch.full((1,6091,1),float(np.log1p(50000.)/np.log1p(100000.)),device=device)
    hidden=None
    with torch.inference_mode():
        for _ in range(100):
            _,hidden=model(one,hidden)
        torch.cuda.synchronize()
        start=time.perf_counter()
        for _ in range(1000):
            _,hidden=model(one,hidden)
        torch.cuda.synchronize()
        online_s=time.perf_counter()-start
    speed={'cells':6091,'simulated_ms':1000,'online_elapsed_s':online_s,
           'reference_full_receptor_elapsed_s_per_simulated_s':657.168,
           'speedup_vs_isolated_reference':657.168/online_s,
           'scope':'PyTorch sensory GRU only; excludes CNS, body, rendering, and KSP'}
    print('SURROGATE_ONLINE_SPEED',json.dumps(speed),flush=True)
    report={'scope':'Out-of-distribution 20ms fullfield flash and online speed for deterministic sensory surrogate',
            'teacher_build_identity':teacher.fp_build_identity().decode(),
            'surrogate_sha256':digest(root/'data/derived/photon_surrogate_pilot_v2/model.pt'),
            'records':records,'online_speed':speed,'biological_gate_passed':False,
            'limitations':'Uncalibrated photon flux, one new seed, no receptor noise or neural feedback, no CNS or body.'}
    (output/'report.json').write_text(json.dumps(report,indent=2))
    files=[output/'report.json',output/'traces.npz',root/'tools/validate_photon_surrogate_flash.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('SURROGATE_FLASH_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
