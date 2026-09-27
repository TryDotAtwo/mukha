"""Exploratory native-space morphology screen for MaleCNS 912317 and MANC SNpp50."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/malecns_v1_lf_proprio_45_skeletons"
TARGET = ROOT / "data/reference/manc_121_lf_snpp50_native_swcs"
REG = ROOT / "data/reference/ti_extensor_transform_inputs"
OUT = ROOT / "reports/malecns_912317_manc_121_snpp50_native_screen.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(d):
    return {"median_um": float(np.median(d)), "p90_um": float(np.quantile(d, .9))}


def main():
    src_manifest = SOURCE / "source_manifest.json"
    dst_manifest = TARGET / "source_manifest.json"
    src = json.loads(src_manifest.read_text())
    dst = json.loads(dst_manifest.read_text())
    src_item = next(x for x in src["entries"] if x["body_id"] == 912317)
    path = SOURCE / "912317.swc"
    assert sha(path) == src_item["sha256"]
    assert dst["release"] == "MANC 1.2.1, not MANC 1.0"
    reg = json.loads((REG / "source_manifest.json").read_text())
    for item in reg["files"]:
        assert sha(REG / item["name"]) == item["sha256"]
    os.environ["FLYBRAINS_DATA"] = str(REG)
    os.environ["PATH"] = str(REG / "elastix_runtime") + os.pathsep + os.environ["PATH"]
    import flybrains  # noqa: F401
    import navis
    route, _ = navis.transforms.registry.find_bridging_path("JRCFIB2022Mraw", "MANC")
    raw = np.loadtxt(path, comments="#")
    source_xyz = raw[:, 2:5]
    mapped_nm = np.asarray(navis.xform_brain(source_xyz.copy(), source="JRCFIB2022Mraw", target="MANC"))
    mapped_um = mapped_nm / 1000
    assert np.isfinite(mapped_um).all()
    source_tree = cKDTree(mapped_um)
    results = []
    for item in dst["files"]:
        target_path = TARGET / f'{item["body_id"]}.swc'
        assert sha(target_path) == item["sha256"]
        target_xyz = np.loadtxt(target_path, comments="#")[:, 2:5]
        forward = cKDTree(target_xyz).query(mapped_um)[0]
        reverse = source_tree.query(target_xyz)[0]
        results.append({"manc_121_id": item["body_id"], "target_nodes": len(target_xyz),
                        "malecns_to_manc": stats(forward), "manc_to_malecns": stats(reverse),
                        "bidirectional_median_mean_um": float((np.median(forward) + np.median(reverse)) / 2)})
    report = {"scope": "Exploratory MaleCNS v1.0-to-MANC 1.2.1 morphology, not an identity proof",
              "male_cns_body_id": 912317, "male_cns_nodes": len(source_xyz),
              "source_manifest_sha256": sha(src_manifest), "target_manifest_sha256": sha(dst_manifest),
              "transform_manifest_sha256": sha(REG / "source_manifest.json"),
              "route": route, "coordinate_units": "MaleCNS native 8-nm voxels; MANC transform nm; MANC SWC um",
              "results": results, "validates_manc_v1_identity": False}
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
