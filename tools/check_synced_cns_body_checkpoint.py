"""Verify exact continuation of one full-CNS/FlyMimic feedback diagnostic.

The four-cell encoder and motor-muscle link are unvalidated hypotheses.
This checks synchronized checkpoint mechanics, not biological fidelity.
"""

import argparse
import ctypes as ct
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml
from probe_live_cns_flymimic import DLL, GRAPH, Parameters, graph_arrays, load_cuda
from probe_lf_four_proprio_body_loop import (
    DT_MS, MOTOR_DECAY_MS, MOTOR_GAIN, PAD_REPORT, PERTURBATION_DEG, SOURCE,
)


ARCHIVED = ROOT / "data/derived/lf_four_proprio_body_loop_v2/traces.npz"
ARCHIVED_REPORT = ROOT / "reports/lf_four_proprio_body_loop_v2.json"
OUT = ROOT / "data/derived/synced_cns_body_checkpoint_v1"
REPORT = ROOT / "reports/synced_cns_body_checkpoint.json"
RESUME_REPORT = ROOT / "reports/synced_cns_body_resume.json"
SPLIT = 250
END = 500
CASE = "four_sensory_motor_connected"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(resume_only=False):
    if resume_only:
        assert OUT.exists() and REPORT.exists() and not RESUME_REPORT.exists()
    else:
        assert not OUT.exists() and not REPORT.exists()
    reference = json.loads(ARCHIVED_REPORT.read_text(encoding="utf-8"))
    assert sha(ARCHIVED) == reference["trace_sha256"]
    assert sha(GRAPH) == reference["runtime_graph_sha256"]
    assert sha(DLL) == reference["runtime_dll_sha256"]
    assert sha(SOURCE) == reference["source_report_sha256"]
    assert sha(PAD_REPORT) == reference["pad_report_sha256"]
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    n, edge_count, _, row, col, weight = graph_arrays()
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
    pad = json.loads(PAD_REPORT.read_text(encoding="utf-8"))["geometry"]["keyframe_passive_2s"]["positive_x_pad_center_mm"]
    xml = modified_xml(pad, True, "+1 0 0")
    assert hashlib.sha256(xml.encode()).hexdigest() == reference["modified_model_xml_sha256"]
    model, _ = load_model(xml)
    assert abs(model.opt.timestep - DT_MS / 1000) < 1e-12
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
    muscle = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
    foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    pad_geom = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
    joint_q, slide_q = model.jnt_qposadr[joint], model.jnt_qposadr[slide]
    reference_q = float(relaxed.qpos[joint_q])
    assert reference_q == reference["initial_knee_reference_rad"]
    state_spec = mj.mjtState.mjSTATE_INTEGRATION
    state_size = mj.mj_stateSize(model, state_spec)
    body = mj.MjData(model)
    body.qpos[:original.nq] = relaxed.qpos
    body.qvel[:original.nv] = relaxed.qvel
    body.act[:] = relaxed.act
    body.qpos[joint_q] += np.deg2rad(PERTURBATION_DEG)
    mj.mj_forward(model, body)
    sensory = np.zeros(n, dtype=np.uint8)
    drive = np.zeros(n, dtype=np.float64)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)
    lib, directory = load_cuda()
    lib.ff_cuda64_checkpoint_size.argtypes = [ct.c_void_p]
    lib.ff_cuda64_checkpoint_size.restype = ct.c_size_t
    for name in ("ff_cuda64_save", "ff_cuda64_load"):
        getattr(lib, name).argtypes = [ct.c_void_p, ct.c_void_p, ct.c_size_t]

    def make_brain():
        handle = lib.ff_cuda64_create(n, edge_count, row.ctypes.data, col.ctypes.data,
                                      weight.ctypes.data, sensory.ctypes.data,
                                      Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
        if not handle:
            raise RuntimeError(lib.ff_cuda64_probe_error())
        return handle

    def run(handle, physical, start, stop, activation):
        trace = []
        events = []
        for tick in range(start, stop):
            assert abs(float(physical.time) - tick * DT_MS / 1000) < 1e-9
            sensory_mv = source["sensor_gain_mv_per_rad_each"] * max(
                0.0, float(physical.qpos[joint_q]) - reference_q)
            drive.fill(0)
            drive[sensor_idx] = sensory_mv
            if lib.ff_cuda64_advance(handle, 1, drive.ctypes.data, voltage.ctypes.data,
                                     synapse.ctypes.data, spikes.ctypes.data):
                raise RuntimeError(lib.ff_cuda64_probe_error())
            events.extend((tick, int(i)) for i in np.flatnonzero(spikes))
            activation *= np.exp(-DT_MS / MOTOR_DECAY_MS)
            activation += MOTOR_GAIN * int(spikes[motor_idx])
            control = min(1.0, max(.0001, activation))
            physical.ctrl[:] = .0001
            physical.ctrl[muscle] = control
            mj.mj_step(model, physical)
            assert not any(w.number for w in physical.warning)
            contacts = sum({c.geom1, c.geom2} == {foot, pad_geom} for c in physical.contact)
            trace.append((float(physical.qpos[joint_q]), float(physical.qpos[slide_q]),
                          sensory_mv, float(voltage[motor_idx]), control, float(contacts),
                          float(spikes[motor_idx]), float(spikes[sensor_idx].sum())))
        return (np.asarray(trace, dtype=np.float64),
                np.asarray(events, dtype=np.uint32).reshape(-1, 2), activation)

    if resume_only:
        prior = json.loads(REPORT.read_text(encoding="utf-8"))
        assert prior["graph_sha256"] == sha(GRAPH)
        assert prior["library_sha256"] == sha(DLL)
        assert prior["model_xml_sha256"] == hashlib.sha256(xml.encode()).hexdigest()
        assert prior["checkpoint_tick"] == SPLIT and prior["end_tick"] == END
        for name, expected in prior["files"].items():
            assert sha(OUT / name) == expected, name
        brain_state = np.load(OUT / "brain_checkpoint.npy")
        body_state = np.load(OUT / "body_checkpoint.npy")
        assert len(brain_state) == prior["brain_checkpoint_bytes"]
        assert len(body_state) == state_size
        resumed_body = mj.MjData(model)
        mj.mj_setState(model, resumed_body, body_state, state_spec)
        mj.mj_forward(model, resumed_body)
        restored_state = np.empty_like(body_state)
        mj.mj_getState(model, resumed_body, restored_state, state_spec)
        assert np.array_equal(body_state, restored_state)
        resumed_brain = make_brain()
        try:
            if lib.ff_cuda64_load(resumed_brain, brain_state.ctypes.data, len(brain_state)):
                raise RuntimeError(lib.ff_cuda64_probe_error())
            replay, replay_events, _ = run(
                resumed_brain, resumed_body, SPLIT, END,
                prior["motor_activation_at_checkpoint"])
        finally:
            lib.ff_cuda64_destroy(resumed_brain)
            directory.close()
        with np.load(OUT / "continuation.npz") as saved:
            assert np.array_equal(replay, saved["original"])
            assert np.array_equal(replay_events, saved["original_events"])
        resume_report = {"scope": "Cross-process synchronized MaleCNS and FlyMimic checkpoint restore",
                         "checkpoint_report_sha256": sha(REPORT),
                         "source_files_sha256": prior["files"],
                         "fresh_process": True, "fresh_brain_handle": True,
                         "fresh_body_data": True, "tail_events_exact": True,
                         "tail_all_eight_traces_exact": True,
                         "biological_validation": False,
                         "limits": prior["limits"]}
        RESUME_REPORT.write_text(json.dumps(resume_report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"cross_process_tail_exact": True,
                          "checkpoint_tick": SPLIT, "end_tick": END}, indent=2))
        return

    brain = make_brain()
    try:
        prefix, prefix_events, activation = run(brain, body, 0, SPLIT, 0.0)
        body_state = np.empty(state_size, dtype=np.float64)
        mj.mj_getState(model, body, body_state, state_spec)
        brain_state = np.empty(lib.ff_cuda64_checkpoint_size(brain), dtype=np.uint8)
        if lib.ff_cuda64_save(brain, brain_state.ctypes.data, len(brain_state)):
            raise RuntimeError(lib.ff_cuda64_probe_error())
        tail, tail_events, _ = run(brain, body, SPLIT, END, activation)
    finally:
        lib.ff_cuda64_destroy(brain)
    restored_body = mj.MjData(model)
    mj.mj_setState(model, restored_body, body_state, state_spec)
    mj.mj_forward(model, restored_body)
    check_state = np.empty_like(body_state)
    mj.mj_getState(model, restored_body, check_state, state_spec)
    assert np.array_equal(body_state, check_state)
    fresh = make_brain()
    try:
        if lib.ff_cuda64_load(fresh, brain_state.ctypes.data, len(brain_state)):
            raise RuntimeError(lib.ff_cuda64_probe_error())
        replay, replay_events, _ = run(fresh, restored_body, SPLIT, END, activation)
    finally:
        lib.ff_cuda64_destroy(fresh)
        directory.close()
    assert np.array_equal(tail_events, replay_events)
    assert np.array_equal(tail, replay)
    names = ("knee_rad", "slide_mm", "sensor_drive_mv", "motor_voltage_mv",
             "muscle_control", "exact_contacts", "motor_spike", "sensor_spike_count")
    complete = np.vstack((prefix, tail))
    with np.load(ARCHIVED) as archived:
        for i, name in enumerate(names):
            assert np.array_equal(complete[:, i], archived[CASE + "_" + name][:END]), name
    archived_events_path = ROOT / "data/derived/lf_four_proprio_body_loop_v2/four_sensory_motor_connected_events.npy"
    archived_events = np.load(archived_events_path)
    assert np.array_equal(np.vstack((prefix_events, tail_events)),
                          archived_events[archived_events[:, 0] < END])
    OUT.mkdir(parents=True)
    np.save(OUT / "brain_checkpoint.npy", brain_state)
    np.save(OUT / "body_checkpoint.npy", body_state)
    np.savez_compressed(OUT / "continuation.npz", original=tail, restored=replay,
                        original_events=tail_events, restored_events=replay_events)
    report = {"scope": "Same-model full-CNS plus FlyMimic feedback checkpoint continuity diagnostic",
              "source_trace_sha256": sha(ARCHIVED), "source_report_sha256": sha(ARCHIVED_REPORT),
              "graph_sha256": sha(GRAPH), "library_sha256": sha(DLL),
              "model_xml_sha256": hashlib.sha256(xml.encode()).hexdigest(),
              "checkpoint_tick": SPLIT, "end_tick": END, "dt_ms": DT_MS,
              "brain_checkpoint_bytes": len(brain_state),
              "body_integration_doubles": len(body_state),
              "motor_activation_at_checkpoint": activation,
              "fresh_brain_handle": True, "fresh_body_data": True,
              "body_state_restored_exact": True, "tail_events_exact": True,
              "tail_all_eight_traces_exact": True, "first_500_ticks_match_archived": True,
              "files": {p.name: sha(p) for p in OUT.iterdir()},
              "biological_validation": False,
              "limits": ["Same machine, DLL, model and graph; not a portable experiment checkpoint",
                         "Unvalidated four-cell sensory encoder and motor-muscle map",
                         "No optical scene, rocket, KSP, training state, or video recorder included"]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("checkpoint_tick", "end_tick",
                      "brain_checkpoint_bytes", "body_integration_doubles",
                      "tail_all_eight_traces_exact", "first_500_ticks_match_archived")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-only", action="store_true")
    args = parser.parse_args()
    main(resume_only=args.resume_only)
