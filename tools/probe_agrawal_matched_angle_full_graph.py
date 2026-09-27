"""Matched-angle opposite-history full MaleCNS diagnostic, not biological fit."""
import hashlib
import json
from pathlib import Path

import numpy as np

from probe_live_cns_flymimic import DLL, GRAPH, Parameters, graph_arrays, load_cuda
from flymimic_public_model import ROOT


SPEC = ROOT / "configs/lf_tibia_passive_movement_probe.json"
REPORT = ROOT / "reports/agrawal_matched_angle_full_graph.json"
DT_MS = 0.1
HISTORY_TICKS = 1000
HOLD_TICKS = 3000
SAMPLE_HOLD_MS = (0, 20, 100, 300)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    n, edges, _, row, col, weight = graph_arrays()
    ids = np.load(ROOT / "data/derived/malecns_v1_candidates/body_ids.npy")
    assert len(ids) == n and ids[spec["sensor_graph_index"]] == spec["sensor_body_id"]
    candidate_report = json.loads((ROOT / "reports/agrawal_13b_connectivity.json").read_text())
    body_ids = [x["bodyId"] for x in candidate_report["candidates"]
                if x["snpp50_51_front_leg_edge_rows"]]
    candidate_indices = np.flatnonzero(np.isin(ids, body_ids))
    assert len(candidate_indices) == 13
    lib, directory = load_cuda()
    sensory = np.zeros(n, np.uint8)
    p = Parameters(DT_MS, -52, -52, -45, 20, 5, 22, 18)
    snapshots = {}
    try:
        for label, history_angle_deg in (("extension_history", 10.0),
                                         ("flexion_history", -10.0)):
            brain = lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                         weight.ctypes.data, sensory.ctypes.data, p, 1)
            if not brain:
                raise RuntimeError(lib.ff_cuda64_probe_error())
            drive = np.zeros(n, np.float64)
            voltage = np.empty(n, np.float64)
            synapse = np.empty(n, np.float64)
            spikes = np.empty(n, np.uint8)
            total_events = 0
            source_events = 0
            candidate_events = 0
            recorded = {}
            try:
                for tick in range(HISTORY_TICKS + HOLD_TICKS + 1):
                    angle = np.deg2rad(history_angle_deg) if tick < HISTORY_TICKS else 0.0
                    drive[spec["sensor_graph_index"]] = (
                        spec["sensor_gain_mv_per_rad"] * max(0.0, angle))
                    if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data,
                                             voltage.ctypes.data, synapse.ctypes.data,
                                             spikes.ctypes.data):
                        raise RuntimeError(lib.ff_cuda64_probe_error())
                    total_events += int(np.count_nonzero(spikes))
                    source_events += int(spikes[spec["sensor_graph_index"]])
                    candidate_events += int(np.count_nonzero(spikes[candidate_indices]))
                    hold_tick = tick - HISTORY_TICKS
                    if hold_tick in (0, 200, 1000, 3000):
                        recorded[str(hold_tick * DT_MS)] = {
                            "voltage": voltage.copy(), "synapse": synapse.copy(),
                            "spikes": spikes.copy()}
            finally:
                lib.ff_cuda64_destroy(brain)
            snapshots[label] = recorded
            snapshots[label + "_counts"] = {
                "all_events": total_events, "source_events": source_events,
                "candidate_events": candidate_events}
            print(label, snapshots[label + "_counts"], flush=True)
    finally:
        directory.close()
    a = snapshots["extension_history"]
    b = snapshots["flexion_history"]
    comparisons = []
    for ms in SAMPLE_HOLD_MS:
        key = str(ms * 1.0)
        av, bv = a[key]["voltage"], b[key]["voltage"]
        ag, bg = a[key]["synapse"], b[key]["synapse"]
        comparisons.append({
            "hold_ms": ms,
            "different_voltage_cells": int(np.count_nonzero(av != bv)),
            "maximum_voltage_difference_mv": float(np.max(np.abs(av - bv))),
            "different_synaptic_cells": int(np.count_nonzero(ag != bg)),
            "maximum_synaptic_difference_mv": float(np.max(np.abs(ag - bg))),
            "candidate_13b_voltage_differences_mv": [
                float(v) for v in (av - bv)[candidate_indices]],
            "source_voltage_difference_mv": float(
                av[spec["sensor_graph_index"]] - bv[spec["sensor_graph_index"]]),
            "event_count_extension": int(np.count_nonzero(a[key]["spikes"])),
            "event_count_flexion": int(np.count_nonzero(b[key]["spikes"]))})
    report = {
        "scope": "full native graph, two opposite angle histories with matched final angle; uncalibrated positive-half-wave single-cell encoder",
        "graph_sha256": sha(GRAPH), "dll_sha256": sha(DLL),
        "encoder_spec_sha256": sha(SPEC),
        "history_ms": HISTORY_TICKS * DT_MS, "hold_ms": HOLD_TICKS * DT_MS,
        "history_angles_deg": {"extension_history": 10.0, "flexion_history": -10.0},
        "common_hold_angle_deg": 0.0, "candidate_body_ids": body_ids,
        "event_counts": {name: snapshots[name + "_counts"] for name in
                         ("extension_history", "flexion_history")},
        "comparisons": comparisons,
        "biological_13b_identity_approved": False,
        "agrawal_protocol_reproduced": False,
        "biological_reaction_reproduced": False,
        "limitations": [
            "The current single-cell rectified angle-to-voltage encoder has unmeasured gain, polarity and cell identity.",
            "The 100-ms history and 300-ms hold do not reproduce the paper's 3-s ramp-and-hold protocol.",
            "These IN13B graph candidates have no approved individual 13Balpha crosswalk.",
            "Voltages and synaptic state are uniform LIF diagnostics, not recorded graded membrane potentials."]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparisons), flush=True)


if __name__ == "__main__":
    main()
