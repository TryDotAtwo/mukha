"""Build a source-model geometric tibia cycle for a future sensory validation run.

This is prescribed kinematics in a fixed FlyMimic pose, not a muscle or CNS run.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from audit_flymimic_knee_angle_direction import interior_angle
from flymimic_public_model import ROOT, MODEL, load_model, mj


OUT = ROOT / "data/derived/flymimic_prescribed_tibia_cycle_v1"
REPORT = ROOT / "reports/flymimic_prescribed_tibia_cycle.json"
DT_S = 0.0001
STEPS = 5000
FREQUENCY_HZ = 2.0
PEAK_TO_PEAK_DEG = 20.0
RELAX_STEPS = 20000
Q_GRID_POINTS = 1001


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    model, _ = load_model()
    assert abs(model.opt.timestep - DT_S) < 1e-12
    data = mj.MjData(model)
    key = mj.mj_name2id(model, mj.mjtObj.mjOBJ_KEY, "default-pose")
    assert key >= 0
    mj.mj_resetDataKeyframe(model, data, key)
    for _ in range(RELAX_STEPS):
        data.ctrl[:] = 0.0001
        mj.mj_step(model, data)
    assert not any(w.number for w in data.warning)
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    bodies = tuple(mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, name)
                   for name in ("LFTrochanter", "LFTibia", "LFTarsus1"))
    assert joint >= 0 and all(body >= 0 for body in bodies)
    q_index = int(model.jnt_qposadr[joint])
    settled_qpos = data.qpos.copy()
    settled_q = float(settled_qpos[q_index])
    data.qvel[:] = 0
    baseline_angle = interior_angle(model, data, *bodies)
    q_grid = np.linspace(*model.jnt_range[joint], Q_GRID_POINTS)
    angle_grid = np.empty_like(q_grid)
    for i, q in enumerate(q_grid):
        data.qpos[q_index] = q
        angle_grid[i] = interior_angle(model, data, *bodies)
    assert np.all(np.diff(angle_grid) < 0)
    target_min = baseline_angle - PEAK_TO_PEAK_DEG / 2
    target_max = baseline_angle + PEAK_TO_PEAK_DEG / 2
    assert angle_grid[-1] < target_min < target_max < angle_grid[0]
    time_s = np.arange(STEPS + 1, dtype=np.float64) * DT_S
    target_deg = baseline_angle + PEAK_TO_PEAK_DEG / 2 * np.sin(
        2 * np.pi * FREQUENCY_HZ * time_s)
    q_target = np.interp(target_deg, angle_grid[::-1], q_grid[::-1])
    actual_deg = np.empty_like(target_deg)
    for i, q in enumerate(q_target):
        data.qpos[q_index] = q
        actual_deg[i] = interior_angle(model, data, *bodies)
    assert np.array_equal(data.qpos[np.arange(model.nq) != q_index],
                          settled_qpos[np.arange(model.nq) != q_index])
    assert not any(w.number for w in data.warning)
    max_error = float(np.max(np.abs(actual_deg - target_deg)))
    assert max_error < 0.02, max_error
    assert abs(time_s[-1] - 0.5) < 1e-12
    assert abs(target_deg[0] - target_deg[-1]) < 1e-12
    OUT.mkdir(parents=True)
    trace = OUT / "kinematics.npz"
    np.savez_compressed(trace, time_s=time_s, joint_q_rad=q_target,
                        target_interior_angle_deg=target_deg,
                        actual_interior_angle_deg=actual_deg,
                        q_calibration_grid=q_grid,
                        angle_calibration_grid_deg=angle_grid)
    report = {
        "scope": "Prescribed tibia geometry in the pinned FlyMimic body; no CNS or force inference",
        "source_model_xml_sha256": sha(MODEL), "mujoco_version": mj.__version__,
        "keyframe": "default-pose", "relax_steps": RELAX_STEPS,
        "relax_activation": 0.0001,
        "settled_qpos_sha256": hashlib.sha256(settled_qpos.tobytes()).hexdigest(),
        "settled_joint_q_rad": settled_q,
        "body_origin_angle_baseline_deg": baseline_angle,
        "angle_definition": "3D interior angle at left tibia body origin using trochanter and tarsus1 body origins",
        "center_angle_choice": "FlyMimic keyframe-derived passive pose, not a recorded experimental start angle",
        "frequency_hz": FREQUENCY_HZ, "target_peak_to_peak_deg": PEAK_TO_PEAK_DEG,
        "steps": STEPS, "dt_s": DT_S, "duration_s": float(time_s[-1]),
        "q_range_rad": model.jnt_range[joint].tolist(),
        "realized_q_range_rad": [float(q_target.min()), float(q_target.max())],
        "realized_angle_range_deg": [float(actual_deg.min()), float(actual_deg.max())],
        "max_abs_angle_error_deg": max_error,
        "other_joint_positions_fixed": True,
        "mechanical_mode": "kinematic boundary imposed by an external experimenter; no mj_step during cycle",
        "trace_sha256": sha(trace),
        "natural_sensory_transduction_validated": False,
        "biological_response_validated": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("body_origin_angle_baseline_deg", "realized_q_range_rad",
                       "realized_angle_range_deg", "max_abs_angle_error_deg")}, indent=2))


if __name__ == "__main__":
    main()
