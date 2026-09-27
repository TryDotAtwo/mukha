"""Native four-condition contact intervention with content-bound evidence."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    export=ROOT/'reports/contact_export.json'
    for name,h in json.loads(export.read_text())['files'].items():
        if sha(ROOT/'data/derived/contact_diagnostic'/name)!=h:raise RuntimeError('Model changed')
    exe=ROOT/'build/contact_probe.exe'
    runtime=ROOT/'data/reference/mujoco_3.9.0/bin'
    env=dict(os.environ);env['PATH']=str(runtime)+os.pathsep+env['PATH']
    run=subprocess.run([str(exe),'data/derived/contact_diagnostic/body.xml','build/contact_trace.csv'],
                       cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
    trace=ROOT/'build/contact_trace.csv'
    checks={'finite':True,'clock':True,'no_contact_no_motion':True,'no_pulse_no_motion':True,
            'pre_pulse_no_motion':True}
    rows={};max_q=0;normal=0
    with trace.open(newline='') as stream:
        for r in csv.DictReader(stream):
            c,p,t=int(r['contact']),int(r['pulse']),int(r['tick'])
            pair=(c,p);rows[pair]=rows.get(pair,0)+1
            q=float(r['slider_q']);f=float(r['normal_force'])
            checks['finite'] &= all(math.isfinite(float(v)) for v in r.values())
            checks['clock'] &= t==rows[pair] and abs(float(r['time'])-t*0.0001)<1e-9
            if not c:checks['no_contact_no_motion'] &= q==0 and f==0 and int(r['contacts'])==0
            if not p:checks['no_pulse_no_motion'] &= q==0
            if t<=2000:checks['pre_pulse_no_motion'] &= q==0
            if c and p:max_q=max(max_q,abs(q));normal=max(normal,f)
    checks['all_conditions']=rows=={(0,0):10000,(0,1):10000,(1,0):10000,(1,1):10000}
    checks['contact_moves_slider']=max_q>1e-4 and normal>0
    report={'scope':'Diagnostic motor-to-paw-to-passive-slider only; no neural control',
        'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'checks':checks,
        'passed':run.returncode==0 and all(checks.values()),'trace_sha256':sha(trace),
        'export_sha256':sha(export),'executable_sha256':sha(exe),
        'runtime_sha256':sha(runtime/'mujoco.dll')}
    (ROOT/'reports/contact_native.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
