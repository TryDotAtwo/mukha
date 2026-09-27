"""Preregister a matched sugar/bitter pair from the author's Figure notebook."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    sugar=json.loads((ROOT/'configs/shiu_sugar_pilot.json').read_text())
    source=ROOT/'data/reference/shiu_2024/figures.ipynb'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=sugar['source_notebook_sha256']:
        raise ValueError('Notebook source differs from pinned sugar protocol')
    notebook=json.loads(source.read_text())
    # This cell and its following experiment loop were inspected before selection.
    tree=ast.parse(''.join(notebook['cells'][23]['source']))
    bitter=None
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='neu_bitter':
            bitter=ast.literal_eval(node.value)
    if bitter is None: raise ValueError('Missing original bitter population')
    ids=np.load(ROOT/'data/derived/shiu_2024/body_ids.npy')
    mapping={int(body):i for i,body in enumerate(ids)}
    targets=[mapping[int(body)] for body in bitter]
    if set(targets)&set(sugar['sensory']): raise ValueError('Unexpected sensory overlap')
    draws=np.random.default_rng(19302).random((sugar['steps'],len(targets)))
    outputs=[ROOT/f'configs/shiu_sugar100_bitter{rate}_pilot.json' for rate in (0,100)]
    if any(path.exists() for path in outputs): raise FileExistsError('Refusing to overwrite preregistered pair')
    for rate,path in zip((0,100),outputs):
        protocol=dict(sugar)
        ticks,channels=np.nonzero(draws<rate*sugar['dt_ms']/1000)
        bitter_events=[dict(tick=int(t),neuron=targets[int(c)]) for t,c in zip(ticks,channels)]
        protocol.update(name=f'shiu-original-sugar100-bitter{rate}-paired-pilot',
            condition=f'100 Hz sugar and {rate} Hz bitter inputs',
            sensory=sugar['sensory']+targets,
            events=sorted(sugar['events']+bitter_events,key=lambda e:(e['tick'],e['neuron'])),
            bitter_seed=19302,bitter_rate_hz=rate,sugar_rate_hz=100,
            source_bitter_cell=23,source_experiment_cell=24,
            hypothesis='Adding bitter drive suppresses MN9 compared with the matched 0 Hz bitter control.',
            evaluation='Compare both runs to Brian2 with shared inputs; report MN9 event counts. One paired seed does not pass full biological replication.',
            sensory_refractory_note='Both populations have zero refractory time in BOTH conditions, including 0 Hz bitter, matching author.poi neu_exc2 handling.')
        path.write_text(json.dumps(protocol,indent=2)+'\n')
        print(json.dumps(dict(path=str(path),sensory_neurons=len(protocol['sensory']),events=len(protocol['events']))))


if __name__=='__main__':main()
