"""Extended step refinement; keep the original four-resolution report immutable."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
old_path=ROOT/'reports/closed_mechanics_causality.json'
old=json.loads(old_path.read_text())
anchor=ROOT/'build/closed_mechanics_eighthstep_trace.csv'
assert hashlib.sha256(anchor.read_bytes()).hexdigest()==old['hashes'][str(anchor.relative_to(ROOT))]
results=[old['refinement'][-1]]
paths=[old_path,anchor]
for label,scale in [('sixteenthstep',16),('thirtysecondstep',32),('sixtyfourthstep',64)]:
    path=ROOT/f'build/closed_mechanics_{label}_trace.csv';paths.append(path)
    f=pd.read_csv(path,float_precision='round_trip')
    n=10000*scale;dt=.0001/scale
    assert len(f)==2*n and np.isfinite(f.to_numpy()).all()
    assert (f.contact==1).all() and (f.pulse==1).all()
    groups={k:g.reset_index(drop=True) for k,g in f.groupby('feedback')}
    assert set(groups)=={0,1}
    for feedback,g in groups.items():
        np.testing.assert_array_equal(g.tick,np.arange(1,n+1))
        np.testing.assert_allclose(g.time,np.arange(1,n+1)*dt,rtol=0,atol=1e-10)
        np.testing.assert_array_equal(g.q_start_mm.iloc[1:],g.q_end_mm.iloc[:-1])
        np.testing.assert_array_equal(g.throttle,np.clip(g.q_start_mm/.3,0,1))
        mass=1000+np.r_[100.,g.fuel_kg.to_numpy()[:-1]]
        force=np.r_[0.,g.thrust_n.to_numpy()[:-1]]
        z=np.r_[2500.,g.altitude_m.to_numpy()[:-1]]
        gravity=-6.5e10/(200000+z)**2
        expected=1000*(gravity-(gravity+force/mass)) if feedback else np.zeros(n)
        np.testing.assert_allclose(g.effective_g_mm_s2,expected,rtol=1e-12,atol=1e-10)
    off,on=groups[0],groups[1]
    dv=float(on.velocity_mps.iloc[-1]-off.velocity_mps.iloc[-1]);assert dv>0
    results.append(dict(dt_seconds=dt,steps=len(f),feedback_velocity_effect_mps=dv,
        final_velocity_mps=float(on.velocity_mps.iloc[-1])))
last=abs(results[-1]['feedback_velocity_effect_mps']-results[-2]['feedback_velocity_effect_mps'])/abs(results[-1]['feedback_velocity_effect_mps'])
paths += [ROOT/'native/closed_mechanics_probe.cpp',ROOT/'native/rocket_vertical.h',
          ROOT/'build/closed_mechanics_probe.exe',ROOT/'data/derived/contact_diagnostic/body.xml',Path(__file__)]
report=dict(causal_and_clock_checks_passed=True,refinement=results,
    last_relative_effect_change=last,last_refinement_within_one_percent=last<.01,
    scope='One-second driven mechanical pair only; no general convergence or biological validation',
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(ROOT/'reports/closed_mechanics_refinement.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='hashes'},indent=2))
