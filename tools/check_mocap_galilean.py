"""Check a welded MuJoCo mocap cabin under a constant-velocity frame change."""
import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np

from flymimic_public_model import ROOT, load_model, mj

SOURCE = ROOT / 'data/derived/flymimic_moving_cabin_v1/contact_0.xml'
REPORT = ROOT / 'reports/mocap_galilean_check.json'
TRACE = ROOT / 'data/derived/mocap_galilean_check_v1/traces.npz'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def run(model, initial, mocap, velocity_mps, steps=100):
    data=mj.MjData(model)
    data.qpos[:len(initial.qpos)]=initial.qpos
    data.qvel[:len(initial.qvel)]=initial.qvel
    data.qvel[2]=velocity_mps*1000.
    data.act[:]=initial.act
    data.mocap_pos[mocap]=[0.,0.,0.]
    data.mocap_quat[mocap]=[1.,0.,0.,0.]
    mj.mj_forward(model,data)
    relative=np.empty((steps,3))
    joints=np.empty((steps,14))
    for tick in range(steps):
        z=velocity_mps*(tick+1)*model.opt.timestep*1000.
        data.mocap_pos[mocap]=[0.,0.,z]
        data.ctrl[:]=.0001
        mj.mj_step(model,data)
        assert not any(w.number for w in data.warning)
        relative[tick]=data.qpos[:3]-data.mocap_pos[mocap]
        joints[tick]=data.qpos[7:21]
    return relative,joints


def main():
    harness=ROOT/'data/derived/flymimic_harness_v1/harness.xml'
    source,_=load_model(harness.read_text(encoding='utf-8'))
    initial=mj.MjData(source)
    mj.mj_resetDataKeyframe(source,initial,mj.mj_name2id(source,mj.mjtObj.mjOBJ_KEY,'default-pose'))
    for _ in range(20000):
        initial.ctrl[:]=.0001
        mj.mj_step(source,initial)
    tree=ET.fromstring(SOURCE.read_text(encoding='utf-8'))
    tree.find("./worldbody/geom[@name='floor']").set('pos','0 0 -2500000')
    TRACE.parent.mkdir(parents=True,exist_ok=True)
    xml_path=TRACE.parent/'no_floor_nearby.xml'
    xml_path.write_text(ET.tostring(tree,encoding='unicode'),encoding='utf-8')
    model,_=load_model(xml_path.read_text(encoding='utf-8'))
    model.opt.gravity[:]=0
    cabin=mj.mj_name2id(model,mj.mjtObj.mjOBJ_BODY,'cabin_frame')
    mocap=int(model.body_mocapid[cabin])
    assert mocap>=0
    still,jstill=run(model,initial,mocap,0.)
    translated,jtranslated=run(model,initial,mocap,-20.)
    residual=translated-still
    joint_residual=jtranslated-jstill
    np.savez_compressed(TRACE,stationary_relative_mm=still,
                        translated_relative_mm=translated,
                        stationary_joint_rad=jstill,translated_joint_rad=jtranslated)
    report={'source_xml_sha256':sha(SOURCE),'modified_xml_sha256':sha(xml_path),'trace_sha256':sha(TRACE),
            'duration_ms':10.,'world_gravity_mm_s2':0.,
            'frame_velocity_mps':-20.,'initial_root_velocity_matched_to_frame':True,
            'final_relative_root_error_mm':residual[-1].tolist(),
            'peak_relative_root_error_mm':float(np.linalg.norm(residual,axis=1).max()),
            'peak_joint_coordinate_error_rad':float(np.abs(joint_residual).max()),
            'pass_under_1e-3_mm':bool(np.linalg.norm(residual,axis=1).max()<1e-3),
            'scope':'Numerical Galilean control for this mocap+weld interface; no rocket or biological motor input.'}
    REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
