"""Independent scalar CPU evaluation of the pinned membrane equations."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def advance(state,current):
    v,sa,si,dra,dri,nov=state
    # Explicit Euler at 0.01 ms; gates advance before voltage, as in author code.
    for _ in range(10):
        targets=[(1/(1+math.exp((-23.7-v)/12.8)))**(1/3),
                 .9/(1+math.exp((-55-v)/-3.9))+.1/(1+math.exp((-74.8-v)/-10.7)),
                 math.sqrt(1/(1+math.exp((-1-v)/9.1))),
                 1/(1+math.exp((-25.7-v)/-6.4)),
                 1/(1+math.exp((-12-v)/11))]
        taus=[.13+3.39*math.exp(-(-73-v)**2/400),
              113*math.exp(-(-71-v)**2/841),
              .5+5.75*math.exp(-(-25-v)**2/1024),890,
              3+166*math.exp(-(-20-v)**2/484)]
        sa,si,dra,dri,nov=[g+.01*(target-g)/tau for g,target,tau in zip((sa,si,dra,dri,nov),targets,taus)]
        potassium=(.082+1.6*sa**3*si+3.5*dra**2*dri+3*nov)*(v+85)
        chloride=.006*(v+30)
        v+=.01*(current-potassium-chloride)/4
    return [v,sa,si,dra,dri,nov]

def main():
    trace=ROOT/'build/photoreceptor_hh_trace.bin'
    actual=np.fromfile(trace,dtype=np.float64).reshape(10000,6,4)
    expected=np.empty_like(actual)
    states=[[-81.9925,.2184,.9653,.0117,.9998,.0017] for _ in range(4)]
    for tick in range(10000):
        for case,current in enumerate((0,10,100,100 if 2000<=tick<4000 else 0)):
            states[case]=advance(states[case],current)
            expected[tick,:,case]=states[case]
    if not np.isfinite(actual).all():raise AssertionError('Nonfinite GPU state')
    errors=np.max(np.abs(actual-expected),axis=(0,2))
    if not np.all(errors<1e-9):raise AssertionError(errors)
    report={'scope':'Fixed-current membrane numerical comparison only; no photons or biological validation',
            'passed':True,'ticks':10000,'simulated_seconds':1,'protocols':4,
            'state_variables':['V','sa','si','dra','dri','nov'],
            'max_abs_error_by_variable':errors.tolist(),
            'gpu_voltage_range_mv':[float(actual[:,0].min()),float(actual[:,0].max())],
            'final_voltage_mv':actual[-1,0].tolist(),
            'initial_voltage_mv':-81.9925,'current_protocols_model_units':['0','10','100','100 on [0.2,0.4) seconds; otherwise 0'],
            'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      (trace,ROOT/'build/photoreceptor_probe.exe',ROOT/'build/photoreceptor_author_hh.cu',Path(__file__))}}
    (ROOT/'reports/photoreceptor_membrane_comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
