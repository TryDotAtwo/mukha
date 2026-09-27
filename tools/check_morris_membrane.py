"""Independent scalar integration against the original author's GPU kernel."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def main():
    trace=ROOT/'build/morris_trace.bin'
    gpu=np.fromfile(trace,dtype=np.float64).reshape(10000,2,4)
    cpu=np.empty_like(gpu)
    states=[[-50.,.5] for _ in range(4)]
    for tick in range(10000):
        for case,current in enumerate((0,-.48,.48,-.96 if 2000<=tick<4000 else 0)):
            v,n=states[case]
            for _ in range(10):
                n_target=.5*(1+math.tanh((v+5)/10))
                dn=.0025*math.cosh((v+5)/20)*(n_target-n)
                calcium=.5*(1+math.tanh((v+1)/15))
                dv=current-.5*(v+50)-2*n*(v+70)-1.1*calcium*(v-10)+.02
                v,n=v+.01*dv,n+.01*dn
            states[case]=[v,n];cpu[tick,:,case]=[v,n]
    errors=np.max(np.abs(gpu-cpu),axis=(0,2))
    if not np.isfinite(gpu).all() or not np.all(errors<1e-9):raise AssertionError(errors)
    report={'scope':'Morris-Lecar equation validation at historical lamina parameter values; not biological calibration',
            'passed':True,'ticks':10000,'dt_seconds':.0001,'membrane_substeps':10,
            'max_abs_errors_V_n':errors.tolist(),'final_V':gpu[-1,0].tolist(),
            'parameter_aliases':{'historical_V_k':'current_V_K','historical_G_Ca':'current_g_Ca','historical_G_k':'current_g_K'},
            'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [trace,ROOT/'build/morris_probe.exe',ROOT/'build/morris_author.cu',Path(__file__)]}}
    (ROOT/'reports/morris_membrane_comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
