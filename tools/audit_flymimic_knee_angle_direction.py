"""Determine the geometric flexion direction of FlyMimic left tibia q."""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, MODEL, load_model, mj


REPORT = ROOT / "reports/flymimic_lf_knee_angle_direction.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interior_angle(model, data, proximal, knee, distal):
    mj.mj_forward(model, data)
    to_proximal = data.xpos[proximal] - data.xpos[knee]
    to_distal = data.xpos[distal] - data.xpos[knee]
    cosine = np.dot(to_proximal, to_distal) / (
        np.linalg.norm(to_proximal) * np.linalg.norm(to_distal))
    return float(np.rad2deg(np.arccos(np.clip(cosine, -1.0, 1.0))))


def main():
    assert not REPORT.exists()
    model, _ = load_model()
    data = mj.MjData(model)
    key = mj.mj_name2id(model, mj.mjtObj.mjOBJ_KEY, "default-pose")
    assert key >= 0
    mj.mj_resetDataKeyframe(model, data, key)
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    proximal = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "LFTrochanter")
    knee = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "LFTibia")
    distal = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "LFTarsus1")
    assert min(joint, proximal, knee, distal) >= 0
    q_index = int(model.jnt_qposadr[joint])
    q_values = np.linspace(*model.jnt_range[joint], 201)
    angles = []
    for q in q_values:
        data.qpos[q_index] = q
        angles.append(interior_angle(model, data, proximal, knee, distal))
    angles = np.asarray(angles)
    assert np.all(np.diff(angles) < 0.0)
    report = {"source_xml_sha256": sha(MODEL),
              "joint": "joint_LFTibia_pitch",
              "joint_q_range_rad": model.jnt_range[joint].tolist(),
              "body_origins": {"proximal": "LFTrochanter", "knee": "LFTibia", "distal": "LFTarsus1"},
              "geometric_measure": "3D interior angle at tibia body origin between proximal trochanter origin and distal tarsus1 origin, with all other joints at source default-pose keyframe",
              "sampled_q_count": len(q_values),
              "interior_angle_deg_at_q_min": float(angles[0]),
              "interior_angle_deg_at_q_max": float(angles[-1]),
              "all_sampled_q_increases_reduce_interior_angle": True,
              "qualitative_direction": "Increasing q flexes; decreasing q extends in this FlyMimic geometry.",
              "mamiya_recorded_angle_direction": "High measured angle extends; low flexes (reports/mamiya_claw_angle_direction.json).",
              "exact_mamiya_to_flymimic_angle_calibration": False,
              "malecns_snpp50_tuning_identified": False}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"q_range_rad": report["joint_q_range_rad"],
                      "interior_angle_deg_endpoints": [float(angles[0]), float(angles[-1])],
                      "all_200_segments_monotonic": True}, indent=2))


if __name__ == "__main__":
    main()
