"""Fetch and audit source-pinned Mamiya leg X-ray SWC structures from VFB."""

import hashlib
import json
import math
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/reference/mamiya2023/xray"
OUT = ROOT / "reports/mamiya_xray_geometry.json"
BASE = "https://www.virtualflybrain.org/data/VFB/i/0010/{}/VFB_00120000/volume.swc"
SOURCES = {
    "arculum_midline": ("2efc", "1688860", "957a19c55db36b39bca829e5c23966383a79deba44453cd2128964486788bc37"),
    "arculum_outline": ("2efd", "1688874", "3cc20d7f24077ff6718cc1cd05cbb195f62359efde64db272e06525cfdc76df4"),
    "feco_medial_tendon": ("2efe", "1688887", "05b71c7c768589924b0af940473f0eca8991c12ebf27a78f99df240dfaad19fd"),
    "feco_lateral_tendon": ("2eff", "1688899", "27b1e68d9e107dffbaa22145038ec4d92ab33dfd506782873c53e9969aad1c8b"),
}


def distance(a, b):
    return math.dist(a, b)


def main():
    pdf_sha = hashlib.sha256((ROOT / "data/reference/mamiya2023/mamiya_2023.pdf").read_bytes()).hexdigest()
    assert pdf_sha == "fdde57f0eb41120dd6ed69d6f7e9810ccbf9ebfeedcba2e0f5eafba38c777cac"
    DEST.mkdir(parents=True, exist_ok=True)
    structures = {}
    points = {}
    for name, (suffix, source_id, expected_sha) in SOURCES.items():
        url = BASE.format(suffix)
        path = DEST / f"{name}.swc"
        if not path.exists():
            with urllib.request.urlopen(url, timeout=40) as response:
                data = response.read()
            assert hashlib.sha256(data).hexdigest() == expected_sha, name
            path.write_bytes(data)
        data = path.read_bytes()
        actual_sha = hashlib.sha256(data).hexdigest()
        assert actual_sha == expected_sha, (name, actual_sha)
        lines = data.decode("utf-8").splitlines()
        meta_line = next(line for line in lines if line.startswith("# Meta: "))
        meta = json.loads(meta_line.removeprefix("# Meta: "))
        assert meta["id"] == source_id and meta["units"] == "1.0 micrometer"
        rows = [line.split() for line in lines if line and not line.startswith("#")]
        assert all(len(row) == 7 for row in rows)
        ids = {int(row[0]) for row in rows}
        assert len(ids) == len(rows)
        assert all(int(row[6]) == -1 or int(row[6]) in ids for row in rows)
        xyz = [tuple(float(value) for value in row[2:5]) for row in rows]
        points[name] = xyz
        by_id = {int(row[0]): tuple(float(value) for value in row[2:5]) for row in rows}
        parent_by_id = {int(row[0]): int(row[6]) for row in rows}
        children = {node_id: [] for node_id in by_id}
        for node_id, parent_id in parent_by_id.items():
            if parent_id != -1:
                children[parent_id].append(node_id)
        roots = [node_id for node_id, parent_id in parent_by_id.items() if parent_id == -1]
        tips = [node_id for node_id, descendants in children.items() if not descendants]
        branch_ids = [node_id for node_id, descendants in children.items() if len(descendants) > 1]
        def ancestor_path(node_id):
            chain = [node_id]
            while parent_by_id[chain[-1]] != -1:
                chain.append(parent_by_id[chain[-1]])
            return chain

        def path_length(chain):
            return sum(distance(by_id[a], by_id[b]) for a, b in zip(chain, chain[1:]))

        root_to_tip = []
        for tip in tips:
            chain = ancestor_path(tip)
            root_to_tip.append({
                "tip_node_id": tip,
                "root_node_id": chain[-1],
                "path_length_um": path_length(chain),
                "straight_line_um": distance(by_id[tip], by_id[chain[-1]]),
                "tip_xyz_um": by_id[tip],
                "root_xyz_um": by_id[chain[-1]],
            })
        edge_lengths = [distance(by_id[int(row[0])], by_id[int(row[6])])
                        for row in rows if int(row[6]) != -1]
        structures[name] = {
            "source_url": url,
            "vfb_id": f"VFB_0010{suffix}",
            "t1leg_id": source_id,
            "source_metadata": meta,
            "local_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": actual_sha,
            "bytes": len(data),
            "node_count": len(rows),
            "root_count": sum(int(row[6]) == -1 for row in rows),
            "endpoint_count": sum(int(row[1]) == 6 for row in rows),
            "topological_tip_count": len(tips),
            "branch_node_ids": branch_ids,
            "root_to_branch_paths": [{"branch_node_id": node_id, "path_length_um": path_length(ancestor_path(node_id)),
                                      "branch_xyz_um": by_id[node_id]} for node_id in branch_ids],
            "root_to_tip_paths": root_to_tip,
            "sum_swc_edge_lengths_um": sum(edge_lengths),
            "largest_swc_edge_um": max(edge_lengths),
            "bbox_min_um": [min(p[i] for p in xyz) for i in range(3)],
            "bbox_max_um": [max(p[i] for p in xyz) for i in range(3)],
        }
    proximity = {}
    for tendon in ("feco_medial_tendon", "feco_lateral_tendon"):
        proximity[tendon] = {}
        for arculum in ("arculum_midline", "arculum_outline"):
            a, b = points[tendon], points[arculum]
            minimum = min((distance(pa, pb), ia, ib) for ia, pa in enumerate(a) for ib, pb in enumerate(b))
            proximity[tendon][arculum] = {
                "nearest_sampled_node_distance_um": minimum[0],
                "tendon_node_xyz_um": a[minimum[1]],
                "arculum_node_xyz_um": b[minimum[2]],
            }
    result = {
        "scope": "Static X-ray reconstruction in source VFB coordinate frame; no joint-angle series, strain, or MaleCNS registration",
        "dataset_url": "https://www.virtualflybrain.org/term/biomechanical-origins-of-proprioceptive-maps-in-the-drosophila-leg-mamiya2022/",
        "units": "micrometer, per original SWC metadata",
        "structures": structures,
        "sampled_node_proximity": proximity,
        "proximity_interpretation": "Nearest sampled SWC nodes only; neither a surface distance nor a validated anatomical attachment point",
        "published_arculum_fem_tendon_model": {
            "source": "Mamiya et al. 2023 author PDF, STAR Methods, 'A finite element model of the arculum', pages e6-e7",
            "pdf_sha256": pdf_sha,
            "resilin_young_modulus_mpa": 1.8,
            "arculum_young_modulus_mpa": 3.6,
            "arculum_density_kg_m3": 1200,
            "poisson_ratio": 0.3,
            "assumed_equilibrium_tendon_lengths_um": {"joint": 72, "femoral": 225, "medial": 268, "lateral": 283},
            "assumed_tendon_areas_um2": {"joint": 295.3, "femoral": 295.3, "medial": 50.9, "lateral": 57.2},
            "medial_spring_stiffness_adjustment": "Author model halves effective stiffness to represent soft proximal coupling",
            "interpretation": "Author FE model assumptions and geometry measurements; not directly fitted or identified by these SWC paths",
        },
        "biological_validation": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"structures": {k: v["node_count"] for k, v in structures.items()}, "proximity_um": {k: {a: x["nearest_sampled_node_distance_um"] for a, x in v.items()} for k, v in proximity.items()}}, indent=2))


if __name__ == "__main__":
    main()
