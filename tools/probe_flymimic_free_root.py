"""Diagnostic free-root variant of published FlyMimic; preserve author joints."""
import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np

from flymimic_public_model import ROOT, MODEL, MODEL_SHA, load_model, mj

OUT = ROOT / "data/derived/flymimic_free_root_v1"
REPORT = ROOT / "reports/flymimic_free_root_local.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source, restored = load_model()
    root = ET.fromstring(MODEL.read_text(encoding="utf-8"))
    thorax = root.find("./worldbody/body[@name='Thorax']")
    key = root.find("./keyframe/key[@name='default-pose']")
    assert thorax is not None and key is not None
    old_qpos = np.fromstring(key.attrib["qpos"], sep=" ")
    assert len(old_qpos) == source.nq == 14
    initial_pos = np.fromstring(thorax.attrib["pos"], sep=" ")
    initial_quat = np.fromstring(thorax.attrib["quat"], sep=" ")
    assert initial_pos.shape == (3,) and initial_quat.shape == (4,)
    ET.SubElement(thorax, "freejoint", name="fly_root")
    key.attrib["qpos"] = " ".join(f"{v:.17g}" for v in np.r_[initial_pos, initial_quat, old_qpos])
    xml = ET.tostring(root, encoding="unicode")
    OUT.mkdir(parents=True, exist_ok=True)
    xml_path = OUT / "free_root.xml"
    xml_path.write_text(xml, encoding="utf-8")
    model, _ = load_model(xml)
    assert model.nq == source.nq + 7 and model.nv == source.nv + 6
    assert model.nu == source.nu and model.ntendon == source.ntendon
    root_joint = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "fly_root")
    thorax_id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "Thorax")
    assert root_joint >= 0 and thorax_id >= 0
    assert model.jnt_type[root_joint] == mj.mjtJoint.mjJNT_FREE
    key_id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_KEY, "default-pose")
    reference = mj.MjData(source)
    mj.mj_resetDataKeyframe(source, reference,
                            mj.mj_name2id(source, mj.mjtObj.mjOBJ_KEY, "default-pose"))
    mj.mj_forward(source, reference)
    trials = {}
    traces = {}
    for label, gravity, steps in (("zero_gravity", False, 1000),
                                  ("source_gravity", True, 1000),
                                  ("source_gravity_2s", True, 20000)):
        variant, _ = load_model(xml)
        if not gravity:
            variant.opt.gravity[:] = 0
        data = mj.MjData(variant)
        mj.mj_resetDataKeyframe(variant, data, key_id)
        mj.mj_forward(variant, data)
        initial_joints = data.qpos[7:].copy()
        np.testing.assert_array_equal(initial_joints, reference.qpos)
        com0 = data.subtree_com[thorax_id].copy()
        trace_root = np.empty((steps + 1, 3))
        trace_com = np.empty((steps + 1, 3))
        trace_contacts = np.empty(steps + 1, dtype=np.int32)
        trace_floor_contacts = np.empty(steps + 1, dtype=np.int32)
        floor = mj.mj_name2id(variant, mj.mjtObj.mjOBJ_GEOM, "floor")
        assert floor >= 0
        trace_root[0] = data.qpos[:3]
        trace_com[0] = data.subtree_com[thorax_id]
        trace_contacts[0] = data.ncon
        trace_floor_contacts[0] = sum(floor in (contact.geom1, contact.geom2)
                                      for contact in data.contact)
        for tick in range(steps):
            data.ctrl[:] = .0001
            mj.mj_step(variant, data)
            assert not any(w.number for w in data.warning)
            assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
            trace_root[tick + 1] = data.qpos[:3]
            trace_com[tick + 1] = data.subtree_com[thorax_id]
            trace_contacts[tick + 1] = data.ncon
            trace_floor_contacts[tick + 1] = sum(floor in (contact.geom1, contact.geom2)
                                                 for contact in data.contact)
        traces[label + "_root_mm"] = trace_root
        traces[label + "_com_mm"] = trace_com
        traces[label + "_contacts"] = trace_contacts
        traces[label + "_floor_contacts"] = trace_floor_contacts
        floor_geom_names = sorted({mj.mj_id2name(variant, mj.mjtObj.mjOBJ_GEOM,
                                                 contact.geom1 if contact.geom2 == floor else contact.geom2)
                                   for contact in data.contact if floor in (contact.geom1, contact.geom2)})
        trials[label] = {"root_initial_mm": trace_root[0].tolist(),
                         "root_final_mm": trace_root[-1].tolist(),
                         "com_initial_mm": com0.tolist(),
                         "com_final_mm": trace_com[-1].tolist(),
                         "maximum_com_displacement_mm": float(np.linalg.norm(trace_com - com0, axis=1).max()),
                         "first_contact_tick": next((int(i) for i in np.flatnonzero(trace_contacts)), None),
                         "first_floor_contact_tick": next((int(i) for i in np.flatnonzero(trace_floor_contacts)), None),
                         "contact_samples": int((trace_contacts > 0).sum()),
                         "floor_contact_samples": int((trace_floor_contacts > 0).sum()),
                         "max_contact_count": int(trace_contacts.max()),
                         "duration_ms": steps * variant.opt.timestep * 1000.,
                         "thorax_up_dot_world_up_final": float(data.xmat[thorax_id].reshape(3, 3)[2, 2]),
                         "floor_contact_geoms_at_end": floor_geom_names}
    assert trials["zero_gravity"]["first_floor_contact_tick"] is None
    assert trials["source_gravity"]["first_floor_contact_tick"] is not None
    assert trials["source_gravity_2s"]["thorax_up_dot_world_up_final"] < -.9
    path = OUT / "traces.npz"
    np.savez_compressed(path, **traces)
    report = {"source_commit": restored["commit"], "source_xml_sha256": MODEL_SHA,
              "free_root_xml_sha256": sha(xml_path), "trace_sha256": sha(path),
              "source_nq": source.nq, "free_nq": model.nq,
              "source_nv": source.nv, "free_nv": model.nv,
              "muscle_actuators": model.nu, "tendons": model.ntendon,
              "author_joint_keyframe_preserved_exactly": True,
              "activation": .0001,
              "trials": trials,
              "scope": "Free six-DOF root diagnostic from published FlyMimic geometry and joint pose; no wings/aerodynamics, seated cabin, validated walking or KSP flight."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(trials, indent=2))


if __name__ == "__main__":
    main()
