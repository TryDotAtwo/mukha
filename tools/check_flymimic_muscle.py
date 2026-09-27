"""Isolated FlyMimic left-front tibia muscle intervention in Molab.

Requires the Git-verified FlyMimic source archive extracted at the pinned path.
It is a mechanical test, not a MaleCNS motor mapping or biological validation.
"""

import hashlib
import json
from pathlib import Path

import mujoco as mj
import numpy as np


ROOT = Path("/marimo/fly-project")
MODEL = ROOT / "data/reference/flymimic/flymimic/assets/models/best_combined_cvt3.xml"
EXPECTED_XML_SHA256 = "d67ff06d0c684599f00d5f33f8f8ac8ced01ab994c41341b551f8148b6d8aa0b"


def run():
    if hashlib.sha256(MODEL.read_bytes()).hexdigest() != EXPECTED_XML_SHA256:
        raise RuntimeError("FlyMimic XML digest mismatch")
    model = mj.MjModel.from_xml_path(str(MODEL))
    actuator_name = "LFTibia_extensor_93932"
    joint_name = "joint_LFTibia_pitch"
    actuator = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, actuator_name)
    joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, joint_name)
    if actuator < 0 or joint < 0:
        raise RuntimeError("required muscle or joint missing")
    qindex = int(model.jnt_qposadr[joint])
    traces = {}
    for pulse in (False, True):
        data = mj.MjData(model)
        mj.mj_resetData(model, data)
        mj.mj_forward(model, data)
        trace = np.empty(1000, dtype=np.float64)
        for tick in range(1000):
            data.ctrl[:] = 0.0001
            if pulse and 200 <= tick < 600:
                data.ctrl[actuator] = 1.0
            mj.mj_step(model, data)
            if any(w.number for w in data.warning):
                raise RuntimeError("MuJoCo warning")
            trace[tick] = data.qpos[qindex]
        traces["pulse" if pulse else "baseline"] = trace
    baseline, pulse = traces["baseline"], traces["pulse"]
    if not np.isfinite(baseline).all() or not np.isfinite(pulse).all():
        raise RuntimeError("nonfinite joint state")
    report = {
        "scope": "FlyMimic author muscle isolated pulse diagnostic in Molab; no neural control or cabin",
        "commit": "9ea1131626cd76f7203b74076ef8f0e9cab30bef",
        "xml_sha256": EXPECTED_XML_SHA256,
        "mujoco_version": mj.__version__,
        "actuator": actuator_name,
        "joint": joint_name,
        "dt_s": model.opt.timestep,
        "ticks": 1000,
        "pulse_ticks": [200, 600],
        "baseline_final_rad": float(baseline[-1]),
        "pulse_final_rad": float(pulse[-1]),
        "max_abs_joint_delta_rad": float(np.max(np.abs(pulse - baseline))),
        "all_finite": True,
        "warnings": 0,
        "limitations": "No MaleCNS identity/activation fit, no contact or cabin, not biological validation",
        "biological_gate_passed": False,
    }
    print("FLYMIMIC_MUSCLE_PULSE", json.dumps(report))
    return report, traces


if __name__ == "__main__":
    run()
