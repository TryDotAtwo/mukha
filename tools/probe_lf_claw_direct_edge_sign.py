"""Replay a frozen diagnostic drive while varying one SNpp50->motor edge.

This is an assumption sensitivity check, not a receptor or reflex measurement.
"""

import ctypes as ct
import hashlib
import json
from pathlib import Path

import numpy as np

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda


SPEC = ROOT / "configs/lf_claw_closed_loop_keyframe_probe.json"
SOURCE_REPORT = ROOT / "reports/lf_claw_closed_loop_keyframe_local.json"
SOURCE_DIR = ROOT / "data/derived/lf_claw_closed_loop_keyframe_v1"
OUT = ROOT / "data/derived/lf_claw_direct_edge_sign_v1"
REPORT = ROOT / "reports/lf_claw_direct_edge_sign.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    source_report = json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))
    assert sha(SPEC) == source_report["spec_sha256"]
    assert sha(SOURCE_DIR / "traces.npz") == source_report["trace_sha256"]
    archived_events = SOURCE_DIR / "negative_position_events.npy"
    assert sha(archived_events) == next(case["event_sha256"] for case in source_report["cases"]
                                         if case["case"] == "negative_position")
    with np.load(SOURCE_DIR / "traces.npz") as traces:
        sensor_drive = traces["negative_position_sensor_drive_mv"].copy()
    assert len(sensor_drive) == spec["ticks"] and np.isfinite(sensor_drive).all()

    n, edge_count, source, row, col, original_weight = graph_arrays()
    assert sha(ROOT / "build/brain_body_graph.bin") == source_report["graph_sha256"]
    assert spec["sensor_graph_index"] == 164105 and spec["motor_graph_index"] == 156979
    lo, hi = int(row[spec["motor_graph_index"]]), int(row[spec["motor_graph_index"] + 1])
    positions = np.flatnonzero(col[lo:hi] == spec["sensor_graph_index"]) + lo
    assert len(positions) == 1 and original_weight[positions].tolist() == [1.375]

    lib, directory = load_cuda()
    sensory = np.zeros(n, dtype=np.uint8)
    sensory[source] = 1
    drive = np.zeros(n, dtype=np.float64)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)
    OUT.mkdir(parents=True)
    summaries = []
    try:
        for name, direct_weight in (("as_archived", 1.375), ("edge_silenced", 0.0),
                                    ("edge_reversed", -1.375)):
            weights = original_weight.copy()
            weights[positions] = direct_weight
            brain = lib.ff_cuda64_create(n, edge_count, row.ctypes.data, col.ctypes.data,
                                         weights.ctypes.data, sensory.ctypes.data,
                                         Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
            if not brain:
                raise RuntimeError(lib.ff_cuda64_probe_error())
            events = []
            motor_ticks = []
            sensor_ticks = []
            try:
                for tick, sensor_mv in enumerate(sensor_drive):
                    drive.fill(0)
                    drive[source] = (spec["source_voltage_jump_mv"]
                                     if tick % spec["source_stimulus_every_ticks"] == 0 else 0)
                    drive[spec["sensor_graph_index"]] = sensor_mv
                    if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data, voltage.ctypes.data,
                                             synapse.ctypes.data, spikes.ctypes.data):
                        raise RuntimeError(lib.ff_cuda64_probe_error())
                    fired = np.flatnonzero(spikes)
                    events.extend((tick, int(index)) for index in fired)
                    if spikes[spec["motor_graph_index"]]:
                        motor_ticks.append(tick)
                    if spikes[spec["sensor_graph_index"]]:
                        sensor_ticks.append(tick)
            finally:
                lib.ff_cuda64_destroy(brain)
            event_array = np.asarray(events, dtype=np.uint32).reshape(-1, 2)
            path = OUT / f"{name}_events.npy"
            np.save(path, event_array)
            if name == "as_archived":
                assert np.array_equal(event_array, np.load(archived_events))
            summaries.append({"variant": name, "direct_weight_mv": direct_weight,
                              "events": len(events), "sensor_spike_ticks": sensor_ticks,
                              "motor_spike_ticks": motor_ticks,
                              "events_sha256": sha(path)})
    finally:
        directory.close()

    baseline = np.load(OUT / "as_archived_events.npy")
    for summary in summaries[1:]:
        changed = np.load(OUT / f"{summary['variant']}_events.npy")
        baseline_pairs = set(map(tuple, baseline.tolist()))
        changed_pairs = set(map(tuple, changed.tolist()))
        delta = baseline_pairs ^ changed_pairs
        summary["first_event_difference_tick"] = min((tick for tick, _ in delta), default=None)
        summary["all_events_identical_to_archived"] = not delta
    report = {"scope": "Frozen full-CNS neural replay under one edge-weight intervention; no body replay, receptor evidence or biological validation",
              "spec_sha256": sha(SPEC), "source_report_sha256": sha(SOURCE_REPORT),
              "source_trace_sha256": source_report["trace_sha256"],
              "source_events_sha256": sha(archived_events),
              "runtime_graph_sha256": source_report["graph_sha256"],
              "presynaptic_body_id": 912317, "postsynaptic_body_id": 815344,
              "presynaptic_graph_index": spec["sensor_graph_index"],
              "postsynaptic_graph_index": spec["motor_graph_index"],
              "original_edge_rows": positions.tolist(), "archived_baseline_exact": True,
              "variants": summaries, "biological_gate_passed": False}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"variants": [{key: item[key] for key in
                                   ("variant", "events", "motor_spike_ticks")}
                                   for item in summaries]}, indent=2))


if __name__ == "__main__":
    main()
