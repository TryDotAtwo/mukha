"""Test full FlyMimic foot contact with a passive diagnostic throttle slide.

Pad placement is fixed from the relaxed, unpulsed foot surface. The source
muscle activation is artificial and not a MaleCNS motor command.
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from flymimic_public_model import ROOT, MODEL, MODEL_SHA, load_model, mj
from audit_flymimic_foot_geometry import world_vertices

OUT_DIR = ROOT / "data/derived/flymimic_passive_throttle_v1"
REPORT = ROOT / "reports/flymimic_passive_throttle_local.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def modified_xml(pad_position, contact, slide_axis="-1 0 0", base_xml_text=None):
    tree = ET.fromstring(MODEL.read_text(encoding="utf-8") if base_xml_text is None else base_xml_text)
    world = tree.find("worldbody")
    assert world is not None
    body = ET.SubElement(world, "body", name="throttle_slider",
                         pos=" ".join(f"{value:.17g}" for value in pad_position))
    ET.SubElement(body, "joint", name="throttle_slide", type="slide",
                  axis=slide_axis, limited="true", range="-0.05 0.3",
                  stiffness="0.5", damping="0.002")
    ET.SubElement(body, "geom", name="throttle_pad", type="box",
                  size="0.01 0.15 0.15", mass="0.001", contype="0", conaffinity="0",
                  rgba="0.2 0.6 0.8 1")
    if contact:
        pairs = ET.SubElement(tree, "contact")
        ET.SubElement(pairs, "pair", geom1="LFTarsus5_geom", geom2="throttle_pad",
                      condim="3", friction="0.5 0.5 0.005 0.0001 0.0001")
    return ET.tostring(tree, encoding="unicode")


def main():
    original, restored = load_model()
    foot = mj.mj_name2id(original, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
    relaxed = mj.MjData(original)
    mj.mj_resetData(original, relaxed)
    mj.mj_forward(original, relaxed)
    for _ in range(20000):
        relaxed.ctrl[:] = 0.0001
        mj.mj_step(original, relaxed)
    assert not any(w.number for w in relaxed.warning)
    vertices = world_vertices(original, relaxed, foot)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    # The near face is 0.01 mm beyond the negative-X surface at the
    # unpulsed relaxed state; pad X half-size is another 0.01 mm.
    pad_position = [float(low[0] - 0.02), float((low[1] + high[1]) / 2),
                    float((low[2] + high[2]) / 2)]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = []
    traces = {}
    for contact in (False, True):
        xml = modified_xml(pad_position, contact)
        xml_path = OUT_DIR / ("body_contact.xml" if contact else "body_no_contact.xml")
        xml_path.write_text(xml, encoding="utf-8")
        model, _ = load_model(xml)
        slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
        pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
        foot_id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
        knee = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
        actuator = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
        assert min(slide, pad, foot_id, knee, actuator) >= 0 and model.nu == original.nu
        assert model.nq == original.nq + 1 and model.na == original.na
        assert not any(model.actuator_trntype[a] == mj.mjtTrn.mjTRN_JOINT
                       and model.actuator_trnid[a, 0] == slide
                       for a in range(model.nu))
        for pulse in (False, True):
            data = mj.MjData(model)
            mj.mj_resetData(model, data)
            data.qpos[:original.nq] = relaxed.qpos
            data.qvel[:original.nv] = relaxed.qvel
            data.act[:] = relaxed.act
            mj.mj_forward(model, data)
            slide_q, knee_q, contacts = [], [], []
            for tick in range(1000):
                data.ctrl[:] = 0.0001
                if pulse and 200 <= tick < 600:
                    data.ctrl[actuator] = 1.0
                mj.mj_step(model, data)
                assert not any(w.number for w in data.warning)
                assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                count = sum({item.geom1, item.geom2} == {foot_id, pad}
                            for item in data.contact)
                slide_q.append(float(data.qpos[model.jnt_qposadr[slide]]))
                knee_q.append(float(data.qpos[model.jnt_qposadr[knee]]))
                contacts.append(count)
            label = f"contact_{int(contact)}_pulse_{int(pulse)}"
            traces[label + "_slide_mm"] = np.asarray(slide_q)
            traces[label + "_knee_rad"] = np.asarray(knee_q)
            traces[label + "_contacts"] = np.asarray(contacts, dtype=np.uint16)
            cases.append({"contact_enabled": contact, "muscle_pulse": pulse,
                          "exact_foot_pad_contact_samples": int(sum(contacts)),
                          "first_contact_tick": next((i for i, n in enumerate(contacts) if n), None),
                          "maximum_absolute_slide_mm": float(np.max(np.abs(slide_q))),
                          "maximum_slide_mm": float(np.max(slide_q)),
                          "xml_path": str(xml_path.relative_to(ROOT)).replace("\\", "/"),
                          "xml_sha256": sha(xml_path)})
    for case in cases:
        label = f"contact_{int(case['contact_enabled'])}_pulse_{int(case['muscle_pulse'])}"
        if not (case["contact_enabled"] and case["muscle_pulse"]):
            assert case["exact_foot_pad_contact_samples"] == 0
            assert np.all(traces[label + "_slide_mm"] == 0)
    active = cases[3]
    assert active["exact_foot_pad_contact_samples"] > 0
    assert active["first_contact_tick"] >= 200
    assert active["maximum_slide_mm"] > 0
    baseline_knee = traces["contact_0_pulse_0_knee_rad"][:200]
    assert all(np.array_equal(baseline_knee, values[:200]) for key, values in traces.items()
               if key.endswith("_knee_rad"))
    trace_path = OUT_DIR / "traces.npz"
    np.savez_compressed(trace_path, **traces)
    report = {"source_commit": restored["commit"], "source_xml_sha256": MODEL_SHA,
              "source_files_verified": restored["file_count"],
              "mujoco_version": mj.__version__,
              "model_counts": {"bodies": original.nbody, "joints": original.njnt,
                               "muscle_actuators": original.nu, "tendons": original.ntendon},
              "relax_steps": 20000,
              "relaxed_foot_minimum_mm": low.tolist(),
              "relaxed_foot_maximum_mm": high.tolist(),
              "pad_center_mm": pad_position,
              "initial_surface_gap_mm": 0.01,
              "pad_half_size_mm": [0.01, 0.15, 0.15],
              "slide_axis": [-1, 0, 0], "slide_actuator_present": False,
              "pre_pulse_knee_trajectories_identical": True,
              "only_contact_plus_muscle_moves_slide": True,
              "mujoco_warnings": 0,
              "cases": cases,
              "trace_path": str(trace_path.relative_to(ROOT)).replace("\\", "/"),
              "trace_sha256": sha(trace_path),
              "scope": "Diagnostic full FlyMimic body and passive one-axis control, artificial muscle pulse; no neural controller, three-axis stick, rocket feedback or KSP landing."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pad_center_mm": pad_position, "cases": cases}, indent=2))


if __name__ == "__main__":
    main()
