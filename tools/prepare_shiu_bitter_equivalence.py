"""Fixed-input full-author-graph numerical equivalence; execute only in MoLab."""
import ast, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]

def main():
    source = ROOT/'data/reference/shiu_2024'
    notebook_path = source/'figures.ipynb'
    notebook = json.loads(notebook_path.read_text())
    literals = {}
    for node in ast.parse(''.join(notebook['cells'][23]['source'])).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name = node.targets[0].id
            if name in ('neu_sugar','neu_bitter','id_mn9'):
                literals[name] = ast.literal_eval(node.value)
    ids = pd.read_csv(source/'2023_03_23_completeness_630_final.csv',index_col=0).index.to_numpy()
    mapping = {int(body):i for i,body in enumerate(ids)}
    sugar = [mapping[int(body)] for body in literals['neu_sugar']]
    bitter = [mapping[int(body)] for body in literals['neu_bitter']]
    if set(sugar)&set(bitter):raise RuntimeError('Overlapping stimulus populations require explicit protocol review')
    sensory = sugar+bitter
    rng = np.random.default_rng(193041)
    active = rng.random((10000,len(sensory))) < .01
    ticks,channels = np.nonzero(active)
    events = [dict(tick=int(t),neuron=sensory[int(c)]) for t,c in zip(ticks,channels)]
    events.sort(key=lambda e:(e['tick'],e['neuron']))
    graph = ROOT/'data/derived/shiu_2024/manifest.json'
    protocol = dict(name='shiu-original-sugar100-bitter100-native-equivalence',
        steps=10000,dt_ms=.1,condition='sugar and bitter populations each100 Hz',
        seed=193041,stimulus_generator='numpy PCG64 Bernoulli(.01) fixed inputs shared with Brian2 and Rust/CUDA; not original Brian Poisson RNG',
        voltage_jump_mv=68.75,sensory=sensory,sugar=sugar,bitter=bitter,
        target_index=mapping[int(literals['id_mn9'])],target_body_id=int(literals['id_mn9']),
        source_notebook_sha256=hashlib.sha256(notebook_path.read_bytes()).hexdigest(),
        source_cells={'neu_sugar':23,'neu_bitter':23,'id_mn9':23},
        graph_manifest_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),events=events,
        hypothesis='Native full author graph reproduces inhibitory sugar/bitter trajectory of unchanged author equations under exact shared input',
        acceptance='10000 completed ticks, exact ordered all-network spike events and target ticks, max target end-step voltage error<.002 mV; sanitizer zero errors separately',
        failure='Preserve first mismatch and reject numerical equivalence for this trajectory. Do not tune on observed output or transfer claim to MaleCNS.',
        scope='One preregistered numerical trajectory, not 30-trial author Poisson replication, whole-grid biology, MaleCNS or KSP',
        max_wall_seconds=1800)
    out = ROOT/'configs/shiu_bitter_equivalence.json'
    out.parent.mkdir(exist_ok=True)
    with out.open('x') as f:f.write(json.dumps(protocol,indent=2)+'\n')
    print(json.dumps({'protocol':str(out),'neurons':len(ids),'sugar':len(sugar),'bitter':len(bitter),'events':len(events),'target_index':protocol['target_index']}))
if __name__=='__main__':main()
