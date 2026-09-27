"""Screen all 69 published left-T1 manual SWCs against two later FANC meshes."""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
SWCS = ROOT / "data/reference/fanc_2021_t1_motor_swcs"
MESHES = ROOT / "data/reference/fanc_ti_extensor_meshes"
OUT = ROOT / "reports/fanc_2021_swc_to_ti_extensor_mesh_screen.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distances(source, target_tree):
    d = target_tree.query(source, workers=-1)[0]
    return {"median_nm": float(np.median(d)),
            "p90_nm": float(np.quantile(d, .9)),
            "within_1000nm_fraction": float(np.mean(d <= 1000))}


def main():
    manifest_path = SWCS / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    mesh_path = ROOT / "reports/fanc_ti_extensor_meshes.json"
    meshes = json.loads(mesh_path.read_text())
    assert len(manifest["files"]) == 69
    neurons = []
    for entry in manifest["files"]:
        path = SWCS / entry["name"]
        assert sha(path) == entry["sha256"]
        xyz = np.loadtxt(path, comments="#")[:, 2:5]
        assert np.isfinite(xyz).all()
        neurons.append((entry["name"], xyz, cKDTree(xyz)))

    rng = np.random.default_rng(20260924)
    result = []
    for item in meshes["meshes"]:
        ident = item["segment_id"]
        path = MESHES / f"{ident}_fragment.bin"
        assert sha(path) == item["fragment_sha256"]
        raw = path.read_bytes()
        n = int(np.frombuffer(raw, dtype="<u4", count=1)[0])
        xyz = np.frombuffer(raw, dtype="<f4", offset=4, count=3*n).reshape(-1, 3)
        pick = np.sort(rng.choice(n, size=min(16_384, n), replace=False))
        sample = xyz[pick].astype(np.float64)
        mesh_tree = cKDTree(sample)
        comparisons = []
        for name, swc, swc_tree in neurons:
            comparisons.append({
                "swc": name,
                "swc_nodes": len(swc),
                "swc_to_mesh_sample": distances(swc, mesh_tree),
                "mesh_sample_to_swc": distances(sample, swc_tree),
            })
        comparisons.sort(key=lambda x: x["swc_to_mesh_sample"]["median_nm"])
        result.append({"fanc_segment_id": ident,
                       "mesh_sample_size": len(sample),
                       "sample_index_sha256": hashlib.sha256(pick.tobytes()).hexdigest(),
                       "comparisons": comparisons})
        print(ident, [(x["swc"], x["swc_to_mesh_sample"]["median_nm"], x["mesh_sample_to_swc"]["median_nm"]) for x in comparisons[:5]], flush=True)
    report = {
        "scope": "2021 SWC to 2024 mesh proximity screen in native FANC coordinates; cross-release identity unverified",
        "swc_manifest_sha256": sha(manifest_path),
        "mesh_report_sha256": sha(mesh_path),
        "results": result,
        "exact_segment_to_swc_match_verified": False,
        "fanc_to_manc_identity_verified": False,
        "motor_mapping_enabled": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
