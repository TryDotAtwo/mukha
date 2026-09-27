"""Independent adaptive ODE and analytic checks of the radial curriculum plant."""
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp

ROOT=Path(__file__).resolve().parents[1]
exe=ROOT/'build/rocket_vertical_probe.exe'
native=np.array([list(map(float,line.split())) for line in subprocess.check_output([str(exe)],text=True).splitlines()])
results=[]
for scenario in range(5):
    mu=0. if scenario in (0,4) else 6.5e10
    tau=0. if scenario in (0,4) else .3
    throttle=0. if scenario==3 else .6
    y=np.array([2. if scenario==3 else 2500.,-20.,.01 if scenario==2 else 100.,0.])
    if scenario==4:y[:2]=[.0001,-.1]
    t=0.;contact=False
    for segment in range(3):
        burning=y[2]>0
        target=throttle*20000 if burning else 0.
        if tau==0:y[3]=target
        def rhs(t,y):
            z,v,fuel,force=y
            force=force if burning else 0.
            return [v,force/(1000+fuel)-mu/(200000+z)**2,-force/3000,
                    (target-force)/tau if tau else 0.]
        def ground(t,y):return y[0]
        def depletion(t,y):return y[2]
        ground.terminal=True;ground.direction=-1
        depletion.terminal=True;depletion.direction=-1
        sol=solve_ivp(rhs,(t,10),y,method='DOP853',rtol=2e-13,atol=1e-12,
                      events=[ground,depletion] if burning else [ground],max_step=.0001 if scenario==4 else .02)
        assert sol.success
        t=sol.t[-1];y=sol.y[:,-1]
        if len(sol.t_events[0]):contact=True;break
        if t>=10:break
        y[2:]=0
    expected=np.r_[t,y,float(contact)]
    actual=native[scenario,1:]
    error=np.abs(actual-expected)
    assert np.all(error<1e-6),(scenario,actual,expected,error)
    if scenario==0:
        analytic=-20+3000*np.log(1100/1060)
        assert abs(actual[2]-analytic)<1e-8
    results.append(dict(scenario=scenario,max_abs_error=float(error.max()),native=actual.tolist(),reference=expected.tolist()))
paths=[exe,ROOT/'native/rocket_vertical.h',ROOT/'native/rocket_vertical_probe.cpp',Path(__file__)]
report=dict(passed=True,cases=results,dt_by_scenario=[.01,.01,.01,.01,.1],duration_limit=10,
    scope='Radial diagnostic plant only; test constants are not a KSP calibration',
    tests=['vacuum rocket equation','inverse-square gravity with engine lag','fuel-depletion event','descending surface contact','substep ground crossing before velocity reversal'],
    limitations=['No rotation or lateral dynamics','Contact terminates; no settled-landing physics',
                 'No cockpit contact interface','No fly control or KSP equivalence'],
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(ROOT/'reports/rocket_vertical_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
