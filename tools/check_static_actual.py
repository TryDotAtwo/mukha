"""Independent actual004 numerical checker: QR coefficients and scalar fsum.

Never imports production runners; never refits frozen H0/H1. The only static
fit reconstruction is the two prescribed training pairs for artifact review.
"""
import argparse
import ast
import hashlib
import io
import json
import math
from pathlib import Path
import tarfile

import numpy as np
from scipy.io import loadmat
from scipy.linalg import lstsq

ARCHIVE_SHA='41cb1b831f81248fe3d591d68842147b2e5f1983a416cbd149ad0ac92d07ed4d'
RESULT_SHA='2b53849cc007872d60ea145db72051822df8ec7204326f2a96cd396b8fad0dab'
BASELINE_SHA='c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb'
PROTOCOL_SHA='9968b2b5a734441483e0a6391e55a4dbb9edf3fe72de445b78a821d48cac4665'


def sha(data): return hashlib.sha256(data).hexdigest()


def members(blob):
    with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as tar:
        return {m.name:tar.extractfile(m).read() for m in tar if m.isfile()}


def weights(t):
    out=np.zeros(len(t))
    for i,d in enumerate(np.diff(t)):
        out[i]+=d/2; out[i+1]+=d/2
    return out


def inner(w,x,y): return math.fsum(float(a*b*c) for a,b,c in zip(w,x,y))


def fit(t,c,y,h0):
    w=weights(t); energy=inner(w,c,c); scale=float(max(abs(c)))
    v=c**3/scale**2; X=np.column_stack([c,v])*np.sqrt(w)[:,None]
    s=np.linalg.svd(X,compute_uv=False); rank=int(sum(s>1e-12*s[0]))
    if rank!=2: raise ValueError('actual004 full-rank premise failed; no fallback inference')
    a,d=lstsq(X,y*np.sqrt(w),cond=1e-12,lapack_driver='gelsy')[0]
    boundary=inner(w,v,y)/inner(w,v,v)
    candidates=[]
    for kind,aa,dd in [('H0',h0,0.),('boundary',0.,boundary),('interior',float(a),float(d))]:
        residual=y-aa*c-dd*v; sse=inner(w,residual,residual)
        candidates.append(dict(kind=kind,a=aa,d=dd,feasible=aa>=0,a_boundary=aa==0.,sse=sse,score=sse/energy))
    feasible=[p for p in candidates if p['feasible']]; best=min(p['score'] for p in feasible)
    tied=[p for p in feasible if p['score']-best<=1e-12+1e-10*abs(best)]
    p=tied[0]; prediction=p['a']*c+p['d']*v
    return dict(status='no_resolved_cubic_increment_on_training' if p['kind']=='H0' else 'ok',
                rank=rank,singular_values=s.tolist(),condition_number=float(s[0]/s[1]),scale=scale,
                training_energy=energy,training_min=float(min(c)),training_max=float(max(c)),
                training_t=t.tolist(),training_control=c.tolist(),training_target=y.tolist(),
                selected_model='H0' if p['kind']=='H0' else 'Hs',selected=p,candidates=candidates,
                training_prediction=prediction.tolist(),training_residual=(y-prediction).tolist(),
                tied_candidates=[p['kind'] for p in tied])


def compare_score(reference,score):
    delta=reference-score; tol=1e-12+1e-10*abs(reference)
    return dict(delta=delta,outcome='improved' if delta>tol else 'worse' if delta < -tol else 'numerically_unresolved')


def transfer(t,c,y,training,baseline):
    w=weights(t); energy=inner(w,c,c); scale=training['scale']; p=training['selected']
    prediction=p['a']*c+p['d']*c**3/scale**2
    residual=y-prediction; sse=inner(w,residual,residual); score=sse/energy
    total=math.fsum(w)
    signed=math.fsum(float(wi) for wi,ci in zip(w,c) if ci<training['training_min'] or ci>training['training_max'])/total
    magnitude=math.fsum(float(wi) for wi,ci in zip(w,c) if abs(ci)>scale)/total
    support=dict(training_min=training['training_min'],training_max=training['training_max'],
                 transfer_min=float(min(c)),transfer_max=float(max(c)),max_abs_over_training_scale=float(max(abs(c))/scale),
                 outside_signed_time_fraction=signed,outside_magnitude_time_fraction=magnitude)
    return dict(status='ok',selected_model=training['selected_model'],
                baselines={'H0':baseline['models']['H0'],'H1':baseline['models']['H1_selected']},
                fallback_H0=None,prediction=prediction.tolist(),residual=residual.tolist(),
                Es=score,sse=sse,support=support,
                versus_H0=compare_score(baseline['models']['H0']['normalized_error'],score),
                versus_H1=compare_score(baseline['models']['H1_selected']['normalized_error'],score),
                t=t.tolist(),control=c.tolist(),target=y.tolist(),control_energy=energy)


def review(path,reviewed_dir):
    blob=Path(path).read_bytes()
    if sha(blob)!=ARCHIVE_SHA: raise ValueError('archive SHA')
    files=members(blob); root='static-control-004/'
    if sha(files[root+'result.json'])!=RESULT_SHA: raise ValueError('result SHA')
    if sha(files[root+'protocol.md'])!=PROTOCOL_SHA: raise ValueError('protocol SHA')
    for name in ('run_pang_static_control.py','run_pang_temporal_transfer.py'):
        if files[root+'code/'+name]!=(Path(reviewed_dir)/'tools'/name).read_bytes(): raise ValueError('reviewed code bytes')
    actual=json.loads(files[root+'result.json']); config=json.loads(files[root+'config.json'])
    if actual['config']!=config or actual['config_sha256']!=sha(files[root+'config.json']): raise ValueError('config binding')
    if actual['runner_sha256']!=sha(files[root+'code/run_pang_static_control.py']): raise ValueError('runner SHA')
    base_bytes=files[root+'baseline-temporal003.tar.gz']
    if sha(base_bytes)!=BASELINE_SHA: raise ValueError('baseline changed')
    base_files=members(base_bytes); base_root='temporal-transfer-003/'
    baseline=json.loads(base_files[base_root+'result.json'])
    # Literal pinned hashes only: do not import or execute archived code.
    tree=ast.parse(files[root+'code/run_pang_temporal_transfer.py'])
    hashes=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='HASHES' for t in n.targets))
    if config['input_sha256']!=hashes: raise ValueError('config input hashes')
    data={}
    for name,digest in hashes.items():
        raw=base_files[base_root+'inputs/'+name]
        if sha(raw)!=digest: raise ValueError('MAT SHA')
        mat=loadmat(io.BytesIO(raw)); data[name]=(mat['t'].ravel(),mat['meanResp'])
    count=0; maximum=0.; worst=''
    def compare(a,b,path):
        nonlocal count,maximum,worst
        if isinstance(b,dict):
            if set(a)!=set(b): raise ValueError(path+': keys')
            for k in b: compare(a[k],b[k],path+'/'+k)
        elif isinstance(b,list):
            if len(a)!=len(b): raise ValueError(path+': length')
            for i,(u,v) in enumerate(zip(a,b)): compare(u,v,path+'/'+str(i))
        elif type(b) is float:
            if type(a) not in (float,int) or not math.isfinite(a): raise ValueError(path+': finite number')
            delta=abs(a-b); count+=1
            if delta>maximum: maximum=delta; worst=path
            if delta>1e-12+1e-10*abs(b): raise ValueError(f'{path}: {a} != {b}')
        elif type(a)!=type(b) or a!=b: raise ValueError(f'{path}: {a!r} != {b!r}')
    def pair(cell,level,row):
        t,c=data[f'{cell}_{level}.mat']; ot,y=data[f'{cell}_CDM_{level}.mat']
        if not np.array_equal(t,ot): raise ValueError('clock')
        return t,c[row],y[row]
    tests=[('highLum',1),('lowLum',0),('lowLum',1)]
    key=lambda r:(r['cell'],r['level'],r['row'])
    actual_rows={key(r):r for r in actual['transfers']}
    baseline_rows={key(r):r for r in baseline['transfers']}
    if len(actual['transfers'])!=6 or set(actual_rows)!={(cell,l,r) for cell in ('L1','L2') for l,r in tests}: raise ValueError('6 keys')
    if set(actual['training'])!={'L1','L2'}: raise ValueError('2 training keys')
    parameters={}; rows=[]
    for cell in ('L1','L2'):
        training=fit(*pair(cell,'highLum',0),baseline['training'][cell]['H0']['a'])
        compare(actual['training'][cell],training,'training/'+cell)
        parameters[cell]={k:training['selected'][k] for k in ('kind','a','d','score')}
        parameters[cell].update(scale=training['scale'],rank=training['rank'])
        for level,row in tests:
            base=baseline_rows[cell,level,row]; actual_row=actual_rows[cell,level,row]
            frozen={'H0':base['models']['H0'],'H1':base['models']['H1_selected']}
            if actual_row['baselines']!=frozen: raise ValueError('frozen baseline mutation')
            expected=transfer(*pair(cell,level,row),training,base)
            expected.update(cell=cell,level=level,row=row)
            compare(actual_row,expected,f'transfer/{cell}/{level}/{row}')
            rows.append(dict(cell=cell,level=level,row=row,Es=expected['Es'],
                             E0=frozen['H0']['normalized_error'],E1=frozen['H1']['normalized_error'],
                             versus_H0=expected['versus_H0'],versus_H1=expected['versus_H1'],support=expected['support']))
    summary=dict(complete_six_ordering=True,all_six_cubic_better_than_H1=all(r['versus_H1']['outcome']=='improved' for r in rows),
                 prior_temporal003_all_six_improved=False)
    compare(actual['summary'],summary,'summary')
    return dict(verdict='NUMERICAL APPROVE',archive_sha256=ARCHIVE_SHA,result_sha256=RESULT_SHA,archive_bytes=len(blob),
                runner_commit='5c826fe209170800619ccbf4d1829996d5f8610c',protocol_commit='704843a695224448470a70527ce8db3649570a16',
                floating_fields_checked=count,max_absolute_error=maximum,worst_absolute_path=worst,
                parameters=parameters,transfers=rows,summary=summary,
                method='Independent cubic polynomial basis, pivoted QR, scalar fsum quadrature and support indicators; no production imports; archived H0/H1 never refit',
                limitations=['Local result review, not new experiment or independent biological data',
                             'One-comparison stop rule applies; both original003 and cubic004 all-six claims false'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path); parser.add_argument('reviewed_dir',type=Path)
    args=parser.parse_args()
    print(json.dumps(review(args.archive,args.reviewed_dir),indent=2,allow_nan=False))
