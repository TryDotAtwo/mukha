"""Compare seven source SWC skeletons with direct tibial motor target profiles."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from flymimic_public_model import ROOT


IDS = (817697, 821306, 908487, 912317, 815843, 817680, 935383)
SWC = ROOT / "data/reference/malecns_v1_lf_proprio_skeletons"
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
OUT = ROOT / "reports/lf_sensory_morphology_vs_motor.json"
MOTOR_TYPES = ("Ti extensor MN", "Ti flexor MN", "Acc. ti flexor MN")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_xyz(body_id):
    path = SWC / f"{body_id}.swc"
    rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]
    return np.array([[float(value) * .008 for value in row[2:5]] for row in rows])


def main():
    manifest_path = SWC / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pinned = {int(entry["body_id"]): entry["sha256"] for entry in manifest["entries"]}
    for body_id in IDS:
        assert sha(SWC / f"{body_id}.swc") == pinned[body_id]
    xyz = {body_id: load_xyz(body_id) for body_id in IDS}
    trees = {body_id: cKDTree(points) for body_id, points in xyz.items()}
    nodes = pd.read_feather(GRAPH / "nodes.feather")
    row = np.load(GRAPH / "indptr.npy", mmap_mode="r")
    col = np.load(GRAPH / "indices.npy", mmap_mode="r")
    counts = np.load(GRAPH / "synapse_counts.npy", mmap_mode="r")
    motors = nodes[(nodes["superclass"] == "vnc_motor") &
                   (nodes["subclass"] == "fl") &
                   (nodes["type"].isin(MOTOR_TYPES))].sort_values("bodyId")
    assert len(motors) == 33
    index = {int(item.bodyId): int(item.compact_index)
             for item in nodes[nodes["bodyId"].isin(IDS)].itertuples()}
    profiles = {}
    for body_id in IDS:
        presyn = index[body_id]
        vector = []
        for motor in motors.itertuples():
            lo, hi = int(row[motor.compact_index]), int(row[motor.compact_index + 1])
            vector.append(int(counts[lo:hi][col[lo:hi] == presyn].sum()))
        profiles[body_id] = np.array(vector, dtype=np.float64)
    pairs = []
    for position, left in enumerate(IDS):
        for right in IDS[position + 1:]:
            a = trees[right].query(xyz[left])[0]
            b = trees[left].query(xyz[right])[0]
            u, v = profiles[left], profiles[right]
            cosine = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)))
            pairs.append({
                "left_body_id": left, "right_body_id": right,
                "mean_bidirectional_nearest_swc_node_distance_um": float((a.mean() + b.mean()) / 2),
                "median_left_to_right_um": float(np.median(a)),
                "median_right_to_left_um": float(np.median(b)),
                "motor_33_contact_cosine": cosine,
            })
    result = {
        "scope": "Seven author SWC skeletons in shared MaleCNS EM coordinates and retained direct contacts to 33 left-front tibial motor candidates",
        "source_manifest_sha256": sha(manifest_path),
        "source_hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                          for path in (GRAPH / "nodes.feather", GRAPH / "indptr.npy",
                                       GRAPH / "indices.npy", GRAPH / "synapse_counts.npy")},
        "skeleton_sha256": {str(body_id): pinned[body_id] for body_id in IDS},
        "skeleton_units": "SWC coordinates multiplied by 0.008 to get micrometers, per author manifest",
        "motor_order_body_ids": [int(value) for value in motors["bodyId"]],
        "motor_contact_vectors": {str(body_id): profiles[body_id].astype(int).tolist() for body_id in IDS},
        "pairs": pairs,
        "interpretation_limit": "Node sampling, reconstruction completeness, shared nerve trunk and motor convergence can affect these measures. Neither morphology nor target cosine identifies the peripheral receptor or physiological tuning.",
        "biological_validation": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for left, right in ((817697, 821306), (817697, 908487), (821306, 912317)):
        item = next(x for x in pairs if {x["left_body_id"], x["right_body_id"]} == {left, right})
        print(left, right, round(item["mean_bidirectional_nearest_swc_node_distance_um"], 3),
              round(item["motor_33_contact_cosine"], 3))


if __name__ == "__main__":
    main()
