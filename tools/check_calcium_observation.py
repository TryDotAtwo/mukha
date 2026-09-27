"""Independent high-precision and numerical-quadrature observation checks."""
from decimal import Decimal, localcontext
import hashlib,json,subprocess
from pathlib import Path
from scipy.integrate import quad
import math
ROOT=Path(__file__).resolve().parents[1]
exe=ROOT/'build/calcium_observation_probe.exe'
lines=subprocess.check_output([str(exe)],text=True).splitlines()
errors=[]; pulse_error=None
for line in lines:
    fields=line.split()
    if fields[0]=='segment':
        dt,end,integral=map(float,fields[1:])
        with localcontext() as ctx:
            ctx.prec=70
            t=Decimal.from_float(dt); c=Decimal.from_float(.2); d=Decimal(3); tau=Decimal('.5')
            decay=(-t/tau).exp()
            expected_end=d+(c-d)*decay
            expected_integral=d*t+(c-d)*tau*(1-decay)
        errors.extend([abs(end-float(expected_end)),abs(integral-float(expected_integral))])
        assert abs(integral-float(expected_integral))<=1e-14*max(abs(float(expected_integral)),1e-300)
    elif fields[0]=='pulse':
        end,mean,split=map(float,fields[1:]); frame=1/8.01
        peak=240*(1-math.exp(-.075/.5))
        value=lambda t:240*(1-math.exp(-t/.5)) if t<=.075 else peak*math.exp(-(t-.075)/.5)
        expected=quad(value,0,frame,points=[.075],epsabs=1e-12,epsrel=1e-12)[0]/frame
        pulse_error=abs(mean-expected)
        assert pulse_error<1e-11 and abs(mean-split)<1e-11 and abs(end-value(frame))<1e-11
    else:
        assert fields==['rejected','4']
assert len(errors)==12 and pulse_error is not None and max(errors)<1e-13
report=dict(segment_checks=6,max_absolute_error=max(errors),pulse_quadrature_error=pulse_error,
    subdivision_check_passed=True,invalid_cases_rejected=4,biological_kinetics_validated=False,
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
      [exe,ROOT/'native/calcium_observation.h',ROOT/'native/calcium_observation_probe.cpp']})
(ROOT/'reports/calcium_observation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
