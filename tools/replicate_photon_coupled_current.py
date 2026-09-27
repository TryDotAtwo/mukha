"""Independent-seed high-flux regression for within-substep TRP current coupling."""
from pathlib import Path
import json

import numpy as np

from benchmark_photon_batch import api
from check_photon_exact_gate_convergence import trace


def stats(values):
    pre=values[499].mean()
    return {'population_peak_delta_mV':float(values[500:].mean(axis=1).max()-pre),
            'max_cell_voltage_mV':float(values.max()),
            'min_cell_voltage_mV':float(values.min()),
            'cells_ever_above_zero':int(np.count_nonzero(np.max(values,axis=0)>0))}


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    coupled=api(root/'build/libfly_photon_coupled_current_diagnostic.so')
    old=np.load(root/'data/derived/photon_high_flux_replication_v1/traces.npz')
    output=root/'data/derived/photon_coupled_replication_v1'
    output.mkdir(parents=True,exist_ok=False)
    rows=[]
    saved={}
    for seed in (19507,19508,19509):
        prior=old[f'{seed}_coarse'].astype(np.float32)
        current=trace(coupled,10000000.,seed=seed)
        saved[str(seed)]=current
        row={'seed':seed,'held_current':stats(prior),'coupled_current':stats(current),
             'preflash_exact':bool(np.array_equal(prior[:500],current[:500]))}
        rows.append(row)
        print('COUPLED_REPLICATE',json.dumps(row),flush=True)
    np.savez_compressed(output/'traces.npz',**saved)
    report={'scope':'Three independent high-flux seeds; exact gates, 64 receptors, 30k microvilli, within-substep TRP current',
            'coupled_identity':coupled.fp_build_identity().decode(),
            'cases':rows,'biological_gate_passed':False,
            'limitations':'Strong flux remains uncalibrated; three seeds do not establish all-input invariance or biological agreement.'}
    path=output/'report.json'
    path.write_text(json.dumps(report,indent=2))
    files=[path,output/'traces.npz',root/'tools/replicate_photon_coupled_current.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('COUPLED_REPLICATION_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
