"""Identify active presynaptic cells in the passive-tibia full-CNS diagnostic."""

import hashlib
import json

import numpy as np
import pandas as pd

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import graph_arrays


SOURCE = ROOT / "reports/lf_tibia_passive_movement.json"
REPORT = ROOT / "reports/lf_tibia_motor_input_audit.json"
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
EVENTS = ROOT / "data/derived/lf_tibia_passive_movement_v1/positive_angle_half_wave_events.npy"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert sha(EVENTS) == next(x["events_sha256"] for x in source["cases"]
                               if x["case"] == "positive_angle_half_wave")
    ids = np.load(GRAPH / "body_ids.npy", mmap_mode="r")
    counts = np.load(GRAPH / "synapse_counts.npy", mmap_mode="r")
    nt = pd.read_feather(GRAPH / "neurotransmitters.feather").set_index("body")
    nodes = pd.read_feather(GRAPH / "nodes.feather", columns=["bodyId", "type"]).set_index("bodyId")
    n, edges, _, row, col, weight = graph_arrays()
    assert len(ids) == n and len(counts) == edges
    events = np.load(EVENTS)
    assert events.shape == (124, 2)
    motor = 156979
    assert int(ids[motor]) == 815344
    lo, hi = int(row[motor]), int(row[motor + 1])
    active = np.unique(events[:, 1])
    cells = []
    for index in active:
        index = int(index)
        body = int(ids[index])
        mask = col[lo:hi] == index
        cells.append({"graph_index": index, "body_id": body,
                      "type": str(nodes.loc[body, "type"]),
                      "spikes": int(np.sum(events[:, 1] == index)),
                      "predicted_nt": str(nt.loc[body, "consensus_nt"]),
                      "direct_edge_rows_to_motor": int(mask.sum()),
                      "contacts_to_motor": int(counts[lo:hi][mask].sum()),
                      "runtime_weights_to_motor_mv": weight[lo:hi][mask].tolist()})
    assert [item["spikes"] for item in cells] == [15, 2, 107]
    assert [item["contacts_to_motor"] for item in cells] == [0, 0, 5]
    assert [item["runtime_weights_to_motor_mv"] for item in cells] == [[], [], [1.375]]
    result = {"source_report_sha256": sha(SOURCE), "event_sha256": sha(EVENTS),
              "graph_sha256": sha(ROOT / "build/brain_body_graph.bin"),
              "motor_graph_index": motor, "motor_body_id": 815344,
              "labelled_tibia_extensor_incoming": [
                  {"body_id": int(ids[index]), "graph_index": index,
                   "incoming_edge_rows": int(row[index + 1] - row[index]),
                   "incoming_contacts": int(counts[int(row[index]):int(row[index + 1])].sum())}
                  for index in (156979, 157213)],
              "active_cells": cells,
              "mechanism": "Only active direct presynaptic cell to this motor was SNpp50 912317; the two active GABAergic intrinsic cells had no direct motor edge",
              "biological_validation": False}
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cells, indent=2))


if __name__ == "__main__":
    main()
