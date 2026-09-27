"""Count source-graph paths from left-front chordotonal candidates to motor.

Anatomical reachability only; no sensory encoder or physiological sign.
"""
import hashlib
import json
import struct

import numpy as np
import pandas as pd

from flymimic_public_model import ROOT

GRAPH = ROOT / "data/derived/malecns_v1_candidates"
CANDIDATES = ROOT / "data/derived/proprioceptive_candidates_v1/nodes.feather"
NEUROTRANSMITTERS = GRAPH / "neurotransmitters.feather"
RAW_ANNOTATIONS = ROOT / "data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather"
REPORT = ROOT / "reports/lf_proprio_motor_paths.json"
DIAGNOSTIC = ROOT / "data/derived/malecns_sign_diagnostic_float64_v2/report.json"
RUNTIME_GRAPH = ROOT / "build/brain_body_graph.bin"
MOTOR_BODY = 815344
MOTOR_INDEX = 156979


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ids = np.load(GRAPH / "body_ids.npy", mmap_mode="r")
    row = np.load(GRAPH / "indptr.npy", mmap_mode="r")
    col = np.load(GRAPH / "indices.npy", mmap_mode="r")
    counts = np.load(GRAPH / "synapse_counts.npy", mmap_mode="r")
    assert int(ids[MOTOR_INDEX]) == MOTOR_BODY
    assert row[-1] == len(col) == len(counts) and len(ids) + 1 == len(row)
    nodes = pd.read_feather(CANDIDATES)
    raw = pd.read_feather(RAW_ANNOTATIONS,
                          columns=["bodyId", "type", "class", "subclass", "entryNerve", "rootSide"])
    raw_chordotonal = raw[raw["subclass"] == "chordotonal organ"]
    raw_by_leg = [
        {"entry_nerve": str(nerve), "root_side": str(side), "cells": int(len(group))}
        for (nerve, side), group in raw_chordotonal.groupby(["entryNerve", "rootSide"])
        if nerve in ("ProLN", "MesoLN", "MetaLN")
    ]
    raw_left_front = raw_chordotonal[(raw_chordotonal["entryNerve"] == "ProLN") &
                                     (raw_chordotonal["rootSide"] == "L")]
    assert len(raw_left_front) == 23
    raw_left_front_proprio = raw[(raw["entryNerve"] == "ProLN") &
                                 (raw["rootSide"] == "L") &
                                 (raw["class"] == "mechanosensory_proprioceptive")]
    assert len(raw_left_front_proprio) == 45
    assert int(raw_left_front_proprio["type"].eq("SNppxx").sum()) == 7
    assert int(raw_left_front_proprio["type"].isna().sum()) == 10
    assert set(raw_left_front_proprio["bodyId"]).issubset(set(nodes["bodyId"]))
    nt = pd.read_feather(NEUROTRANSMITTERS)
    assert nt["body"].is_unique
    nt_by_body = nt.set_index("body")
    diagnostic = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
    assert diagnostic["spec"]["graph_manifest_sha256"] == sha(GRAPH / "manifest.json")
    assert diagnostic["spec"]["shared_assumptions"]["acetylcholine"] == 1
    with RUNTIME_GRAPH.open("rb") as stream:
        runtime_nodes, runtime_edges, _ = struct.unpack("<IQI", stream.read(16))
    assert runtime_nodes == len(ids) and runtime_edges == len(col)
    runtime_row = np.memmap(RUNTIME_GRAPH, mode="r", dtype="<u8", offset=16,
                            shape=(runtime_nodes + 1,))
    runtime_col = np.memmap(RUNTIME_GRAPH, mode="r", dtype="<u4",
                            offset=16 + 8 * (runtime_nodes + 1), shape=(runtime_edges,))
    runtime_weight = np.memmap(RUNTIME_GRAPH, mode="r", dtype="<f8",
                               offset=16 + 8 * (runtime_nodes + 1) + 4 * runtime_edges,
                               shape=(runtime_edges,))
    assert int(runtime_row[-1]) == runtime_edges
    runtime_lo, runtime_hi = int(runtime_row[MOTOR_INDEX]), int(runtime_row[MOTOR_INDEX + 1])
    assert np.array_equal(runtime_col[runtime_lo:runtime_hi], col[row[MOTOR_INDEX]:row[MOTOR_INDEX + 1]])
    direct_runtime_weights = runtime_weight[runtime_lo:runtime_hi][
        runtime_col[runtime_lo:runtime_hi] == int(np.flatnonzero(ids == 912317)[0])]
    assert direct_runtime_weights.tolist() == [1.375]
    selected = nodes[(nodes["subclass"] == "chordotonal organ") &
                     (nodes["entryNerve"] == "ProLN") &
                     (nodes["rootSide"] == "L")].copy()
    assert len(selected) == 23
    assert set(selected["bodyId"]) == set(raw_left_front["bodyId"])
    type_counts = {str(key): int(value) for key, value in
                   selected["type"].value_counts().sort_index().items()}
    assert type_counts["SNpp50"] == 1 and type_counts["SNpp51"] == 3
    global_snpp50 = nodes[nodes["type"] == "SNpp50"]
    snpp50_by_nerve_side = [
        {"entry_nerve": str(nerve), "root_side": str(side), "cells": int(len(group))}
        for (nerve, side), group in global_snpp50.groupby(["entryNerve", "rootSide"])
    ]
    assert len(global_snpp50) == 62
    selected.sort_values("compact_index", inplace=True)
    for item in selected.itertuples():
        assert int(ids[item.compact_index]) == item.bodyId
    # CSR rows contain presynaptic graph indices for each postsynaptic node.
    immediate = np.unique(col[row[MOTOR_INDEX]:row[MOTOR_INDEX + 1]])
    motor_lo, motor_hi = int(row[MOTOR_INDEX]), int(row[MOTOR_INDEX + 1])
    all_left_front_proprio = nodes[(nodes["entryNerve"] == "ProLN") &
                                   (nodes["rootSide"] == "L") &
                                   (nodes["class"] == "mechanosensory_proprioceptive")]
    all_proprio_direct = []
    for item in all_left_front_proprio.itertuples():
        mask = col[motor_lo:motor_hi] == int(item.compact_index)
        if mask.any():
            chemical = nt_by_body.loc[int(item.bodyId)]
            all_proprio_direct.append({
                "body_id": int(item.bodyId), "graph_index": int(item.compact_index),
                "type": None if pd.isna(item.type) else str(item.type),
                "subclass": None if pd.isna(item.subclass) else str(item.subclass),
                "edge_rows": int(mask.sum()),
                "contacts": int(counts[motor_lo:motor_hi][mask].sum()),
                "consensus_nt": str(chemical["consensus_nt"]),
                "predicted_nt_confidence": float(chemical["predicted_nt_confidence"]),
                "ground_truth_nt": None if pd.isna(chemical["ground_truth"])
                                   else str(chemical["ground_truth"])})
    all_proprio_direct.sort(key=lambda item: item["body_id"])
    assert [(item["body_id"], item["contacts"]) for item in all_proprio_direct] == [
        (817697, 28), (821306, 12), (908487, 18), (912317, 5)]
    upstream = np.concatenate([col[row[int(pre)]:row[int(pre) + 1]] for pre in immediate])
    two_hop_multiplicity = np.bincount(upstream, minlength=len(ids))
    candidates = []
    for item in selected.itertuples():
        index = int(item.compact_index)
        direct_mask = col[motor_lo:motor_hi] == index
        candidates.append({"body_id": int(item.bodyId), "graph_index": index,
                           "type": item.type, "root_side": item.rootSide,
                           "entry_nerve": item.entryNerve,
                           "direct_edge_rows_to_motor": int(np.sum(direct_mask)),
                           "direct_synapse_contacts_to_motor": int(np.sum(
                               counts[motor_lo:motor_hi][direct_mask])),
                           "two_hop_path_rows_to_motor": int(two_hop_multiplicity[index])})
    report = {
        "motor_body_id": MOTOR_BODY, "motor_graph_index": MOTOR_INDEX,
        "selection": "MaleCNS chordotonal organ, ProLN entry nerve, left root side",
        "selected_cells": len(candidates),
        "selected_type_counts": type_counts,
        "raw_chordotonal_by_leg_nerve_and_root_side": raw_by_leg,
        "raw_left_front_cells_retained_in_graph": True,
        "raw_left_front_proprioceptive_class_cells": len(raw_left_front_proprio),
        "raw_left_front_proprioceptive_class_untyped_snppxx": 7,
        "raw_left_front_proprioceptive_class_no_type": 10,
        "raw_left_front_proprioceptive_class_cells_retained_in_graph": True,
        "global_snpp50_cells": len(global_snpp50),
        "global_snpp50_by_entry_nerve_and_root_side": snpp50_by_nerve_side,
        "cells_with_direct_edge": sum(x["direct_edge_rows_to_motor"] > 0 for x in candidates),
        "all_left_front_proprioceptive_class_direct_to_motor": all_proprio_direct,
        "cells_with_two_hop_path": sum(x["two_hop_path_rows_to_motor"] > 0 for x in candidates),
        "motor_unique_immediate_presynaptic_cells": len(immediate),
        "candidates": candidates,
        "direct_edge_presynaptic_nt": [
            {
                "body_id": item["body_id"],
                "predicted_nt": str(record["predicted_nt"]),
                "predicted_nt_confidence": float(record["predicted_nt_confidence"]),
                "ground_truth": None if pd.isna(record["ground_truth"]) else str(record["ground_truth"]),
                "postsynaptic_receptor_sign_verified": False,
            }
            for item in candidates if item["direct_edge_rows_to_motor"] > 0
            for record in [nt.loc[nt["body"] == item["body_id"]].iloc[0]]
        ],
        "diagnostic_direct_edge_weight": {
            "presynaptic_body_id": 912317,
            "postsynaptic_body_id": MOTOR_BODY,
            "consensus_nt": str(nt.loc[nt["body"] == 912317, "consensus_nt"].iloc[0]),
            "assumed_sign": diagnostic["spec"]["shared_assumptions"]["acetylcholine"],
            "contacts": next(item["direct_synapse_contacts_to_motor"] for item in candidates
                             if item["body_id"] == 912317),
            "weight_mv_per_contact": diagnostic["spec"]["weight_mv_per_contact"],
            "diagnostic_weight_mv": next(item["direct_synapse_contacts_to_motor"] for item in candidates
                                         if item["body_id"] == 912317) *
                                    diagnostic["spec"]["weight_mv_per_contact"],
            "runtime_binary_edge_weight_mv": float(direct_runtime_weights[0]),
            "runtime_graph_path": str(RUNTIME_GRAPH.relative_to(ROOT)).replace("\\", "/"),
            "source_report_sha256": sha(DIAGNOSTIC),
            "biological_sign_verified": False,
        },
        "source_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                          for path in (GRAPH / "body_ids.npy", GRAPH / "indptr.npy",
                                       GRAPH / "indices.npy", GRAPH / "synapse_counts.npy",
                                       CANDIDATES, NEUROTRANSMITTERS, RAW_ANNOTATIONS)},
        "physiology_verified": False,
        "scope": "Exact one- and two-edge graph reachability, not a FeCO identity crosswalk, transduction, response sign, active feedback or biological validation."
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected_cells": len(candidates),
                      "cells_with_direct_edge": report["cells_with_direct_edge"],
                      "cells_with_two_hop_path": report["cells_with_two_hop_path"],
                      "snpp39_two_hop_counts": [x["two_hop_path_rows_to_motor"] for x in candidates
                                                if x["type"] == "SNpp39"]}, indent=2))


if __name__ == "__main__":
    main()
