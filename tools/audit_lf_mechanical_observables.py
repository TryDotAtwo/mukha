"""Replay the archived body controls and measure available mechanical channels.

Joint and solver forces are MuJoCo outputs, not calibrated receptor signals or
measurements of cuticular strain/hair deflection.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, MODEL, load_model, mj
from probe_flymimic_passive_throttle import modified_xml


SOURCE = ROOT / "reports/lf_four_proprio_body_loop.json"
PAD_REPORT = ROOT / "reports/flymimic_keyframe_contact_local.json"
TRACES = ROOT / "data/derived/lf_four_proprio_body_loop_v1/traces.npz"
OUT = ROOT / "data/derived/lf_mechanical_observables_v1"
REPORT = ROOT / "reports/lf_mechanical_observables.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert sha(TRACES) == source["trace_sha256"]
    archived = np.load(TRACES)
    assert source["ticks"] == 5000 and source["initial_perturbation_deg"] == 10.0
    original, _ = load_model()
    assert original.nsensor == 0
    relaxed = mj.MjData(original)
    key = mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose")
    mj.mj_resetDataKeyframe(original, relaxed, key)
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(original, relaxed)
    pad_report = json.loads(PAD_REPORT.read_text(encoding="utf-8"))
    pad_center = pad_report["geometry"]["keyframe_passive_2s"]["positive_x_pad_center_mm"]
    model, _ = load_model(modified_xml(pad_center, True, "+1 0 0"))
    assert model.nsensor == 0
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
    extensor = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
    foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
    joint_q = int(model.jnt_qposadr[joint])
    joint_v = int(model.jnt_dofadr[joint])
    slide_q = int(model.jnt_qposadr[slide])
    assert np.isclose(float(relaxed.qpos[joint_q]), source["initial_knee_reference_rad"], atol=1e-12)
    outputs = {}
    case_reports = []
    for case in source["cases"]:
        name = case["case"]
        body = mj.MjData(model)
        body.qpos[:original.nq] = relaxed.qpos
        body.qvel[:original.nv] = relaxed.qvel
        body.act[:] = relaxed.act
        body.qpos[joint_q] += np.deg2rad(source["initial_perturbation_deg"])
        mj.mj_forward(model, body)
        channels = {key: np.empty(source["ticks"], dtype=np.float64) for key in (
            "joint_angle_rad", "joint_velocity_rad_s", "joint_actuator_generalized_force",
            "joint_constraint_generalized_force", "extensor_actuator_force",
            "extensor_tendon_length_model_units", "exact_foot_pad_normal_force_model_units",
            "exact_foot_pad_contact_count")}
        for tick, control in enumerate(archived[name + "_muscle_control"]):
            body.ctrl[:] = .0001
            body.ctrl[extensor] = control
            mj.mj_step(model, body)
            assert not any(w.number for w in body.warning)
            channels["joint_angle_rad"][tick] = body.qpos[joint_q]
            channels["joint_velocity_rad_s"][tick] = body.qvel[joint_v]
            channels["joint_actuator_generalized_force"][tick] = body.qfrc_actuator[joint_v]
            channels["joint_constraint_generalized_force"][tick] = body.qfrc_constraint[joint_v]
            channels["extensor_actuator_force"][tick] = body.actuator_force[extensor]
            tendon_id = int(model.actuator_trnid[extensor, 0])
            channels["extensor_tendon_length_model_units"][tick] = body.ten_length[tendon_id]
            normal = 0.0
            contact_count = 0
            for i, contact in enumerate(body.contact):
                if {contact.geom1, contact.geom2} == {foot, pad}:
                    contact_count += 1
                    wrench = np.empty(6, dtype=np.float64)
                    mj.mj_contactForce(model, body, i, wrench)
                    normal += float(wrench[0])
            channels["exact_foot_pad_normal_force_model_units"][tick] = normal
            channels["exact_foot_pad_contact_count"][tick] = contact_count
        q_error = float(np.max(np.abs(channels["joint_angle_rad"] - archived[name + "_knee_rad"])))
        slide_error = float(np.max(np.abs(body.qpos[slide_q] - archived[name + "_slide_mm"][-1])))
        assert q_error < 1e-10 and slide_error < 1e-10
        assert np.array_equal(channels["exact_foot_pad_contact_count"] > 0,
                              archived[name + "_exact_contacts"] > 0)
        outputs.update({name + "_" + key: value for key, value in channels.items()})
        case_reports.append({"case": name,
                             "max_knee_replay_error_rad": q_error,
                             "final_slide_replay_error_mm": slide_error,
                             "velocity_range_rad_s": [float(channels["joint_velocity_rad_s"].min()),
                                                      float(channels["joint_velocity_rad_s"].max())],
                             "joint_actuator_force_range": [float(channels["joint_actuator_generalized_force"].min()),
                                                            float(channels["joint_actuator_generalized_force"].max())],
                             "joint_constraint_force_range": [float(channels["joint_constraint_generalized_force"].min()),
                                                              float(channels["joint_constraint_generalized_force"].max())],
                             "extensor_force_range": [float(channels["extensor_actuator_force"].min()),
                                                      float(channels["extensor_actuator_force"].max())],
                             "exact_contact_force_positive_ticks": int(np.count_nonzero(
                                 channels["exact_foot_pad_normal_force_model_units"] > 0)),
                             "exact_contact_geometry_ticks": int(np.count_nonzero(
                                 channels["exact_foot_pad_contact_count"] > 0)),
                             "exact_contact_normal_force_max": float(
                                 channels["exact_foot_pad_normal_force_model_units"].max())})
    OUT.mkdir(parents=True)
    path = OUT / "mechanical_channels.npz"
    np.savez_compressed(path, **outputs)
    report = {"scope": "Exact-control physical replay of 500-ms four-cell diagnostic; synchronized mechanical observables after each 0.1-ms MuJoCo step",
              "source_report_sha256": sha(SOURCE), "source_trace_sha256": sha(TRACES),
              "source_xml_sha256": sha(MODEL), "pad_report_sha256": sha(PAD_REPORT),
              "source_and_modified_model_sensor_count": [original.nsensor, model.nsensor],
              "cases": case_reports,
              "output_sha256": sha(path),
              "interpretation": "Joint angle/velocity, generalized forces, tendon length, and pad contact force are mechanics outputs; generalized joint force is not cuticular strain, and no hair-plate deflection or receptor tuning is present.",
              "biological_sensor_calibration": False}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(case_reports, indent=2))


if __name__ == "__main__":
    main()
