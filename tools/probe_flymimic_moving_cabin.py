"""Move a named cabin frame carrying the harness and passive foot pad."""
import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml

HARNESS = ROOT / "data/derived/flymimic_harness_v1/harness.xml"
PAD_REPORT = ROOT / "reports/flymimic_harness_contact_local.json"
OUT = ROOT / "data/derived/flymimic_moving_cabin_v1"
REPORT = ROOT / "reports/flymimic_moving_cabin_local.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cabin_xml(base, pad_center, contact):
    tree = ET.fromstring(modified_xml(pad_center, contact, "+1 0 0", base))
    world = tree.find("worldbody")
    slider = world.find("./body[@name='throttle_slider']")
    weld = tree.find("./equality/weld[@name='thorax_cabin_harness']")
    assert slider is not None and weld is not None
    cabin = ET.SubElement(world, "body", name="cabin_frame", mocap="true", pos="0 0 0")
    world.remove(slider)
    cabin.append(slider)
    weld.attrib["body2"] = "cabin_frame"
    return ET.tostring(tree, encoding="unicode")


def main():
    harness_report = json.loads((ROOT / "reports/flymimic_harness_local.json").read_text())
    pad_report = json.loads(PAD_REPORT.read_text())
    assert sha(HARNESS) == harness_report["harness_xml_sha256"]
    assert pad_report["source_harness_xml_sha256"] == sha(HARNESS)
    base = HARNESS.read_text(encoding="utf-8")
    original, _ = load_model(base)
    state = mj.MjData(original)
    mj.mj_resetDataKeyframe(original, state,
                            mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose"))
    for _ in range(20000):
        state.ctrl[:] = .0001
        mj.mj_step(original, state)
    assert not any(w.number for w in state.warning)
    OUT.mkdir(parents=True, exist_ok=True)
    cases, traces = [], {}
    for contact in (False, True):
        xml = cabin_xml(base, pad_report["pad_centers_mm"]["positive_x"], contact)
        xml_path = OUT / f"contact_{int(contact)}.xml"
        xml_path.write_text(xml, encoding="utf-8")
        model, _ = load_model(xml)
        assert model.nq == original.nq + 1 and model.neq == original.neq
        cabin_id = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "cabin_frame")
        mocap = int(model.body_mocapid[cabin_id])
        assert mocap >= 0
        slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
        foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
        pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
        muscle = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
        assert min(slide, foot, pad, muscle) >= 0
        for moving in (False, True):
            for pulse in (False, True):
                data = mj.MjData(model)
                data.qpos[:original.nq] = state.qpos
                data.qvel[:original.nv] = state.qvel
                data.act[:] = state.act
                data.mocap_pos[mocap] = [0., 0., 0.]
                data.mocap_quat[mocap] = [1., 0., 0., 0.]
                mj.mj_forward(model, data)
                slide_q, root_relative, contacts, cabin_z = [], [], [], []
                for tick in range(1000):
                    time = tick * model.opt.timestep
                    z = .05 * (1 - np.cos(2 * np.pi * time / .1)) if moving else 0.
                    data.mocap_pos[mocap] = [0., 0., z]
                    data.ctrl[:] = .0001
                    if pulse and 200 <= tick < 600:
                        data.ctrl[muscle] = 1.
                    mj.mj_step(model, data)
                    assert not any(w.number for w in data.warning)
                    assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                    slide_q.append(float(data.qpos[model.jnt_qposadr[slide]]))
                    root_relative.append((data.qpos[:3] - data.mocap_pos[mocap]).copy())
                    contacts.append(sum({item.geom1, item.geom2} == {foot, pad}
                                        for item in data.contact))
                    cabin_z.append(z)
                label = f"contact_{int(contact)}_moving_{int(moving)}_pulse_{int(pulse)}"
                traces[label + "_slide_mm"] = np.asarray(slide_q)
                traces[label + "_root_relative_mm"] = np.asarray(root_relative)
                traces[label + "_contacts"] = np.asarray(contacts, dtype=np.uint16)
                traces[label + "_cabin_z_mm"] = np.asarray(cabin_z)
                cases.append({"contact": contact, "moving": moving, "pulse": pulse,
                              "exact_contact_samples": int(sum(contacts)),
                              "first_contact_tick": next((i for i, n in enumerate(contacts) if n), None),
                              "peak_slide_mm": float(max(slide_q)),
                              "peak_cabin_z_mm": float(max(cabin_z)),
                              "peak_root_relative_displacement_mm": float(np.max(np.linalg.norm(np.asarray(root_relative)-state.qpos[:3],axis=1))),
                              "xml_sha256": sha(xml_path)})
                if not contact:
                    assert sum(contacts) == 0 and np.all(np.asarray(slide_q) == 0)
    active = next(c for c in cases if c["contact"] and c["moving"] and c["pulse"])
    moving_controls = [c for c in cases if c["moving"] and c is not active]
    assert active["first_contact_tick"] >= 200 and active["exact_contact_samples"] > 0
    assert all(c["exact_contact_samples"] == 0 and c["peak_slide_mm"] == 0
               for c in moving_controls)
    assert np.all(traces["contact_1_moving_1_pulse_1_slide_mm"][:active["first_contact_tick"]] == 0)
    earlier_path = ROOT / "data/derived/flymimic_harness_contact_v1/traces.npz"
    with np.load(earlier_path) as earlier:
        static_replays_exactly = np.array_equal(
            traces["contact_1_moving_0_pulse_1_slide_mm"],
            earlier["positive_x_contact_1_pulse_1_slide_mm"])
    assert static_replays_exactly
    path = OUT / "traces.npz"
    np.savez_compressed(path, **traces)
    report = {"harness_xml_sha256": sha(HARNESS), "pad_report_sha256": sha(PAD_REPORT),
              "source_initial_root_qpos": state.qpos[:7].tolist(),
              "cabin_frame": "mocap body; prescribed z(t)=0.05*(1-cos(2*pi*t/0.1)) mm over 100 ms",
              "pad_is_cabin_child": True, "harness_weld_body2": "cabin_frame",
              "causal_checks": {"moving_three_controls_zero": True,
                                "moving_slide_zero_before_contact": True,
                                "static_replays_prior_harness_slide_exactly": static_replays_exactly},
              "cases": cases, "trace_sha256": sha(path),
              "scope": "Moving cabin frame with explicit harness/pad mechanics; prescribed motion, artificial muscle pulse, no neural control, rocket dynamics, or KSP."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
