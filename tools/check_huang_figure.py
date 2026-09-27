"""Compare translated model to numerical arrays in the author's saved FIG file."""
import hashlib
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from scipy.io import loadmat

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'reference'))
from huang import parameters,figure5d_protocol,simulate

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true');args=parser.parse_args()
    simulator=simulate
    if args.native:
        from huang_native import simulate as simulator
    source=ROOT/'data/reference/huang_2024'
    lock=ROOT/'reports/huang_reference_sources.json'
    manifest=json.loads(lock.read_text())
    for entry in manifest['files']:
        if hashlib.sha256((source/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Author artifact changed')
    fig=loadmat(source/'matlab_code/figure_code_examples/figures/figure5d27-Mar-2023_3modules.fig',simplify_cells=True)
    images=[]
    def walk(node):
        if isinstance(node,dict):
            if node.get('type')=='image':images.append(np.asarray(node['properties']['CData']))
            for value in node.values():walk(value)
        elif isinstance(node,(list,np.ndarray)):
            for value in node:walk(value)
    walk(fig['hgS_070000'])
    if len(images)!=18 or any(x.shape!=(9,12) for x in images):raise ValueError('Unexpected author panel structure')
    predictions=np.empty((6,3,9,12))
    for vi,valence in enumerate(range(-4,5)):
        params=parameters(source/'data_and_parameters/Dx_steady_state_nonlinear_3_27-Mar-2023_3modules.mat',valence)
        for ri,rest in enumerate(range(165,3466,300)):
            activity=simulator(params,figure5d_protocol(rest))
            predictions[:,0,vi,ri]=activity[:,0,1]-activity[:,0,0]
            predictions[:,1,vi,ri]=activity[:,1,1]-activity[:,1,0]
            predictions[:,2,vi,ri]=activity[:,0,1]-activity[:,1,1]
    # Saved axes follow author construction order: each neuron, CS+, CS-, difference.
    errors=[float(np.max(np.abs(a-b))) for a,b in zip(predictions.reshape(18,9,12),images)]
    report={'scope':'Model reproduction against author saved numeric Figure 5d panels; not a fresh MATLAB run or full-CNS plasticity',
        'source_commit':manifest['commit'],'source_lock_sha256':hashlib.sha256(lock.read_bytes()).hexdigest(),
        'protocols':108,'panels':18,'numeric_values':1944,'tolerance':1e-8,
        'panel_max_absolute_errors':errors,'max_absolute_error':max(errors),
        'passed':max(errors)<1e-8,'full_cns_plasticity_validated':False}
    tag='huang_native_figure5d' if args.native else 'huang_figure5d'
    report['backend']='native-cpp-fp64' if args.native else 'numpy-fp64'
    if args.native:
        report['library_sha256']=hashlib.sha256((ROOT/'build/huang_reference.dll').read_bytes()).hexdigest()
        report['native_source_sha256']=hashlib.sha256((ROOT/'native/huang.cpp').read_bytes()).hexdigest()
    np.save(ROOT/f'build/{tag}_prediction.npy',predictions)
    report['prediction_sha256']=hashlib.sha256((ROOT/f'build/{tag}_prediction.npy').read_bytes()).hexdigest()
    report['translation_sha256']=hashlib.sha256((ROOT/'reference/huang.py').read_bytes()).hexdigest()
    (ROOT/f'reports/{tag}_comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
