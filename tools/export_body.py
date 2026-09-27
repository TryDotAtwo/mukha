"""Compose pinned NeuroMechFly using author code; no simulation or animation."""
import hashlib
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'build/matplotlib-cache'))
sys.path[:0] = [str(ROOT / 'build/body-python'), str(ROOT / 'build/body-python-extra'),
                str(ROOT / 'build/body-render-python'),
                str(ROOT / 'data/reference/flygym_2.1.0/src')]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actuated', action='store_true')
    args = parser.parse_args()
    source_lock = ROOT / 'reports/body_reference_sources.json'
    lock = json.loads(source_lock.read_text())
    for entry in lock['flygym_files']:
        path = ROOT / entry['path'].replace('\\', '/')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise RuntimeError(f'Source hash mismatch: {path}')
    import mujoco as mj
    from flygym.anatomy import Skeleton, JointPreset, ActuatedDOFPreset
    from flygym.compose import NeuroMechFly, KinematicPosePreset

    if mj.__version__ != '3.9.0':
        raise RuntimeError('Expected pinned MuJoCo 3.9.0')
    fly = NeuroMechFly()
    assets = {}
    for mesh in fly.mjcf_root.meshes:
        path = Path(mesh.file)
        raw = path.read_bytes()
        if path.name in assets and assets[path.name] != raw:
            raise RuntimeError('Conflicting mesh basenames')
        assets[path.name] = raw
        mesh.file = path.name
    fly.mjcf_root.assets = assets
    fly.mjcf_root.meshdir = ''
    skeleton = Skeleton(axis_order=['yaw', 'pitch', 'roll'],
                        joint_preset=JointPreset.ALL_BIOLOGICAL)
    fly.add_joints(skeleton, KinematicPosePreset.NEUTRAL)
    if args.actuated:
        joints = skeleton.get_actuated_dofs_from_preset(ActuatedDOFPreset.LEGS_ACTIVE_ONLY)
        fly.add_actuators(joints, 'motor', forcerange=(-1.0, 1.0),
                          ctrllimited=True, ctrlrange=(-1.0, 1.0))
    # A static thorax is an explicit diagnostic support, not an animated body.
    # No controller, muscles or neural mapping are supplied by this export.
    tag = 'body_motor' if args.actuated else 'body'
    output = ROOT / f'data/derived/{tag}_diagnostic'
    output.mkdir(parents=True, exist_ok=True)
    xml = fly.mjcf_root.to_xml()
    for name, raw in assets.items():
        (output / name).write_bytes(raw)
    (output / 'body.xml').write_text(xml, encoding='utf-8')
    model = mj.MjModel.from_xml_string(xml, assets=assets)
    report = {
        'scope': 'Fixed thorax, author anatomy; diagnostic joint motors' if args.actuated else 'Author anatomy with passive joints and fixed thorax; no cockpit or neural controller',
        'mujoco_version': mj.__version__, 'nq': model.nq, 'nv': model.nv,
        'nbody': model.nbody, 'ngeom': model.ngeom, 'nu': model.nu,
        'timestep': model.opt.timestep,
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(output.iterdir()) if p.is_file()},
        'physics_executed': False,
        'source_lock_sha256': hashlib.sha256(source_lock.read_bytes()).hexdigest(),
    }
    (ROOT / f'reports/{tag}_export.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != 'files'}, indent=2))

if __name__ == '__main__':
    main()
