"""Describe observed transfer failure without refitting on the assessment set."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
pilot_path=ROOT/'reports/feco_motion_pilot.json'
pilot=json.loads(pilot_path.read_text())
partition=json.loads((ROOT/'data/derived/feco_protocol_partition_v1/manifest.json').read_text())
records=[]
for fit in pilot['results']:
    path=ROOT/'data/derived/mamiya2018_recordings_v1'/fit['file']
    expected=next(e['sha256'] for e in partition['entries'] if e['file']==fit['file'])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    with np.load(path,allow_pickle=False) as data:
        protocols={}
        for protocol in ('RampAndHold_FlexFirst','RampAndHold_ExtFirst','Swing_FlexFirst'):
            a=data[protocol+'_Angle']; y=data[protocol+'_DFF']
            keep=np.isfinite(a).all(axis=1)&np.isfinite(y).all(axis=1)
            assert np.flatnonzero(~keep).tolist()==fit['excluded_rows'][protocol]
            a=a[keep]; y=y[keep]
            speed=np.abs(np.diff(a,axis=1))*8.01
            protocols[protocol]=dict(rows=int(keep.sum()),frames=a.shape[1],
                angle_min=float(a.min()),angle_max=float(a.max()),
                frame_averaged_speed_quantiles=np.quantile(speed,[.5,.95,.99,1]).tolist(),
                row_peak_speed_median=float(np.median(speed.max(axis=1))),
                response_row_peak_median=float(np.median(y.max(axis=1))))
        prediction_path=ROOT/'data/derived/feco_motion_pilot_v1'/(path.stem+'_prediction.npz')
        with np.load(prediction_path,allow_pickle=False) as saved:
            observed=saved['observed'].reshape(data['Swing_FlexFirst_DFF'].shape)
            predicted=saved['predicted'].reshape(observed.shape)
            assert observed.shape==data['Swing_FlexFirst_DFF'].shape
            np.testing.assert_array_equal(observed,data['Swing_FlexFirst_DFF'])
            peak_ratio=float(np.median(predicted.max(axis=1))/np.median(observed.max(axis=1)))
            bias=float((predicted-observed).mean())
            mse=float(np.mean((predicted-observed)**2))
            assert np.isclose(mse,fit['holdout_mse'],rtol=1e-14,atol=1e-14)
    records.append(dict(file=fit['file'],protocols=protocols,
        swing_prediction_to_observed_median_peak_ratio=peak_ratio,swing_mean_error=bias,
        swing_mse=mse,swing_constant_baseline_mse=fit['constant_baseline_mse']))
report=dict(pilot_sha256=hashlib.sha256(pilot_path.read_bytes()).hexdigest(),
    refit_performed=False,records=records,
    sampling=dict(imaging_interval_seconds=1/8.01,
      nominal_ramp_displacement_degrees=18,nominal_motor_speed_degrees_per_second=240,
      nominal_constant_speed_traverse_seconds=18/240,
      nominal_traverse_imaging_frames=18/240*8.01,
      caveat='Motor specification excludes acceleration and specimen mechanics; exported angle is frame averaged, not instantaneous velocity',
      source='https://faculty.washington.edu/tuthill/docs/mamiya_2018.pdf',source_section='STAR Methods, Moving the tibia/pin and Tracking the femur-tibia joint angle'),
    conclusion='Frame-rate differentiation cannot identify within-frame peak speed. Failure does not uniquely identify saturation or calcium kinetics.',
    runtime_enabled=False)
(ROOT/'reports/feco_transfer_diagnosis.json').write_text(json.dumps(report,indent=2))
print(json.dumps([dict(file=r['file'],peak_ratio=r['swing_prediction_to_observed_median_peak_ratio'],
    median_peak_speed_by_protocol={p:v['row_peak_speed_median'] for p,v in r['protocols'].items()}) for r in records],indent=2))
