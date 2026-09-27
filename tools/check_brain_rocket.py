import pandas as pd,numpy as np,json,hashlib
from pathlib import Path
expected=np.load('data/derived/malecns_sign_diagnostic_float64_v2/unclear_excitatory_events.npy');baseline=None;cases=[]
for prefix in ['brain_rocket','brain_rocket_nocontact']:
 env=pd.read_csv('build/'+prefix+'_environment.csv');body=pd.read_csv('build/'+prefix+'_body.csv');events=pd.read_csv('build/'+prefix+'_spikes.csv')
 for enabled in [0,1]:
  e=env[env.enabled==enabled];assert len(e)==1000
  np.testing.assert_array_equal(e.tick,np.arange(1000));np.testing.assert_allclose(e.time,(np.arange(1000)+1)*.0001,atol=1e-12,rtol=0)
  np.testing.assert_array_equal(e.throttle,np.clip(e.q_start_mm/.3,0,1));np.testing.assert_array_equal(e.q_start_mm.to_numpy()[1:],e.q_end_mm.to_numpy()[:-1])
  thrust_start=np.r_[0,e.thrust_n.to_numpy()[:-1]];fuel_start=np.r_[100,e.fuel_kg.to_numpy()[:-1]]
  np.testing.assert_allclose(e.effective_g_mm_s2,-1000*thrust_start/(1000+fuel_start),rtol=1e-14,atol=1e-14)
  np.testing.assert_array_equal(events.loc[events.enabled==enabled,['tick','graph_index']].to_numpy(),expected)
  state=e[['altitude_m','velocity_mps','fuel_kg','thrust_n']].to_numpy()
  if baseline is None:baseline=state
  else:np.testing.assert_array_equal(state,baseline)
  controls=body[body.enabled==enabled].control.to_numpy()
  assert (np.any(controls!=0) if enabled else not np.any(controls))
  cases.append(dict(contact=bool(e.contact.iloc[0]),motor_enabled=bool(enabled),max_throttle=float(e.throttle.max()),max_abs_control=float(np.abs(controls).max())))
 on=body[body.enabled==1].position.to_numpy();off=body[body.enabled==0].position.to_numpy();assert np.max(np.abs(on-off))>1e-9
report=dict(cases=cases,all_neural_events_match=True,clock_and_control_sampling_passed=True,all_rocket_traces_equal_ballistic_baseline=True,lever_actuation_achieved=False,sensory_feedback_to_brain=False,biological_validation=False,scope='100-ms full native brain-body-radial-rocket diagnostic; negative contact-control outcome',hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('build').glob('brain_rocket*.csv')})
Path('reports/brain_rocket_diagnostic.json').write_text(json.dumps(report,indent=2));print(json.dumps(cases,indent=2))
