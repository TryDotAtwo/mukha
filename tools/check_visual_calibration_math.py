"""Independent PyTorch FP64 checks of native published calibration arithmetic."""
import hashlib
import json
import subprocess
from pathlib import Path
import torch

ROOT=Path(__file__).resolve().parents[1]
exe=ROOT/'build/visual_calibration_probe.exe'
lines=subprocess.check_output([str(exe)],text=True).splitlines()
records=[line.split() for line in lines]
errors=[]
for kind,q,value in [r for r in records if r[0]=='capture']:
    expected=torch.log((torch.tensor(float(q),dtype=torch.float64)+.001)/1.001).item()
    errors.append(abs(expected-float(value)))
assert len(errors)==7 and max(errors)<1e-14
p=torch.tensor([1.,2.,3.],dtype=torch.float64)
v=torch.tensor([3.,2.,1.],dtype=torch.float64)
w=torch.tensor([1.,2.,4.],dtype=torch.float64)
expected=((w*p*v).sum()/torch.sqrt((w*p*p).sum()*(w*v*v).sum())).item()
values={r[0]:float(r[1]) for r in records if r[0]!='capture'}
assert abs(values['weighted']-expected)<1e-14
assert abs(values['extreme']-expected)<1e-14
assert values['rejected']==4
paths=[exe,ROOT/'native/visual_calibration_math.h',ROOT/'native/visual_calibration_probe.cpp',Path(__file__)]
report=dict(passed=True,doi='10.1038/s41593-024-01640-4',
    max_capture_error=max(errors),weighted_alignment_error=abs(values['weighted']-expected),
    extreme_scale_error=abs(values['extreme']-expected), invalid_cases_rejected=4,
    semantics='Equation 9 weighted uncentered normalized dot product; not centered Pearson correlation',
    scope='Arithmetic verification only; no observation transformation identified or physiology fit',
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(ROOT/'reports/visual_calibration_math.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
