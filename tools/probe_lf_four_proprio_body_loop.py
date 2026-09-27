"""Perturbed knee -> four hypothetical proprioceptors -> full CNS -> body.

Exploratory circuit and mechanics sensitivity only. Sensory encoder and
individual motor-to-muscle map are unvalidated, and the initial perturbation
is an explicit experimental intervention.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda


SOURCE = ROOT / "reports/lf_four_direct_proprio_inputs.json"
PAD_REPORT = ROOT / "reports/flymimic_keyframe_contact_local.json"
OUT = ROOT / "data/derived/lf_four_proprio_body_loop_v2"
REPORT = ROOT / "reports/lf_four_proprio_body_loop_v2.json"
CASES = (("sensory_blocked", False, True),
         ("four_sensory_motor_connected", True, True),
         ("four_sensory_motor_disconnected", True, False))
TICKS = 5000
DT_MS = 0.1
PERTURBATION_DEG = 10.0
MOTOR_GAIN = 0.1
MOTOR_DECAY_MS = 20.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_diff(left, right):
    indices = np.flatnonzero(np.asarray(left) != np.asarray(right))
    return int(indices[0]) if len(indices) else None


def main():
    assert not OUT.exists() and not REPORT.exists()
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert tuple(source["sensory_body_ids"]) == (817697, 821306, 908487, 912317)
    assert source["sensor_gain_mv_per_rad_each"] == 200.0
    n, edges, _, row, col, weight = graph_arrays()
    body_ids = np.load(ROOT / "data/derived/malecns_v1_candidates/body_ids.npy", mmap_mode="r")
    sensor_idx = np.asarray(source["sensory_graph_indices"], dtype=np.intp)
    assert [int(body_ids[i]) for i in sensor_idx] == source["sensory_body_ids"]
    motor_idx = source["motor_graph_index"]
    assert int(body_ids[motor_idx]) == 815344
    original, _ = load_model()
    assert abs(original.opt.timestep - DT_MS / 1000.0) < 1e-12
    relaxed = mj.MjData(original)
    key = mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose")
    assert key >= 0
    mj.mj_resetDataKeyframe(original, relaxed, key)
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(original, relaxed)
    assert not any(w.number for w in relaxed.warning)
    pad_report = json.loads(PAD_REPORT.read_text(encoding="utf-8"))
    pad = pad_report["geometry"]["keyframe_passive_2s"]["positive_x_pad_center_mm"]
    modified_model_xml = modified_xml(pad, True, "+1 0 0")
    model, _ = load_model(modified_model_xml)
    assert abs(model.opt.timestep - DT_MS / 1000.0) < 1e-12
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
    muscle = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
    foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    pad_geom = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
    joint_q = model.jnt_qposadr[joint]
    slide_q = model.jnt_qposadr[slide]
    reference_q = float(relaxed.qpos[joint_q])
    perturbation = np.deg2rad(PERTURBATION_DEG)
    assert model.jnt_range[joint, 0] < reference_q + perturbation < model.jnt_range[joint, 1]
    lib, directory = load_cuda()
    sensory = np.zeros(n, dtype=np.uint8)
    drive = np.zeros(n, dtype=np.float64)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)
    runs = {}
    try:
        for label, sensor_on, motor_connected in CASES:
            body = mj.MjData(model)
            body.qpos[:original.nq] = relaxed.qpos
            body.qvel[:original.nv] = relaxed.qvel
            body.act[:] = relaxed.act
            body.qpos[joint_q] += perturbation
            mj.mj_forward(model, body)
            brain = lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                         weight.ctypes.data, sensory.ctypes.data,
                                         Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
            if not brain:
                raise RuntimeError(lib.ff_cuda64_probe_error())
            traces = {name: np.empty(TICKS, dtype=np.float64) for name in
                      ("knee_rad", "slide_mm", "sensor_drive_mv", "motor_voltage_mv",
                       "muscle_control", "exact_contacts")}
            traces["motor_spike"] = np.empty(TICKS, dtype=np.uint8)
            traces["sensor_spike_count"] = np.empty(TICKS, dtype=np.uint8)
            events = []
            activation = 0.0
            try:
                for tick in range(TICKS):
                    start_time = float(body.time)
                    assert abs(start_time - tick * DT_MS / 1000.0) < 1e-9
                    q_start = float(body.qpos[joint_q])
                    sensory_mv = (source["sensor_gain_mv_per_rad_each"] *
                                  max(0.0, q_start - reference_q) if sensor_on else 0.0)
                    drive.fill(0)
                    drive[sensor_idx] = sensory_mv
                    if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data,
                                             voltage.ctypes.data, synapse.ctypes.data,
                                             spikes.ctypes.data):
                        raise RuntimeError(lib.ff_cuda64_probe_error())
                    events.extend((tick, int(i)) for i in np.flatnonzero(spikes))
                    activation *= np.exp(-DT_MS / MOTOR_DECAY_MS)
                    activation += MOTOR_GAIN * int(spikes[motor_idx])
                    control = min(1.0, max(.0001, activation)) if motor_connected else .0001
                    body.ctrl[:] = .0001
                    body.ctrl[muscle] = control
                    mj.mj_step(model, body)
                    assert abs(float(body.time) - (tick + 1) * DT_MS / 1000.0) < 1e-9
                    if any(w.number for w in body.warning):
                        raise RuntimeError(f"MuJoCo warning at tick {tick}: " +
                                           str([w.number for w in body.warning]))
                    traces["knee_rad"][tick] = body.qpos[joint_q]
                    traces["slide_mm"][tick] = body.qpos[slide_q]
                    traces["sensor_drive_mv"][tick] = sensory_mv
                    traces["motor_voltage_mv"][tick] = voltage[motor_idx]
                    traces["muscle_control"][tick] = control
                    traces["exact_contacts"][tick] = sum(
                        {c.geom1, c.geom2} == {foot, pad_geom} for c in body.contact)
                    traces["motor_spike"][tick] = spikes[motor_idx]
                    traces["sensor_spike_count"][tick] = spikes[sensor_idx].sum()
            finally:
                lib.ff_cuda64_destroy(brain)
            runs[label] = (traces, np.asarray(events, dtype=np.uint32).reshape(-1, 2))
    finally:
        directory.close()
    OUT.mkdir(parents=True)
    flat = {label + "_" + name: series for label, (traces, _) in runs.items()
            for name, series in traces.items()}
    trace_path = OUT / "traces.npz"
    np.savez_compressed(trace_path, **flat)
    summaries = []
    for label, (traces, events) in runs.items():
        path = OUT / (label + "_events.npy")
        np.save(path, events)
        summaries.append({"case": label, "event_count": len(events),
                          "sensor_spike_count": int(traces["sensor_spike_count"].sum()),
                          "motor_spike_ticks": np.flatnonzero(traces["motor_spike"]).tolist(),
                          "exact_foot_pad_contact_ticks": int(np.count_nonzero(traces["exact_contacts"])),
                          "max_slide_mm": float(traces["slide_mm"].max()),
                          "final_slide_mm": float(traces["slide_mm"][-1]),
                          "final_knee_rad": float(traces["knee_rad"][-1]),
                          "event_sha256": sha(path)})
    blocked = runs[CASES[0][0]][0]
    connected = runs[CASES[1][0]][0]
    disconnected = runs[CASES[2][0]][0]
    first_motor = first_diff(connected["motor_spike"], blocked["motor_spike"])
    assert summaries[0]["motor_spike_ticks"] == []
    if first_motor is not None:
        assert np.array_equal(connected["motor_spike"][:first_motor + 1],
                              disconnected["motor_spike"][:first_motor + 1])
    executed_sources = (ROOT / "tools/probe_lf_four_proprio_body_loop.py",
                        ROOT / "tools/flymimic_public_model.py",
                        ROOT / "tools/probe_flymimic_passive_throttle.py",
                        ROOT / "tools/probe_live_cns_flymimic.py")
    report = {"scope": "500-ms initial knee perturbation, full native MaleCNS and FlyMimic; unvalidated four-cell angle encoding and motor-muscle map",
              "source_report_sha256": sha(SOURCE), "pad_report_sha256": sha(PAD_REPORT),
              "runtime_graph_sha256": sha(ROOT / "build/brain_body_graph.bin"),
              "runtime_dll_sha256": sha(ROOT / "build/fly_cuda64.dll"),
              "source_flymimic_xml_sha256": sha(ROOT / "data/reference/flymimic/flymimic/assets/models/best_combined_cvt3.xml"),
              "modified_model_xml_sha256": hashlib.sha256(modified_model_xml.encode("utf-8")).hexdigest(),
              "executed_source_sha256": {str(path.relative_to(ROOT)).replace('\\', '/'): sha(path)
                                         for path in executed_sources},
              "mujoco_version": mj.__version__,
              "numpy_version": np.__version__,
              "sensor_body_ids": source["sensory_body_ids"],
              "sensor_gain_mv_per_rad_each": source["sensor_gain_mv_per_rad_each"],
              "initial_knee_reference_rad": reference_q,
              "initial_perturbation_deg": PERTURBATION_DEG,
              "ticks": TICKS, "dt_ms": DT_MS,
              "trace_phase_contract": {
                  "step_interval": "tick t spans [t*dt,(t+1)*dt); MuJoCo dt is asserted equal to neural DT_MS",
                  "sensor_drive_mv": "computed from knee qpos at t*dt before neural and mechanical advances",
                  "motor_spike_and_voltage": "after one neural advance associated with the same step interval",
                  "muscle_control": "command applied to MuJoCo step t",
                  "exact_contacts": "mj_step leaves contact geometry from forward evaluation at step start t*dt",
                  "knee_rad_and_slide_mm": "qpos after integration at (t+1)*dt",
                  "difference_ticks": "first array-index differences only; contact and qpos fields have distinct sample phases and do not establish physiological latency"},
              "motor_gain_per_spike": MOTOR_GAIN, "motor_decay_ms": MOTOR_DECAY_MS,
              "central_direct_drive": False,
              "cases": summaries,
              "first_sensor_drive_difference_vs_blocked_tick": first_diff(connected["sensor_drive_mv"], blocked["sensor_drive_mv"]),
              "first_motor_spike_difference_vs_blocked_tick": first_motor,
              "first_muscle_control_difference_vs_blocked_tick": first_diff(connected["muscle_control"], blocked["muscle_control"]),
              "first_slide_difference_vs_motor_disconnected_tick": first_diff(connected["slide_mm"], disconnected["slide_mm"]),
              "first_exact_contact_difference_vs_motor_disconnected_tick": first_diff(connected["exact_contacts"], disconnected["exact_contacts"]),
              "trace_sha256": sha(trace_path),
              "biological_validation": False,
              "limitations": ["Three cells have unknown angle tuning and no individual MANC identity",
                              "The common sensory gain and synchrony are artificial hypotheses",
                              "Motor-to-muscle identity and spike-force gain are unvalidated",
                              "Initial joint offset is an external diagnostic perturbation",
                              "Contacts and qpos are saved at different MuJoCo phases; tick offsets are not physiological delays"]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": [{k: value for k, value in case.items()
                                 if k != "motor_spike_ticks"} | {"motor_spikes": len(case["motor_spike_ticks"])}
                                for case in summaries],
                      "first_motor_tick": first_motor,
                      "first_slide_difference_tick": report["first_slide_difference_vs_motor_disconnected_tick"],
                      "first_exact_contact_difference_tick": report["first_exact_contact_difference_vs_motor_disconnected_tick"]}, indent=2))


if __name__ == "__main__":
    main()
