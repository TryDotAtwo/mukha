import numpy as np,json,hashlib
from pathlib import Path
root=Path('data/derived');a=root/'malecns_sign_diagnostic_float64_v2';b=root/'malecns_sign_diagnostic_float64_checkpoint_v2';results=[]
for name in ['unclear_excitatory','unclear_inhibitory']:
 for kind in ['events','counts']:np.testing.assert_array_equal(np.load(a/(name+'_'+kind+'.npy')),np.load(b/(name+'_'+kind+'.npy')))
 with np.load(a/(name+'_final_state.npz')) as x,np.load(b/(name+'_final_state.npz')) as y:
  for key in ['v','g']:np.testing.assert_array_equal(x[key],y[key])
 p=b/(name+'_checkpoint.bin');results.append(dict(variant=name,checkpoint_bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),all_events_exact=True,final_state_bit_exact=True))
report=dict(results=results,restore_tick=500,graph_neurons=167216,graph_edges=25587572,fresh_cuda_handle=True,fresh_process=False,scope='Brain diagnostic continuation only; no body/sensory/plasticity/recorder checkpoint')
Path('reports/malecns_full_checkpoint.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
