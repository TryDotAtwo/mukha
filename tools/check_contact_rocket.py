"""Audit the live body -> passive slider -> radial rocket diagnostic."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
trace=ROOT/'build/contact_rocket_trace.csv'
f=pd.read_csv(trace,float_precision='round_trip')
assert len(f)==40000 and np.isfinite(f.to_numpy()).all()
groups={k:g.reset_index(drop=True) for k,g in f.groupby(['contact','pulse'])}
assert set(groups)=={(0,0),(0,1),(1,0),(1,1)}
dt=.0001
engine_errors=[]
fuel_errors=[]
for key,g in groups.items():
    np.testing.assert_array_equal(g.tick,np.arange(1,10001))
    np.testing.assert_allclose(g.time,np.arange(1,10001)*dt,rtol=0,atol=1e-12)
    np.testing.assert_array_equal(g.q_start_mm.iloc[1:].to_numpy(),g.q_end_mm.iloc[:-1].to_numpy())
    np.testing.assert_array_equal(g.throttle.to_numpy(),np.clip(g.q_start_mm.to_numpy()/.3,0,1))
    previous=np.r_[0.,g.thrust_n.to_numpy()[:-1]]
    target=g.throttle.to_numpy()*20000
    expected_force=target+(previous-target)*np.exp(-dt/.3)
    impulse=target*dt+(previous-target)*.3*(-np.expm1(-dt/.3))
    expected_fuel=np.r_[100.,g.fuel_kg.to_numpy()[:-1]]-impulse/3000
    engine_errors.append(float(np.max(abs(g.thrust_n.to_numpy()-expected_force))))
    fuel_errors.append(float(np.max(abs(g.fuel_kg.to_numpy()-expected_fuel))))
assert max(engine_errors)<1e-9 and max(fuel_errors)<1e-12
cols=['altitude_m','velocity_mps','fuel_kg','thrust_n']
baseline=groups[(0,0)][cols].to_numpy()
for key in [(0,1),(1,0)]:np.testing.assert_array_equal(baseline,groups[key][cols].to_numpy())
driven=groups[(1,1)]
effect=float(np.max(abs(driven.velocity_mps.to_numpy()-baseline[:,1])))
assert effect>1e-3 and driven.throttle.max()>0
paths=[trace,ROOT/'native/contact_rocket_probe.cpp',ROOT/'native/rocket_vertical.h',
       ROOT/'build/contact_rocket_probe.exe',ROOT/'data/derived/contact_diagnostic/body.xml',
       ROOT/'data/reference/mujoco_3.9.0/bin/mujoco.dll',Path(__file__)]
report=dict(passed=True,physics_steps=40000,dt_seconds=dt,
    no_contact_pulse_equals_baseline=True,no_pulse_contact_equals_baseline=True,
    max_velocity_effect_mps=effect,max_throttle=float(driven.throttle.max()),
    max_engine_recurrence_error=max(engine_errors),max_fuel_recurrence_error=max(fuel_errors),
    sampling='joint position at beginning of each shared body/rocket step',
    scope='Live one-way mechanical diagnostic, no neural controller or landing',
    limitations=['Fixed supported body uses existing diagnostic gravity',
                 'No rocket acceleration feedback to body','No calibrated motor mapping',
                 'Single passive slider; no three-axis joystick'],
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(ROOT/'reports/contact_rocket_causality.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
