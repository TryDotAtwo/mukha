"""Experimental physical knee -> SNpp50 -> full MaleCNS -> FlyMimic loop."""
import argparse
import ctypes as ct
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda

SPEC = ROOT / "configs/lf_claw_closed_loop_probe.json"
OUT = ROOT / "data/derived/lf_claw_closed_loop_v1"
REPORT = ROOT / "reports/lf_claw_closed_loop_local.json"
CASE_SETTINGS = (("feedback_blocked", 0, True),
                 ("positive_position", 1, True),
                 ("negative_position", -1, True),
                 ("positive_motor_disconnected", 1, False))
KEYFRAME_CASE_SETTINGS = (("feedback_blocked", 0, True),
                          ("positive_position", 1, True),
                          ("negative_position", -1, True),
                          ("negative_motor_disconnected", -1, False))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_difference(a, b):
    indices = np.flatnonzero(a != b)
    return int(indices[0]) if len(indices) else None


def first_event_difference(a, b, ticks):
    for tick in range(ticks):
        left = a[a[:, 0] == tick, 1]
        right = b[b[:, 0] == tick, 1]
        if not np.array_equal(left, right):
            return tick, np.setdiff1d(right, left).astype(int).tolist(), \
                np.setdiff1d(left, right).astype(int).tolist()
    return None, [], []


def main(normal_sensor_refractory=False, keyframe_derived=False):
    spec_path = (ROOT / "configs/lf_claw_closed_loop_keyframe_probe.json" if keyframe_derived
                 else ROOT / "configs/lf_claw_closed_loop_refractory_probe.json"
                 if normal_sensor_refractory else SPEC)
    out_dir = (ROOT / "data/derived/lf_claw_closed_loop_keyframe_v1" if keyframe_derived
               else ROOT / "data/derived/lf_claw_closed_loop_refractory_v1"
               if normal_sensor_refractory else OUT)
    report_path = (ROOT / "reports/lf_claw_closed_loop_keyframe_local.json" if keyframe_derived
                   else ROOT / "reports/lf_claw_closed_loop_refractory_local.json"
                   if normal_sensor_refractory else REPORT)
    case_settings = KEYFRAME_CASE_SETTINGS if keyframe_derived else CASE_SETTINGS
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec["cases"] == [case[0] for case in case_settings]
    assert spec["ticks"] == 1000 and spec["dt_ms"] == .1
    if normal_sensor_refractory or keyframe_derived:
        assert spec["sensor_refractory_ticks"] == 22
    assert spec["sensor_graph_index"] == 164105 and spec["motor_graph_index"] == 156979
    n, edges, source, row, col, weight = graph_arrays()
    assert source == 46
    lib, directory = load_cuda()
    sensory = np.zeros(n, dtype=np.uint8)
    sensory[source] = 1
    sensory[spec["sensor_graph_index"]] = 0 if (normal_sensor_refractory or keyframe_derived) else 1
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
    assert not any(w.number for w in relaxed.warning)
    pad_path = (ROOT / "reports/flymimic_keyframe_contact_local.json" if keyframe_derived
                else ROOT / "reports/flymimic_passive_throttle_local.json")
    pad_report = json.loads(pad_path.read_text())
    pad_center = (pad_report["geometry"]["keyframe_passive_2s"]["positive_x_pad_center_mm"]
                  if keyframe_derived else pad_report["pad_center_mm"])
    body_model, _ = load_model(modified_xml(pad_center, True,
                                            "+1 0 0" if keyframe_derived else "-1 0 0"))
    joint = mj.mj_name2id(body_model, mj.mjtObj.mjOBJ_JOINT, spec["physical_joint"])
    slide = mj.mj_name2id(body_model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
    muscle = mj.mj_name2id(body_model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
    foot = mj.mj_name2id(body_model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    pad = mj.mj_name2id(body_model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
    cases = []
    try:
        for label, polarity, motor_connected in case_settings:
            brain = lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                         weight.ctypes.data, sensory.ctypes.data,
                                         Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
            if not brain:
                raise RuntimeError(lib.ff_cuda64_probe_error())
            try:
                body = mj.MjData(body_model)
                body.qpos[:original.nq] = relaxed.qpos
                body.qvel[:original.nv] = relaxed.qvel
                body.act[:] = relaxed.act
                mj.mj_forward(body_model, body)
                q_reference = float(body.qpos[body_model.jnt_qposadr[joint]])
                drive = np.zeros(n, dtype=np.float64)
                voltage = np.empty(n, dtype=np.float64)
                synapse = np.empty(n, dtype=np.float64)
                spikes = np.empty(n, dtype=np.uint8)
                values = {key: [] for key in ("knee_rad", "slide_mm", "sensor_drive_mv",
                                              "sensor_spike", "motor_spike", "muscle_control",
                                              "exact_contacts", "global_spike_count")}
                events = []
                activation = 0.
                for tick in range(spec["ticks"]):
                    q_start = float(body.qpos[body_model.jnt_qposadr[joint]])
                    sensor_drive = spec["sensor_drive_mv_per_rad"] * max(
                        0., polarity * (q_start - q_reference))
                    drive[source] = spec["source_voltage_jump_mv"] if tick % 100 == 0 else 0.
                    drive[spec["sensor_graph_index"]] = sensor_drive
                    if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data, voltage.ctypes.data,
                                             synapse.ctypes.data, spikes.ctypes.data):
                        raise RuntimeError(lib.ff_cuda64_probe_error())
                    assert np.isfinite(voltage).all() and np.isfinite(synapse).all()
                    fired = np.flatnonzero(spikes)
                    events.extend((tick, int(index)) for index in fired)
                    activation *= np.exp(-spec["dt_ms"] / spec["motor_decay_ms"])
                    activation += spec["motor_gain_per_spike"] * int(spikes[156979])
                    control = min(1., max(.0001, activation)) if motor_connected else .0001
                    body.ctrl[:] = .0001
                    body.ctrl[muscle] = control
                    mj.mj_step(body_model, body)
                    assert not any(w.number for w in body.warning)
                    assert np.isfinite(body.qpos).all() and np.isfinite(body.qvel).all()
                    values["knee_rad"].append(float(body.qpos[body_model.jnt_qposadr[joint]]))
                    values["slide_mm"].append(float(body.qpos[body_model.jnt_qposadr[slide]]))
                    values["sensor_drive_mv"].append(sensor_drive)
                    values["sensor_spike"].append(int(spikes[spec["sensor_graph_index"]]))
                    values["motor_spike"].append(int(spikes[spec["motor_graph_index"]]))
                    values["muscle_control"].append(control)
                    values["exact_contacts"].append(sum({item.geom1, item.geom2} == {foot, pad}
                                                        for item in body.contact))
                    values["global_spike_count"].append(len(fired))
                cases.append((label, values, np.asarray(events, dtype=np.uint32).reshape(-1, 2)))
            finally:
                lib.ff_cuda64_destroy(brain)
    finally:
        directory.close()
    out_dir.mkdir(parents=True, exist_ok=True)
    traces = {}
    summaries = []
    for label, values, events in cases:
        for key, value in values.items():
            traces[label + "_" + key] = np.asarray(value)
        event_path = out_dir / f"{label}_events.npy"
        np.save(event_path, events)
        sensor_ticks = np.flatnonzero(values["sensor_spike"])
        summaries.append({"case": label, "spikes": len(events),
                          "sensor_spikes": int(sum(values["sensor_spike"])),
                          "minimum_sensor_interspike_ticks": (int(np.diff(sensor_ticks).min())
                              if len(sensor_ticks) > 1 else None),
                          "motor_spike_ticks": np.flatnonzero(values["motor_spike"]).tolist(),
                          "exact_contacts": int(sum(values["exact_contacts"])),
                          "max_slide_mm": float(max(values["slide_mm"])),
                          "max_sensor_drive_mv": float(max(values["sensor_drive_mv"])),
                          "event_sha256": sha(event_path)})
    baseline_events = cases[0][2]
    pinned_events = np.load(ROOT / "data/derived/malecns_sign_diagnostic_float64_v2/unclear_excitatory_events.npy")
    assert np.array_equal(baseline_events, pinned_events)
    comparisons = []
    for label, values, events in cases[1:]:
        base = cases[0][1]
        event_equal = np.array_equal(baseline_events, events)
        first_event_tick, added, removed = first_event_difference(
            baseline_events, events, spec["ticks"])
        comparisons.append({"case": label, "all_events_identical_to_blocked": event_equal,
                            "first_exact_event_difference_tick": first_event_tick,
                            "first_added_neuron_indices": added,
                            "first_removed_neuron_indices": removed,
                            "first_sensor_drive_difference_tick": first_difference(
                                np.asarray(base["sensor_drive_mv"]),
                                np.asarray(values["sensor_drive_mv"])),
                            "first_global_spike_count_difference_tick": first_difference(
                                np.asarray(base["global_spike_count"]),
                                np.asarray(values["global_spike_count"])),
                            "first_motor_spike_difference_tick": first_difference(
                                np.asarray(base["motor_spike"]),
                                np.asarray(values["motor_spike"])),
                            "first_muscle_control_difference_tick": first_difference(
                                np.asarray(base["muscle_control"]),
                                np.asarray(values["muscle_control"])),
                            "first_slide_difference_tick": first_difference(
                                np.asarray(base["slide_mm"]),
                                np.asarray(values["slide_mm"]))})
    trace_path = out_dir / "traces.npz"
    np.savez_compressed(trace_path, **traces)
    if not keyframe_derived:
        assert comparisons[1]["all_events_identical_to_blocked"]
        assert comparisons[2]["all_events_identical_to_blocked"]
    assert summaries[3]["max_slide_mm"] == 0
    if normal_sensor_refractory or keyframe_derived:
        assert all(case["minimum_sensor_interspike_ticks"] is None or
                   case["minimum_sensor_interspike_ticks"] >= 22 for case in summaries)
    if not keyframe_derived:
        positive = comparisons[0]
        if positive["first_exact_event_difference_tick"] is not None:
            assert positive["first_sensor_drive_difference_tick"] <= positive["first_exact_event_difference_tick"]
        if positive["first_motor_spike_difference_tick"] is not None:
            assert positive["first_exact_event_difference_tick"] <= positive["first_motor_spike_difference_tick"]
        if positive["first_slide_difference_tick"] is not None:
            assert positive["first_motor_spike_difference_tick"] <= positive["first_slide_difference_tick"]
    report = {"spec_sha256": sha(spec_path), "graph_sha256": sha(ROOT / "build/brain_body_graph.bin"),
              "sensor_refractory_ticks": 22 if (normal_sensor_refractory or keyframe_derived) else 0,
              "initial_pose": "default-pose plus 20000 passive steps" if keyframe_derived
                              else "zero reset plus 20000 passive steps",
              "pad_report_sha256": sha(pad_path), "pad_center_mm": pad_center,
              "blocked_events_match_pinned_source": True,
              "source_model_xml_sha256": pad_report["source_xml_sha256"],
              "cases": summaries, "comparisons_to_blocked": comparisons,
              "trace_sha256": sha(trace_path),
              "scope": "Exploratory closed proprioceptive diagnostic on full native CNS and FlyMimic; one assumed SNpp50 knee-position encoder, unknown polarity/gain, hypothetical motor map, artificial central stimulus, no biological validation or KSP landing."}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": summaries, "comparisons_to_blocked": comparisons}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-sensor-refractory", action="store_true")
    parser.add_argument("--keyframe-derived", action="store_true")
    args = parser.parse_args()
    main(args.normal_sensor_refractory, args.keyframe_derived)
