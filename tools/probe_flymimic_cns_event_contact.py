"""Hypothetical recorded full-CNS event to FlyMimic muscle/contact replay."""
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml

SOURCE = ROOT / "data/derived/malecns_sign_diagnostic_float64_v2"
OUT = ROOT / "data/derived/flymimic_cns_event_contact_v1"
REPORT = ROOT / "reports/flymimic_cns_event_contact_local.json"
MOTOR_INDEX = 156979
OTHER_INDEX = 157213
GAIN = .1
TAU_MS = 20.
DT_MS = .1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = json.loads((SOURCE / "spec.json").read_text())
    assert spec["steps"] == 1000 and spec["dt_ms"] == DT_MS
    assert not spec["biological_validation"] and not spec["brain_body_connected"]
    pad_report = json.loads((ROOT / "reports/flymimic_passive_throttle_local.json").read_text())
    original, _ = load_model()
    relaxed = mj.MjData(original)
    for _ in range(20000):
        relaxed.ctrl[:] = .0001
        mj.mj_step(original, relaxed)
    assert not any(w.number for w in relaxed.warning)
    OUT.mkdir(parents=True, exist_ok=True)
    traces, cases, event_sources = {}, [], {}
    for variant in ("unclear_excitatory", "unclear_inhibitory"):
        path = SOURCE / f"{variant}_events.npy"
        events = np.load(path)
        assert events.ndim == 2 and events.shape[1] == 2 and events.dtype == np.uint32
        motor_ticks = events[events[:, 1] == MOTOR_INDEX, 0].astype(int).tolist()
        other_ticks = events[events[:, 1] == OTHER_INDEX, 0].astype(int).tolist()
        assert motor_ticks[0] == 190 and len(motor_ticks) == 2 and other_ticks == []
        event_sources[variant] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                                  "sha256": sha(path), "motor_ticks": motor_ticks,
                                  "other_candidate_ticks": other_ticks}
        filtered = np.zeros(1000)
        level = 0.
        for tick in range(1000):
            level *= np.exp(-DT_MS / TAU_MS)
            level += GAIN * motor_ticks.count(tick)
            filtered[tick] = min(1., max(.0001, level))
        independent = np.asarray([min(1., max(.0001, GAIN * sum(
            np.exp(-(tick - event) * DT_MS / TAU_MS)
            for event in motor_ticks if event <= tick))) for tick in range(1000)])
        np.testing.assert_allclose(filtered, independent, rtol=0, atol=1e-15)
        for contact in (False, True):
            model, _ = load_model(modified_xml(pad_report["pad_center_mm"], contact))
            slide = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "throttle_slide")
            pad = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "throttle_pad")
            foot = mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom")
            knee = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "joint_LFTibia_pitch")
            actuator = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "LFTibia_extensor_93932")
            for connected in (False, True):
                data = mj.MjData(model)
                data.qpos[:original.nq] = relaxed.qpos
                data.qvel[:original.nv] = relaxed.qvel
                data.act[:] = relaxed.act
                mj.mj_forward(model, data)
                slide_trace, knee_trace, contacts, controls = [], [], [], []
                for tick in range(1000):
                    data.ctrl[:] = .0001
                    if connected:
                        data.ctrl[actuator] = filtered[tick]
                    controls.append(float(data.ctrl[actuator]))
                    mj.mj_step(model, data)
                    assert not any(w.number for w in data.warning)
                    assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                    slide_trace.append(float(data.qpos[model.jnt_qposadr[slide]]))
                    knee_trace.append(float(data.qpos[model.jnt_qposadr[knee]]))
                    contacts.append(sum({c.geom1, c.geom2} == {foot, pad} for c in data.contact))
                label = f"{variant}_contact_{int(contact)}_motor_{int(connected)}"
                traces[label + "_slide_mm"] = np.asarray(slide_trace)
                traces[label + "_knee_rad"] = np.asarray(knee_trace)
                traces[label + "_contacts"] = np.asarray(contacts)
                traces[label + "_control"] = np.asarray(controls)
                cases.append({"variant": variant, "contact": contact, "motor_connected": connected,
                              "exact_contact_samples": int(sum(contacts)),
                              "first_contact_tick": next((i for i, n in enumerate(contacts) if n), None),
                              "max_slide_mm": float(max(slide_trace)),
                              "max_control": float(max(controls))})
        for case in cases[-4:]:
            if not (case["contact"] and case["motor_connected"]):
                assert case["exact_contact_samples"] == 0 and case["max_slide_mm"] == 0
        base = traces[f"{variant}_contact_0_motor_0_knee_rad"][:190]
        for key, value in traces.items():
            if key.startswith(variant) and key.endswith("_knee_rad"):
                np.testing.assert_array_equal(base, value[:190])
    trace_path = OUT / "traces.npz"
    np.savez_compressed(trace_path, **traces)
    report = {"source_spec_sha256": sha(SOURCE / "spec.json"),
              "event_sources": event_sources, "motor_graph_index": MOTOR_INDEX,
              "other_candidate_graph_index": OTHER_INDEX,
              "filter": {"gain_per_spike": GAIN, "tau_ms": TAU_MS,
                         "dt_ms": DT_MS, "clamp": [.0001, 1.]},
              "cases": cases, "pre_first_event_knee_identical": True,
              "trace_sha256": sha(trace_path),
              "scope": "Recorded full-graph artificial-drive CNS events through hypothetical motor-to-muscle assignment; no biological validation, sensory loop, rocket feedback or KSP landing."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
