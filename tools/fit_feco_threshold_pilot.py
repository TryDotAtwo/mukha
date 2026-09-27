"""Retrospective protocol comparison; not reproduction of unavailable Dryad fit."""
import json,hashlib,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
old=json.loads((ROOT/'reports/feco_motion_pilot.json').read_text())
partition=json.loads((ROOT/'data/derived/feco_protocol_partition_v1/manifest.json').read_text())
out=ROOT/'data/derived/feco_threshold_pilot_v1'
if out.exists():raise FileExistsError('Immutable experiment exists')
out.mkdir();(out/'INCOMPLETE').write_text('running')
spec=dict(threshold_hook=-5,threshold_club=5,sampling_rate=8.01,
    calibration='Ramp-and-hold; ordinary least-squares scale and intercept per region',
    assessment='Previously observed swing set; retrospective model comparison',
    missing='Identical complete-row exclusions to linear pilot',
    original_author_fit_reproduced=False,independent_validation=False,runtime_enabled=False)
(out/'spec.json').write_text(json.dumps(spec,indent=2))
results=[];errors=[]
exe=ROOT/'build/dallmann_observation_cli.exe'
for previous in old['results']:
    name=previous['file']; path=ROOT/'data/derived/mamiya2018_recordings_v1'/name
    expected=next(e['sha256'] for e in partition['entries'] if e['file']==name)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    mode=0 if previous['population']=='hook' else 2; threshold=-5 if mode==0 else 5
    groups={};requests=[];references=[];sizes=[]
    with np.load(path,allow_pickle=False) as d:
        for protocol in ('RampAndHold_FlexFirst','RampAndHold_ExtFirst','Swing_FlexFirst'):
            a=d[protocol+'_Angle'];y=d[protocol+'_DFF']
            keep=np.isfinite(a).all(axis=1)&np.isfinite(y).all(axis=1)
            assert np.flatnonzero(~keep).tolist()==previous['excluded_rows'][protocol]
            groups[protocol]=y[keep].ravel();sizes.append(int(keep.sum()))
            for row in a[keep]:
                requests.append(f'{mode} {len(row)} 8.01 {threshold} '+' '.join(map(repr,row.tolist())))
                v=np.diff(row)*8.01;v=np.r_[v[0],v]
                active=v<threshold if mode==0 else (v>threshold)|(v<-threshold)
                t=np.linspace(0,len(row)/8.01,len(row));k=np.exp(-t/.3)-np.exp(-t/.03);k/=k.sum()
                references.append(np.convolve(active,k)[:len(row)])
    lines=subprocess.check_output([str(exe)],input='\n'.join(requests)+'\n',text=True).splitlines()
    assert len(lines)==len(references)
    predictions=[np.fromstring(line,sep=' ') for line in lines]
    for got,ref in zip(predictions,references):
        assert got.shape==ref.shape;errors.append(float(np.max(np.abs(got-ref))))
    cut=sum(sizes[:2]);train_x=np.concatenate(predictions[:cut]);test_x=np.concatenate(predictions[cut:])
    train_y=np.concatenate(list(groups.values())[:2]);test_y=groups['Swing_FlexFirst']
    design=np.column_stack([train_x,np.ones(len(train_x))])
    weights=np.linalg.lstsq(design,train_y,rcond=None)[0]
    predicted=weights[0]*test_x+weights[1]
    mse=float(np.mean((predicted-test_y)**2));baseline=float(np.mean((train_y.mean()-test_y)**2))
    np.savez_compressed(out/(Path(name).stem+'.npz'),predicted=predicted,observed=test_y)
    results.append(dict(file=name,scale=float(weights[0]),intercept=float(weights[1]),
        assessment_mse=mse,baseline_mse=baseline,relative_mse_improvement=1-mse/baseline,
        previous_linear_mse=previous['holdout_mse']))
assert max(errors)<1e-12
report=dict(spec=spec,results=results,native_numpy_max_error=max(errors),
    executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),biological_validation=False)
(out/'report.json').write_text(json.dumps(report,indent=2))
(ROOT/'reports/feco_threshold_pilot.json').write_text(json.dumps(report,indent=2))
(out/'INCOMPLETE').unlink()
print(json.dumps(results,indent=2))
