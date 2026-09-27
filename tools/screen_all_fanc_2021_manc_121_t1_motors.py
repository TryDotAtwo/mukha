"""Measure two MANC 1.2.1 cells against all 69 published FANC 2021 T1-left motor trees."""

import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
FANC = ROOT / "data/reference/fanc_2021_t1_motor_swcs"
MANC = ROOT / "data/reference/manc_121_ti_extensor_native_swcs"
REG = ROOT / "data/reference/ti_extensor_transform_inputs"
OUT = ROOT / "reports/fanc_2021_manc_121_all_t1_motor_screen.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source_manifest = FANC / "source_manifest.json"
    target_manifest = MANC / "source_manifest.json"
    source = json.loads(source_manifest.read_text())
    target = json.loads(target_manifest.read_text())
    assert len(source["files"]) == 69
    assert target["release"] == "MANC 1.2.1, not MANC 1.0"
    os.environ["FLYBRAINS_DATA"] = str(REG)
    import flybrains  # noqa: F401
    import navis
    route, _ = navis.transforms.registry.find_bridging_path("FANC", "MANC")
    assert route == ["FANC", "MANC"]
    targets = {}
    for item in target["files"]:
        path = MANC / f'{item["body_id"]}.swc'
        assert sha(path) == item["sha256"]
        xyz = np.loadtxt(path, comments="#")[:, 2:5]
        targets[item["body_id"]] = (xyz, cKDTree(xyz))
    rows = []
    for ix, item in enumerate(source["files"], 1):
        path = FANC / item["name"]
        assert sha(path) == item["sha256"]
        match = re.search(r"\(neuron (\d+)\)", item["name"])
        assert match
        xyz_nm = np.loadtxt(path, comments="#")[:, 2:5]
        transformed_um = np.asarray(navis.xform_brain(xyz_nm, source="FANC", target="MANC")) / 1000
        tree = cKDTree(transformed_um)
        row = {"fanc_neuron_id": int(match.group(1)), "source_name": item["name"],
               "fanc_nodes": len(xyz_nm), "targets": {}}
        for body_id, (manc_xyz, manc_tree) in targets.items():
            forward = manc_tree.query(transformed_um)[0]
            reverse = tree.query(manc_xyz)[0]
            row["targets"][str(body_id)] = {
                "fanc_to_manc_median_um": float(np.median(forward)),
                "manc_to_fanc_median_um": float(np.median(reverse)),
                "mean_bidirectional_median_um": float((np.median(forward) + np.median(reverse)) / 2),
            }
        rows.append(row)
        if ix % 10 == 0:
            print(f"{ix}/69", flush=True)
    rankings = {}
    for body_id in targets:
        key = str(body_id)
        rankings[key] = [r["fanc_neuron_id"] for r in sorted(
            rows, key=lambda r: r["targets"][key]["mean_bidirectional_median_um"])]
    report = {"scope": "All 69 FANC 2021 T1-left motor SWCs against two MANC 1.2.1 native SWCs",
              "fanc_release": "2021 manual", "manc_release": target["release"],
              "route": route, "source_manifest_sha256": sha(source_manifest),
              "target_manifest_sha256": sha(target_manifest),
              "rank_metric": "mean of forward and reverse median nearest-node distance, um",
              "rows": rows, "rankings": rankings, "validates_manc_v1_identity": False}
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v[:10] for k, v in rankings.items()}, indent=2), flush=True)


if __name__ == "__main__":
    main()
