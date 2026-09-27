"""Live full MaleCNS, FlyMimic and radial rocket diagnostic loop."""
import argparse
import ctypes as ct
import hashlib
import json
import numpy as np

from audit_flymimic_foot_geometry import world_vertices
from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda, GRAPH, DLL as BRAIN_DLL

HARNESS = ROOT / "data/derived/flymimic_harness_v1/harness.xml"
ROCKET_DLL = ROOT / "build/rocket_vertical_abi.dll"
SPEC = ROOT / "configs/lf_claw_closed_loop_keyframe_probe.json"
OUT = ROOT / "data/derived/live_cabin_claw_v2"
REPORT = ROOT / "reports/live_cabin_claw_v2_local.json"
CASES = (("blocked", 0, True, True), ("negative", -1, True, True),
         ("motor_off", -1, False, True), ("contact_off", -1, True, False))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first(array):
    x = np.flatnonzero(array)
    return int(x[0]) if len(x) else None


def main(central_drive='periodic'):
    out = OUT if central_drive == 'periodic' else ROOT / 'data/derived/live_cabin_claw_no_central_v2'
    report_path = REPORT if central_drive == 'periodic' else ROOT / 'reports/live_cabin_claw_no_central_v2_local.json'
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["ticks"] == 1000 and spec["dt_ms"] == .1
    n, edges, source, row, col, weight = graph_arrays()
    assert source == 46
    brain_lib, directory = load_cuda()
    rocket = ct.CDLL(str(ROCKET_DLL))
    rocket.rocket_new.restype = ct.c_void_p
    rocket.rocket_delete.argtypes = [ct.c_void_p]
    rocket.rocket_effective_g.argtypes = [ct.c_void_p]
    rocket.rocket_effective_g.restype = ct.c_double
    rocket.rocket_advance.argtypes = [ct.c_void_p, ct.c_double, ct.c_double,
                                      ct.POINTER(ct.c_double)]
    rocket.rocket_advance.restype = ct.c_int
    original, _ = load_model(HARNESS.read_text(encoding="utf-8"))
    original.opt.gravity[:] = 0.
    relaxed = mj.MjData(original)
    key = mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose")
    mj.mj_resetDataKeyframe(original, relaxed, key)
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(original, relaxed)
    assert not any(w.number for w in relaxed.warning)
    mj.mj_forward(original, relaxed)
    foot0 = mj.mj_name2id(original, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    vertices = world_vertices(original, relaxed, foot0)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    pad_position = [float(high[0] + .12), float((low[1] + high[1]) / 2),
                    float((low[2] + high[2]) / 2)]
    sensory = np.zeros(n, dtype=np.uint8)
    sensory[source] = 1
    out.mkdir(parents=True, exist_ok=True)
    traces, summaries = {}, []
    try:
        for label, polarity, connected, contact in CASES:
            brain = brain_lib.ff_cuda64_create(n, edges, row.ctypes.data,
                col.ctypes.data, weight.ctypes.data, sensory.ctypes.data,
                Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
            if not brain:
                raise RuntimeError(brain_lib.ff_cuda64_probe_error())
            handle = rocket.rocket_new()
            assert handle
            try:
                xml = modified_xml(pad_position, contact, "+1 0 0",
                                   HARNESS.read_text(encoding="utf-8"))
                model, _ = load_model(xml)
                model.opt.gravity[:] = 0.
                body = mj.MjData(model)
                body.qpos[:original.nq] = relaxed.qpos
                body.qvel[:original.nv] = relaxed.qvel
                body.act[:] = relaxed.act
                mj.mj_forward(model, body)
                joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, spec["physical_joint"])
                slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
                muscle = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
                foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
                pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
                q_ref = float(body.qpos[model.jnt_qposadr[joint]])
                drive = np.zeros(n, dtype=np.float64)
                voltage = np.empty(n, dtype=np.float64)
                synapse = np.empty(n, dtype=np.float64)
                spikes = np.empty(n, dtype=np.uint8)
                state = (ct.c_double * 5)()
                fields = ("knee_rad", "sensor_mv", "sensor_spike", "motor_spike",
                          "muscle_control", "contacts", "slide_mm", "throttle",
                          "rocket_velocity_mps", "effective_g_mm_s2", "global_spike_count",
                          "step_start_s", "step_end_s")
                values = {name: [] for name in fields}
                events = []
                activation = 0.
                for tick in range(spec["ticks"]):
                    step_start_s = float(body.time)
                    q = float(body.qpos[model.jnt_qposadr[joint]])
                    sensor_mv = spec["sensor_drive_mv_per_rad"] * max(0., polarity * (q - q_ref))
                    drive[source] = (spec["source_voltage_jump_mv"]
                                     if central_drive == 'periodic' and tick % 100 == 0 else 0.)
                    drive[spec["sensor_graph_index"]] = sensor_mv
                    if brain_lib.ff_cuda64_advance(brain, 1, drive.ctypes.data,
                            voltage.ctypes.data, synapse.ctypes.data, spikes.ctypes.data):
                        raise RuntimeError(brain_lib.ff_cuda64_probe_error())
                    fired = np.flatnonzero(spikes)
                    events.extend((tick, int(i)) for i in fired)
                    activation *= np.exp(-.1 / spec["motor_decay_ms"])
                    activation += spec["motor_gain_per_spike"] * int(spikes[spec["motor_graph_index"]])
                    control = min(1., max(.0001, activation)) if connected else .0001
                    slider_q = float(body.qpos[model.jnt_qposadr[slide]])
                    effective_g = rocket.rocket_effective_g(handle)
                    model.opt.gravity[2] = effective_g
                    body.ctrl[:] = .0001
                    body.ctrl[muscle] = control
                    mj.mj_step(model, body)
                    assert rocket.rocket_advance(handle, slider_q, .0001, state)
                    assert abs(body.time - state[0]) < 1e-10
                    assert not any(w.number for w in body.warning)
                    assert np.isfinite(body.qpos).all() and np.isfinite(body.qvel).all()
                    values["knee_rad"].append(float(body.qpos[model.jnt_qposadr[joint]]))
                    values["sensor_mv"].append(sensor_mv)
                    values["sensor_spike"].append(int(spikes[spec["sensor_graph_index"]]))
                    values["motor_spike"].append(int(spikes[spec["motor_graph_index"]]))
                    values["muscle_control"].append(control)
                    values["contacts"].append(sum({c.geom1, c.geom2} == {foot, pad} for c in body.contact))
                    values["slide_mm"].append(float(body.qpos[model.jnt_qposadr[slide]]))
                    values["throttle"].append(float(np.clip(slider_q / .3, 0., 1.)))
                    values["rocket_velocity_mps"].append(float(state[2]))
                    values["effective_g_mm_s2"].append(effective_g)
                    values["global_spike_count"].append(len(fired))
                    values["step_start_s"].append(step_start_s)
                    values["step_end_s"].append(float(body.time))
                path = out / f"{label}_events.npy"
                np.save(path, np.asarray(events, dtype=np.uint32).reshape(-1, 2))
                traces.update({f"{label}_{name}": np.asarray(seq) for name, seq in values.items()})
                summaries.append({"case": label, "event_count": len(events),
                    "sensor_spikes": int(sum(values["sensor_spike"])),
                    "motor_spike_ticks": np.flatnonzero(values["motor_spike"]).tolist(),
                    "first_contact_tick": first(values["contacts"]),
                    "first_slide_tick": first(values["slide_mm"]),
                    "first_throttle_tick": first(values["throttle"]),
                    "max_slide_mm": float(max(values["slide_mm"])),
                    "max_sensor_drive_mv": float(max(values["sensor_mv"])),
                    "event_sha256": sha(path)})
            finally:
                rocket.rocket_delete(handle)
                brain_lib.ff_cuda64_destroy(brain)
    finally:
        directory.close()
    trace_path = out / "traces.npz"
    np.savez_compressed(trace_path, **traces)
    report = {"cases": summaries, "pad_center_mm": pad_position,
        "central_drive": central_drive,
        "trace_phase_contract": "index t: sensed q, CNS spikes, motor command, contacts, effective g and applied throttle describe step [t*dt,(t+1)*dt); qpos and rocket velocity are at (t+1)*dt",
        "relaxed_knee_q_rad": q_ref, "graph_sha256": sha(GRAPH),
        "brain_dll_sha256": sha(BRAIN_DLL), "rocket_dll_sha256": sha(ROCKET_DLL),
        "harness_sha256": sha(HARNESS), "spec_sha256": sha(SPEC),
        "trace_sha256": sha(trace_path),
        "executed_source_sha256": sha(ROOT / "tools/probe_live_cabin_claw.py"),
        "scope": "Live full-graph/body/radial-rocket diagnostic; artificial central jumps and unvalidated sensor/motor mapping, no KSP or landing."}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--central-drive', choices=('periodic', 'none'), default='periodic')
    args = parser.parse_args()
    main(args.central_drive)
