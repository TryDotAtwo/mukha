"""Full-retina throughput check of exact-gate HH numerical diagnostic."""
from pathlib import Path
import json
import numpy as np

from benchmark_photon_batch import api,case


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    output=root/'data/derived/photon_exact_gates_speed_v1'
    output.mkdir(parents=True,exist_ok=False)
    base=api(root/'build/libfly_photon.so')
    new=api(root/'build/libfly_photon_exact_gates_diagnostic.so')
    cases=[]
    for cells,ticks in ((16,100),(6091,100)):
        a=case(base,cells,ticks,False)
        b=case(new,cells,ticks,False)
        rec={'cells':cells,'ticks':ticks,'microvilli_per_cell':30000,
             'baseline_elapsed_s':a['elapsed_s'],'exact_gates_elapsed_s':b['elapsed_s'],
             'speed_ratio_baseline_over_new':a['elapsed_s']/b['elapsed_s'],
             'max_observed_state_difference':float(np.max(np.abs(a['voltage']-b['voltage'])))}
        cases.append(rec)
        print('EXACT_GATES_SPEED_CASE',json.dumps(rec),flush=True)
    report={'scope':'Paired isolated photoreceptor speed under gray 50k photons/s, seed 19503',
            'cases':cases,'biological_gate_passed':False,
            'limitation':'100 ticks only; no CNS/body, no late high-flux performance.'}
    path=output/'report.json'
    path.write_text(json.dumps(report,indent=2))
    files=[path,root/'tools/benchmark_photon_exact_gates.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('EXACT_GATES_SPEED_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
