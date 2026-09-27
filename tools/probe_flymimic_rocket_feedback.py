"""Exploratory closed FlyMimic pad/native-rocket mechanics in a co-falling cabin."""
import ctypes
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml

OUT = ROOT / "data/derived/flymimic_rocket_feedback_v1"
REPORT = ROOT / "reports/flymimic_rocket_feedback_local.json"
DLL = ROOT / "build/rocket_vertical_abi.dll"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source_report = json.loads((ROOT / "reports/flymimic_passive_throttle_local.json").read_text())
    pad_position = source_report["pad_center_mm"]
    original, _ = load_model()
    relaxed = mj.MjData(original)
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(original, relaxed)
    assert not any(w.number for w in relaxed.warning)
    lib = ctypes.CDLL(str(DLL))
    lib.rocket_new.restype = ctypes.c_void_p
    lib.rocket_delete.argtypes = [ctypes.c_void_p]
    lib.rocket_effective_g.argtypes = [ctypes.c_void_p]
    lib.rocket_effective_g.restype = ctypes.c_double
    lib.rocket_advance.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double,
                                    ctypes.POINTER(ctypes.c_double)]
    lib.rocket_advance.restype = ctypes.c_int
    OUT.mkdir(parents=True, exist_ok=True)
    cases = []
    traces = {}
    for feedback in (False, True):
        for contact in (False, True):
            xml = modified_xml(pad_position, contact)
            model, _ = load_model(xml)
            slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
            foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
            pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
            actuator = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
            for pulse in (False, True):
                data = mj.MjData(model)
                data.qpos[:original.nq] = relaxed.qpos
                data.qvel[:original.nv] = relaxed.qvel
                data.act[:] = relaxed.act
                model.opt.gravity[:] = 0
                mj.mj_forward(model, data)
                handle = lib.rocket_new()
                assert handle
                state = (ctypes.c_double * 5)()
                slide_trace, throttle_trace, velocity_trace, contact_trace, gravity_trace = [], [], [], [], []
                try:
                    for tick in range(1000):
                        q = float(data.qpos[model.jnt_qposadr[slide]])
                        effective_g = lib.rocket_effective_g(handle) if feedback else 0.
                        model.opt.gravity[2] = effective_g
                        data.ctrl[:] = .0001
                        if pulse and 200 <= tick < 600:
                            data.ctrl[actuator] = 1.
                        mj.mj_step(model, data)
                        assert lib.rocket_advance(handle, q, model.opt.timestep, state)
                        assert abs(data.time - state[0]) < 1e-10
                        assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                        assert not any(w.number for w in data.warning)
                        slide_trace.append(float(data.qpos[model.jnt_qposadr[slide]]))
                        throttle_trace.append(float(np.clip(q / .3, 0, 1)))
                        velocity_trace.append(state[2])
                        contact_trace.append(sum({c.geom1, c.geom2} == {foot, pad} for c in data.contact))
                        gravity_trace.append(effective_g)
                finally:
                    lib.rocket_delete(handle)
                label = f"feedback_{int(feedback)}_contact_{int(contact)}_pulse_{int(pulse)}"
                traces[label + "_slide_mm"] = np.asarray(slide_trace)
                traces[label + "_throttle"] = np.asarray(throttle_trace)
                traces[label + "_velocity_mps"] = np.asarray(velocity_trace)
                traces[label + "_contacts"] = np.asarray(contact_trace)
                traces[label + "_effective_g_mm_s2"] = np.asarray(gravity_trace)
                cases.append({"feedback": feedback, "contact": contact, "pulse": pulse,
                              "exact_contact_samples": int(sum(contact_trace)),
                              "max_slide_mm": float(max(slide_trace)),
                              "max_throttle": float(max(throttle_trace)),
                              "max_abs_effective_g_mm_s2": float(max(abs(x) for x in gravity_trace))})
    trace_path = OUT / "traces.npz"
    for feedback in (0, 1):
        base = f"feedback_{feedback}_contact_0_pulse_0"
        for contact, pulse in ((0, 1), (1, 0)):
            control = f"feedback_{feedback}_contact_{contact}_pulse_{pulse}"
            np.testing.assert_array_equal(traces[base + "_velocity_mps"],
                                          traces[control + "_velocity_mps"])
            assert np.all(traces[control + "_slide_mm"] == 0)
            assert np.all(traces[control + "_throttle"] == 0)
        assert np.all(traces[base + "_effective_g_mm_s2"] == 0)
    open_loop = "feedback_0_contact_1_pulse_1"
    closed_loop = "feedback_1_contact_1_pulse_1"
    first_throttle = int(np.flatnonzero(traces[open_loop + "_throttle"] > 0)[0])
    assert first_throttle >= 200
    for suffix in ("_slide_mm", "_throttle", "_velocity_mps"):
        np.testing.assert_array_equal(traces[open_loop + suffix][:first_throttle + 1],
                                      traces[closed_loop + suffix][:first_throttle + 1])
    assert np.all(traces[closed_loop + "_effective_g_mm_s2"][:first_throttle + 1] == 0)
    slide_effect = float(np.max(np.abs(traces[closed_loop + "_slide_mm"] -
                                       traces[open_loop + "_slide_mm"])))
    velocity_effect = float(np.max(np.abs(traces[closed_loop + "_velocity_mps"] -
                                          traces[open_loop + "_velocity_mps"])))
    assert slide_effect > 0 and velocity_effect > 0
    np.savez_compressed(trace_path, **traces)
    report = {"cases": cases, "source_xml_sha256": source_report["source_xml_sha256"],
              "pad_center_mm": pad_position, "mujoco_version": mj.__version__,
              "cabin_frame": "nonrotating co-falling local frame; effective gravity is -thrust/m",
              "relaxation": "source gravity -9801 mm/s2 for 20000 steps, then co-falling frame at t=0",
              "rocket_plant": "native/rocket_vertical.h via native/rocket_vertical_abi.cpp",
              "first_nonzero_throttle_tick": first_throttle,
              "identical_trajectories_through_first_nonzero_throttle": True,
              "max_feedback_slide_difference_mm": slide_effect,
              "max_feedback_velocity_difference_mps": velocity_effect,
              "zero_controls_identical": True,
              "trace_sha256": sha(trace_path), "abi_sha256": sha(DLL),
              "scope": "Exploratory prescribed-muscle mechanical loop; no MaleCNS motor mapping, realistic seated cabin or KSP landing."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
