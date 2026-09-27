"""Advance the full native MaleCNS graph live with physical FlyMimic controls.

Artificial voltage-jump input and neuron-to-muscle filter are diagnostics,
not validated sensory or motor physiology.
"""
import argparse
import ctypes as ct
import hashlib
import json
import os
import struct

import numpy as np

from flymimic_public_model import ROOT, load_model, mj
from probe_flymimic_passive_throttle import modified_xml

GRAPH = ROOT / "build/brain_body_graph.bin"
DLL = ROOT / "build/fly_cuda64.dll"
EVENTS = ROOT / "data/derived/malecns_sign_diagnostic_float64_v2/unclear_excitatory_events.npy"
OUT = ROOT / "data/derived/live_cns_flymimic_v1"
REPORT = ROOT / "reports/live_cns_flymimic_local.json"
KEYFRAME_OUT = ROOT / "data/derived/live_cns_flymimic_keyframe_v1"
KEYFRAME_REPORT = ROOT / "reports/live_cns_flymimic_keyframe_local.json"


class Parameters(ct.Structure):
    _fields_ = [(name, ct.c_double) for name in ("dt_ms", "rest_mv", "reset_mv",
                 "threshold_mv", "membrane_ms", "synapse_ms")] + [
                 ("refractory_ticks", ct.c_uint32), ("delay_ticks", ct.c_uint32)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph_arrays():
    with GRAPH.open("rb") as stream:
        n, edges, source = struct.unpack("<IQI", stream.read(16))
        assert (n, edges) == (167216, 25587572) and source < n
        row = np.fromfile(stream, dtype="<u8", count=n + 1)
        col = np.fromfile(stream, dtype="<u4", count=edges)
        weight = np.fromfile(stream, dtype="<f8", count=edges)
        assert stream.read(1) == b""
    assert row[-1] == edges and len(col) == len(weight) == edges
    return n, edges, source, row, col, weight


def load_cuda():
    directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
    lib = ct.CDLL(str(DLL))
    lib.ff_cuda64_create.argtypes = [ct.c_uint32, ct.c_uint64, ct.c_void_p,
                                     ct.c_void_p, ct.c_void_p, ct.c_void_p,
                                     Parameters, ct.c_uint32]
    lib.ff_cuda64_create.restype = ct.c_void_p
    lib.ff_cuda64_destroy.argtypes = [ct.c_void_p]
    lib.ff_cuda64_advance.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_void_p,
                                      ct.c_void_p, ct.c_void_p, ct.c_void_p]
    lib.ff_cuda64_advance.restype = ct.c_int
    lib.ff_cuda64_probe_error.restype = ct.c_char_p
    return lib, directory


def main(steps, keyframe_derived=False):
    n, edges, source, row, col, weight = graph_arrays()
    lib, directory = load_cuda()
    sensory = np.zeros(n, dtype=np.uint8)
    sensory[source] = 1
    model = lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                 weight.ctypes.data, sensory.ctypes.data,
                                 Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
    if not model:
        raise RuntimeError(lib.ff_cuda64_probe_error())
    try:
        pad_source = ("reports/flymimic_keyframe_contact_local.json" if keyframe_derived
                      else "reports/flymimic_passive_throttle_local.json")
        pad_report = json.loads((ROOT / pad_source).read_text())
        original, _ = load_model()
        relaxed = mj.MjData(original)
        if keyframe_derived:
            keyframe = mj.mj_name2id(original, mj.mjtObj.mjOBJ_KEY, "default-pose")
            assert keyframe >= 0
            mj.mj_resetDataKeyframe(original, relaxed, keyframe)
        else:
            mj.mj_resetData(original, relaxed)
        for _ in range(20000):
            relaxed.ctrl[:] = .0001
            mj.mj_step(original, relaxed)
        assert not any(w.number for w in relaxed.warning)
        bodies = []
        pad_position = (pad_report["geometry"]["keyframe_passive_2s"]["positive_x_pad_center_mm"]
                        if keyframe_derived else pad_report["pad_center_mm"])
        axis = "+1 0 0" if keyframe_derived else "-1 0 0"
        for contact in (False, True):
            physical, _ = load_model(modified_xml(pad_position, contact, axis))
            for connected in (False, True):
                state = mj.MjData(physical)
                state.qpos[:original.nq] = relaxed.qpos
                state.qvel[:original.nv] = relaxed.qvel
                state.act[:] = relaxed.act
                mj.mj_forward(physical, state)
                bodies.append((contact, connected, physical, state,
                               mj.mj_name2id(physical, mj.mjtObj.mjOBJ_JOINT, "throttle_slide"),
                               mj.mj_name2id(physical, mj.mjtObj.mjOBJ_GEOM, "LFTarsus5_geom"),
                               mj.mj_name2id(physical, mj.mjtObj.mjOBJ_GEOM, "throttle_pad"),
                               mj.mj_name2id(physical, mj.mjtObj.mjOBJ_ACTUATOR,
                                             "LFTibia_extensor_93932")))
        drive = np.zeros(n, dtype=np.float64)
        voltage = np.empty(n, dtype=np.float64)
        synapse = np.empty(n, dtype=np.float64)
        spikes = np.empty(n, dtype=np.uint8)
        events = []
        traces = {f"contact_{int(c)}_motor_{int(m)}_{suffix}": []
                  for c, m, *_ in bodies for suffix in ("slide_mm", "contacts", "control")}
        level = 0.
        for tick in range(steps):
            drive[source] = 68.75 if tick % 100 == 0 else 0.
            status = lib.ff_cuda64_advance(model, 1, drive.ctypes.data, voltage.ctypes.data,
                                           synapse.ctypes.data, spikes.ctypes.data)
            if status:
                raise RuntimeError(lib.ff_cuda64_probe_error())
            assert np.isfinite(voltage).all() and np.isfinite(synapse).all()
            fired = np.flatnonzero(spikes)
            events.extend((tick, int(index)) for index in fired)
            level *= np.exp(-.1 / 20.)
            level += .1 * int(spikes[156979])
            control = min(1., max(.0001, level))
            for contact, connected, physical, state, slide, foot, pad, actuator in bodies:
                state.ctrl[:] = .0001
                if connected:
                    state.ctrl[actuator] = control
                mj.mj_step(physical, state)
                assert not any(w.number for w in state.warning)
                key = f"contact_{int(contact)}_motor_{int(connected)}_"
                traces[key + "slide_mm"].append(float(state.qpos[physical.jnt_qposadr[slide]]))
                traces[key + "contacts"].append(sum({item.geom1, item.geom2} == {foot, pad}
                                                       for item in state.contact))
                traces[key + "control"].append(float(state.ctrl[actuator]))
        live_events = np.asarray(events, dtype=np.uint32).reshape(-1, 2)
        reference = np.load(EVENTS)
        reference_prefix = reference[reference[:, 0] < steps]
        exact = np.array_equal(live_events, reference_prefix)
        assert exact, "Live full-graph events diverged from pinned reference"
        offline_trace_path = ROOT / "data/derived/flymimic_cns_event_contact_v1/traces.npz"
        body_exact = None
        if not keyframe_derived:
            with np.load(offline_trace_path) as offline:
                body_exact = all(np.array_equal(np.asarray(values),
                                               offline["unclear_excitatory_" + key][:steps])
                                 for key, values in traces.items())
            assert body_exact, "Live body traces diverged from pinned event replay"
        out = KEYFRAME_OUT if keyframe_derived else OUT
        report_path = KEYFRAME_REPORT if keyframe_derived else REPORT
        out.mkdir(parents=True, exist_ok=True)
        event_path = out / "events.npy"
        trace_path = out / "traces.npz"
        np.save(event_path, live_events)
        np.savez_compressed(trace_path, **{key: np.asarray(value) for key, value in traces.items()})
        cases = []
        for contact, connected, *_ in bodies:
            key = f"contact_{int(contact)}_motor_{int(connected)}_"
            cases.append({"contact": contact, "motor_connected": connected,
                          "exact_contact_samples": int(sum(traces[key + "contacts"])),
                          "max_slide_mm": float(max(traces[key + "slide_mm"])),
                          "max_control": float(max(traces[key + "control"]))})
        causal_checks = None
        if keyframe_derived:
            active_key = "contact_1_motor_1_"
            contacts_active = np.asarray(traces[active_key + "contacts"])
            slide_active = np.asarray(traces[active_key + "slide_mm"])
            first_contact = int(np.flatnonzero(contacts_active)[0])
            first_slide = int(np.flatnonzero(slide_active)[0])
            motor_ticks = live_events[live_events[:, 1] == 156979, 0]
            assert len(motor_ticks) and int(motor_ticks[0]) < first_contact
            assert first_slide >= first_contact and np.all(slide_active[:first_contact] == 0)
            assert all(c["exact_contact_samples"] == 0 and c["max_slide_mm"] == 0
                       for c in cases if not (c["contact"] and c["motor_connected"]))
            assert np.array_equal(np.asarray(traces[active_key + "control"][:int(motor_ticks[0])]),
                                  np.asarray(traces["contact_1_motor_0_control"][:int(motor_ticks[0])]))
            causal_checks = {"first_contact_tick": first_contact, "first_slide_tick": first_slide,
                             "motor_precedes_contact": True, "slide_zero_before_contact": True,
                             "all_three_controls_zero": True}
        report = {"steps": steps, "graph_nodes": n, "graph_edges": edges,
                  "initial_pose": "default-pose then 20000 passive steps" if keyframe_derived
                                  else "zero reset then 20000 passive steps",
                  "pad_source": pad_source, "pad_center_mm": pad_position, "slide_axis": axis,
                  "source_index": source, "full_event_trace_matches_prior": exact,
                  "physical_traces_match_offline_event_replay": body_exact,
                  "live_event_count": len(live_events), "reference_event_count": len(reference_prefix),
                  "motor_event_ticks": live_events[live_events[:, 1] == 156979, 0].tolist(),
                  "causal_checks": causal_checks,
                  "cases": cases, "mujoco_version": mj.__version__,
                  "hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                             for path in ((GRAPH, DLL, EVENTS, ROOT / pad_source,
                                           event_path, trace_path) if keyframe_derived
                                          else (GRAPH, DLL, EVENTS, offline_trace_path,
                                                event_path, trace_path))},
                  "scope": "Live full native FP64 MaleCNS to physical FlyMimic diagnostic; artificial voltage jumps and hypothetical motor-to-muscle filter, no natural sensory loop or validated pilot."}
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: report[key] for key in ("steps", "full_event_trace_matches_prior",
                                                 "live_event_count", "motor_event_ticks", "cases")}, indent=2))
    finally:
        lib.ff_cuda64_destroy(model)
        directory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--keyframe-derived", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.steps <= 1000:
        parser.error("steps must be 1..1000")
    main(args.steps, args.keyframe_derived)
