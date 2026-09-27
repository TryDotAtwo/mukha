import subprocess,math,json
from scipy.integrate import quad
from pathlib import Path
r={}; errors=[]
for line in subprocess.check_output(['build/exposure_observation_probe.exe'],text=True).splitlines():
 s=line.split()
 if s[0]=='rejected': assert s[1]=='5'; continue
 mode,i,end,mean=int(s[1]),int(s[2]),int(s[3]),float(s[4]); r[mode,i]=mean
 assert end==(i*100000000000+400)//801
 start=((i-1)*100000000000+400)//801
 def signal(t):return 240*(-math.expm1(-t/.5)) if t<=.075 else 240*(-math.expm1(-.075/.5))*math.exp(-(t-.075)/.5)
 a=start*1e-9;b=end*1e-9
 expected=quad(signal,a,b,points=[.075] if a<.075<b else None,epsabs=1e-12)[0]/(b-a)
 errors.append(abs(expected-mean))
assert len(r)==16 and max(errors)<1e-10
split=max(abs(r[0,i]-r[1,i]) for i in range(1,9)); assert split<1e-10
report=dict(frames_checked=16,invalid_cases=5,max_quadrature_error=max(errors),max_subdivision_error=split,invalid_input_preserves_state=True,biological_validation=False)
Path('reports/exposure_observation.json').write_text(json.dumps(report,indent=2)); print(report)
