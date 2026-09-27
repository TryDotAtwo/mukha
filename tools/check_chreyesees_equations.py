"""Run only two inspected author functions, not package/database initialization."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
path = ROOT/'data/reference/chreyesees/chreyesees/paccman.py'
raw = path.read_bytes()
manifest = json.loads((ROOT/'reports/chreyesees_sources.json').read_text())
assert hashlib.sha256(raw).hexdigest() == manifest['files']['chreyesees/paccman.py']['sha256']
tree = ast.parse(raw)
selected = [n for n in tree.body if isinstance(n, ast.FunctionDef)
            and n.name in ('tanh_like', 'step_forward')]
assert len(selected) == 2
env = {'torch':torch}
exec(compile(ast.Module(body=selected, type_ignores=[]),str(path),'exec'),env)

# Author code uses r0 = -gamma relative to manuscript equation 5, and epsilon.
x = np.linspace(-12.,12.,257)
errors = []
paper_differences = []
for gamma in (-.8,0.,.8):
    scale = np.where(x <= 0,1+gamma,1-gamma)
    expected = scale*np.tanh(x/(scale+1e-6))
    actual = env['tanh_like'](torch.tensor(x),r0=-gamma).numpy()
    errors.append(float(np.max(np.abs(expected-actual))))
    paper_differences.append(float(np.max(np.abs(actual-scale*np.tanh(x/scale)))))
assert max(errors)<1e-14

rng = np.random.default_rng(741)
X,Y,Wi,Wr = [rng.normal(size=s) for s in [(17,5),(17,12),(5,12),(12,12)]]
gain = rng.uniform(.1,2,size=12)
offset = rng.uniform(-.5,.5,size=12)
actual = env['step_forward'](*map(torch.tensor,[X,Y,Wi,Wr,offset,gain]),torch.tanh).numpy()
expected = np.tanh(gain*(X@Wi+Y@Wr)-offset)+np.tanh(offset)
step_error = float(np.max(np.abs(actual-expected)))
assert step_error<1e-13
# Offset is outside gain in this source function. This must not be silently
# replaced with the manuscript's different parameterization.
zero = env['step_forward'](torch.zeros((1,5),dtype=torch.float64),
    torch.zeros((1,12),dtype=torch.float64),torch.tensor(Wi),torch.tensor(Wr),
    torch.tensor(offset),torch.tensor(gain),torch.tanh)
assert torch.equal(zero,torch.zeros_like(zero))
report = dict(source_sha256=hashlib.sha256(raw).hexdigest(),
    executed_functions=[n.name for n in selected], package_imported=False,
    tanh_max_abs_errors=errors, paper_equation5_epsilon_differences=paper_differences,
    gamma_mapping='r0 = -gamma; author denominator adds 1e-6',
    step_max_abs_error=step_error, zero_input_zero_state_exact=True,
    matrix_orientation='pre x post',
    scope='FP64 equation checks with synthetic inputs; not a fitted circuit replication',
    biological_validation_passed=False, malecns_transfer_enabled=False)
(ROOT/'reports/chreyesees_equation_checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
