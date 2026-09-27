"""Specificity control: all 23 MaleCNS left-front chordotonal SWCs vs 3 MANC SNpp50."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
ANNOT = ROOT / "data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather"
SOURCE = ROOT / "data/reference/malecns_v1_lf_proprio_45_skeletons"
TARGET = ROOT / "data/reference/manc_121_lf_snpp50_native_swcs"
REG = ROOT / "data/reference/ti_extensor_transform_inputs"
OUT = ROOT / "reports/malecns_23_chordotonal_manc_121_snpp50_screen.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    annotations = pd.read_feather(ANNOT)
    selected = annotations[(annotations.entryNerve == "ProLN")
                           & (annotations.rootSide == "L")
                           & (annotations["subclass"] == "chordotonal organ")]
    ids = sorted(selected.bodyId.astype(int).tolist())
    assert len(ids) == 23 and 912317 in ids
    source_manifest = SOURCE / "source_manifest.json"
    target_manifest = TARGET / "source_manifest.json"
    source = json.loads(source_manifest.read_text())
    target = json.loads(target_manifest.read_text())
    source_items = {x["body_id"]: x for x in source["entries"]}
    assert all(source_items[i]["status"] == "downloaded" for i in ids)
    assert target["release"] == "MANC 1.2.1, not MANC 1.0"
    targets = {}
    for item in target["files"]:
        path = TARGET / f'{item["body_id"]}.swc'
        assert sha(path) == item["sha256"]
        xyz = np.loadtxt(path, comments="#")[:, 2:5]
        targets[item["body_id"]] = (xyz, cKDTree(xyz))
    reg_manifest = REG / "source_manifest.json"
    for item in json.loads(reg_manifest.read_text())["files"]:
        assert sha(REG / item["name"]) == item["sha256"]
    os.environ["FLYBRAINS_DATA"] = str(REG)
    os.environ["PATH"] = str(REG / "elastix_runtime") + os.pathsep + os.environ["PATH"]
    import flybrains  # noqa: F401
    import navis
    route, _ = navis.transforms.registry.find_bridging_path("JRCFIB2022Mraw", "MANC")
    rows = []
    for idx, body_id in enumerate(ids, 1):
        path = SOURCE / f"{body_id}.swc"
        assert sha(path) == source_items[body_id]["sha256"]
        raw = np.loadtxt(path, comments="#")
        mapped_um = np.asarray(navis.xform_brain(raw[:, 2:5].copy(), source="JRCFIB2022Mraw", target="MANC")) / 1000
        assert np.isfinite(mapped_um).all()
        tree = cKDTree(mapped_um)
        row = {"malecns_body_id": body_id,
               "malecns_type": str(selected.loc[selected.bodyId == body_id, "type"].iloc[0]),
               "nodes": len(raw), "targets": {}}
        for target_id, (xyz, target_tree) in targets.items():
            forward = target_tree.query(mapped_um)[0]
            reverse = tree.query(xyz)[0]
            row["targets"][str(target_id)] = {
                "malecns_to_manc_median_um": float(np.median(forward)),
                "manc_to_malecns_median_um": float(np.median(reverse)),
                "bidirectional_median_mean_um": float((np.median(forward) + np.median(reverse)) / 2),
            }
        rows.append(row)
        print(f"{idx}/{len(ids)} body {body_id}", flush=True)
    rankings = {str(target_id): [r["malecns_body_id"] for r in sorted(
        rows, key=lambda r: r["targets"][str(target_id)]["bidirectional_median_mean_um"])]
        for target_id in targets}
    report = {"scope": "Cross-release morphology specificity control, not cell identity proof",
              "malecns_release": "v1.0", "manc_release": target["release"],
              "selection": "all 23 annotated chordotonal / left ProLN MaleCNS cells",
              "annotation_sha256": sha(ANNOT),
              "source_manifest_sha256": sha(source_manifest),
              "target_manifest_sha256": sha(target_manifest),
              "transform_manifest_sha256": sha(reg_manifest),
              "route": route, "rows": rows, "rankings": rankings,
              "validates_manc_v1_identity": False}
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v[:5] for k, v in rankings.items()}, indent=2))


if __name__ == "__main__":
    main()
