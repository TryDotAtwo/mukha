"""Preregister original JON input populations and two named descending readouts."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rates',nargs='+',type=int,choices=[0,*range(20,221,20)],default=[0,100])
    args=parser.parse_args()
    if len(set(args.rates))!=len(args.rates): raise ValueError('Duplicate requested rate')
    base=json.loads((ROOT/'configs/shiu_sugar_pilot.json').read_text())
    source=ROOT/'data/reference/shiu_2024/figures.ipynb'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=base['source_notebook_sha256']:
        raise ValueError('Source notebook hash changed')
    notebook=json.loads(source.read_text());values={}
    for cell in (50,54):
        for node in ast.parse(''.join(notebook['cells'][cell]['source'])).body:
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
                name=node.targets[0].id
                if name in ('neu_JON_CE','neu_JON_F','neu_JON_D_m','id_DN1_1','id_DN2_l'):
                    values[name]=ast.literal_eval(node.value)
    ids=np.load(ROOT/'data/derived/shiu_2024/body_ids.npy')
    mapping={int(body):i for i,body in enumerate(ids)}
    bodies=values['neu_JON_CE']+values['neu_JON_F']+values['neu_JON_D_m']
    if len(set(bodies))!=len(bodies): raise ValueError('Duplicate JON input ID')
    sensory=[mapping[body] for body in bodies]
    readouts={name:dict(body_id=values[name],index=mapping[values[name]]) for name in ('id_DN1_1','id_DN2_l')}
    draws=np.random.default_rng(19303).random((base['steps'],len(sensory)))
    outputs=[ROOT/f'configs/shiu_jon{rate}_pilot.json' for rate in args.rates]
    if any(p.exists() for p in outputs): raise FileExistsError('Refusing to overwrite preregistration')
    for rate,path in zip(args.rates,outputs):
        ticks,channels=np.nonzero(draws<rate*.0001)
        protocol=dict(base)
        protocol.update(name=f'shiu-original-JON-{rate}Hz-pilot',seed=19303,
            condition=f'JON CE + F + D_m input at {rate} Hz',sensory=sensory,
            target_index=readouts['id_DN1_1']['index'],target_body_id=readouts['id_DN1_1']['body_id'],
            secondary_readouts=readouts,source_cells={'JON_populations':50,'rate_sweep':51,'readouts':54},
            events=[dict(tick=int(t),neuron=sensory[int(c)]) for t,c in zip(ticks,channels)],
            hypothesis='JON drive recruits the named descending readouts relative to zero input.',
            evaluation='Compare every native spike to Brian2 and report both readouts. Neural response is not evidence of physically executed grooming.',
            caveat='Nonzero rate belongs to the original 20–220 Hz input sweep; one seed is a pilot, not reproduction of the full sweep.',
            followup_context='Rates added after the initial 100 Hz pilot are follow-up dose tests; preserve the negative 100 Hz readout and do not select only successful doses.')
        path.write_text(json.dumps(protocol,indent=2)+'\n')
        print(json.dumps(dict(path=str(path),sensory_neurons=len(sensory),events=len(ticks),readouts=readouts)))


if __name__=='__main__':main()
