"""Test an explicit compliant thorax-to-cabin harness for free-root FlyMimic."""
import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np

from flymimic_public_model import ROOT, load_model, mj

SOURCE = ROOT / "data/derived/flymimic_free_root_v1/free_root.xml"
OUT = ROOT / "data/derived/flymimic_harness_v1"
REPORT = ROOT / "reports/flymimic_harness_local.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quaternion_matrix(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def main():
    free_report = json.loads((ROOT / "reports/flymimic_free_root_local.json").read_text())
    assert sha(SOURCE) == free_report["free_root_xml_sha256"]
    tree = ET.fromstring(SOURCE.read_text(encoding="utf-8"))
    thorax = tree.find("./worldbody/body[@name='Thorax']")
    equality = tree.find("equality")
    assert thorax is not None and equality is not None
    anchor_position = np.fromstring(thorax.attrib["pos"], sep=" ")
    anchor_quat = np.fromstring(thorax.attrib["quat"], sep=" ")
    anchor_quat /= np.linalg.norm(anchor_quat)
    inverse_position = -quaternion_matrix(anchor_quat).T @ anchor_position
    inverse_quat = anchor_quat * np.array([1., -1., -1., -1.])
    relpose = np.r_[inverse_position, inverse_quat]
    ET.SubElement(equality, "weld", name="thorax_cabin_harness", body1="Thorax",
                  body2="world", relpose=" ".join(f"{v:.17g}" for v in relpose),
                  solref="0.001 1", solimp="0.9999 0.9999 0.001 0.5 2")
    OUT.mkdir(parents=True, exist_ok=True)
    xml_path = OUT / "harness.xml"
    xml_path.write_text(ET.tostring(tree, encoding="unicode"), encoding="utf-8")
    model, _ = load_model(xml_path.read_text(encoding="utf-8"))
    assert model.nq == 21 and model.neq == 8
    key = mj.mj_name2id(model, mj.mjtObj.mjOBJ_KEY, "default-pose")
    root = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "Thorax")
    floor = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "floor")
    harness = mj.mj_name2id(model, mj.mjtObj.mjOBJ_EQUALITY, "thorax_cabin_harness")
    assert min(key, root, floor, harness) >= 0
    data = mj.MjData(model)
    mj.mj_resetDataKeyframe(model, data, key)
    mj.mj_forward(model, data)
    initial = data.qpos[:7].copy()
    trace = np.empty((20001, 7))
    floor_contacts = np.empty(20001, dtype=np.int32)
    trace[0] = initial
    floor_contacts[0] = sum(floor in (c.geom1, c.geom2) for c in data.contact)
    for tick in range(20000):
        data.ctrl[:] = .0001
        mj.mj_step(model, data)
        assert not any(w.number for w in data.warning)
        assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
        trace[tick+1] = data.qpos[:7]
        floor_contacts[tick+1] = sum(floor in (c.geom1, c.geom2) for c in data.contact)
    path = OUT / "traces.npz"
    np.savez_compressed(path, root_qpos=trace, floor_contacts=floor_contacts)
    positional_error = np.linalg.norm(trace[:, :3] - initial[:3], axis=1)
    up_dot = float(data.xmat[root].reshape(3, 3)[2, 2])
    report = {"source_free_root_xml_sha256": sha(SOURCE),
              "harness_xml_sha256": sha(xml_path), "trace_sha256": sha(path),
              "harness_equality_index": harness,
              "relative_pose_body2_in_body1": relpose.tolist(),
              "solref": [0.001, 1.], "solimp": [0.9999, 0.9999, 0.001, 0.5, 2.],
              "initial_root_qpos": initial.tolist(), "final_root_qpos": trace[-1].tolist(),
              "maximum_root_translation_from_anchor_mm": float(positional_error.max()),
              "final_root_translation_from_anchor_mm": float(positional_error[-1]),
              "thorax_up_dot_world_up_final": up_dot,
              "floor_contact_samples": int((floor_contacts > 0).sum()),
              "mujoco_warnings": 0, "duration_ms": 2000.,
              "scope": "Explicit strong compliant world-anchored thorax harness. Engineering cabin support diagnostic; not measured seat biomechanics, active posture control, free flight, or KSP."}
    assert up_dot > .99 and positional_error.max() < .05
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("maximum_root_translation_from_anchor_mm",
                                      "final_root_translation_from_anchor_mm",
                                      "thorax_up_dot_world_up_final", "floor_contact_samples")}, indent=2))


if __name__ == "__main__":
    main()
