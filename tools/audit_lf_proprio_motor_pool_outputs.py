"""Audit direct outputs of left-front proprioceptors to tibia motor groups.

Structural evidence only; output preference cannot identify sensory tuning.
"""

import hashlib
import json

import numpy as np
import pandas as pd

from flymimic_public_model import ROOT


GRAPH = ROOT / "data/derived/malecns_v1_candidates"
RAW = ROOT / "data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather"
REPORT = ROOT / "reports/lf_proprio_motor_pool_outputs.json"
MOTOR_TYPES = ("Ti extensor MN", "Ti flexor MN", "Acc. ti flexor MN")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    nodes = pd.read_feather(GRAPH / "nodes.feather")
    source = nodes[(nodes["class"] == "mechanosensory_proprioceptive") &
                   (nodes["entryNerve"] == "ProLN") &
                   (nodes["rootSide"] == "L")].copy()
    assert len(source) == 45
    motor = nodes[(nodes["superclass"] == "vnc_motor") &
                  (nodes["subclass"] == "fl") &
                  (nodes["type"].isin(MOTOR_TYPES))].copy()
    assert motor["type"].value_counts().to_dict() == {
        "Acc. ti flexor MN": 19, "Ti flexor MN": 10, "Ti extensor MN": 4}
    row = np.load(GRAPH / "indptr.npy", mmap_mode="r")
    col = np.load(GRAPH / "indices.npy", mmap_mode="r")
    counts = np.load(GRAPH / "synapse_counts.npy", mmap_mode="r")
    source_by_index = {int(item.compact_index): int(item.bodyId)
                       for item in source.itertuples()}
    connections = {body: {name: 0 for name in MOTOR_TYPES}
                   for body in source_by_index.values()}
    for item in motor.itertuples():
        lo, hi = int(row[item.compact_index]), int(row[item.compact_index + 1])
        for presyn, contact_count in zip(col[lo:hi], counts[lo:hi]):
            body = source_by_index.get(int(presyn))
            if body is not None:
                connections[body][item.type] += int(contact_count)
    records = []
    for item in source.sort_values("bodyId").itertuples():
        body = int(item.bodyId)
        records.append({"body_id": body,
                        "graph_index": int(item.compact_index),
                        "type": None if pd.isna(item.type) else str(item.type),
                        "subclass": None if pd.isna(item.subclass) else str(item.subclass),
                        "contacts_by_motor_type": connections[body]})
    lookup = {entry["body_id"]: entry["contacts_by_motor_type"] for entry in records}
    assert [lookup[b]["Ti extensor MN"] for b in
            (817697, 821306, 908487, 912317)] == [33, 25, 20, 9]
    assert [lookup[b]["Ti flexor MN"] for b in (815843, 817680, 935383)] == [25, 14, 26]
    assert all(lookup[b]["Ti flexor MN"] == 0 for b in
               (817697, 821306, 908487, 912317))
    assert all(lookup[b]["Ti extensor MN"] == 0 for b in (815843, 817680, 935383))
    report = {"scope": "Retained direct contacts from 45 source-annotated left-front proprioceptors to 33 front tibia motor candidates, both soma-side labels; no functional subtype assignment",
              "source_hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                                for path in (GRAPH / "nodes.feather", GRAPH / "indptr.npy",
                                             GRAPH / "indices.npy", GRAPH / "synapse_counts.npy", RAW)},
              "motor_group_cells": motor["type"].value_counts().to_dict(),
              "records": records, "biological_validation": False}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([record for record in records
                      if record["body_id"] in (817697, 821306, 908487, 912317,
                                               815843, 817680, 935383)], indent=2))


if __name__ == "__main__":
    main()
