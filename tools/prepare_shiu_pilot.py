"""Preregister an original-dataset sugar pilot with fully recorded input events."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    notebook_path = ROOT/'data/reference/shiu_2024/figures.ipynb'
    notebook = json.loads(notebook_path.read_text())
    literals = {}
    for cell_index,cell in enumerate(notebook['cells']):
        if cell['cell_type']!='code': continue
        try: tree = ast.parse(''.join(cell['source']))
        except SyntaxError: continue
        for node in tree.body:
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
                name = node.targets[0].id
                if name in ('neu_sugar','id_mn9') and name not in literals:
                    try: literals[name] = (ast.literal_eval(node.value),cell_index)
                    except (ValueError,TypeError): pass
    ids = np.load(ROOT/'data/derived/shiu_2024/body_ids.npy')
    mapping = {int(body):i for i,body in enumerate(ids)}
    sensory = [mapping[int(body)] for body in literals['neu_sugar'][0]]
    target = mapping[int(literals['id_mn9'][0])]
    steps,seed,rate = 10000,19301,100
    rng = np.random.default_rng(seed)
    active = rng.random((steps,len(sensory))) < rate*0.0001
    ticks,channels = np.nonzero(active)
    protocol = dict(name='shiu-original-sugar-100Hz-single-seed-pilot',steps=steps,dt_ms=.1,
                    condition='right labellar sugar GRNs at 100 Hz',seed=seed,
                    stimulus_generator='numpy.default_rng PCG64; Bernoulli(rate*dt), N=1 per cell per tick',
                    voltage_jump_mv=68.75,sensory=sensory,target_index=target,
                    target_body_id=int(literals['id_mn9'][0]),
                    source_notebook_sha256=hashlib.sha256(notebook_path.read_bytes()).hexdigest(),
                    source_cells={name:cell for name,(_,cell) in literals.items()},
                    graph_manifest_sha256=hashlib.sha256((ROOT/'data/derived/shiu_2024/manifest.json').read_bytes()).hexdigest(),
                    events=[dict(tick=int(t),neuron=sensory[int(c)]) for t,c in zip(ticks,channels)],
                    hypothesis='Published sugar drive recruits MN9 through the unmodified author graph.',
                    evaluation='Report all MN9 spikes and network counts; compare exact shared-input Brian2 reference. One seed alone does not pass biological replication.',
                    failure='Any hidden input, pruned edge, graph mismatch, numerical divergence or absent predicted response must be reported.',
                    max_wall_seconds=1800)
    out = ROOT/'configs/shiu_sugar_pilot.json'
    out.parent.mkdir(exist_ok=True)
    if out.exists(): raise FileExistsError('Refusing to replace preregistered protocol')
    out.write_text(json.dumps(protocol,indent=2)+'\n')
    print(json.dumps(dict(protocol=str(out),neurons=len(ids),input_neurons=len(sensory),events=len(ticks),target_index=target)))


if __name__ == '__main__': main()
