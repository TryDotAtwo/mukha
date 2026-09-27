"""Checkpoint the full CNS, FlyMimic body and radial rocket in one live loop.

The sensory encoder and motor-muscle transfer are diagnostic hypotheses.
"""

import argparse
import ctypes as ct
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml
from probe_live_cns_flymimic import DLL as BRAIN_DLL, GRAPH, Parameters, graph_arrays, load_cuda
from probe_lf_four_proprio_body_loop import (
    DT_MS, MOTOR_DECAY_MS, MOTOR_GAIN, PAD_REPORT, PERTURBATION_DEG, SOURCE,
)


ROCKET_DLL = ROOT / "build/rocket_vertical_checkpoint_abi.dll"
OUT = ROOT / "data/derived/closed_cns_body_rocket_checkpoint_v1"
REPORT = ROOT / "reports/closed_cns_body_rocket_checkpoint.json"
RESUME_REPORT = ROOT / "reports/closed_cns_body_rocket_resume.json"
CONTROL_OUT = ROOT / "data/derived/closed_cns_body_rocket_feedback_off_v1"
CONTROL_REPORT = ROOT / "reports/closed_cns_body_rocket_feedback_control.json"
CAPTURE_OUT = ROOT / "data/derived/closed_cns_body_rocket_capture_v1"
CAPTURE_REPORT = ROOT / "reports/closed_cns_body_rocket_capture.json"
SPLIT = 500
END = 1000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rocket_library():
    lib = ct.CDLL(str(ROCKET_DLL))
    lib.rocket_new.restype = ct.c_void_p
    lib.rocket_new_from_snapshot.argtypes = [ct.POINTER(ct.c_double)]
    lib.rocket_new_from_snapshot.restype = ct.c_void_p
    lib.rocket_snapshot.argtypes = [ct.c_void_p, ct.POINTER(ct.c_double)]
    lib.rocket_snapshot.restype = ct.c_int
    lib.rocket_current_state.argtypes = [ct.c_void_p, ct.POINTER(ct.c_double)]
    lib.rocket_current_state.restype = ct.c_int
    lib.rocket_effective_g.argtypes = [ct.c_void_p]
    lib.rocket_effective_g.restype = ct.c_double
    lib.rocket_advance.argtypes = [ct.c_void_p, ct.c_double, ct.c_double,
                                   ct.POINTER(ct.c_double)]
    lib.rocket_advance.restype = ct.c_int
    lib.rocket_delete.argtypes = [ct.c_void_p]
    return lib


def main(resume_only=False, feedback_off=False, capture_only=False):
    assert sum((resume_only, feedback_off, capture_only)) <= 1
    if resume_only:
        assert OUT.exists() and REPORT.exists() and not RESUME_REPORT.exists()
    elif feedback_off:
        assert OUT.exists() and REPORT.exists() and not CONTROL_OUT.exists() and not CONTROL_REPORT.exists()
    elif capture_only:
        assert OUT.exists() and REPORT.exists() and not CAPTURE_OUT.exists() and not CAPTURE_REPORT.exists()
    else:
        assert not OUT.exists() and not REPORT.exists()
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert tuple(source["sensory_body_ids"]) == (817697, 821306, 908487, 912317)
    n, edges, _, row, col, weights = graph_arrays()
    sensor_idx = np.asarray(source["sensory_graph_indices"], dtype=np.intp)
    motor_idx = int(source["motor_graph_index"])
    original, _ = load_model()
    relaxed = mj.MjData(original)
    key = mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose")
    mj.mj_resetDataKeyframe(original, relaxed, key)
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(original, relaxed)
    assert not any(w.number for w in relaxed.warning)
    pad_report = json.loads(PAD_REPORT.read_text(encoding="utf-8"))
    pad = pad_report["geometry"]["keyframe_passive_2s"]["positive_x_pad_center_mm"]
    xml = modified_xml(pad, True, "+1 0 0")
    model, _ = load_model(xml)
    assert abs(model.opt.timestep - DT_MS / 1000) < 1e-12
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
    muscle = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
    foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    pad_geom = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
    joint_q = model.jnt_qposadr[joint]
    slide_q = model.jnt_qposadr[slide]
    reference_q = float(relaxed.qpos[joint_q])
    state_spec = mj.mjtState.mjSTATE_INTEGRATION
    brain_lib, directory = load_cuda()
    brain_lib.ff_cuda64_checkpoint_size.argtypes = [ct.c_void_p]
    brain_lib.ff_cuda64_checkpoint_size.restype = ct.c_size_t
    for name in ("ff_cuda64_save", "ff_cuda64_load"):
        getattr(brain_lib, name).argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]
    rocket_lib = rocket_library()
    sensory_mask = np.zeros(n, dtype=np.uint8)
    drive = np.zeros(n, dtype=np.float64)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)

    def make_brain():
        handle = brain_lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                            weights.ctypes.data, sensory_mask.ctypes.data,
                                            Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
        if not handle:
            raise RuntimeError(brain_lib.ff_cuda64_probe_error())
        return handle

    def run(brain, body, rocket, start, stop, activation, apply_rocket_feedback=True,
            frame_sink=None):
        trace = []
        events = []
        state = np.empty(5, dtype=np.float64)
        for tick in range(start, stop):
            assert abs(float(body.time) - tick * DT_MS / 1000) < 1e-9
            assert rocket_lib.rocket_current_state(
                rocket, state.ctypes.data_as(ct.POINTER(ct.c_double)))
            assert abs(state[0] - body.time) < 1e-9
            effective_g = (rocket_lib.rocket_effective_g(rocket)
                           if apply_rocket_feedback else 0.0)
            assert np.isfinite(effective_g)
            model.opt.gravity[2] = effective_g
            knee_start = float(body.qpos[joint_q])
            slide_start = float(body.qpos[slide_q])
            sensory_mv = source["sensor_gain_mv_per_rad_each"] * max(0.0, knee_start - reference_q)
            drive.fill(0)
            drive[sensor_idx] = sensory_mv
            if brain_lib.ff_cuda64_advance(brain, 1, drive.ctypes.data, voltage.ctypes.data,
                                           synapse.ctypes.data, spikes.ctypes.data):
                raise RuntimeError(brain_lib.ff_cuda64_probe_error())
            events.extend((tick, int(i)) for i in np.flatnonzero(spikes))
            activation *= np.exp(-DT_MS / MOTOR_DECAY_MS)
            activation += MOTOR_GAIN * int(spikes[motor_idx])
            control = min(1.0, max(.0001, activation))
            body.ctrl[:] = .0001
            body.ctrl[muscle] = control
            mj.mj_step(model, body)
            assert rocket_lib.rocket_advance(
                rocket, slide_start, DT_MS / 1000,
                state.ctypes.data_as(ct.POINTER(ct.c_double)))
            assert abs(body.time - state[0]) < 1e-9
            assert not any(w.number for w in body.warning)
            contacts = sum({c.geom1, c.geom2} == {foot, pad_geom} for c in body.contact)
            trace.append((float(body.qpos[joint_q]), float(body.qpos[slide_q]),
                          sensory_mv, float(voltage[motor_idx]), control,
                          float(contacts), float(spikes[motor_idx]),
                          float(spikes[sensor_idx].sum()), effective_g,
                          slide_start, *state.tolist()))
            if frame_sink is not None and (tick + 1) % 10 == 0:
                body_snapshot = np.empty(mj.mj_stateSize(model, state_spec), dtype=np.float64)
                rocket_snapshot = np.empty(6, dtype=np.float64)
                mj.mj_getState(model, body, body_snapshot, state_spec)
                assert rocket_lib.rocket_snapshot(
                    rocket, rocket_snapshot.ctypes.data_as(ct.POINTER(ct.c_double)))
                frame_sink.append((tick + 1, body_snapshot, rocket_snapshot))
        return (np.asarray(trace, dtype=np.float64),
                np.asarray(events, dtype=np.uint32).reshape(-1, 2), activation)

    try:
        if capture_only:
            prior = json.loads(REPORT.read_text(encoding="utf-8"))
            assert prior["graph_sha256"] == sha(GRAPH)
            assert prior["brain_dll_sha256"] == sha(BRAIN_DLL)
            assert prior["rocket_dll_sha256"] == sha(ROCKET_DLL)
            assert prior["body_model_xml_sha256"] == hashlib.sha256(xml.encode()).hexdigest()
            body = mj.MjData(model)
            body.qpos[:original.nq] = relaxed.qpos
            body.qvel[:original.nv] = relaxed.qvel
            body.act[:] = relaxed.act
            body.qpos[joint_q] += np.deg2rad(PERTURBATION_DEG)
            model.opt.gravity[2] = 0
            mj.mj_forward(model, body)
            brain = make_brain()
            rocket = rocket_lib.rocket_new()
            assert rocket
            frames = []
            try:
                capture, capture_events, _ = run(brain, body, rocket, 0, END, 0.0,
                                                 frame_sink=frames)
            finally:
                brain_lib.ff_cuda64_destroy(brain)
                rocket_lib.rocket_delete(rocket)
            with np.load(OUT / "trace.npz") as archived:
                assert np.array_equal(capture, archived["continuous"])
                assert np.array_equal(capture_events,
                                      np.vstack((archived["prefix_events"],
                                                 archived["tail_events"])))
            frame_ticks = np.asarray([f[0] for f in frames], dtype=np.uint32)
            body_states = np.stack([f[1] for f in frames])
            rocket_states = np.stack([f[2] for f in frames])
            assert np.array_equal(frame_ticks, np.arange(10, END + 1, 10))
            assert np.array_equal(rocket_states[:, 0], capture[frame_ticks - 1, 10])
            CAPTURE_OUT.mkdir(parents=True)
            np.savez_compressed(CAPTURE_OUT / "frames.npz", tick=frame_ticks,
                                body_state=body_states, rocket_state=rocket_states)
            capture_report = {"scope": "Replayed full-CNS/body/rocket state capture for synchronized diagnostic rendering",
                              "closed_report_sha256": sha(REPORT),
                              "closed_trace_sha256": prior["files"]["trace.npz"],
                              "frame_count": len(frames), "frame_step_ticks": 10,
                              "first_frame_tick": int(frame_ticks[0]),
                              "last_frame_tick": int(frame_ticks[-1]),
                              "frame_phase": "after MuJoCo and rocket integration at tick boundary; neural events for preceding interval",
                              "whole_1000_tick_trace_and_events_exact": True,
                              "frame_states_sha256": sha(CAPTURE_OUT / "frames.npz"),
                              "biological_validation": False}
            CAPTURE_REPORT.write_text(json.dumps(capture_report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"frames": len(frames),
                              "whole_trace_and_events_exact": True}, indent=2))
            return

        if feedback_off:
            prior = json.loads(REPORT.read_text(encoding="utf-8"))
            assert prior["graph_sha256"] == sha(GRAPH)
            assert prior["brain_dll_sha256"] == sha(BRAIN_DLL)
            assert prior["rocket_dll_sha256"] == sha(ROCKET_DLL)
            assert prior["body_model_xml_sha256"] == hashlib.sha256(xml.encode()).hexdigest()
            body = mj.MjData(model)
            body.qpos[:original.nq] = relaxed.qpos
            body.qvel[:original.nv] = relaxed.qvel
            body.act[:] = relaxed.act
            body.qpos[joint_q] += np.deg2rad(PERTURBATION_DEG)
            model.opt.gravity[2] = 0
            mj.mj_forward(model, body)
            brain = make_brain()
            rocket = rocket_lib.rocket_new()
            assert rocket
            try:
                control, control_events, _ = run(brain, body, rocket, 0, END, 0.0,
                                                 apply_rocket_feedback=False)
            finally:
                brain_lib.ff_cuda64_destroy(brain)
                rocket_lib.rocket_delete(rocket)
            with np.load(OUT / "trace.npz") as archived:
                connected = archived["continuous"]
                connected_events = np.vstack((archived["prefix_events"],
                                              archived["tail_events"]))
            assert control.shape == connected.shape == (END, 15)
            effective_tick = prior["first_nonzero_effective_gravity_tick"]
            assert effective_tick is not None
            assert np.array_equal(control[:effective_tick, :8],
                                  connected[:effective_tick, :8])
            assert np.all(control[:, 8] == 0)
            differences = {}
            for name, index in (("knee", 0), ("slide", 1), ("sensor_drive", 2),
                                ("motor_voltage", 3), ("rocket_velocity", 12)):
                delta = connected[:, index] - control[:, index]
                ix = np.flatnonzero(delta != 0)
                differences[name] = {"first_tick": int(ix[0]) if len(ix) else None,
                                     "max_abs": float(np.max(np.abs(delta)))}
            assert differences["knee"]["first_tick"] is not None
            assert differences["rocket_velocity"]["first_tick"] is not None
            original_events = set(map(tuple, connected_events.tolist()))
            other_events = set(map(tuple, control_events.tolist()))
            changed_events = original_events ^ other_events
            CONTROL_OUT.mkdir(parents=True)
            np.savez_compressed(CONTROL_OUT / "trace.npz", feedback_off=control,
                                feedback_off_events=control_events)
            result = {"scope": "Counterfactual rocket-to-body acceleration disconnect in the same live CNS/body/rocket diagnostic",
                      "closed_report_sha256": sha(REPORT),
                      "closed_trace_sha256": prior["files"]["trace.npz"],
                      "feedback_off_trace_sha256": sha(CONTROL_OUT / "trace.npz"),
                      "identical_neural_and_body_signals_before_feedback_tick": True,
                      "closed_first_nonzero_feedback_tick": effective_tick,
                      "differences": differences,
                      "first_event_difference_tick": min((int(t) for t, _ in changed_events), default=None),
                      "closed_event_count": len(connected_events),
                      "feedback_off_event_count": len(control_events),
                      "biological_validation": False,
                      "limits": ["Both branches retain unvalidated sensory and motor mappings",
                                 "One radial diagnostic plant, not KSP or landing"]}
            CONTROL_REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"differences": differences,
                              "first_event_difference_tick": result["first_event_difference_tick"]}, indent=2))
            return

        if resume_only:
            prior = json.loads(REPORT.read_text(encoding="utf-8"))
            assert prior["graph_sha256"] == sha(GRAPH)
            assert prior["brain_dll_sha256"] == sha(BRAIN_DLL)
            assert prior["rocket_dll_sha256"] == sha(ROCKET_DLL)
            assert prior["body_model_xml_sha256"] == hashlib.sha256(xml.encode()).hexdigest()
            assert prior["source_report_sha256"] == sha(SOURCE)
            assert prior["checkpoint_tick"] == SPLIT and prior["end_tick"] == END
            for name, expected in prior["files"].items():
                assert sha(OUT / name) == expected
            brain_state = np.load(OUT / "brain_state.npy")
            body_state = np.load(OUT / "body_state.npy")
            rocket_state = np.load(OUT / "rocket_state.npy")
            assert brain_state.dtype == np.uint8 and body_state.dtype == np.float64
            assert rocket_state.shape == (6,)
            rocket = rocket_lib.rocket_new_from_snapshot(
                rocket_state.ctypes.data_as(ct.POINTER(ct.c_double)))
            assert rocket
            body = mj.MjData(model)
            mj.mj_setState(model, body, body_state, state_spec)
            model.opt.gravity[2] = rocket_lib.rocket_effective_g(rocket)
            mj.mj_forward(model, body)
            check = np.empty_like(body_state)
            mj.mj_getState(model, body, check, state_spec)
            assert np.array_equal(body_state, check)
            brain = make_brain()
            try:
                if brain_lib.ff_cuda64_load(brain, brain_state.ctypes.data, len(brain_state)):
                    raise RuntimeError(brain_lib.ff_cuda64_probe_error())
                replay, replay_events, _ = run(brain, body, rocket, SPLIT, END,
                                               prior["motor_activation_at_checkpoint"])
            finally:
                brain_lib.ff_cuda64_destroy(brain)
                rocket_lib.rocket_delete(rocket)
            with np.load(OUT / "trace.npz") as saved:
                assert np.array_equal(replay, saved["continuous"][SPLIT:])
                assert np.array_equal(replay_events, saved["tail_events"])
            result = {"scope": "Cross-process full-CNS/FlyMimic/radial-rocket closed-loop checkpoint restore",
                      "checkpoint_report_sha256": sha(REPORT),
                      "brain_body_rocket_tail_exact": True,
                      "fresh_process": True, "biological_validation": False}
            RESUME_REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"cross_process_tail_exact": True}, indent=2))
            return

        body = mj.MjData(model)
        body.qpos[:original.nq] = relaxed.qpos
        body.qvel[:original.nv] = relaxed.qvel
        body.act[:] = relaxed.act
        body.qpos[joint_q] += np.deg2rad(PERTURBATION_DEG)
        model.opt.gravity[2] = 0
        mj.mj_forward(model, body)
        brain = make_brain()
        rocket = rocket_lib.rocket_new()
        assert rocket
        try:
            prefix, prefix_events, activation = run(brain, body, rocket, 0, SPLIT, 0.0)
            brain_state = np.empty(brain_lib.ff_cuda64_checkpoint_size(brain), dtype=np.uint8)
            if brain_lib.ff_cuda64_save(brain, brain_state.ctypes.data, len(brain_state)):
                raise RuntimeError(brain_lib.ff_cuda64_probe_error())
            body_state = np.empty(mj.mj_stateSize(model, state_spec), dtype=np.float64)
            mj.mj_getState(model, body, body_state, state_spec)
            rocket_state = np.empty(6, dtype=np.float64)
            assert rocket_lib.rocket_snapshot(
                rocket, rocket_state.ctypes.data_as(ct.POINTER(ct.c_double)))
            tail, tail_events, _ = run(brain, body, rocket, SPLIT, END, activation)
        finally:
            brain_lib.ff_cuda64_destroy(brain)
            rocket_lib.rocket_delete(rocket)
        restored_rocket = rocket_lib.rocket_new_from_snapshot(
            rocket_state.ctypes.data_as(ct.POINTER(ct.c_double)))
        assert restored_rocket
        restored_body = mj.MjData(model)
        mj.mj_setState(model, restored_body, body_state, state_spec)
        model.opt.gravity[2] = rocket_lib.rocket_effective_g(restored_rocket)
        mj.mj_forward(model, restored_body)
        check = np.empty_like(body_state)
        mj.mj_getState(model, restored_body, check, state_spec)
        assert np.array_equal(body_state, check)
        restored_brain = make_brain()
        try:
            if brain_lib.ff_cuda64_load(restored_brain, brain_state.ctypes.data,
                                        len(brain_state)):
                raise RuntimeError(brain_lib.ff_cuda64_probe_error())
            replay, replay_events, _ = run(restored_brain, restored_body,
                                           restored_rocket, SPLIT, END, activation)
        finally:
            brain_lib.ff_cuda64_destroy(restored_brain)
            rocket_lib.rocket_delete(restored_rocket)
        assert np.array_equal(tail_events, replay_events)
        assert np.array_equal(tail, replay)
        continuous = np.vstack((prefix, tail))
        first_throttle = np.flatnonzero(continuous[:, 9] > 0)
        first_effective = np.flatnonzero(continuous[:, 8] != 0)
        OUT.mkdir(parents=True)
        np.save(OUT / "brain_state.npy", brain_state)
        np.save(OUT / "body_state.npy", body_state)
        np.save(OUT / "rocket_state.npy", rocket_state)
        np.savez_compressed(OUT / "trace.npz", continuous=continuous,
                            prefix_events=prefix_events, tail_events=tail_events)
        report = {"scope": "Closed native MaleCNS/FlyMimic/radial-rocket diagnostic checkpoint",
                  "graph_sha256": sha(GRAPH), "brain_dll_sha256": sha(BRAIN_DLL),
                  "rocket_dll_sha256": sha(ROCKET_DLL),
                  "body_model_xml_sha256": hashlib.sha256(xml.encode()).hexdigest(),
                  "source_report_sha256": sha(SOURCE), "pad_report_sha256": sha(PAD_REPORT),
                  "checkpoint_tick": SPLIT, "end_tick": END, "dt_ms": DT_MS,
                  "brain_checkpoint_bytes": len(brain_state),
                  "body_integration_doubles": len(body_state),
                  "rocket_state_fields": ["time_s", "altitude_m", "velocity_mps", "fuel_kg", "thrust_n", "contact_flag"],
                  "motor_activation_at_checkpoint": activation,
                  "first_nonzero_slide_start_tick": int(first_throttle[0]) if len(first_throttle) else None,
                  "first_nonzero_effective_gravity_tick": int(first_effective[0]) if len(first_effective) else None,
                  "max_abs_effective_gravity_mm_s2": float(np.max(np.abs(continuous[:, 8]))),
                  "max_slide_mm": float(continuous[:, 1].max()),
                  "exact_contact_samples": int(continuous[:, 5].sum()),
                  "motor_spike_count": int(continuous[:, 6].sum()),
                  "neural_event_count": len(prefix_events) + len(tail_events),
                  "tail_events_and_all_15_traces_exact": True,
                  "files": {p.name: sha(p) for p in OUT.iterdir()},
                  "biological_validation": False,
                  "limits": ["Hypothetical common sensory encoder and individual motor-muscle link",
                             "Fixed thorax, nonrotating co-falling cabin and radial diagnostic rocket",
                             "No KSP, vision, learning, landing or video recorder"]}
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: report[k] for k in (
            "first_nonzero_slide_start_tick", "first_nonzero_effective_gravity_tick",
            "max_abs_effective_gravity_mm_s2", "max_slide_mm",
            "exact_contact_samples", "motor_spike_count",
            "tail_events_and_all_15_traces_exact")}, indent=2))
    finally:
        directory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-only", action="store_true")
    parser.add_argument("--feedback-off", action="store_true")
    parser.add_argument("--capture-only", action="store_true")
    args = parser.parse_args()
    main(args.resume_only, args.feedback_off, args.capture_only)
