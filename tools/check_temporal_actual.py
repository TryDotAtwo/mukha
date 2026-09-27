"""Independent archived-result oracle: convolution quadrature + LAPACK QR.

No production runner imports, no Molab, no model/protocol search beyond frozen
32 candidates. Archive identity/provenance audit remains a separate peer lane.
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

ARCHIVE_SHA = 'c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb'
COMMIT = '297201d6a0f2946f0e7b4eae86bf356025219fc1'
ATOL, RTOL, RCOND = 1e-12, 1e-10, 1e-12
NODES, GAUSS = np.polynomial.legendre.leggauss(24)


def state(t, c, tau):
    # Direct integrating-factor convolution from t0 for every output sample.
    # Integrate linear c on each original interval by 24-point Gauss quadrature;
    # never recursively propagate the production interval update.
    out = [float(c[0])]
    for j in range(1, len(t)):
        dt = np.diff(t[:j+1])
        u = t[:j,None]+dt[:,None]*(NODES+1)/2
        amplitude = c[:j,None]+np.diff(c[:j+1])[:,None]*(NODES+1)/2
        integrals = np.exp(-(t[j]-u)/tau)*amplitude/tau*dt[:,None]/2*GAUSS
        out.append(c[0]*math.exp(-(t[j]-t[0])/tau)+math.fsum(integrals.ravel()))
    return np.array(out)


def weights(t):
    return np.array([(t[min(i+1,len(t)-1)]-t[max(i-1,0)])/2 for i in range(len(t))])


def dot(w, x, y):
    return math.fsum(float(a*b*c) for a,b,c in zip(w,x,y))


def tolerance(x):
    return ATOL+RTOL*abs(x)


def fit(t,c,y):
    w=weights(t); energy=dot(w,c,c)
    if energy == 0:
        raise ValueError('zero_training_control_energy')
    a=max(0.,dot(w,c,y)/energy)
    h0=dict(model='H0',a=a,b=0.,tau=None,status='ok',sse=dot(w,y-a*c,y-a*c))
    h0['score']=h0['sse']/energy
    profile=[]
    for index,tau in enumerate(np.geomspace(np.median(np.diff(t)),.25,32)):
        r=c-state(t,c,float(tau)); X=np.column_stack((c,r))*np.sqrt(w)[:,None]
        # SVD for protocol rank diagnostics only; full-rank coefficients use
        # a pivoted QR driver rather than the production SVD reconstruction.
        singular=np.linalg.svd(X,compute_uv=False)
        rank=int(sum(singular>RCOND*singular[0]))
        coef=lstsq(X,y*np.sqrt(w),cond=RCOND,lapack_driver='gelsy' if rank==2 else 'gelsd')[0]
        a,b=map(float,coef); unc=[a,b]
        norm=np.linalg.norm(X,axis=0)
        corr=float(np.dot(X[:,0],X[:,1])/(norm[0]*norm[1])) if all(norm>0) else None
        if a<0:
            a=0.; b=dot(w,r,y)/dot(w,r,r) if dot(w,r,r)>0 else 0.
        residual=y-a*c-b*r; sse=dot(w,residual,residual)
        profile.append(dict(model='H1',index=index,tau=float(tau),a=a,b=b,
                            unconstrained_minimum_norm=unc,singular_values=singular.tolist(),rank=rank,
                            column_correlation=corr,column_norms=norm.tolist(),
                            status='ok' if rank==2 else 'nonidentifiable',a_boundary=a==0.,
                            sse=sse,score=sse/energy))
    eligible=[h0]+[p for p in profile if p['rank']==2]
    best=min(p['score'] for p in eligible)
    tied=[p for p in eligible if p['score']-best<=tolerance(best)]
    selected=tied[0]
    warnings=[]
    if any(p['rank']<2 for p in profile): warnings.append('nonidentifiable_candidates_excluded')
    if len(tied)>1: warnings.append('numerically_tied_profile')
    if selected.get('index') in (0,31): warnings.append('boundary_tau')
    return dict(status='ok',H0=h0,selected=selected,profiles=profile,
                training_control_energy=energy,training_t=t.tolist(),training_control=c.tolist(),
                training_target=y.tolist(),training_predictions={k:predict(t,c,p)[0].tolist()
                for k,p in [('H0',h0),('H1_selected',selected)]},warnings=warnings,tied_candidates=len(tied))


def predict(t,c,p):
    if p['model']=='H0': return p['a']*c,None
    z=state(t,c,p['tau'])
    return p['a']*c+p['b']*(c-z),z


def transfer(t,c,y,training):
    w=weights(t); energy=dot(w,c,c); models={}
    for key,p in [('H0',training['H0']),('H1_selected',training['selected'])]:
        pred,z=predict(t,c,p); residual=y-pred; sse=dot(w,residual,residual)
        models[key]=dict(parameters=p,prediction=pred.tolist(),residual=residual.tolist(),sse=sse,
                         normalized_error=sse/energy if energy else None,state=z.tolist() if z is not None else None)
    delta=None; outcome='zero_control_energy'
    if energy:
        e0=models['H0']['normalized_error']; e1=models['H1_selected']['normalized_error']; delta=e0-e1
        outcome='improved' if delta>tolerance(e0) else 'worse' if delta < -tolerance(e0) else 'numerically_unresolved'
    return dict(status='ok' if energy else 'zero_control_energy',t=t.tolist(),control=c.tolist(),target=y.tolist(),
                control_energy=energy,models=models,error_improvement=delta,outcome=outcome)


def review(archive_path, reviewed_runner):
    blob=Path(archive_path).read_bytes()
    if hashlib.sha256(blob).hexdigest()!=ARCHIVE_SHA: raise ValueError('archive mismatch')
    with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as tar:
        files={m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    root='temporal-transfer-003/'
    code=Path(reviewed_runner).read_bytes()
    if code!=files[root+'code/run_pang_temporal_transfer.py']: raise ValueError('reviewed source mismatch')
    # Read only literal hashes from independently pinned source; never execute it.
    tree=ast.parse(code)
    hashes=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='HASHES' for t in n.targets))
    config=json.loads(files[root+'config.json']); actual=json.loads(files[root+'result.json'])
    if config['input_sha256']!=hashes: raise ValueError('input config mismatch')
    for key,value in [('rank_rcond',RCOND),('comparison_atol',ATOL),('comparison_rtol',RTOL)]:
        if config[key]!=value: raise ValueError('policy mismatch '+key)
    if actual['config_sha256']!=hashlib.sha256(files[root+'config.json']).hexdigest(): raise ValueError('config hash')
    if actual['runner_sha256']!=hashlib.sha256(code).hexdigest(): raise ValueError('runner hash')
    arrays={}
    for name,digest in hashes.items():
        data=files[root+'inputs/'+name]
        if hashlib.sha256(data).hexdigest()!=digest: raise ValueError('input hash '+name)
        mat=loadmat(io.BytesIO(data)); arrays[name]=(mat['t'].ravel(),mat['meanResp'])
    checks=0; max_error=0.; max_relative=0.; worst=''
    def compare(a,b,path):
        nonlocal checks,max_error,max_relative,worst
        if isinstance(b,dict):
            if set(a)!=set(b): raise ValueError(path+': dictionary keys')
            for k in b: compare(a[k],b[k],path+'/'+k)
        elif isinstance(b,list):
            if len(a)!=len(b): raise ValueError(path+': list length')
            for i,(u,v) in enumerate(zip(a,b)): compare(u,v,path+'/'+str(i))
        elif type(b) is float:
            if type(a) not in (float,int) or not math.isfinite(a): raise ValueError(path+': finite float')
            e=abs(a-b); checks+=1
            if e>max_error: max_error=e; worst=path
            max_relative=max(max_relative,e/max(1.,abs(b)))
            if e>1e-12+1e-10*abs(b): raise ValueError(f'{path}: {a} != {b}; error={e}')
        elif type(a)!=type(b) or a!=b: raise ValueError(f'{path}: {a!r} != {b!r}')
    def pair(cell,level,row):
        t,c=arrays[f'{cell}_{level}.mat']; u,y=arrays[f'{cell}_CDM_{level}.mat']
        if not np.array_equal(t,u): raise ValueError('clock mismatch')
        return t,c[row],y[row]
    observations=[]; selected_parameters={}; deltas=[]
    expected_keys={(cell,level,row) for cell in ('L1','L2') for level,row in [('highLum',1),('lowLum',0),('lowLum',1)]}
    keyed={(r['cell'],r['level'],r['row']):r for r in actual['transfers']}
    if len(actual['transfers'])!=6 or set(keyed)!=expected_keys: raise ValueError('transfer keys')
    if set(actual['training'])!={'L1','L2'}: raise ValueError('training keys')
    for cell in ('L1','L2'):
        training=fit(*pair(cell,'highLum',0))
        compare(actual['training'][cell],training,'training/'+cell)
        selected_parameters[cell]={k:training['selected'][k] for k in ('model','a','b','tau','score')}
        for level,row in [('highLum',1),('lowLum',0),('lowLum',1)]:
            expected=transfer(*pair(cell,level,row),training)
            expected.update(cell=cell,level=level,row=row)
            compare(keyed[cell,level,row],expected,f'transfer/{cell}/{level}/{row}')
            deltas.append(expected['error_improvement'])
            observations.append(dict(cell=cell,level=level,row=row,
                                     E0=expected['models']['H0']['normalized_error'],
                                     E1=expected['models']['H1_selected']['normalized_error'],
                                     delta=expected['error_improvement'],outcome=expected['outcome']))
    summary=dict(status='ok',all_six_improved=all(r['outcome']=='improved' for r in observations),
                 sum_normalized_error_improvement=math.fsum(deltas))
    compare(actual['summary'],summary,'summary')
    return dict(verdict='NUMERICAL APPROVE',archive_sha256=ARCHIVE_SHA,archive_bytes=len(blob),
                runner_commit=COMMIT,runner_sha256=hashlib.sha256(code).hexdigest(),profiles_checked=64,
                floating_fields_checked=checks,max_absolute_error=max_error,worst_absolute_path=worst,
                max_error_over_max1_reference=max_relative,selected_parameters=selected_parameters,
                transfers=observations,summary=summary,
                method='Direct integrating-factor convolution via 24-node Gauss quadrature; pivoted QR coefficients; fsum weighted scores; no runner imports',
                limitations=['Local foreground artifact per operator receipt, not Molab execution',
                             'Deterministic fixed mean curves; not independent animals or blind validation',
                             'Rank and comparison policies unchanged; no causal/feedback/physiological conclusion'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path); parser.add_argument('reviewed_runner',type=Path)
    args=parser.parse_args()
    print(json.dumps(review(args.archive,args.reviewed_runner),indent=2,allow_nan=False))
