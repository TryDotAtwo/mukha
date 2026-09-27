"""Check staggered cabin acceleration and causal interventions at four steps."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
results=[];paths=[]
for suffix,scale in [('',1),('_halfstep',2),('_quarterstep',4),('_eighthstep',8)]:
    path=ROOT/f'build/closed_mechanics{suffix}_trace.csv';paths.append(path)
    f=pd.read_csv(path,float_precision='round_trip')
    assert np.isfinite(f.to_numpy()).all()
    groups={k:g.reset_index(drop=True) for k,g in f.groupby(['feedback','contact','pulse'])}
    n=10000*scale;dt=.0001/scale
    assert len(f)==n*(8 if scale<=2 else 2)
    for (feedback,contact,pulse),g in groups.items():
        np.testing.assert_array_equal(g.tick,np.arange(1,n+1))
        np.testing.assert_allclose(g.time,np.arange(1,n+1)*dt,rtol=0,atol=1e-10)
        np.testing.assert_array_equal(g.q_start_mm.iloc[1:],g.q_end_mm.iloc[:-1])
        np.testing.assert_array_equal(g.throttle,np.clip(g.q_start_mm/.3,0,1))
        mass=1000+np.r_[100.,g.fuel_kg.to_numpy()[:-1]]
        force=np.r_[0.,g.thrust_n.to_numpy()[:-1]]
        z=np.r_[2500.,g.altitude_m.to_numpy()[:-1]]
        gravity=-6.5e10/(200000+z)**2
        acceleration=gravity+force/mass
        expected=1000*(gravity-acceleration) if feedback else np.zeros(n)
        np.testing.assert_allclose(g.effective_g_mm_s2,expected,rtol=1e-12,atol=1e-10)
        target=g.throttle.to_numpy()*20000
        np.testing.assert_allclose(g.thrust_n,target+(force-target)*np.exp(-dt/.3),rtol=0,atol=1e-9)
    cols=['altitude_m','velocity_mps','fuel_kg','thrust_n']
    if scale<=2:
        baseline=groups[(0,0,0)][cols].to_numpy()
        for key,g in groups.items():
            if key[1:]!=(1,1):
                np.testing.assert_array_equal(g[cols].to_numpy(),baseline)
                assert (g.effective_g_mm_s2==0).all()
    off=groups[(0,1,1)];on=groups[(1,1,1)]
    dv=float(on.velocity_mps.iloc[-1]-off.velocity_mps.iloc[-1])
    dq=float(np.max(abs(on.q_end_mm.to_numpy()-off.q_end_mm.to_numpy())))
    assert dv>0 and dq>0 and (on.effective_g_mm_s2<0).any()
    results.append(dict(dt_seconds=dt,steps=len(f),feedback_velocity_effect_mps=dv,
        feedback_slider_effect_mm=dq,final_velocity_mps=float(on.velocity_mps.iloc[-1])))
last=abs(results[-1]['feedback_velocity_effect_mps']-results[-2]['feedback_velocity_effect_mps'])/abs(results[-1]['feedback_velocity_effect_mps'])
paths += [ROOT/'native/closed_mechanics_probe.cpp',ROOT/'native/rocket_vertical.h',
          ROOT/'build/closed_mechanics_probe.exe',ROOT/'data/derived/contact_diagnostic/body.xml',
          ROOT/'data/reference/mujoco_3.9.0/bin/mujoco.dll',Path(__file__)]
report=dict(causal_and_clock_checks_passed=True,refinement=results,
    last_relative_effect_change=last,last_refinement_within_one_percent=last<.01,
    scope='Closed radial mechanics diagnostic, fixed joint pulse, no neural controller',
    assumptions=['Nonrotating cabin with +z radial outward','Uniform gravity at rocket center',
                 'Fixed supported thorax; model units mm','Start-of-step coupling held for one step'],
    limitations=['No rotation, tidal terms or physical landing supports',
                 'Convergence of diagnostic effect magnitude not yet established',
                 'Not a biological or learned flight result'],
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(ROOT/'reports/closed_mechanics_causality.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='hashes'},indent=2))
