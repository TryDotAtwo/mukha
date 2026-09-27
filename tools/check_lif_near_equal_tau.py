"""Compare compiled LIF coupling against an independent high-precision ODE integral."""
import json
import math
import subprocess
from pathlib import Path

import mpmath as mp

ROOT=Path(__file__).resolve().parents[1]
EXE=ROOT/'build/lif_coeff_probe.exe'
REPORT=ROOT/'reports/lif_near_equal_tau.json'


def main():
    EXE.parent.mkdir(exist_ok=True)
    subprocess.run(['cmd','/c','tools\\build_lif_coeff_probe.cmd'],check=True,cwd=ROOT)
    mp.mp.dps=80
    t=20.0
    cases=[('equal',0.1,t,t),
           ('next_float_up',0.1,t,math.nextafter(t,math.inf)),
           ('next_float_down',0.1,t,math.nextafter(t,-math.inf)),
           ('near_up',0.1,t,20.000001),
           ('near_down',0.1,t,19.999999),
           ('ordinary',0.1,t,5.0)]
    results=[]
    for name,dt,tm,ts in cases:
        output=subprocess.check_output([str(EXE),repr(dt),repr(tm),repr(ts)],text=True).split()
        actual=float(output[0]); changed=bool(int(output[1]))
        md,mm,ms=map(mp.mpf,(dt,tm,ts))
        reference=mp.quad(lambda s:mp.exp(-(md-s)/mm)*mp.exp(-s/ms)/mm,[0,md])
        error=abs(actual-float(reference))
        if error>2e-15:
            raise AssertionError(f'{name}: {actual} vs {reference}')
        if name=='ordinary':
            legacy=(math.exp(-dt/tm)-math.exp(-dt/ts))*ts/(tm-ts)
            if actual!=legacy or changed:
                raise AssertionError('ordinary source profile changed')
        if name.startswith('next_float') and not changed:
            raise AssertionError('near-equal branch not selected')
        results.append({'case':name,'dt_ms':dt,'membrane_ms':tm,'synapse_ms':ts,
                        'coefficient':actual,'reference':float(reference),
                        'absolute_error':error,'checkpoint_semantic_tag_required':changed})
    REPORT.write_text(json.dumps({'passed':True,'reference':'80-digit ODE integral',
                                  'cases':results},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'cases':len(results),'max_absolute_error':max(x['absolute_error'] for x in results)}))


if __name__=='__main__':
    main()
