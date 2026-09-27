"""Native rocket and MuJoCo cabin diagnostic in an initial-velocity frame."""
import ctypes as C
import argparse
import hashlib
import json
import xml.etree.ElementTree as E
from pathlib import Path
import numpy as np
from flymimic_public_model import ROOT, load_model, mj

DLL = ROOT / 'build/rocket_vertical_abi.dll'
OUT = ROOT / 'data/derived/native_cabin_loop_v1'
REPORT = ROOT / 'reports/native_cabin_loop_local.json'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def api():
    lib = C.CDLL(str(DLL))
    lib.rocket_new.restype = C.c_void_p
    lib.rocket_delete.argtypes = [C.c_void_p]
    lib.rocket_current_state.argtypes = [C.c_void_p, C.POINTER(C.c_double)]
    lib.rocket_current_state.restype = C.c_int
    lib.rocket_world_gravity.argtypes = [C.c_void_p]
    lib.rocket_world_gravity.restype = C.c_double
    lib.rocket_advance.argtypes = [C.c_void_p, C.c_double, C.c_double, C.POINTER(C.c_double)]
    lib.rocket_advance.restype = C.c_int
    return lib

def main(pad_shift_mm=0., motor_events=False):
    lib = api()
    harness = ROOT / 'data/derived/flymimic_harness_v1/harness.xml'
    source, _ = load_model(harness.read_text(encoding='utf-8'))
    rest = mj.MjData(source)
    mj.mj_resetDataKeyframe(source, rest, mj.mj_name2id(source, mj.mjtObj.mjOBJ_KEY, 'default-pose'))
    for _ in range(20000):
        rest.ctrl[:] = .0001
        mj.mj_step(source, rest)
    dt = float(source.opt.timestep)
    baseline = lib.rocket_new()
    s = (C.c_double * 5)()
    assert lib.rocket_current_state(baseline, s)
    z0, v0 = s[1], s[2]
    ballistic = np.empty(1001)
    ballistic[0] = z0
    for t in range(1000):
        assert lib.rocket_advance(baseline, 0., dt, s)
        ballistic[t+1] = s[1]
    lib.rocket_delete(baseline)
    suffix = f'native_cabin_events_gap_{round(pad_shift_mm*1000)}um' if motor_events else f'native_cabin_gap_{round(pad_shift_mm*1000)}um'
    output_dir = ROOT / 'data/derived' / (suffix + '_v1') if motor_events or pad_shift_mm else OUT
    report_path = ROOT / 'reports' / (suffix + '_local.json') if motor_events or pad_shift_mm else REPORT
    output_dir.mkdir(parents=True, exist_ok=True)
    event_path=ROOT/'data/derived/malecns_sign_diagnostic_float64_v2/unclear_excitatory_events.npy'
    motor_ticks=set()
    if motor_events:
        events=np.load(event_path)
        motor_ticks=set(map(int,events[events[:,1]==156979,0]))
        assert motor_ticks=={190,641}
    cases, traces = [], {}
    for contact in (False, True):
        original = ROOT / 'data/derived/flymimic_moving_cabin_v1' / f'contact_{int(contact)}.xml'
        tree = E.fromstring(original.read_text(encoding='utf-8'))
        tree.find("./worldbody/geom[@name='floor']").set('pos', '0 0 -2500000')
        pad_body = tree.find("./worldbody/body[@name='cabin_frame']/body[@name='throttle_slider']")
        position = np.fromstring(pad_body.get('pos'), sep=' ')
        position[0] += pad_shift_mm
        pad_body.set('pos', ' '.join(f'{v:.17g}' for v in position))
        xml = output_dir / original.name
        xml.write_text(E.tostring(tree, encoding='unicode'), encoding='utf-8')
        model, _ = load_model(xml.read_text(encoding='utf-8'))
        cabin = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, 'cabin_frame')
        mocap = int(model.body_mocapid[cabin])
        slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, 'throttle_slide')
        foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, 'LFTarsus5_geom')
        pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, 'throttle_pad')
        muscle = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, 'LFTibia_extensor_93932')
        floor = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, 'floor')
        for feedback in (False, True):
            for pulse in (False, True):
                body = mj.MjData(model)
                body.qpos[:source.nq] = rest.qpos
                body.qvel[:source.nv] = rest.qvel
                body.act[:] = rest.act
                body.mocap_pos[mocap] = [0., 0., 0.]
                body.mocap_quat[mocap] = [1., 0., 0., 0.]
                mj.mj_forward(model, body)
                rocket = lib.rocket_new()
                now = (C.c_double * 5)()
                values = {k: [] for k in ('slide', 'contacts', 'throttle', 'altitude', 'cabin_z', 'relative_root', 'muscle_control')}
                motor_level=0.
                try:
                    for tick in range(1000):
                        q = float(body.qpos[model.jnt_qposadr[slide]])
                        assert lib.rocket_advance(rocket, q, dt, now)
                        altitude = now[1] if feedback else ballistic[tick+1]
                        local_z = (altitude-z0-v0*now[0])*1000.
                        body.mocap_pos[mocap] = [0., 0., local_z]
                        model.opt.gravity[2] = lib.rocket_world_gravity(rocket)*1000.
                        body.ctrl[:] = .0001
                        if motor_events:
                            motor_level *= np.exp(-.1/20.)
                            motor_level += .1*int(tick in motor_ticks)
                            if pulse: body.ctrl[muscle] = min(1.,max(.0001,motor_level))
                        elif pulse and 200 <= tick < 600: body.ctrl[muscle] = 1.
                        mj.mj_step(model, body)
                        assert not any(w.number for w in body.warning)
                        assert np.isfinite(body.qpos).all() and np.isfinite(body.qvel).all()
                        assert abs(body.time-now[0]) < 1e-10
                        assert not any(floor in (c.geom1, c.geom2) for c in body.contact)
                        values['slide'].append(float(body.qpos[model.jnt_qposadr[slide]]))
                        values['contacts'].append(sum({c.geom1, c.geom2} == {foot, pad} for c in body.contact))
                        values['throttle'].append(float(np.clip(q/.3, 0., 1.)))
                        values['altitude'].append(now[1])
                        values['cabin_z'].append(local_z)
                        values['relative_root'].append((body.qpos[:3]-body.mocap_pos[mocap]).copy())
                        values['muscle_control'].append(float(body.ctrl[muscle]))
                finally:
                    lib.rocket_delete(rocket)
                name = f'feedback_{int(feedback)}_contact_{int(contact)}_pulse_{int(pulse)}'
                for key, value in values.items(): traces[name+'_'+key] = np.asarray(value)
                cases.append(dict(feedback=feedback, contact=contact, pulse=pulse,
                    contacts=int(sum(values['contacts'])), peak_slide_mm=float(max(values['slide'])),
                    peak_throttle=float(max(values['throttle'])), final_altitude_m=float(values['altitude'][-1]),
                    max_relative_root_mm=float(np.max(np.linalg.norm(np.asarray(values['relative_root'])-rest.qpos[:3], axis=1)))))
    trace_path=output_dir/'traces.npz'
    np.savez_compressed(trace_path, **traces)
    report = dict(initial_altitude_m=z0, initial_velocity_mps=v0,
        executed_source_sha256=sha(ROOT/'tools/native_cabin_loop.py'),
        ballistic_final_altitude_m=float(ballistic[-1]), pad_shift_mm=pad_shift_mm, cases=cases,
        motor_drive='recorded full-graph candidate 156979 events with 0.1 per spike and 20-ms decay' if motor_events else 'prescribed full-strength pulse ticks [200,600)',
        motor_event_source_sha256=sha(event_path) if motor_events else None,
        motor_event_ticks=sorted(motor_ticks) if motor_events else None,
        source_harness_xml_sha256=sha(harness), rocket_abi_sha256=sha(DLL),
        moving_cabin_report_sha256=sha(ROOT/'reports/flymimic_moving_cabin_local.json'),
        contact_xml_sha256={f'contact_{i}':sha(output_dir/f'contact_{i}.xml') for i in (0,1)},
        traces_sha256=sha(trace_path),
        frame='inertial frame moving at initial rocket velocity; cabin local z=(alt-z0-v0*t)*1000 mm',
        scope='Exploratory rocket/cabin/foot coupling with artificial muscle pulse; no neural controller, KSP or landing.')
    report_path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(cases, indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--pad-shift-mm',type=float,default=0.)
    parser.add_argument('--motor-events',action='store_true')
    args=parser.parse_args()
    if args.pad_shift_mm<0 or args.pad_shift_mm>.3: parser.error('pad shift must be in [0,0.3] mm')
    main(args.pad_shift_mm,args.motor_events)
