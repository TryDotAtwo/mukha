"""Full CSR CPU oracle using SciPy SpMV and NumPy state updates."""
import hashlib,json,math,time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
ROOT=Path(__file__).resolve().parents[1];g=ROOT/'data/derived/malecns_v1_candidates'
gpu=ROOT/'data/derived/malecns_sign_diagnostic_float64_v2'
report=json.loads((gpu/'report.json').read_text());spec=report['spec']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
assert sha(g/'manifest.json')==spec['graph_manifest_sha256']
m=json.loads((g/'manifest.json').read_text())
for name in ['body_ids.npy','indptr.npy','indices.npy','synapse_counts.npy','neurotransmitters.feather']:
 assert sha(g/name)==m['files'][name]['sha256']
ids=np.load(g/'body_ids.npy');ptr=np.load(g/'indptr.npy');col=np.load(g/'indices.npy');counts=np.load(g/'synapse_counts.npy')
labels=pd.read_feather(g/'neurotransmitters.feather').set_index('body').reindex(ids).consensus_nt.fillna('missing_annotation')
n=len(ids);source=int(np.flatnonzero(ids==spec['input_body'])[0]);results=[]
a=math.exp(-.1/20);b=math.exp(-.1/5);c=(a-b)*5/15
out=ROOT/'data/derived/malecns_cpu_reference_v1'
if out.exists():raise FileExistsError('Immutable result exists')
out.mkdir();(out/'INCOMPLETE').write_text('running')
for variant,unknown in spec['variants'].items():
 weights=counts.astype(np.float64)*labels.map(dict(spec['shared_assumptions'],unclear=unknown)).to_numpy(dtype=np.float64)[col]*.275
 expected=next(r for r in report['results'] if r['variant']==variant)
 assert hashlib.sha256(weights.tobytes()).hexdigest()==expected['weights_sha256']
 w=csr_matrix((weights,col,ptr),shape=(n,n));assert w.nnz==len(col)
 v=np.full(n,-52.);syn=np.zeros(n);next_allowed=np.zeros(n,dtype=np.int64)
 refractory=np.full(n,22,dtype=np.int64);refractory[source]=0
 ring=np.zeros((19,n));events=[];started=time.monotonic()
 for tick in range(spec['steps']):
  allowed=tick>=next_allowed
  v[allowed]=-52+a*(v[allowed]+52)+c*syn[allowed];syn[allowed]*=b
  fired=allowed&(v>-45);ring[tick%19]=fired
  incoming=w@ring[(tick-18)%19]
  syn[allowed]+=incoming[allowed]
  if tick in spec['stimulus_ticks'] and allowed[source]:v[source]+=spec['voltage_jump_mv']
  v[fired]=-52;syn[fired]=0;next_allowed[fired]=tick+refractory[fired]
  indices=np.flatnonzero(fired)
  if len(indices):events.append(np.column_stack((np.full(len(indices),tick),indices)).astype(np.uint32))
  if tick%250==249:print(variant,'completed ticks',tick+1,flush=True)
  if time.monotonic()-started>600:raise TimeoutError('CPU oracle 600-second cap')
 recorded=np.concatenate(events) if events else np.empty((0,2),dtype=np.uint32)
 assert np.isfinite(v).all() and np.isfinite(syn).all()
 reference_path=gpu/(variant+'_events.npy');state_path=gpu/(variant+'_final_state.npz')
 assert sha(reference_path)==report['files'][reference_path.name]
 assert sha(state_path)==report['files'][state_path.name]
 reference=np.load(reference_path);state=np.load(state_path)
 result=dict(variant=variant,events=len(recorded),all_events_exact=bool(np.array_equal(recorded,reference)),
  final_v_error_mv=float(np.max(np.abs(v-state['v']))),final_g_error_mv=float(np.max(np.abs(syn-state['g']))),wall_seconds=time.monotonic()-started)
 result['passed']=result['all_events_exact'] and max(result['final_v_error_mv'],result['final_g_error_mv'])<1e-8
 np.save(out/(variant+'_events.npy'),recorded);np.savez(out/(variant+'_final_state.npz'),v=v,g=syn)
 results.append(result);print(json.dumps(result),flush=True)
final=dict(results=results,neurons=n,edges=len(col),steps=spec['steps'],source_gpu_report_sha256=sha(gpu/'report.json'),
 scope='Independent CPU SpMV/state implementation of declared LIF hypotheses; not biological validation',passed=all(r['passed'] for r in results))
(ROOT/'reports/malecns_cpu_equivalence.json').write_text(json.dumps(final,indent=2));(out/'report.json').write_text(json.dumps(final,indent=2));(out/'INCOMPLETE').unlink()
if not final['passed']:raise SystemExit(1)
