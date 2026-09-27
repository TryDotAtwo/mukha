"""Engineering contact bench; anatomical meshes unchanged, no neural controller."""
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import export_body
import mujoco as mj
import numpy as np

ROOT = export_body.ROOT
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source = ROOT/'data/derived/body_motor_diagnostic'
    report = json.loads((ROOT/'reports/body_motor_export.json').read_text())
    for name,h in report['files'].items():
        if sha(source/name)!=h: raise RuntimeError('Model hash mismatch')
    assets={p.name:p.read_bytes() for p in source.glob('*.stl')}
    xml=(source/'body.xml').read_text()
    m=mj.MjModel.from_xml_string(xml,assets=assets)
    d=mj.MjData(m)
    mj.mj_resetDataKeyframe(m,d,mj.mj_name2id(m,mj.mjtObj.mjOBJ_KEY,'neutral'))
    mj.mj_forward(m,d)
    gid=mj.mj_name2id(m,mj.mjtObj.mjOBJ_GEOM,'lf_tarsus5')
    mid=m.geom_dataid[gid]
    vertices=m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid]+m.mesh_vertnum[mid]]
    world=vertices@d.geom_xmat[gid].reshape(3,3).T+d.geom_xpos[gid]
    # A small passive slider represents one control, not the final joystick.
    center=d.geom_xpos[gid].copy()
    center[1]=float(world[:,1].max())+0.01+0.01
    tree=ET.fromstring(xml)
    body=ET.SubElement(tree.find('worldbody'),'body',name='control_slider',pos=' '.join(map(str,center)))
    ET.SubElement(body,'joint',name='control_slide',type='slide',axis='0 1 0',
                  limited='true',range='-0.05 0.3',stiffness='0.5',damping='0.002')
    ET.SubElement(body,'geom',name='control_pad',type='box',size='0.15 0.01 0.15',
                  mass='0.001',contype='0',conaffinity='0',rgba='0.2 0.6 0.8 1')
    contact=tree.find('contact')
    if contact is None: contact=ET.SubElement(tree,'contact')
    ET.SubElement(contact,'pair',geom1='lf_tarsus5',geom2='control_pad',condim='3',
                  friction='0.5 0.5 0.005 0.0001 0.0001')
    for key in tree.findall('./keyframe/key'):
        key.set('qpos',key.get('qpos','')+' 0')
        if 'qvel' in key.attrib: key.set('qvel',key.get('qvel')+' 0')
    output=ROOT/'data/derived/contact_diagnostic'
    output.mkdir(parents=True,exist_ok=True)
    for name,raw in assets.items(): (output/name).write_bytes(raw)
    result=ET.tostring(tree,encoding='unicode')
    mj.MjModel.from_xml_string(result,assets=assets)
    (output/'body.xml').write_text(result)
    result_report={'scope':'Engineering passive slider contact bench, fixed thorax, no neural input',
        'base_export_sha256':sha(ROOT/'reports/body_motor_export.json'),
        'initial_gap_mm':0.01,'slider_center_mm':center.tolist(),
        'mass_model_units':0.001,'stiffness_model_units':0.5,'damping_model_units':0.002,
        'files':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    (ROOT/'reports/contact_export.json').write_text(json.dumps(result_report,indent=2))
    print(json.dumps({k:v for k,v in result_report.items() if k!='files'},indent=2))

if __name__=='__main__': main()
