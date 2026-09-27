"""Run the same-model checkpoint diagnostic and retain its exact build evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
exe=ROOT/'build/mechanics_checkpoint_probe.exe'
model=ROOT/'data/derived/contact_diagnostic/body.xml'
dll=ROOT/'data/reference/mujoco_3.9.0/bin/mujoco.dll'
env=os.environ.copy();env['PATH']=str(dll.parent)+os.pathsep+env.get('PATH','')
run=subprocess.run([str(exe),str(model)],env=env,capture_output=True,text=True,check=True)
result=json.loads(run.stdout)
assert result['exact'] and result['checkpoint_tick']==3000 and result['compared_ticks']==7000
assert result['body_state_values']==971 and result['max_body_error']==0
paths=[exe,model,dll,ROOT/'native/mechanics_checkpoint_probe.cpp',ROOT/'native/rocket_vertical.h',Path(__file__)]
result.update(scope='Same-process, same-model in-memory closed-mechanics continuation only',
    state='MuJoCo mjSTATE_INTEGRATION plus rocket State; scheduler tick retained by fixture',
    limitations=['Not a portable checkpoint file','No different-build or process restart test',
                 'No brain, sensors, RNG or recorder state in this checkpoint',
                 '0.1-ms fixture tests replay, not mechanical integration convergence'],
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(ROOT/'reports/mechanics_checkpoint.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='hashes'},indent=2))
