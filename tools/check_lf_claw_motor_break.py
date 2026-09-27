"""Post-result motor-break intervention with fixed positive-case sensory input."""
import argparse
import ctypes as ct
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda

SPEC = ROOT / "configs/lf_claw_closed_loop_probe.json"
TRACE = ROOT / "data/derived/lf_claw_closed_loop_v1/traces.npz"
EVENTS = ROOT / "data/derived/lf_claw_closed_loop_v1/positive_position_events.npy"
REPORT = ROOT / "reports/lf_claw_motor_break_replay.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(normal_sensor_refractory=False, keyframe_derived=False):
    spec_path = (ROOT / "configs/lf_claw_closed_loop_keyframe_probe.json" if keyframe_derived
                 else ROOT / "configs/lf_claw_closed_loop_refractory_probe.json"
                 if normal_sensor_refractory else SPEC)
    base = (ROOT / "data/derived/lf_claw_closed_loop_keyframe_v1" if keyframe_derived
            else ROOT / "data/derived/lf_claw_closed_loop_refractory_v1"
            if normal_sensor_refractory else TRACE.parent)
    polarity = "negative" if keyframe_derived else "positive"
    trace_path = base / "traces.npz"
    event_path = base / f"{polarity}_position_events.npy"
    source_report = (ROOT / "reports/lf_claw_closed_loop_keyframe_local.json" if keyframe_derived
                     else ROOT / "reports/lf_claw_closed_loop_refractory_local.json"
                     if normal_sensor_refractory else ROOT / "reports/lf_claw_closed_loop_local.json")
    report_path = (ROOT / "reports/lf_claw_motor_break_keyframe_replay.json" if keyframe_derived
                   else ROOT / "reports/lf_claw_motor_break_refractory_replay.json"
                   if normal_sensor_refractory else REPORT)
    spec = json.loads(spec_path.read_text())
    original_report = json.loads(source_report.read_text())
    assert original_report["trace_sha256"] == sha(trace_path)
    with np.load(trace_path) as arrays:
        fixed_sensor = arrays[f"{polarity}_position_sensor_drive_mv"].copy()
        original_motor_spikes = arrays[f"{polarity}_position_motor_spike"].copy()
    expected_events = np.load(event_path)
    n, edges, source, row, col, weight = graph_arrays()
    lib, directory = load_cuda()
    sense = np.zeros(n, dtype=np.uint8)
    sense[source] = 1
    sense[spec["sensor_graph_index"]] = 0 if (normal_sensor_refractory or keyframe_derived) else 1
    brain = lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                 weight.ctypes.data, sense.ctypes.data,
                                 Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
    if not brain:
        raise RuntimeError(lib.ff_cuda64_probe_error())
    try:
        pad_report = json.loads((ROOT / ("reports/flymimic_keyframe_contact_local.json"
                                         if keyframe_derived else "reports/flymimic_passive_throttle_local.json")).read_text())
        original, _ = load_model()
        relaxed = mj.MjData(original)
        if keyframe_derived:
            key = mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose")
            assert key >= 0
            mj.mj_resetDataKeyframe(original, relaxed, key)
        else:
            mj.mj_resetData(original, relaxed)
        for _ in range(20000):
            relaxed.ctrl[:] = .0001
            mj.mj_step(original, relaxed)
        pad_center = (pad_report["geometry"]["keyframe_passive_2s"]["positive_x_pad_center_mm"]
                      if keyframe_derived else pad_report["pad_center_mm"])
        physical, _ = load_model(modified_xml(pad_center, True,
                                               "+1 0 0" if keyframe_derived else "-1 0 0"))
        body = mj.MjData(physical)
        body.qpos[:original.nq] = relaxed.qpos
        body.qvel[:original.nv] = relaxed.qvel
        body.act[:] = relaxed.act
        mj.mj_forward(physical, body)
        slide = mj.mj_name2id(physical, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
        muscle = mj.mj_name2id(physical, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
        foot = mj.mj_name2id(physical, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
        pad = mj.mj_name2id(physical, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
        drive = np.zeros(n, dtype=np.float64)
        voltage = np.empty(n, dtype=np.float64)
        synapse = np.empty(n, dtype=np.float64)
        spikes = np.empty(n, dtype=np.uint8)
        events = []
        knee = []
        slide_trace = []
        contacts = []
        motor_spikes = []
        for tick in range(spec["ticks"]):
            drive[source] = spec["source_voltage_jump_mv"] if tick % 100 == 0 else 0.
            drive[spec["sensor_graph_index"]] = fixed_sensor[tick]
            if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data, voltage.ctypes.data,
                                     synapse.ctypes.data, spikes.ctypes.data):
                raise RuntimeError(lib.ff_cuda64_probe_error())
            fired = np.flatnonzero(spikes)
            events.extend((tick, int(index)) for index in fired)
            motor_spikes.append(int(spikes[spec["motor_graph_index"]]))
            body.ctrl[:] = .0001  # motor output disconnected from the one muscle
            mj.mj_step(physical, body)
            assert not any(w.number for w in body.warning)
            knee.append(float(body.qpos[physical.jnt_qposadr[
                mj.mj_name2id(physical, mj.mjtObj.mjOBJ_JOINT, spec["physical_joint"])]]))
            slide_trace.append(float(body.qpos[physical.jnt_qposadr[slide]]))
            contacts.append(sum({item.geom1, item.geom2} == {foot, pad} for item in body.contact))
        same_events = np.array_equal(np.asarray(events, dtype=np.uint32).reshape(-1, 2),
                                     expected_events)
        same_motor = np.array_equal(np.asarray(motor_spikes), original_motor_spikes)
        assert same_events and same_motor and max(slide_trace) == 0 and sum(contacts) == 0
        report = {"passed": True, "intervention": f"{polarity} sensory drive replayed exactly; muscle output disconnected",
                  "source_closed_loop_report_sha256": sha(source_report),
                  "sensor_refractory_ticks": 22 if (normal_sensor_refractory or keyframe_derived) else 0,
                  "initial_pose": "default-pose plus 20000 passive steps" if keyframe_derived
                                  else "zero reset plus 20000 passive steps",
                  "sensory_trace_sha256": sha(trace_path), "original_event_sha256": sha(event_path),
                  "full_neural_events_identical": same_events,
                  "motor_spikes_identical": same_motor,
                  "motor_spike_ticks": np.flatnonzero(motor_spikes).tolist(),
                  "exact_foot_pad_contacts": int(sum(contacts)),
                  "max_slide_mm": float(max(slide_trace)),
                  "max_abs_knee_change_rad": float(max(abs(np.asarray(knee) - knee[0]))),
                  "scope": "Post-result motor-path break under fixed sensory replay; no claim of natural transduction or a live feedback loop in this control."}
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: report[key] for key in ("passed", "full_neural_events_identical",
                                                   "exact_foot_pad_contacts", "max_slide_mm")}, indent=2))
    finally:
        lib.ff_cuda64_destroy(brain)
        directory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-sensor-refractory", action="store_true")
    parser.add_argument("--keyframe-derived", action="store_true")
    args = parser.parse_args()
    main(args.normal_sensor_refractory, args.keyframe_derived)
