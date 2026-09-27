"""Re-derive foot pad and test muscle/contact controls with explicit harness."""
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from audit_flymimic_foot_geometry import world_vertices
from probe_flymimic_passive_throttle import modified_xml

SOURCE = ROOT / "data/derived/flymimic_harness_v1/harness.xml"
OUT = ROOT / "data/derived/flymimic_harness_contact_v1"
REPORT = ROOT / "reports/flymimic_harness_contact_local.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    harness_report = json.loads((ROOT / "reports/flymimic_harness_local.json").read_text())
    assert sha(SOURCE) == harness_report["harness_xml_sha256"]
    source_text = SOURCE.read_text(encoding="utf-8")
    original, _ = load_model(source_text)
    state = mj.MjData(original)
    mj.mj_resetDataKeyframe(original, state,
                            mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose"))
    for _ in range(20000):
        state.ctrl[:] = .0001
        mj.mj_step(original, state)
    assert not any(w.number for w in state.warning)
    foot = mj.mj_name2id(original, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    vertices = world_vertices(original, state, foot)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    OUT.mkdir(parents=True, exist_ok=True)
    cases, traces, pads = [], {}, {}
    for side in ("negative_x", "positive_x"):
        x = low[0] - .02 if side == "negative_x" else high[0] + .02
        center = [float(x), float((low[1]+high[1])/2), float((low[2]+high[2])/2)]
        pads[side] = center
        axis = "-1 0 0" if side == "negative_x" else "+1 0 0"
        for contact in (False, True):
            xml = modified_xml(center, contact, axis, source_text)
            xml_path = OUT / f"{side}_contact_{int(contact)}.xml"
            xml_path.write_text(xml, encoding="utf-8")
            model, _ = load_model(xml)
            assert model.nq == original.nq + 1 and model.neq == original.neq
            slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
            pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
            foot_id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
            muscle = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
            knee = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
            assert min(slide, pad, foot_id, muscle, knee) >= 0
            for pulse in (False, True):
                data = mj.MjData(model)
                data.qpos[:original.nq] = state.qpos
                data.qvel[:original.nv] = state.qvel
                data.act[:] = state.act
                mj.mj_forward(model, data)
                slide_q, knee_q, contacts, root_q = [], [], [], []
                for tick in range(1000):
                    data.ctrl[:] = .0001
                    if pulse and 200 <= tick < 600:
                        data.ctrl[muscle] = 1.
                    mj.mj_step(model, data)
                    assert not any(w.number for w in data.warning)
                    assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                    contacts.append(sum({item.geom1, item.geom2} == {foot_id, pad}
                                        for item in data.contact))
                    slide_q.append(float(data.qpos[model.jnt_qposadr[slide]]))
                    knee_q.append(float(data.qpos[model.jnt_qposadr[knee]]))
                    root_q.append(data.qpos[:3].copy())
                label = f"{side}_contact_{int(contact)}_pulse_{int(pulse)}"
                traces[label + "_slide_mm"] = np.asarray(slide_q)
                traces[label + "_knee_rad"] = np.asarray(knee_q)
                traces[label + "_root_mm"] = np.asarray(root_q)
                traces[label + "_contacts"] = np.asarray(contacts, dtype=np.uint16)
                cases.append({"side": side, "contact": contact, "pulse": pulse,
                              "exact_foot_pad_contact_samples": int(sum(contacts)),
                              "first_contact_tick": next((i for i, n in enumerate(contacts) if n), None),
                              "peak_abs_slide_mm": float(np.max(np.abs(slide_q))),
                              "final_slide_mm": float(slide_q[-1]),
                              "peak_root_displacement_from_initial_mm": float(np.max(np.linalg.norm(np.asarray(root_q)-state.qpos[:3],axis=1))),
                              "xml_sha256": sha(xml_path)})
                if not contact:
                    assert sum(contacts) == 0 and np.all(np.asarray(slide_q) == 0)
    active = next(c for c in cases if c["side"] == "positive_x" and c["contact"] and c["pulse"])
    controls = [c for c in cases if c["side"] == "positive_x" and c is not active]
    assert active["first_contact_tick"] >= 200 and active["exact_foot_pad_contact_samples"] > 0
    assert all(c["exact_foot_pad_contact_samples"] == 0 and c["peak_abs_slide_mm"] == 0
               for c in controls)
    prefix = "positive_x_contact_1_"
    assert np.array_equal(traces[prefix + "pulse_1_knee_rad"][:200],
                          traces[prefix + "pulse_0_knee_rad"][:200])
    assert np.all(traces[prefix + "pulse_1_slide_mm"][:active["first_contact_tick"]] == 0)
    path = OUT / "traces.npz"
    np.savez_compressed(path, **traces)
    report = {"source_harness_xml_sha256": sha(SOURCE), "source_harness_report_sha256": sha(ROOT / "reports/flymimic_harness_local.json"),
              "source_initial_root_qpos": state.qpos[:7].tolist(),
              "source_initial_knee_rad": float(state.qpos[original.jnt_qposadr[mj.mj_name2id(original,mj.mjtObj.mjOBJ_JOINT,"joint_LFTibia_pitch")]]),
              "foot_bbox_low_mm": low.tolist(), "foot_bbox_high_mm": high.tolist(),
              "pad_centers_mm": pads, "initial_gap_mm": .01,
              "causal_checks": {"all_three_positive_x_controls_zero": True,
                                "pre_pulse_knee_identical": True,
                                "slide_zero_before_first_contact": True},
              "cases": cases, "trace_sha256": sha(path),
              "scope": "Passive one-axis pad from harness-supported free-root FlyMimic posture; full-strength muscle pulse diagnostic, no validated cabin or neural-muscle command."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
