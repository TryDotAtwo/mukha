"""Check causal voltage-current coupling in isolated full-microvillus receptors."""
from pathlib import Path
import json

import numpy as np

from benchmark_photon_batch import api,case
from check_photon_exact_gate_convergence import trace


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    source=api(root/'build/libfly_photon_exact_gates_diagnostic.so')
    coupled=api(root/'build/libfly_photon_coupled_current_diagnostic.so')
    output=root/'data/derived/photon_coupled_current_v1'
    output.mkdir(parents=True,exist_ok=False)
    rows=[]
    traces={}
    for rate in (10000.,10000000.):
        old=trace(source,rate)
        new=trace(coupled,rate)
        traces[str(int(rate))+'_held_current']=old
        traces[str(int(rate))+'_coupled_current']=new
        pre_old=float(old[499].mean())
        pre_new=float(new[499].mean())
        rec={'photons_s':rate,
             'held_peak_delta_mV':float(old[500:].mean(axis=1).max()-pre_old),
             'coupled_peak_delta_mV':float(new[500:].mean(axis=1).max()-pre_new),
             'held_max_cell_voltage_mV':float(old.max()),
             'coupled_max_cell_voltage_mV':float(new.max()),
             'trace_rmse_mV':float(np.sqrt(np.mean((old.astype(np.float64)-new.astype(np.float64))**2))),
             'preflash_exact':bool(np.array_equal(old[:500],new[:500]))}
        rows.append(rec)
        print('COUPLED_CURRENT_CASE',json.dumps(rec),flush=True)
    np.savez_compressed(output/'traces.npz',**traces)
    a=case(source,6091,100,False)
    b=case(coupled,6091,100,False)
    speed={'cells':6091,'ticks':100,'source_elapsed_s':a['elapsed_s'],
           'coupled_elapsed_s':b['elapsed_s'],
           'speed_ratio':a['elapsed_s']/b['elapsed_s'],
           'max_observed_state_difference':float(np.max(np.abs(a['voltage']-b['voltage'])))}
    print('COUPLED_CURRENT_SPEED',json.dumps(speed),flush=True)
    report={'scope':'Recompute TRP driving-force current at each HH substep while holding open-channel count over 0.1ms',
            'source_identity':source.fp_build_identity().decode(),
            'coupled_identity':coupled.fp_build_identity().decode(),
            'cases':rows,'speed':speed,'biological_gate_passed':False,
            'limitations':'Numerical coupling diagnostic; no photon calibration, independent biological comparison, noise gate or downstream CNS validation.'}
    report_path=output/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[report_path,output/'traces.npz',
           root/'tools/build_photon_coupled_current.py',root/'tools/check_photon_coupled_current.py',
           root/'build/photocurrent_coupled.cuh',root/'build/photoreceptor_hh_coupled.cu',
           root/'build/photon_coupled_current_diagnostic.cu',root/'build/photon_coupled_current_build_id.h',
           root/'build/photon_coupled_current_build.json',
           root/'build/libfly_photon_coupled_current_diagnostic.so']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('COUPLED_CURRENT_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
