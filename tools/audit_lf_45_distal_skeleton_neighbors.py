"""Repeat 45-cell SWC neighbor audit after excluding early root-distance nodes."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from flymimic_public_model import ROOT


SOURCE = ROOT / "data/reference/malecns_v1_lf_proprio_45_skeletons"
FULL = ROOT / "reports/lf_45_skeleton_neighbors.json"
OUT = ROOT / "reports/lf_45_distal_skeleton_neighbors.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_nodes(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            parts = line.split()
            rows[int(parts[0])] = (np.array([float(x) * .008 for x in parts[2:5]]), int(parts[6]))
    depth = {}

    def root_distance(node_id):
        if node_id not in depth:
            xyz, parent = rows[node_id]
            depth[node_id] = 0.0 if parent == -1 else root_distance(parent) + float(
                np.linalg.norm(xyz - rows[parent][0]))
        return depth[node_id]

    for node_id in rows:
        root_distance(node_id)
    ids = list(rows)
    distances = np.array([depth[node_id] for node_id in ids])
    cutoff = float(np.quantile(distances, .75))
    keep = [node_id for node_id in ids if depth[node_id] >= cutoff]
    return np.array([rows[node_id][0] for node_id in keep]), {
        "all_nodes": len(rows), "selected_nodes": len(keep),
        "root_distance_q75_um": cutoff, "maximum_root_distance_um": float(distances.max()),
    }


def main():
    manifest_path = SOURCE / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    full = json.loads(FULL.read_text(encoding="utf-8"))
    assert full["manifest_sha256"] == sha(manifest_path)
    points = {}
    selection = {}
    for entry in manifest["entries"]:
        body_id = int(entry["body_id"])
        path = SOURCE / f"{body_id}.swc"
        assert sha(path) == entry["sha256"]
        points[body_id], selection[body_id] = selected_nodes(path)
    assert len(points) == 45
    trees = {body_id: cKDTree(xyz) for body_id, xyz in points.items()}
    ids = sorted(points)
    pairs = []
    for position, left in enumerate(ids):
        for right in ids[position + 1:]:
            a = trees[right].query(points[left])[0]
            b = trees[left].query(points[right])[0]
            pairs.append({"left_body_id": left, "right_body_id": right,
                          "mean_bidirectional_nearest_selected_node_um": float((a.mean() + b.mean()) / 2)})
    nearest = {}
    for body_id in ids:
        local = sorted((item for item in pairs if body_id in (item["left_body_id"], item["right_body_id"])),
                       key=lambda item: item["mean_bidirectional_nearest_selected_node_um"])
        nearest[str(body_id)] = [{"neighbor_body_id": item["right_body_id"] if item["left_body_id"] == body_id else item["left_body_id"],
                                  "distance_um": item["mean_bidirectional_nearest_selected_node_um"]}
                                 for item in local[:5]]
    result = {
        "scope": "All 45 source SWCs; root-distance top quartile of sampled nodes per neuron, compared in shared EM coordinates",
        "manifest_sha256": sha(manifest_path), "full_neighbor_report_sha256": sha(FULL),
        "selection_method": "For each SWC node, sum edge lengths to its source root; retain nodes at or above that cell's 75th percentile of sampled root distances",
        "selection": {str(body_id): selection[body_id] for body_id in ids},
        "pairs": pairs, "nearest_five": nearest,
        "limit": "Top quartile of source-root distance is a computational sensitivity check, not histological compartment segmentation; branches and sampling density affect it.",
        "biological_validation": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: nearest[key] for key in ("817697", "821306", "912317")}, indent=2))


if __name__ == "__main__":
    main()
