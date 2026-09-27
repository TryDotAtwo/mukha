"""Compare all 45 source-pinned left-front sensory SWC centerlines."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from flymimic_public_model import ROOT


SOURCE = ROOT / "data/reference/malecns_v1_lf_proprio_45_skeletons"
GRAPH = ROOT / "data/derived/malecns_v1_candidates/nodes.feather"
OUT = ROOT / "reports/lf_45_skeleton_neighbors.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = SOURCE / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["entries"]) == 45
    nodes = pd.read_feather(GRAPH).set_index("bodyId")
    points = {}
    records = {}
    for entry in manifest["entries"]:
        body_id = int(entry["body_id"])
        assert entry["status"] == "downloaded"
        path = SOURCE / f"{body_id}.swc"
        assert sha(path) == entry["sha256"]
        rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")]
        xyz = np.array([[float(value) * .008 for value in row[2:5]] for row in rows])
        assert len(xyz) > 10
        points[body_id] = xyz
        item = nodes.loc[body_id]
        records[body_id] = {
            "body_id": body_id,
            "type": None if pd.isna(item["type"]) else str(item["type"]),
            "subclass": None if pd.isna(item["subclass"]) else str(item["subclass"]),
            "nodes": len(rows),
            "bounds_um": [xyz.min(axis=0).tolist(), xyz.max(axis=0).tolist()],
        }
    trees = {body_id: cKDTree(xyz) for body_id, xyz in points.items()}
    ids = sorted(points)
    pairwise = []
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            a = trees[right].query(points[left])[0]
            b = trees[left].query(points[right])[0]
            pairwise.append({
                "left_body_id": left, "right_body_id": right,
                "mean_bidirectional_nearest_node_um": float((a.mean() + b.mean()) / 2),
                "left_fraction_nodes_within_5um_of_right": float((a < 5).mean()),
                "right_fraction_nodes_within_5um_of_left": float((b < 5).mean()),
                "left_p95_nearest_um": float(np.quantile(a, .95)),
                "right_p95_nearest_um": float(np.quantile(b, .95)),
            })
    nearest = {}
    for body_id in ids:
        local = sorted((entry for entry in pairwise if body_id in
                        (entry["left_body_id"], entry["right_body_id"])),
                       key=lambda item: item["mean_bidirectional_nearest_node_um"])
        nearest[str(body_id)] = [{"neighbor_body_id": x["right_body_id"] if x["left_body_id"] == body_id else x["left_body_id"],
                                  "distance_um": x["mean_bidirectional_nearest_node_um"]}
                                 for x in local[:5]]
    result = {
        "scope": "All 45 source-annotated left-front ProLN proprioceptive neurons; source SWC centerline comparison in native MaleCNS EM coordinates",
        "manifest_sha256": sha(manifest_path),
        "graph_nodes_sha256": sha(GRAPH),
        "units": "micrometers after multiplying SWC coordinates by 0.008",
        "records": [records[body_id] for body_id in ids],
        "pairwise": pairwise,
        "nearest_five": nearest,
        "limit": "Sparse SWC sampling, shared nerve segment, reconstruction completeness, and soma location bias nearest-node distances. This is no validated cell-type or modality classifier.",
        "biological_validation": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: nearest[key] for key in ("817697", "821306", "908487", "912317")}, indent=2))


if __name__ == "__main__":
    main()
