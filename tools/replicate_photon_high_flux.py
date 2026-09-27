"""Replicate high-flux exact-gate responses across independent RNG seeds."""
from pathlib import Path
import json

import numpy as np

from benchmark_photon_batch import api
from check_photon_exact_gate_convergence import trace


def summarize(values):
    before=values[499].astype(np.float64)
    mean_delta=values[500:].mean(axis=1).astype(np.float64)-before.mean()
    cell_peaks=values[500:].max(axis=0).astype(np.float64)-before
    return {'population_peak_delta_mV':float(mean_delta.max()),
            'mean_cell_peak_delta_mV':float(cell_peaks.mean()),
            'std_cell_peak_delta_mV':float(cell_peaks.std(ddof=1)),
            'max_cell_voltage_mV':float(values.max()),
            'terminal_population_voltage_mV':float(values[-1].mean())}


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    coarse_path=root/'build/libfly_photon_exact_gates_diagnostic.so'
    fine_path=root/'build/libfly_photon_exact_gates_fine.so'
    assert coarse_path.exists() and fine_path.exists()
    coarse=api(coarse_path)
    fine=api(fine_path)
    output=root/'data/derived/photon_high_flux_replication_v1'
    output.mkdir(parents=True,exist_ok=False)
    seeds=(19507,19508,19509)
    rows=[]
    traces={}
    for seed in seeds:
        a=trace(coarse,10000000.,seed=seed)
        b=trace(fine,10000000.,seed=seed)
        traces[f'{seed}_coarse']=a
        traces[f'{seed}_fine']=b
        sa,sb=summarize(a),summarize(b)
        row={'seed':seed,'coarse':sa,'fine':sb,
             'peak_difference_mV':sb['population_peak_delta_mV']-sa['population_peak_delta_mV'],
             'paired_trace_rmse_mV':float(np.sqrt(np.mean((b.astype(np.float64)-a.astype(np.float64))**2)))}
        rows.append(row)
        print('HIGH_FLUX_REPLICATE',json.dumps(row),flush=True)
    np.savez_compressed(output/'traces.npz',**traces)
    report={'scope':'Independent-seed numerical sensitivity at 10^7 photons/s 10ms pulse; 64 receptors and 30000 microvilli each',
            'coarse_identity':coarse.fp_build_identity().decode(),
            'fine_identity':fine.fp_build_identity().decode(),
            'seeds':seeds,'cases':rows,'biological_gate_passed':False,
            'limitations':'Three additional seeds, one stimulus and specimen-uncalibrated photon rate; paired pathwise differences include stochastic amplification.'}
    report_path=output/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[report_path,output/'traces.npz',root/'tools/replicate_photon_high_flux.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('HIGH_FLUX_REPLICATION_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
