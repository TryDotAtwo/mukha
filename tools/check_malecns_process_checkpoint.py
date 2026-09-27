from pathlib import Path
import numpy as np,json,hashlib
root=Path('data/derived');a=root/'malecns_sign_diagnostic_float64_v2';b=root/'malecns_sign_diagnostic_float64_resume_v2';results=[]
for name in ['unclear_excitatory','unclear_inhibitory']:
 full=np.load(a/(name+'_events.npy'));suffix=full[full[:,0]>=500];got=np.load(b/(name+'_events.npy'))
 np.testing.assert_array_equal(got,suffix)
 np.testing.assert_array_equal(np.load(b/(name+'_counts.npy')),np.bincount(suffix[:,1],minlength=167216))
 with np.load(a/(name+'_final_state.npz')) as x,np.load(b/(name+'_final_state.npz')) as y:
  for key in ['v','g']:np.testing.assert_array_equal(x[key],y[key])
 results.append(dict(variant=name,continuation_spikes=len(got),events_exact=True,final_state_bit_exact=True))
report=dict(results=results,fresh_process=True,restore_tick=500,stop_tick=1000,source_report_sha256=hashlib.sha256((b/'report.json').read_bytes()).hexdigest(),scope='Same machine/library diagnostic brain state only; not cross-platform or composite experiment checkpoint')
Path('reports/malecns_process_checkpoint.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
