import pandas as pd,numpy as np,json,xml.etree.ElementTree as ET,hashlib
from pathlib import Path
root=Path('.');trace=pd.read_csv('build/motor_replay_trace.csv');mapping=json.loads(Path('configs/knee_interface_draft.json').read_text())['entries'];events=np.load('data/derived/malecns_sign_diagnostic_float64_v2/unclear_excitatory_events.npy')
act=[x.attrib['name'] for x in ET.parse('data/derived/contact_diagnostic/body.xml').getroot().find('actuator')];expected=np.zeros((1000,len(act)));ticks=np.arange(1000)
for e in mapping:
 ai=act.index(e['proposed_joint']+'-motor')
 for t,i in events[events[:,1]==e['graph_index']]:
  dt=ticks-int(t);valid=dt>=0;expected[valid,ai]+=.1*e['proposed_torque_sign']*np.exp(-dt[valid]*.1/20)
expected=np.clip(expected,-1,1)
on=trace[trace.enabled==1].pivot(index='tick',columns='actuator',values='control').to_numpy();off=trace[trace.enabled==0].pivot(index='tick',columns='actuator',values='control').to_numpy()
np.testing.assert_allclose(on,expected,atol=1e-14,rtol=1e-13);assert not off.any()
a=trace[trace.enabled==1].position.to_numpy();b=trace[trace.enabled==0].position.to_numpy();delta=float(np.max(np.abs(a-b)));assert delta>1e-9
r=dict(samples=len(trace),source_motor_spikes=14,max_control_error=float(np.max(np.abs(on-expected))),max_joint_difference_radians=delta,disabled_controls_zero=True,closed_loop=False,biological_motor_map_validated=False,trace_sha256=hashlib.sha256(Path('build/motor_replay_trace.csv').read_bytes()).hexdigest())
Path('reports/motor_replay_validation.json').write_text(json.dumps(r,indent=2));print(r)
