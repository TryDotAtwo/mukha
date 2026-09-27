"""Replay the published FlyMimic left-front extensor pulse locally.

This checks source model mechanics only. The extensor command is artificial,
and no MaleCNS activity or cockpit control is used.
"""
import json
from pathlib import Path

import numpy as np
from flymimic_public_model import ROOT, MODEL_SHA, load_model, mj, sha

OUT = ROOT / "reports/flymimic_muscle_local_replay.json"
TRACE = ROOT / "data/derived/flymimic_muscle_local_replay/trace.npz"


def main():
    model, restored = load_model()
    assert model.nbody == 73 and model.njnt == 14 and model.nu == 15
    assert abs(model.opt.timestep - 0.0001) < 1e-12
    actuator = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
    assert actuator >= 0 and joint >= 0
    qindex = model.jnt_qposadr[joint]
    traces = {}
    for pulse in (False, True):
        data = mj.MjData(model)
        mj.mj_resetData(model, data)
        mj.mj_forward(model, data)
        q = np.empty(1000, dtype=np.float64)
        for tick in range(1000):
            data.ctrl[:] = 0.0001
            if pulse and 200 <= tick < 600:
                data.ctrl[actuator] = 1.0
            mj.mj_step(model, data)
            assert not any(item.number for item in data.warning)
            assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
            q[tick] = data.qpos[qindex]
        traces["pulse" if pulse else "baseline"] = q
    delta = traces["pulse"] - traces["baseline"]
    maximum = float(np.max(np.abs(delta)))
    TRACE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(TRACE, **traces)
    report = {
        "source_commit": restored["commit"], "model_sha256": MODEL_SHA,
        "mujoco_version": mj.__version__, "source_files_verified": 73,
        "model_counts": {"bodies": model.nbody, "joints": model.njnt,
                         "actuators": model.nu, "tendons": model.ntendon},
        "joint": "joint_LFTibia_pitch", "actuator": "LFTibia_extensor_93932",
        "timestep_s": model.opt.timestep, "steps_per_condition": 1000,
        "pulse_ticks": [200, 600], "baseline_command": 0.0001,
        "pulse_command": 1.0,
        "maximum_absolute_joint_difference_rad": maximum,
        "matches_prior_molab_maximum_within_1e_6_rad": abs(maximum - 0.411480) < 1e-6,
        "trace_path": str(TRACE.relative_to(ROOT)).replace("\\", "/"),
        "trace_sha256": sha(TRACE),
        "scope": "Local author-model muscle pulse; artificial activation, no MaleCNS mapping, contact, rocket or biological calibration.",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"maximum_absolute_joint_difference_rad": maximum,
                      "matches_prior_molab": report["matches_prior_molab_maximum_within_1e_6_rad"],
                      "trace_sha256": report["trace_sha256"]}))
    assert report["matches_prior_molab_maximum_within_1e_6_rad"]


if __name__ == "__main__":
    main()
