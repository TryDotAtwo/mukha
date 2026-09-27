import json,hashlib,subprocess
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
lines=subprocess.check_output([str(root/'build/dallmann_observation_probe.exe')],text=True).splitlines()
assert lines[-1]=='rejected 5'
got=np.array([[float(x) for x in line.split()] for line in lines[:-1]])
a=np.array([90,89,88,86,86,87,89,90,90.]);v=np.diff(a)*5;v=np.r_[v[0],v]
t=np.linspace(0,len(a)/5,len(a));k=np.exp(-t/.30)-np.exp(-t/.03);k/=k.sum()
errors=[]
x=a-80
claw=-4.28350195279596e-09*x**4-3.08701145496934e-07*x**3+.000123726627502515*x**2+.000474757347677466*x-.0357758464550021
masked=v.copy();masked[3]=0
for m,active in enumerate([v < -5,v > 5,(v > 5)|(v < -5),claw,(masked>5)|(masked<-5),a]):
 rows=got[got[:,0]==m];assert len(rows)==len(a)
 np.testing.assert_allclose(rows[:,2],active,rtol=1e-14,atol=1e-14)
 expected=np.convolve(active.astype(float),k)[:len(a)]
 np.testing.assert_allclose(rows[:,3],k,rtol=2e-14,atol=1e-14)
 np.testing.assert_allclose(rows[:,4],expected,rtol=2e-14,atol=1e-14)
 errors.extend(np.abs(rows[:,3]-k));errors.extend(np.abs(rows[:,4]-expected))
assert max(errors)<1e-12 # web carries angle-sized values (~90), unlike binary motion.
source=root/'data/reference/feco_inhibition/code/utils/imaging_predict_gcamp.m'
report=dict(modes=['hook_flex','hook_ext','club','claw','9A','web'],samples=54,max_error=float(max(errors)),threshold_equality_inactive=True,invalid_inputs_rejected=5,matlab_executed=False,biological_validation=False,external_9a_mask_is_analysis_only=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(root/'reports/dallmann_observation.json').write_text(json.dumps(report,indent=2));print(report)
