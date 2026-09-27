"""Harnessed FlyMimic in a cabin-local frame with explicit effective gravity."""
import ctypes
import argparse
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from audit_flymimic_foot_geometry import world_vertices
from probe_flymimic_passive_throttle import modified_xml

OUT = ROOT / "data/derived/harness_effective_g_v2"
REPORT = ROOT / "reports/harness_effective_g_v2_local.json"
DLL = ROOT / "build/rocket_vertical_abi.dll"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_paths(gap_um, motor_events, event_sign, relaxation_gravity, pad_reference):
    assert 0 <= gap_um <= 300
    stem = f'harness_effective_g_gap_{gap_um}um'
    if motor_events:
        stem += '_events'
        if event_sign == 'inhibitory':
            stem += '_unclear_inhibitory'
    if relaxation_gravity == 'zero':
        stem += '_zero_g_relax'
    if pad_reference == 'relaxed':
        stem += '_relaxed_pad'
    default_case = (gap_um == 0 and not motor_events and
                    relaxation_gravity == 'earth' and pad_reference == 'earth')
    out = OUT if default_case else ROOT / 'data/derived' / f'{stem}_v2'
    report_path = REPORT if default_case else ROOT / 'reports' / f'{stem}_v2_local.json'
    return out, report_path


def main(pad_shift_mm=0., motor_events=False, event_sign='excitatory', relaxation_gravity='earth', pad_reference='earth'):
    gap_um = round(pad_shift_mm * 1000)
    assert 0 <= gap_um <= 300 and abs(pad_shift_mm * 1000 - gap_um) < 1e-9
    source_report = json.loads((ROOT / "reports/flymimic_harness_contact_local.json").read_text())
    harness = ROOT / "data/derived/flymimic_harness_v1/harness.xml"
    assert sha(harness) == source_report["source_harness_xml_sha256"]
    pad_position = source_report["pad_centers_mm"]["positive_x"]
    pad_position = list(pad_position)
    pad_position[0] += pad_shift_mm
    original, _ = load_model(harness.read_text(encoding="utf-8"))
    if relaxation_gravity == 'zero':
        original.opt.gravity[:] = 0.
    relaxed = mj.MjData(original)
    mj.mj_resetDataKeyframe(original, relaxed,
                            mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose"))
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(original, relaxed)
    assert not any(w.number for w in relaxed.warning)
    mj.mj_forward(original, relaxed)
    foot_original = mj.mj_name2id(original, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    knee_original = mj.mj_name2id(original, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    relaxed_foot_center = relaxed.geom_xpos[foot_original].copy()
    relaxed_knee_q = float(relaxed.qpos[original.jnt_qposadr[knee_original]])
    if pad_reference == 'relaxed':
        vertices = world_vertices(original, relaxed, foot_original)
        low, high = vertices.min(axis=0), vertices.max(axis=0)
        pad_position = [float(high[0] + .02 + pad_shift_mm),
                        float((low[1] + high[1]) / 2),
                        float((low[2] + high[2]) / 2)]
    lib = ctypes.CDLL(str(DLL))
    lib.rocket_new.restype = ctypes.c_void_p
    lib.rocket_delete.argtypes = [ctypes.c_void_p]
    lib.rocket_effective_g.argtypes = [ctypes.c_void_p]
    lib.rocket_effective_g.restype = ctypes.c_double
    lib.rocket_advance.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double,
                                    ctypes.POINTER(ctypes.c_double)]
    lib.rocket_advance.restype = ctypes.c_int
    out, report_path = artifact_paths(gap_um, motor_events, event_sign,
                                      relaxation_gravity, pad_reference)
    out.mkdir(parents=True, exist_ok=True)
    event_path = ROOT / 'data/derived/malecns_sign_diagnostic_float64_v2' / f'unclear_{event_sign}_events.npy'
    motor_ticks = set()
    if motor_events:
        events = np.load(event_path)
        motor_ticks = set(map(int, events[events[:, 1] == 156979, 0]))
        assert motor_ticks == ({190, 641} if event_sign == 'excitatory' else {190, 761})
    cases = []
    traces = {}
    for feedback in (False, True):
        for contact in (False, True):
            xml = modified_xml(pad_position, contact, "+1 0 0",
                               harness.read_text(encoding="utf-8"))
            model, _ = load_model(xml)
            slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
            foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
            pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
            actuator = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
            knee = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
            activation_address = int(model.actuator_actadr[actuator])
            assert int(model.actuator_actnum[actuator]) == 1 and activation_address >= 0
            for pulse in (False, True):
                data = mj.MjData(model)
                data.qpos[:original.nq] = relaxed.qpos
                data.qvel[:original.nv] = relaxed.qvel
                data.act[:] = relaxed.act
                model.opt.gravity[:] = 0
                mj.mj_forward(model, data)
                handle = lib.rocket_new()
                assert handle
                state = (ctypes.c_double * 5)()
                slide_trace, throttle_trace, velocity_trace, contact_trace, gravity_trace = [], [], [], [], []
                motor_trace = []
                activation_trace, force_trace, knee_trace = [], [], []
                step_start_trace, step_end_trace = [], []
                motor_level = 0.
                try:
                    for tick in range(1000):
                        step_start_s = float(data.time)
                        q = float(data.qpos[model.jnt_qposadr[slide]])
                        effective_g = lib.rocket_effective_g(handle) if feedback else 0.
                        model.opt.gravity[2] = effective_g
                        data.ctrl[:] = .0001
                        if motor_events:
                            motor_level *= np.exp(-.1 / 20.)
                            motor_level += .1 * int(tick in motor_ticks)
                            if pulse:
                                data.ctrl[actuator] = min(1., max(.0001, motor_level))
                        elif pulse and 200 <= tick < 600:
                            data.ctrl[actuator] = 1.
                        mj.mj_step(model, data)
                        assert lib.rocket_advance(handle, q, model.opt.timestep, state)
                        assert abs(data.time - state[0]) < 1e-10
                        assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                        assert not any(w.number for w in data.warning)
                        slide_trace.append(float(data.qpos[model.jnt_qposadr[slide]]))
                        throttle_trace.append(float(np.clip(q / .3, 0, 1)))
                        velocity_trace.append(state[2])
                        contact_trace.append(sum({c.geom1, c.geom2} == {foot, pad} for c in data.contact))
                        gravity_trace.append(effective_g)
                        motor_trace.append(float(data.ctrl[actuator]))
                        activation_trace.append(float(data.act[activation_address]))
                        force_trace.append(float(data.actuator_force[actuator]))
                        knee_trace.append(float(data.qpos[model.jnt_qposadr[knee]]))
                        step_start_trace.append(step_start_s)
                        step_end_trace.append(float(data.time))
                finally:
                    lib.rocket_delete(handle)
                label = f"feedback_{int(feedback)}_contact_{int(contact)}_pulse_{int(pulse)}"
                traces[label + "_slide_mm"] = np.asarray(slide_trace)
                traces[label + "_throttle"] = np.asarray(throttle_trace)
                traces[label + "_velocity_mps"] = np.asarray(velocity_trace)
                traces[label + "_contacts"] = np.asarray(contact_trace)
                traces[label + "_effective_g_mm_s2"] = np.asarray(gravity_trace)
                traces[label + "_motor_control"] = np.asarray(motor_trace)
                traces[label + "_motor_activation"] = np.asarray(activation_trace)
                traces[label + "_motor_force"] = np.asarray(force_trace)
                traces[label + "_knee_q_rad"] = np.asarray(knee_trace)
                traces[label + "_step_start_s"] = np.asarray(step_start_trace)
                traces[label + "_step_end_s"] = np.asarray(step_end_trace)
                cases.append({"feedback": feedback, "contact": contact, "pulse": pulse,
                              "exact_contact_samples": int(sum(contact_trace)),
                              "first_contact_tick": next((i for i,x in enumerate(contact_trace) if x), None),
                              "first_slide_tick": next((i for i,x in enumerate(slide_trace) if x), None),
                              "first_throttle_tick": next((i for i,x in enumerate(throttle_trace) if x), None),
                              "max_slide_mm": float(max(slide_trace)),
                              "max_throttle": float(max(throttle_trace)),
                              "max_abs_effective_g_mm_s2": float(max(abs(x) for x in gravity_trace))})
    trace_path = out / "traces.npz"
    open_loop = "feedback_0_contact_1_pulse_1"
    closed_loop = "feedback_1_contact_1_pulse_1"
    first_indices = np.flatnonzero(traces[open_loop + "_throttle"] > 0)
    first_throttle = int(first_indices[0]) if len(first_indices) else None
    prefeedback_equal = (all(np.array_equal(traces[open_loop + suffix][:first_throttle+1],
                                           traces[closed_loop + suffix][:first_throttle+1])
                             for suffix in ("_slide_mm", "_throttle", "_velocity_mps"))
                         if first_throttle is not None else None)
    slide_effect = float(np.max(np.abs(traces[closed_loop + "_slide_mm"] -
                                       traces[open_loop + "_slide_mm"])))
    velocity_effect = float(np.max(np.abs(traces[closed_loop + "_velocity_mps"] -
                                          traces[open_loop + "_velocity_mps"])))
    np.savez_compressed(trace_path, **traces)
    report = {"cases": cases, "source_harness_xml_sha256": sha(harness),
              "executed_source_sha256": sha(ROOT / "tools/probe_harness_effective_g.py"),
              "pad_center_mm": pad_position, "mujoco_version": mj.__version__,
              "relaxed_foot_center_mm": relaxed_foot_center.tolist(),
              "relaxed_knee_q_rad": relaxed_knee_q,
              "pad_shift_mm": pad_shift_mm,
              "pad_reference": pad_reference,
              "motor_drive": ("recorded full-graph candidate 156979 events with 0.1 per spike and 20-ms decay"
                              if motor_events else "prescribed full-strength pulse ticks [200,600)"),
              "motor_event_source_sha256": sha(event_path) if motor_events else None,
              "unclear_transmitter_sign_assumption": event_sign if motor_events else None,
              "motor_event_ticks": sorted(motor_ticks) if motor_events else None,
              "cabin_frame": "nonrotating co-falling local frame; effective gravity is -thrust/m",
              "trace_phase_contract": "index t: command, effective g, contacts and actuator_force describe step [t*dt,(t+1)*dt); qpos, activation and rocket state are at (t+1)*dt; throttle uses slider q at t*dt",
              "relaxation": ("zero gravity for 20000 steps before co-falling frame"
                             if relaxation_gravity == 'zero' else
                             "source gravity -9801 mm/s2 for 20000 steps, then co-falling frame at t=0"),
              "rocket_plant": "native/rocket_vertical.h via native/rocket_vertical_abi.cpp",
              "first_nonzero_throttle_tick": first_throttle,
              "identical_trajectories_through_first_nonzero_throttle": prefeedback_equal,
              "max_feedback_slide_difference_mm": slide_effect,
              "max_feedback_velocity_difference_mps": velocity_effect,
              "no_pulse_contact_caused_throttle": any(c["contact"] and not c["pulse"] and c["max_throttle"]>0 for c in cases),
              "trace_sha256": sha(trace_path), "abi_sha256": sha(DLL),
              "scope": "Exploratory replay through hypothetical motor-to-muscle gain; no validated MaleCNS motor mapping, realistic seated cabin or KSP landing."}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--pad-shift-mm',type=float,default=0.)
    parser.add_argument('--motor-events',action='store_true')
    parser.add_argument('--event-sign',choices=('excitatory','inhibitory'),default='excitatory')
    parser.add_argument('--relaxation-gravity',choices=('earth','zero'),default='earth')
    parser.add_argument('--pad-reference',choices=('earth','relaxed'),default='earth')
    args=parser.parse_args()
    if not 0 <= args.pad_shift_mm <= .3 or abs(args.pad_shift_mm*1000-round(args.pad_shift_mm*1000)) >= 1e-9:
        parser.error('pad shift must be in [0,0.3] mm at an integer micrometre')
    main(args.pad_shift_mm,args.motor_events,args.event_sign,args.relaxation_gravity,args.pad_reference)
