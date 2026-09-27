import json,hashlib,numpy as np,pandas as pd
from pathlib import Path
p=Path('build/brain_body_trace.csv');prior=Path('build/motor_replay_modular_trace.csv');assert p.read_bytes()==prior.read_bytes()
e=pd.read_csv('build/brain_body_events.csv');expected=np.load('data/derived/malecns_sign_diagnostic_float64_v2/unclear_excitatory_events.npy')
for enabled in [0,1]:np.testing.assert_array_equal(e.loc[e.enabled.eq(enabled),['tick','graph_index']].to_numpy(),expected)
report=dict(full_graph_neurons=167216,full_graph_edges=25587572,steps_per_condition=1000,conditions=2,spikes_per_condition=len(expected),all_neural_events_match_recorded_baseline=True,body_trace_byte_identical_to_replay=True,brain_and_body_native=True,sensory_feedback=False,biological_validation=False,files={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p,Path('build/brain_body_events.csv'),Path('build/brain_body_graph.bin'),Path('build/brain_body_mapping.txt'),Path('build/brain_body_probe.exe')]})
Path('reports/brain_body_native_diagnostic.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
