"""Test whether named left-front flexor and extensor oppose at relaxed pose."""
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, MODEL_SHA, load_model, mj

OUT = ROOT / "data/derived/flymimic_knee_antagonists_v1"
REPORT = ROOT / "reports/flymimic_knee_antagonists_local.json"
MUSCLES = ("LFTibia_extensor_93932", "LFTibia_flex_93434")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def opening_angle(model, data, ids):
    femur, tibia, tarsus = (data.xpos[i] for i in ids)
    proximal = femur - tibia
    distal = tarsus - tibia
    cosine = np.dot(proximal, distal) / (np.linalg.norm(proximal) * np.linalg.norm(distal))
    return float(np.degrees(np.arccos(np.clip(cosine, -1, 1))))


def main():
    model, restored = load_model()
    relaxed = mj.MjData(model)
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(model, relaxed)
    assert not any(w.number for w in relaxed.warning)
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    qadr = model.jnt_qposadr[joint]
    q0 = float(relaxed.qpos[qadr])
    ids = [mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, name)
           for name in ("LFFemur", "LFTibia", "LFTarsus1")]
    muscles = [mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, name) for name in MUSCLES]
    assert min(joint, *ids, *muscles) >= 0
    samples = []
    geometry = mj.MjData(model)
    geometry.qpos[:] = relaxed.qpos
    geometry.qvel[:] = relaxed.qvel
    geometry.act[:] = relaxed.act
    for offset in (-.02, 0., .02):
        geometry.qpos[qadr] = q0 + offset
        mj.mj_forward(model, geometry)
        samples.append({"q_offset_rad": offset,
                        "opening_angle_deg": opening_angle(model, geometry, ids),
                        "tendon_lengths_mm": {name: float(geometry.actuator_length[a])
                                              for name, a in zip(MUSCLES, muscles)}})
    results = {}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, actuator in (("baseline", None), *zip(MUSCLES, muscles)):
        data = mj.MjData(model)
        data.qpos[:] = relaxed.qpos
        data.qvel[:] = relaxed.qvel
        data.act[:] = relaxed.act
        mj.mj_forward(model, data)
        qtrace = []
        for tick in range(1000):
            data.ctrl[:] = .0001
            if actuator is not None and 200 <= tick < 600:
                data.ctrl[actuator] = 1.
            mj.mj_step(model, data)
            assert not any(w.number for w in data.warning)
            assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
            qtrace.append(float(data.qpos[qadr]))
        results[name] = np.asarray(qtrace)
    comparisons = []
    for name in MUSCLES:
        difference = results[name] - results["baseline"]
        comparisons.append({"actuator": name,
                            "joint_difference_at_pulse_end_rad": float(difference[599]),
                            "joint_difference_at_run_end_rad": float(difference[-1]),
                            "maximum_positive_joint_difference_rad": float(difference.max()),
                            "minimum_joint_difference_rad": float(difference.min())})
    trace_path = OUT / "knee_traces.npz"
    np.savez_compressed(trace_path, **results)
    report = {"source_commit": restored["commit"], "source_xml_sha256": MODEL_SHA,
              "mujoco_version": mj.__version__, "relax_steps": 20000,
              "pulse_ticks": [200, 600], "pulse_activation": 1.,
              "joint_initial_q_rad": q0,
              "joint_coordinate_range_rad": model.jnt_range[joint].tolist(),
              "geometry_samples": samples, "muscle_trials": comparisons,
              "trace_sha256": sha(trace_path),
              "scope": "Local MuJoCo behavior of two named FlyMimic MTUs, not measured muscle physiology or MaleCNS mapping."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"geometry_samples": samples, "muscle_trials": comparisons}, indent=2))


if __name__ == "__main__":
    main()
