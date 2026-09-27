"""Monte Carlo comparison of independent and lumped source-law CPU oracles."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import random
import statistics
import time

from reference.grouped_vistrans import BASAL, grouped_tick, independent_tick


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def metrics(histogram):
    if isinstance(histogram, list):
        histogram=Counter(histogram)
    return {'basal_count':histogram.get(BASAL,0),
            'sum_x0':sum(state[0]*count for state,count in histogram.items()),
            'sum_x5':sum(state[5]*count for state,count in histogram.items()),
            'sum_x6':sum(state[6]*count for state,count in histogram.items())}


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    samples=500
    cells=128
    ticks=20
    photon_rate=50000.
    ensembles={name:[] for name in ('independent','grouped')}
    timings={}
    for name in ensembles:
        start=time.perf_counter()
        for replicate in range(samples):
            rng=random.Random((100000 if name=='independent' else 200000)+replicate)
            if name=='independent':
                state=[BASAL]*cells
                for _ in range(ticks):
                    state=independent_tick(state,-56.,1.,photon_rate,rng)
            else:
                state=Counter({BASAL:cells})
                for _ in range(ticks):
                    state=grouped_tick(state,-56.,1.,photon_rate,rng)
            ensembles[name].append(metrics(state))
        timings[name]=time.perf_counter()-start
        print('GROUPED_LAW_ENSEMBLE',name,samples,'wall_s',timings[name],flush=True)
    comparisons=[]
    for key in ('basal_count','sum_x0','sum_x5','sum_x6'):
        a=[r[key] for r in ensembles['independent']]
        b=[r[key] for r in ensembles['grouped']]
        mean_a=statistics.mean(a)
        mean_b=statistics.mean(b)
        se=math.sqrt(statistics.pvariance(a)/samples+statistics.pvariance(b)/samples)
        z=(mean_b-mean_a)/se if se else (0. if mean_a==mean_b else math.inf)
        rec={'metric':key,'independent_mean':mean_a,'grouped_mean':mean_b,
             'independent_sd':statistics.pstdev(a),'grouped_sd':statistics.pstdev(b),
             'mean_difference_standard_errors':z}
        comparisons.append(rec)
        print('GROUPED_LAW_METRIC',json.dumps(rec),flush=True)
    passed=all(abs(row['mean_difference_standard_errors'])<4.5 for row in comparisons)
    report={'scope':'CPU distribution comparison for author-style independent versus grouped VisTrans events at fixed Vm/ns',
            'samples_per_method':samples,'microvilli_per_receptor':cells,'ticks':ticks,
            'dt_ms':0.1,'vm_mV':-56,'ns':1,'photon_rate_s':photon_rate,
            'seed_ranges':{'independent':[100000,100000+samples-1],
                           'grouped':[200000,200000+samples-1]},
            'timings_s':timings,'comparisons':comparisons,'screen_passed':passed,
            'limitations':'Both implementations share a Python rate oracle; this does not validate CUDA chemistry, biological physiology, or GPU performance. A 4.5-SE screen is a diagnostic, not proof of distribution equality.'}
    folder=root/'data/derived/grouped_vistrans_cpu_v1'
    folder.mkdir(parents=True,exist_ok=False)
    path=folder/'report.json'
    path.write_text(json.dumps(report,indent=2))
    files=[path,root/'tools/check_grouped_vistrans_distribution.py',
           root/'reference/grouped_vistrans.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('GROUPED_LAW_RESULT',json.dumps({'screen_passed':passed,'timings_s':timings}),flush=True)
    print('GROUPED_LAW_ARCHIVE',json.dumps(receipt),flush=True)
    if not passed:raise RuntimeError('Grouped source-law distribution diagnostic failed')
    return receipt


if __name__=='__main__':run()
