"""Full-graph hypothesis sensitivity, never a validated physiological model."""
import ctypes as ct,hashlib,json,os,time,argparse
from pathlib import Path
import numpy as np
import pandas as pd
from check_cuda_reference import Params
ROOT=Path(__file__).resolve().parents[1];g=ROOT/'data/derived/malecns_v1_candidates'
parser=argparse.ArgumentParser()
parser.add_argument('--dtype',choices=['float32','float64'],default='float32')
parser.add_argument('--checkpoint',action='store_true',help='Restore into a new handle at tick 500')
parser.add_argument('--resume',action='store_true',help='Resume previously saved tick-500 checkpoint in this process')
args=parser.parse_args();scalar=np.float64 if args.dtype=='float64' else np.float32
params_type=type('Params64',(ct.Structure,),{'_fields_':[(name,ct.c_double if typ is ct.c_float else typ) for name,typ in Params._fields_]}) if args.dtype=='float64' else Params
if args.checkpoint and args.resume:parser.error('checkpoint and resume are mutually exclusive')
suffix='_resume' if args.resume else '_checkpoint' if args.checkpoint else ''
out=ROOT/('data/derived/malecns_sign_diagnostic_'+args.dtype+suffix+'_v2')
if out.exists():raise FileExistsError('Immutable experiment exists')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
m=json.loads((g/'manifest.json').read_text())
for name in ['body_ids.npy','indptr.npy','indices.npy','synapse_counts.npy','neurotransmitters.feather']:
 assert sha(g/name)==m['files'][name]['sha256']
ids=np.load(g/'body_ids.npy');rows=np.load(g/'indptr.npy');cols=np.load(g/'indices.npy')
counts=np.load(g/'synapse_counts.npy');nt=pd.read_feather(g/'neurotransmitters.feather').set_index('body').reindex(ids)
labels=nt.consensus_nt.fillna('missing_annotation')
source=int(np.flatnonzero(ids==10056)[0]);targets=[802115,803114,804940,805004,805450,805777]
target_ix=[int(np.flatnonzero(ids==v)[0]) for v in targets]
spec=dict(graph_manifest_sha256=sha(g/'manifest.json'),steps=1000,dt_ms=.1,input_body=10056,
 stimulus_ticks=list(range(0,1000,100)),voltage_jump_mv=68.75,
 hypothesis='Measure dependence of a full-graph LIF diagnostic on unclear transmitter signs',
 shared_assumptions={'acetylcholine':1,'gaba':-1,'glutamate':-1,'histamine':-1,'dopamine':0,'octopamine':0,'serotonin':0,'missing_annotation':0},
 variants={'unclear_excitatory':1,'unclear_inhibitory':-1},weight_mv_per_contact=.275,
 limitations=['Uniform LIF physiology is unvalidated on MaleCNS','Blanket glutamate inhibition conflicts with some known visual physiology',
 'Zero aminergic electrical weights do not model neuromodulation; all CSR rows retained',
 'Only unclear sign is varied, not a bound on all physiological uncertainty','Short deterministic direct drive, not physiological sensory stimulation'],
 biological_validation=False,brain_body_connected=False,max_wall_seconds_per_variant=180,dtype=args.dtype,checkpoint_tick=500 if args.checkpoint else None,
 event_recording='Every spike tick and graph index; per-chunk extraction before next advance')
out.mkdir();(out/'spec.json').write_text(json.dumps(spec,indent=2));(out/'INCOMPLETE').write_text('running')
resume_root=ROOT/('data/derived/malecns_sign_diagnostic_'+args.dtype+'_checkpoint_v2')
resume_report=None
if args.resume:
 resume_report=json.loads((resume_root/'report.json').read_text())
 assert not (resume_root/'INCOMPLETE').exists() and resume_report['complete']
 assert resume_report['spec']['checkpoint_tick']==500
 for key,value in spec.items():
  if key!='checkpoint_tick':assert resume_report['spec'][key]==value,key
directory=os.add_dll_directory(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin')
libpath=ROOT/('build/fly_cuda64.dll' if args.dtype=='float64' else 'build/fly_cuda_probe.dll');lib=ct.CDLL(str(libpath))
if args.resume:assert sha(libpath)==resume_report['library_sha256']
if args.dtype=='float64':
 for api_suffix in ['probe_error','create','destroy','advance','checkpoint_size','save','load']:setattr(lib,'ff_cuda_'+api_suffix,getattr(lib,'ff_cuda64_'+api_suffix))
lib.ff_cuda_probe_error.restype=ct.c_char_p
lib.ff_cuda_create.argtypes=[ct.c_uint32,ct.c_uint64]+[ct.c_void_p]*4+[params_type,ct.c_uint32];lib.ff_cuda_create.restype=ct.c_void_p
lib.ff_cuda_destroy.argtypes=[ct.c_void_p]
lib.ff_cuda_advance.argtypes=[ct.c_void_p,ct.c_uint32]+[ct.c_void_p]*4
lib.ff_cuda_checkpoint_size.argtypes=[ct.c_void_p];lib.ff_cuda_checkpoint_size.restype=ct.c_size_t
for api_name in ['ff_cuda_save','ff_cuda_load']:getattr(lib,api_name).argtypes=[ct.c_void_p,ct.c_void_p,ct.c_size_t]
cap=20;n=len(ids);sense=np.zeros(n,dtype=np.uint8);sense[source]=1
drive=np.zeros((cap,n),dtype=scalar);v=np.empty_like(drive);syn=np.empty_like(drive);spikes=np.empty((cap,n),dtype=np.uint8)
results=[]
for name,unknown in spec['variants'].items():
 mapping=dict(spec['shared_assumptions'],unclear=unknown)
 sign=labels.map(mapping);assert sign.notna().all()
 weights=np.asarray(counts,dtype=scalar)*np.asarray(sign,dtype=scalar)[cols]*scalar(.275)
 assert len(weights)==25587572 and np.isfinite(weights).all()
 handle=lib.ff_cuda_create(n,len(cols),*[a.ctypes.data for a in (rows,cols,weights,sense)],params_type(.1,-52,-52,-45,20,5,22,18),cap)
 if not handle:raise RuntimeError(lib.ff_cuda_probe_error().decode())
 start=time.monotonic();totals=np.zeros(n,dtype=np.uint64);target_spikes=[];events=[]
 try:
  if args.resume:
   saved=resume_root/(name+'_checkpoint.bin')
   assert sha(saved)==resume_report['files'][saved.name]
   expected=next(r for r in resume_report['results'] if r['variant']==name)
   assert hashlib.sha256(weights.tobytes()).hexdigest()==expected['weights_sha256']
   restored=np.frombuffer(saved.read_bytes(),dtype=np.uint8).copy()
   if lib.ff_cuda_load(handle,restored.ctypes.data,len(restored)):raise RuntimeError(lib.ff_cuda_probe_error().decode())
  for tick in range(500 if args.resume else 0,1000,cap):
   drive.fill(0)
   for t in range(tick,tick+cap):
    if t%100==0:drive[t-tick,source]=68.75
   rc=lib.ff_cuda_advance(handle,cap,*[a.ctypes.data for a in (drive,v,syn,spikes)])
   if rc:raise RuntimeError(lib.ff_cuda_probe_error().decode())
   assert np.isfinite(v).all() and np.isfinite(syn).all()
   totals+=spikes.sum(axis=0,dtype=np.uint64)
   ts_all,ix_all=np.nonzero(spikes);events.append(np.column_stack((ts_all+tick,ix_all)).astype(np.uint32))
   ts,cs=np.nonzero(spikes[:,target_ix]);target_spikes.extend((int(tick+t),targets[c]) for t,c in zip(ts,cs))
   if args.checkpoint and tick+cap==500:
    blob=np.empty(lib.ff_cuda_checkpoint_size(handle),dtype=np.uint8)
    if lib.ff_cuda_save(handle,blob.ctypes.data,len(blob)):raise RuntimeError(lib.ff_cuda_probe_error().decode())
    pending=out/(name+'_checkpoint.pending');saved=out/(name+'_checkpoint.bin')
    with pending.open('xb') as f:
     f.write(blob.tobytes());f.flush();os.fsync(f.fileno())
    pending.rename(saved)
    lib.ff_cuda_destroy(handle);handle=None
    handle=lib.ff_cuda_create(n,len(cols),*[a.ctypes.data for a in (rows,cols,weights,sense)],params_type(.1,-52,-52,-45,20,5,22,18),cap)
    if not handle:raise RuntimeError(lib.ff_cuda_probe_error().decode())
    restored=np.frombuffer(saved.read_bytes(),dtype=np.uint8).copy()
    np.testing.assert_array_equal(restored,blob)
    if lib.ff_cuda_load(handle,restored.ctypes.data,len(restored)):raise RuntimeError(lib.ff_cuda_probe_error().decode())
   if time.monotonic()-start>180:raise TimeoutError('diagnostic time cap exceeded')
 finally:
  if handle:lib.ff_cuda_destroy(handle)
 np.save(out/(name+'_counts.npy'),totals)
 all_events=np.concatenate(events)
 assert len(all_events)==int(totals.sum())
 np.testing.assert_array_equal(np.bincount(all_events[:,1],minlength=n),totals)
 np.save(out/(name+'_events.npy'),all_events)
 np.savez(out/(name+'_final_state.npz'),v=v[-1],g=syn[-1])
 results.append(dict(variant=name,elapsed_seconds=time.monotonic()-start,total_spikes=int(totals.sum()),
   active_neurons=int(np.count_nonzero(totals)),input_spikes=int(totals[source]),target_spikes=target_spikes,
   weights_sha256=hashlib.sha256(weights.tobytes()).hexdigest()))
 print(json.dumps({k:v for k,v in results[-1].items() if k!='target_spikes'}),flush=True)
report=dict(spec=spec,results=results,library_sha256=sha(libpath),complete=True,full_event_recording=True,
 event_tick_range=[500 if args.resume else 0,1000],resume_source_sha256=sha(resume_root/'report.json') if args.resume else None,
 files={p.name:sha(p) for p in out.iterdir() if p.suffix in ['.npy','.npz','.bin']})
(out/'report.json').write_text(json.dumps(report,indent=2));(ROOT/('reports/malecns_sign_diagnostic_'+args.dtype+suffix+'.json')).write_text(json.dumps(report,indent=2));(out/'INCOMPLETE').unlink()
