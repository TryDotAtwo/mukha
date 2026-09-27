"""Check coarse SWC proximity of exact 13B candidate pairs; no identity claim."""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

root = Path(__file__).resolve().parents[1]
candidate_dir = root / "data/reference/malecns_v1_agrawal_13b_candidates"
sensory_dir = root / "data/reference/malecns_v1_lf_proprio_skeletons"
candidate_manifest = json.loads((candidate_dir / "source_manifest.json").read_text())
sensory_manifest = json.loads((sensory_dir / "source_manifest.json").read_text())
screen_path = root / "reports/agrawal_13b_connectivity.json"
assert hashlib.sha256(screen_path.read_bytes()).hexdigest() == candidate_manifest["screen_sha256"]
screen = json.loads(screen_path.read_text())
sensory_entries = {x["body_id"]: x for x in sensory_manifest["entries"]}


def points(directory, entry):
    path = directory / f"{entry['body_id']}.swc"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    xyz = np.loadtxt(path, comments="#", usecols=(2, 3, 4))
    assert xyz.ndim == 2 and xyz.shape[1] == 3 and np.isfinite(xyz).all()
    return xyz


trees = {}
for body in {source for c in screen["candidates"] for source in c["snpp50_51_source_body_ids"]}:
    assert body in sensory_entries
    trees[body] = cKDTree(points(sensory_dir, sensory_entries[body]))

results = []
for entry in candidate_manifest["entries"]:
    body = entry["body_id"]
    candidate = next(x for x in screen["candidates"] if x["bodyId"] == body)
    xyz = points(candidate_dir, entry)
    pairs = []
    for source in candidate["snpp50_51_source_body_ids"]:
        distance_voxels = float(trees[source].query(xyz, workers=1)[0].min())
        pairs.append({"source_body_id": source, "minimum_swc_node_distance_voxels": distance_voxels,
                      "minimum_swc_node_distance_um": distance_voxels * 0.008})
    results.append({"bodyId": body, "somaSide": candidate["somaSide"],
                    "source_root_sides": candidate["snpp50_51_source_root_sides"],
                    "swc_nodes": len(xyz), "swc_bbox_min": xyz.min(axis=0).tolist(),
                    "swc_bbox_max": xyz.max(axis=0).tolist(), "pairs": pairs})

report = {"screen_sha256": candidate_manifest["screen_sha256"],
          "candidate_manifest_sha256": hashlib.sha256((candidate_dir / "source_manifest.json").read_bytes()).hexdigest(),
          "sensory_manifest_sha256": hashlib.sha256((sensory_dir / "source_manifest.json").read_bytes()).hexdigest(),
          "coordinate_scale_um_per_voxel": 0.008,
          "scope": "coarse SWC-node proximity; no synapse coordinates or individual experimental identity",
          "candidate_count": len(results), "pairs": sum(len(x["pairs"]) for x in results),
          "results": results}
(root / "reports/agrawal_13b_skeleton_proximity.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"candidates": len(results), "pairs": report["pairs"],
                  "distance_um_range": [min(p["minimum_swc_node_distance_um"] for x in results for p in x["pairs"]),
                                        max(p["minimum_swc_node_distance_um"] for x in results for p in x["pairs"])]}))
