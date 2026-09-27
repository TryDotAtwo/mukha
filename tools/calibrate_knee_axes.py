"""Static geometry calibration, explicitly not a simulated movement trajectory."""
import hashlib
import json
import math
import export_body
import mujoco as mj
import numpy as np

ROOT=export_body.ROOT
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    directory=ROOT/'data/derived/body_motor_diagnostic'
    manifest=ROOT/'reports/body_motor_export.json'
    for name,h in json.loads(manifest.read_text())['files'].items():
        if sha(directory/name)!=h:raise ValueError('Model changed')
    assets={p.name:p.read_bytes() for p in directory.glob('*.stl')}
    m=mj.MjModel.from_xml_string((directory/'body.xml').read_text(),assets=assets)
    d=mj.MjData(m)
    key=mj.mj_name2id(m,mj.mjtObj.mjOBJ_KEY,'neutral')
    if key<0:raise ValueError('Missing neutral keyframe')
    mj.mj_resetDataKeyframe(m,d,key);neutral=d.qpos.copy()
    results=[]
    for leg in ['lf','lm','lh','rf','rm','rh']:
        name=f'{leg}_trochanterfemur-{leg}_tibia-pitch'
        jid=mj.mj_name2id(m,mj.mjtObj.mjOBJ_JOINT,name)
        bids=[mj.mj_name2id(m,mj.mjtObj.mjOBJ_BODY,f'{leg}_{part}')
              for part in ['trochanterfemur','tibia','tarsus1']]
        if jid<0 or min(bids)<0:raise ValueError('Missing anatomical landmark')
        address=m.jnt_qposadr[jid]
        def angle(offset):
            d.qpos[:]=neutral;d.qpos[address]+=offset
            mj.mj_forward(m,d)
            proximal,knee,distal=d.xpos[bids]
            a,b=proximal-knee,distal-knee
            return math.acos(float(np.clip(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1)))
        # Several local poses and two step sizes guard against a numerical sign accident.
        derivatives=[]
        for offset in [-0.2,-0.1,0,0.1,0.2]:
            for epsilon in [1e-4,1e-5]:
                derivatives.append((angle(offset+epsilon)-angle(offset-epsilon))/(2*epsilon))
        sign=int(np.sign(derivatives[0]))
        if sign==0 or not all(math.isfinite(x) and x*sign>0.5 for x in derivatives):
            raise ValueError(f'Unstable local anatomical sign: {leg}')
        results.append({'leg':leg,'joint':name,'neutral_opening_angle_rad':angle(0),
            'opening_angle_derivatives':derivatives,'positive_q_opens_knee':sign>0,
            'local_flexion_q_sign':-sign,'local_extension_q_sign':sign,
            'scope':'Geometric angle convention near neutral; not muscle moment-arm or torque validation'})
    report={'model_export_sha256':sha(manifest),
        'angle_definition':'angle between knee-to-proximal trochanterfemur origin and knee-to-tarsus1 origin',
        'offsets_rad':[-0.2,-0.1,0,0.1,0.2],'epsilon_rad':[1e-4,1e-5],
        'results':results,'all_six_local_signs_stable':True,'motor_mapping_enabled':False}
    (ROOT/'reports/knee_axis_calibration.json').write_text(json.dumps(report,indent=2))
    print(json.dumps([{k:r[k] for k in ['leg','local_flexion_q_sign','local_extension_q_sign']} for r in results],indent=2))

if __name__=='__main__':main()
