"""Compare full-CNS dynamics for a source-bound Dm9 direct-effect sign variant.

The Dm9 voltage pulses are artificial and serve only as a graph sensitivity
experiment. No visual or behavioral response is claimed.
"""

import hashlib
import json

import numpy as np
import pandas as pd

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import DLL, GRAPH, Parameters, graph_arrays, load_cuda


PATCH = ROOT / "data/derived/dm9_direct_support_variant_v1/csr_edge_offsets.npy"
PATCH_REPORT = ROOT / "reports/dm9_direct_support_variant.json"
SOURCE_EDGES = ROOT / "data/derived/dm9_physiology_evidence_v1/visual_edge_evidence.feather"
OUT = ROOT / "data/derived/dm9_direct_support_probe_v1"
REPORT = ROOT / "reports/dm9_direct_support_probe.json"
TICKS = 1000
CHUNK = 20


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    patch_report = json.loads(PATCH_REPORT.read_text(encoding="utf-8"))
    assert sha(PATCH) == patch_report["csr_edge_offsets_sha256"]
    assert sha(GRAPH) == patch_report["baseline_graph_sha256"]
    assert sha(SOURCE_EDGES) == patch_report["source_evidence_sha256"]
    offsets = np.load(PATCH)
    edges = pd.read_feather(SOURCE_EDGES)
    selected = edges[edges.evidence_family.eq("dm9_to_inner")]
    assert np.array_equal(offsets, selected.csr_edge_index.to_numpy())
    source_contacts = selected.groupby("pre_graph_index").synapse_count.sum()
    source = int(source_contacts.idxmax())
    source_edges = selected[selected.pre_graph_index.eq(source)]
    target = int(source_edges.loc[source_edges.synapse_count.idxmax(), "post_graph_index"])
    target_body = int(source_edges.loc[source_edges.synapse_count.idxmax(), "post_body_id"])
    source_body = int(source_edges.iloc[0].pre_body_id)
    n, total, _, row, col, original = graph_arrays()
    assert np.array_equal(col[offsets], selected.pre_graph_index.to_numpy(dtype=np.uint32))
    assert row[target] <= int(source_edges.loc[source_edges.synapse_count.idxmax(), "csr_edge_index"]) < row[target + 1]
    lib, directory = load_cuda()
    sensory = np.zeros(n, dtype=np.uint8)
    drive = np.zeros((CHUNK, n), dtype=np.float64)
    voltage = np.empty_like(drive)
    synapse = np.empty_like(drive)
    spikes = np.empty((CHUNK, n), dtype=np.uint8)
    OUT.mkdir(parents=True)
    results = []
    try:
        for variant in ("baseline", "dm9_direct_support"):
            weights = original.copy()
            if variant == "dm9_direct_support":
                weights[offsets] *= -1
            brain = lib.ff_cuda64_create(n, total, row.ctypes.data, col.ctypes.data,
                                         weights.ctypes.data, sensory.ctypes.data,
                                         Parameters(.1, -52, -52, -45, 20, 5, 22, 18), CHUNK)
            if not brain:
                raise RuntimeError(lib.ff_cuda64_probe_error())
            events = []
            source_voltage = np.empty(TICKS, dtype=np.float64)
            target_voltage = np.empty(TICKS, dtype=np.float64)
            try:
                for tick in range(0, TICKS, CHUNK):
                    drive.fill(0)
                    for local in range(CHUNK):
                        if (tick + local) % 100 == 0:
                            drive[local, source] = 68.75
                    if lib.ff_cuda64_advance(brain, CHUNK, drive.ctypes.data,
                                             voltage.ctypes.data, synapse.ctypes.data,
                                             spikes.ctypes.data):
                        raise RuntimeError(lib.ff_cuda64_probe_error())
                    assert np.isfinite(voltage).all() and np.isfinite(synapse).all()
                    ts, ix = np.nonzero(spikes)
                    events.append(np.column_stack((ts + tick, ix)).astype(np.uint32))
                    source_voltage[tick:tick + CHUNK] = voltage[:, source]
                    target_voltage[tick:tick + CHUNK] = voltage[:, target]
            finally:
                lib.ff_cuda64_destroy(brain)
            all_events = np.concatenate(events)
            events_path = OUT / f"{variant}_events.npy"
            voltage_path = OUT / f"{variant}_voltages.npz"
            np.save(events_path, all_events)
            np.savez_compressed(voltage_path, source_mv=source_voltage,
                                target_mv=target_voltage)
            results.append({"variant": variant,
                            "weights_sha256": hashlib.sha256(weights.tobytes()).hexdigest(),
                            "events_sha256": sha(events_path), "voltages_sha256": sha(voltage_path),
                            "all_spikes": len(all_events),
                            "source_spike_ticks": all_events[all_events[:, 1] == source, 0].tolist(),
                            "target_spike_ticks": all_events[all_events[:, 1] == target, 0].tolist(),
                            "target_voltage_min_mv": float(target_voltage.min()),
                            "target_voltage_max_mv": float(target_voltage.max())})
    finally:
        directory.close()
    a = np.load(OUT / "baseline_voltages.npz")["target_mv"]
    b = np.load(OUT / "dm9_direct_support_voltages.npz")["target_mv"]
    ev_a = np.load(OUT / "baseline_events.npy")
    ev_b = np.load(OUT / "dm9_direct_support_events.npy")
    differing = set(map(tuple, ev_a.tolist())) ^ set(map(tuple, ev_b.tolist()))
    report = {"scope": "Full native CNS diagnostic sensitivity to a sparse Dm9 direct-effect sign alternative",
              "patch_report_sha256": sha(PATCH_REPORT), "graph_sha256": sha(GRAPH),
              "library_sha256": sha(DLL), "source_graph_index": source,
              "source_body_id": source_body, "target_graph_index": target,
              "target_body_id": target_body,
              "selection": "Dm9 with maximum source contacts to named R7/R8; its highest-contact target",
              "input": "68.75-mV artificial voltage jump to Dm9 every 10 ms, for 100 ms",
              "dt_ms": 0.1, "ticks": TICKS, "variants": results,
              "max_abs_target_voltage_difference_mv": float(np.max(np.abs(a - b))),
              "first_target_voltage_difference_tick": int(np.flatnonzero(a != b)[0]) if np.any(a != b) else None,
              "first_event_difference_tick": min((int(t) for t, _ in differing), default=None),
              "biological_validation": False,
              "limitations": ["Artificial central Dm9 input, not photon-driven visual response",
                              "Source effect evidence comes from female calcium recordings",
                              "Direct receptor and uniform voltage scale remain uncalibrated"]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_body_id": source_body, "target_body_id": target_body,
                      "max_abs_target_voltage_difference_mv": report["max_abs_target_voltage_difference_mv"],
                      "first_event_difference_tick": report["first_event_difference_tick"],
                      "variants": [{"name": r["variant"], "spikes": r["all_spikes"],
                                    "target_spikes": r["target_spike_ticks"]} for r in results]}, indent=2))


if __name__ == "__main__":
    main()
