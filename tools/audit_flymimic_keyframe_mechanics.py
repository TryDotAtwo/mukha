"""Compare knee antagonist pulses from the published keyframe and its passive settle."""
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, MODEL_SHA, load_model, mj

OUT = ROOT / "data/derived/flymimic_keyframe_mechanics_v1"
REPORT = ROOT / "reports/flymimic_keyframe_mechanics_local.json"
MUSCLES = ("LFTibia_extensor_93932", "LFTibia_flex_93434")


def angle(data, ids):
    femur, tibia, tarsus = (data.xpos[i] for i in ids)
    a, b = femur - tibia, tarsus - tibia
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))))


def clone(model, source):
    data = mj.MjData(model)
    data.qpos[:] = source.qpos
    data.qvel[:] = source.qvel
    data.act[:] = source.act
    mj.mj_forward(model, data)
    return data


def trial(model, source, qadr, actuator):
    data = clone(model, source)
    trace = np.empty(1000)
    for tick in range(1000):
        data.ctrl[:] = .0001
        if actuator is not None and 200 <= tick < 600:
            data.ctrl[actuator] = 1.
        mj.mj_step(model, data)
        assert not any(w.number for w in data.warning)
        assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
        trace[tick] = data.qpos[qadr]
    return trace


def main():
    model, restored = load_model()
    key = mj.mj_name2id(model, mj.mjtObj.mjOBJ_KEY, "default-pose")
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    ids = [mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, name)
           for name in ("LFFemur", "LFTibia", "LFTarsus1")]
    muscles = [mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, name) for name in MUSCLES]
    assert min(key, joint, *ids, *muscles) >= 0
    qadr = model.jnt_qposadr[joint]
    initial = mj.MjData(model)
    mj.mj_resetDataKeyframe(model, initial, key)
    mj.mj_forward(model, initial)
    relaxed = clone(model, initial)
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(model, relaxed)
    assert not any(w.number for w in relaxed.warning)
    OUT.mkdir(parents=True, exist_ok=True)
    conditions = {}
    traces = {}
    for label, source in (("author_keyframe", initial), ("keyframe_passive_2s", relaxed)):
        q0 = float(source.qpos[qadr])
        samples = []
        for offset in (-.02, 0., .02):
            geometry = clone(model, source)
            geometry.qpos[qadr] = q0 + offset
            mj.mj_forward(model, geometry)
            samples.append({"q_offset_rad": offset, "opening_angle_deg": angle(geometry, ids),
                            "actuator_lengths_mm": {name: float(geometry.actuator_length[actuator])
                                                     for name, actuator in zip(MUSCLES, muscles)}})
        baseline = trial(model, source, qadr, None)
        traces[label + "_baseline"] = baseline
        comparisons = []
        for name, actuator in zip(MUSCLES, muscles):
            result = trial(model, source, qadr, actuator)
            traces[label + "_" + name] = result
            diff = result - baseline
            comparisons.append({"actuator": name, "joint_difference_at_pulse_end_rad": float(diff[599]),
                                "joint_difference_at_run_end_rad": float(diff[-1]),
                                "min_difference_rad": float(diff.min()), "max_difference_rad": float(diff.max())})
        conditions[label] = {"initial_knee_q_rad": q0, "geometry_samples": samples,
                             "pulse_comparisons": comparisons}
    path = OUT / "knee_traces.npz"
    np.savez_compressed(path, **traces)
    report = {"source_commit": restored["commit"], "source_xml_sha256": MODEL_SHA,
              "mujoco_version": mj.__version__, "author_keyframe": "default-pose",
              "passive_settle_steps": 20000, "baseline_activation": .0001,
              "pulse_ticks": [200, 600], "pulse_activation": 1.,
              "joint_coordinate_range_rad": model.jnt_range[joint].tolist(),
              "conditions": conditions,
              "trace_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "scope": "Local source-model mechanics from the XML keyframe. Passive 2s settle and isolated full-strength MTU pulses are diagnostic, not an author gait or biological validation."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(conditions, indent=2))


if __name__ == "__main__":
    main()
