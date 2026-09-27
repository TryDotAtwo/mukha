"""Compare explicit-input traces against the actual pinned author's Brian2 model."""
import importlib.util
import json
import sys
import tempfile
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'build/python-reference')]
import numpy as np
import pandas as pd
import torch
import brian2 as b
from reference.lif import LifReference


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--author',choices=['shiu','dallmann'],default='shiu')
    args=parser.parse_args()
    source=ROOT/('data/reference/shiu_2024/model.py' if args.author=='shiu' else 'data/reference/feco_inhibition/code/simulation_model.py')
    commit='91bdd1e7dcf193f3e7ca5a8933497fcef63b7960' if args.author=='shiu' else 'e1233f4a987c532c9f1ab42273af21a0a6a50393'
    prefix='' if args.author=='shiu' else 'dallmann_'
    b.prefs.codegen.target = 'numpy'
    spec = importlib.util.spec_from_file_location('original_author', source)
    model = importlib.util.module_from_spec(spec); spec.loader.exec_module(model)
    n, steps = 5, 1200
    pre = [0,0,1,2,2,3,4]
    post = [2,3,2,3,4,4,2]
    counts = [140,60,-100,90,80,60,12]
    jump = np.zeros((steps,n))
    rng = np.random.default_rng(19301)
    jump[:,0] = (rng.random(steps) < 0.025)*68.75
    jump[:,1] = (rng.random(steps) < 0.017)*68.75
    # Include adjacent events, injections during ordinary-neuron refractoriness,
    # and duplicate stimulus ticks so scheduling differences become observable.
    jump[10:15,0] = 68.75
    jump[250:255,3] = 68.75
    with tempfile.TemporaryDirectory(dir=ROOT/'build') as tmp:
        path = Path(tmp)
        pd.DataFrame(index=np.arange(n)+10).to_csv(path/'nodes.csv')
        pd.DataFrame({'Presynaptic_Index':pre,'Postsynaptic_Index':post,
                      'Excitatory x Connectivity':counts}).to_parquet(path/'edges.parquet')
        b.start_scope(); b.defaultclock.dt = 0.1*b.ms
        neurons,synapses,spikes = model.create_model(path/'nodes.csv',path/'edges.parquet',dict(model.default_params))
        neurons.rfc[[0,1]] = 0*b.ms
        stimulus = b.TimedArray(jump*b.mV,dt=b.defaultclock.dt)
        neurons.namespace['stimulus'] = stimulus
        neurons.run_regularly('v += stimulus(t, i)',when='synapses',order=1)
        states = b.StateMonitor(neurons,['v','g'],record=True,when='end')
        net = b.Network(neurons,synapses,spikes,states)
        net.run(steps*b.defaultclock.dt)
        bv = np.asarray(states.v/b.mV).T
        bg = np.asarray(states.g/b.mV).T
        bs = np.zeros((steps,n),dtype=bool)
        bs[np.rint(np.asarray(spikes.t/b.defaultclock.dt)).astype(int),np.asarray(spikes.i)] = True
        results = []
        for dtype in [torch.float64,torch.float32]:
            ref = LifReference(n,pre,post,[w*0.275 for w in counts],sensory=[0,1],dtype=dtype)
            vs,gs,ss = [],[],[]
            for drive in jump:
                ss.append(ref.step(drive).numpy());vs.append(ref.v.numpy().copy());gs.append(ref.g.numpy().copy())
            dv = float(np.max(np.abs(np.array(vs)-bv)))
            dg = float(np.max(np.abs(np.array(gs)-bg)))
            mismatch = int(np.count_nonzero(np.array(ss)!=bs))
            tol = 1e-8 if dtype==torch.float64 else 0.002
            results.append({'dtype':str(dtype),'max_voltage_error_mv':dv,'max_synapse_error_mv':dg,
                'spike_mismatches':mismatch,'tolerance_mv':tol,'passed':dv<tol and dg<tol and mismatch==0})
        report = {'brian2_version':b.__version__,'author_model_commit':commit,'author_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'author_equations_modified':False,'deterministic_stimulus_in_place_of_poisson':True,
            'neurons':n,'steps':steps,'brian_spike_count':int(bs.sum()),'comparisons':results,
            'scope':'numerical scheduling fixture only; not biological replication'}
        (ROOT/('reports/'+prefix+'brian_torch_equivalence.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        fixture = {'n':n,'pre':pre,'post':post,'weights_mv':[x*0.275 for x in counts],
                   'sensory':[0,1],'stimuli':jump.tolist(),'expected_v':bv.tolist(),
                   'expected_g':bg.tolist(),'expected_spikes':bs.astype(int).tolist()}
        (ROOT/('build/'+prefix+'brian_fixture.json')).write_text(json.dumps(fixture),encoding='utf-8')
        print(json.dumps(report,indent=2))
        if not all(r['passed'] for r in results):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
