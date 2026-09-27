"""Test passive foot-pad contact from the published FlyMimic keyframe states."""
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, MODEL_SHA, load_model, mj
from audit_flymimic_foot_geometry import world_vertices
from probe_flymimic_passive_throttle import modified_xml

OUT = ROOT / "data/derived/flymimic_keyframe_contact_v1"
REPORT = ROOT / "reports/flymimic_keyframe_contact_local.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original, restored = load_model()
    key = mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose")
    foot = mj.mj_name2id(original, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    assert min(key, foot) >= 0
    source = mj.MjData(original)
    mj.mj_resetDataKeyframe(original, source, key)
    mj.mj_forward(original, source)
    states = [("author_keyframe", source)]
    settled = mj.MjData(original)
    settled.qpos[:] = source.qpos
    settled.qvel[:] = source.qvel
    settled.act[:] = source.act
    mj.mj_forward(original, settled)
    for _ in range(20000):
        settled.ctrl[:] = .0001
        mj.mj_step(original, settled)
    assert not any(w.number for w in settled.warning)
    states.append(("keyframe_passive_2s", settled))
    OUT.mkdir(parents=True, exist_ok=True)
    cases, geometries, traces = [], {}, {}
    for state_label, state in states:
        vertices = world_vertices(original, state, foot)
        low, high = vertices.min(axis=0), vertices.max(axis=0)
        geometries[state_label] = {"foot_bbox_low_mm": low.tolist(), "foot_bbox_high_mm": high.tolist()}
        for side in ("negative_x", "positive_x"):
            x = low[0] - .02 if side == "negative_x" else high[0] + .02
            pad_position = [float(x), float((low[1] + high[1]) / 2), float((low[2] + high[2]) / 2)]
            geometries[state_label][side + "_pad_center_mm"] = pad_position
            for contact in (False, True):
                axis = "+1 0 0" if side == "positive_x" else "-1 0 0"
                xml = modified_xml(pad_position, contact, axis)
                xml_path = OUT / f"{state_label}_{side}_contact_{int(contact)}.xml"
                xml_path.write_text(xml, encoding="utf-8")
                model, _ = load_model(xml)
                slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
                pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
                foot_id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
                knee = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
                actuator = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
                assert min(slide, pad, foot_id, knee, actuator) >= 0
                assert model.nq == original.nq + 1 and model.nu == original.nu
                for pulse in (False, True):
                    data = mj.MjData(model)
                    data.qpos[:original.nq] = state.qpos
                    data.qvel[:original.nv] = state.qvel
                    data.act[:] = state.act
                    mj.mj_forward(model, data)
                    slide_q, knee_q, contacts = [], [], []
                    for tick in range(1000):
                        data.ctrl[:] = .0001
                        if pulse and 200 <= tick < 600:
                            data.ctrl[actuator] = 1.
                        mj.mj_step(model, data)
                        assert not any(w.number for w in data.warning)
                        assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                        contacts.append(sum({item.geom1, item.geom2} == {foot_id, pad}
                                            for item in data.contact))
                        slide_q.append(float(data.qpos[model.jnt_qposadr[slide]]))
                        knee_q.append(float(data.qpos[model.jnt_qposadr[knee]]))
                    label = f"{state_label}_{side}_contact_{int(contact)}_pulse_{int(pulse)}"
                    traces[label + "_slide_mm"] = np.asarray(slide_q)
                    traces[label + "_knee_rad"] = np.asarray(knee_q)
                    traces[label + "_contacts"] = np.asarray(contacts, dtype=np.uint16)
                    cases.append({"state": state_label, "side": side, "slide_axis": axis,
                                  "contact_enabled": contact,
                                  "muscle_pulse": pulse, "exact_foot_pad_contact_samples": int(sum(contacts)),
                                  "first_contact_tick": next((i for i, n in enumerate(contacts) if n), None),
                                  "peak_abs_slide_mm": float(np.max(np.abs(slide_q))),
                                  "final_slide_mm": float(slide_q[-1]),
                                  "xml_path": str(xml_path.relative_to(ROOT)).replace("\\", "/"),
                                  "xml_sha256": sha(xml_path)})
                    if not contact:
                        assert sum(contacts) == 0 and np.all(np.asarray(slide_q) == 0)
    label = "keyframe_passive_2s_positive_x_"
    active = next(c for c in cases if c["state"] == "keyframe_passive_2s"
                  and c["side"] == "positive_x" and c["contact_enabled"]
                  and c["muscle_pulse"])
    controls = [c for c in cases if c["state"] == "keyframe_passive_2s"
                and c["side"] == "positive_x" and c is not active]
    assert active["first_contact_tick"] >= 200 and active["exact_foot_pad_contact_samples"] > 0
    assert all(c["exact_foot_pad_contact_samples"] == 0 and c["peak_abs_slide_mm"] == 0
               for c in controls)
    assert np.array_equal(traces[label + "contact_1_pulse_1_knee_rad"][:200],
                          traces[label + "contact_1_pulse_0_knee_rad"][:200])
    assert np.all(traces[label + "contact_1_pulse_1_slide_mm"][:active["first_contact_tick"]] == 0)
    path = OUT / "traces.npz"
    np.savez_compressed(path, **traces)
    report = {"source_commit": restored["commit"], "source_xml_sha256": MODEL_SHA,
              "mujoco_version": mj.__version__, "source_keyframe": "default-pose",
              "passive_settle_steps": 20000, "pad_surface_gap_mm": .01,
              "pad_half_size_mm": [.01, .15, .15], "slide_axis_by_side": {"negative_x": [-1, 0, 0], "positive_x": [1, 0, 0]},
              "pulse_ticks": [200, 600], "pulse_activation": 1.,
              "geometry": geometries, "cases": cases,
              "trace_path": str(path.relative_to(ROOT)).replace("\\", "/"),
              "trace_sha256": sha(path),
              "scope": "Exploratory source-keyframe geometry and one-axis passive pad; no biological muscle command or validated cockpit."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"geometry": geometries, "cases": [{k: v for k, v in case.items() if k not in ("xml_path", "xml_sha256")} for case in cases]}, indent=2))


if __name__ == "__main__":
    main()
