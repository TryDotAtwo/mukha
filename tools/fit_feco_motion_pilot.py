"""Exploratory calcium predictor; deliberately not a neural firing model."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import lsq_linear

ROOT = Path(__file__).resolve().parents[1]
partition_path = ROOT/'data/derived/feco_protocol_partition_v1/manifest.json'
partition = json.loads(partition_path.read_text())
out = ROOT/'data/derived/feco_motion_pilot_v1'
if out.exists():
    raise FileExistsError('Immutable experiment already exists')
out.mkdir()
spec = dict(hypothesis='Nonnegative filtered flexion/extension velocity predicts calcium response',
    tau_seconds=[0.125, 0.25, 0.5, 1.0, 2.0], dt_seconds=1/8.01,
    parameters='One shared pair of velocity gains and intercept per recording region',
    initialization='Zero filtered velocity at first recorded frame; initial velocity zero',
    missing='Exclude entire response row if any angle or response sample is nonfinite; no interpolation',
    fit='Unweighted sample least squares; nonnegative gains, unrestricted intercept; tau chosen on calibration SSE',
    test='Frozen swing protocol; compare MSE against calibration response mean',
    acceptance='Exploratory only; improvement must be positive in every tested region to support general transfer',
    limitations=['Not independent animals', 'Calcium kinetics and sensory dynamics are confounded',
                'No spike-rate interpretation', 'Assumed zero initial filter state',
                'Missing-row exclusion can bias sampling', 'No MaleCNS mapping'],
    partition_sha256=hashlib.sha256(partition_path.read_bytes()).hexdigest(), runtime_enabled=False)
(out/'spec.json').write_text(json.dumps(spec,indent=2))
(out/'INCOMPLETE').write_text('running')

def design(angle, tau):
    velocity = np.diff(angle,axis=1,prepend=angle[:,:1])/spec['dt_seconds']
    drive = np.stack([np.maximum(-velocity,0),np.maximum(velocity,0)],axis=-1)
    filtered = np.zeros_like(drive)
    decay = np.exp(-spec['dt_seconds']/tau)
    for t in range(1,angle.shape[1]):
        filtered[:,t] = decay*filtered[:,t-1]+(1-decay)*drive[:,t]
    return np.column_stack([filtered.reshape(-1,2),np.ones(angle.size)])

results=[]
files=sorted({e['file'] for e in partition['entries'] if e['population'] in ('club','hook')})
for filename in files:
    path=ROOT/'data/derived/mamiya2018_recordings_v1'/filename
    entries=[e for e in partition['entries'] if e['file']==filename]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==entries[0]['sha256']
    groups={'calibration':[], 'protocol_holdout':[]}; excluded={}
    with np.load(path,allow_pickle=False) as data:
        for e in entries:
            prefix=e['protocol']; a=data[prefix+'_Angle']; y=data[prefix+'_DFF']
            valid=np.isfinite(a).all(axis=1)&np.isfinite(y).all(axis=1)
            excluded[prefix]=np.flatnonzero(~valid).tolist()
            groups[e['role']].append((a[valid], y[valid]))
    train_y=np.concatenate([y.ravel() for a,y in groups['calibration']])
    best=None
    for tau in spec['tau_seconds']:
        x=np.concatenate([design(a,tau) for a,y in groups['calibration']])
        fit=lsq_linear(x,train_y,bounds=([0,0,-np.inf],[np.inf]*3),tol=1e-12)
        assert fit.success
        mse=float(np.mean((x@fit.x-train_y)**2))
        if best is None or mse<best[0]:best=(mse,tau,fit.x)
    mse,tau,weights=best
    test_y=np.concatenate([y.ravel() for a,y in groups['protocol_holdout']])
    prediction=np.concatenate([design(a,tau)@weights for a,y in groups['protocol_holdout']])
    test_mse=float(np.mean((prediction-test_y)**2))
    baseline=float(np.mean((test_y-train_y.mean())**2))
    np.savez_compressed(out/(Path(filename).stem+'_prediction.npz'),predicted=prediction,observed=test_y)
    results.append(dict(file=filename,population=entries[0]['population'],excluded_rows=excluded,
        calibration_samples=train_y.size,holdout_samples=test_y.size,tau_seconds=tau,
        flexion_gain=weights[0],extension_gain=weights[1],intercept=weights[2],
        calibration_mse=mse,holdout_mse=test_mse,constant_baseline_mse=baseline,
        relative_mse_improvement=1-test_mse/baseline))
report=dict(spec=spec,results=results,all_regions_improve=all(r['relative_mse_improvement']>0 for r in results),
    biological_validation_passed=False,runtime_enabled=False)
(out/'report.json').write_text(json.dumps(report,indent=2))
(ROOT/'reports/feco_motion_pilot.json').write_text(json.dumps(report,indent=2))
(out/'INCOMPLETE').unlink()
print(json.dumps([{k:r[k] for k in ('file','tau_seconds','relative_mse_improvement')} for r in results],indent=2))
