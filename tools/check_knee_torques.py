"""Physical native torque diagnostic; never overwrites poses during a run."""
import ctypes as c
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    directory=os.add_dll_directory(str(ROOT/'data/reference/mujoco_3.9.0/bin'))
    lib=c.CDLL(str(ROOT/'build/fly_body.dll'));p=c.c_void_p;dp=c.POINTER(c.c_double)
    for name,args,ret in [('fb_create',[c.c_char_p],p),('fb_destroy',[p],None),
        ('fb_controls',[p],c.c_size_t),('fb_advance',[p,dp,c.c_size_t,c.c_uint32],c.c_int),
        ('fb_joint_position',[p,c.c_char_p,dp],c.c_int)]:
        f=getattr(lib,name);f.argtypes=args;f.restype=ret
    model=ROOT/'data/derived/contact_diagnostic/body.xml'
    tree=ET.parse(model);actuators=tree.findall('./actuator/general')
    axes=ROOT/'reports/knee_axis_calibration.json'
    results=[]
    for axis in json.loads(axes.read_text())['results']:
        joint=axis['joint'];motor=next(i for i,a in enumerate(actuators) if a.get('joint')==joint)
        measured={}
        for label,command in [('zero',0.),('positive',1.),('negative',-1.)]:
            body=lib.fb_create(b'data/derived/contact_diagnostic/body.xml')
            if not body:raise RuntimeError('Body load failed')
            try:
                u=(c.c_double*lib.fb_controls(body))();u[motor]=command
                if lib.fb_advance(body,u,len(u),100):raise RuntimeError('Native step failed')
                q=c.c_double()
                if lib.fb_joint_position(body,joint.encode(),c.byref(q)):raise RuntimeError('Joint read failed')
                measured[label]=q.value
            finally:lib.fb_destroy(body)
        plus=measured['positive']-measured['zero'];minus=measured['negative']-measured['zero']
        results.append({'joint':joint,'positions_rad':measured,'positive_delta_rad':plus,
                        'negative_delta_rad':minus,'passed':plus>1e-6 and minus< -1e-6})
    report={'scope':'Native 10 ms diagnostic torques at neutral; no neural input or muscle calibration',
        'model_sha256':sha(model),'library_sha256':sha(ROOT/'build/fly_body.dll'),
        'axis_calibration_sha256':sha(axes),'results':results,
        'passed':all(r['passed'] for r in results)}
    (ROOT/'reports/knee_torque_checks.json').write_text(json.dumps(report,indent=2))
    directory.close();print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
