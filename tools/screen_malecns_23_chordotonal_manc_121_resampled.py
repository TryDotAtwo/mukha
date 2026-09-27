"""Rerank a cross-release morphology screen after uniform cable resampling."""

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
PRIOR = ROOT / "reports/malecns_23_chordotonal_manc_121_snpp50_screen.json"
OUT = ROOT / "reports/malecns_23_chordotonal_manc_121_resampled_screen.json"
STEPS_UM = (1.0, 2.0, 4.0)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cable_samples(swc, xyz, step):
    """Midpoint samples every <=step um on each nonzero SWC parent segment."""
    assert len(swc) == len(xyz)
    node_ids = swc[:, 0].astype(np.int64)
    parents = swc[:, 6].astype(np.int64)
    assert len(set(node_ids)) == len(node_ids)
    index = {int(n): i for i, n in enumerate(node_ids)}
    pieces = []
    lengths = []
    skipped_parent = 0
    for i, parent in enumerate(parents):
        if parent == -1:
            continue
        if int(parent) not in index:
            skipped_parent += 1
            continue
        a, b = xyz[index[int(parent)]], xyz[i]
        length = float(np.linalg.norm(b - a))
        if length == 0:
            continue
        n = max(1, int(np.ceil(length / step)))
        t = (np.arange(n, dtype=np.float64) + .5) / n
        pieces.append(a + t[:, None] * (b - a))
        lengths.append(length)
    assert pieces
    return np.concatenate(pieces), {"samples": int(sum(len(p) for p in pieces)),
                                    "segments": len(pieces),
                                    "cable_length_um": float(sum(lengths)),
                                    "missing_parent_links": skipped_parent}


def main():
    annotations = pd.read_feather(ANNOT)
    selected = annotations[(annotations.entryNerve == "ProLN")
                           & (annotations.rootSide == "L")
                           & (annotations["subclass"] == "chordotonal organ")]
    ids = sorted(selected.bodyId.astype(int).tolist())
    assert len(ids) == 23 and 912317 in ids
    src_manifest = SOURCE / "source_manifest.json"
    dst_manifest = TARGET / "source_manifest.json"
    source = json.loads(src_manifest.read_text())
    target = json.loads(dst_manifest.read_text())
    source_items = {x["body_id"]: x for x in source["entries"]}
    assert target["release"] == "MANC 1.2.1, not MANC 1.0"
    prior = json.loads(PRIOR.read_text())
    assert prior["source_manifest_sha256"] == sha(src_manifest)
    assert prior["target_manifest_sha256"] == sha(dst_manifest)
    targets = {}
    for item in target["files"]:
        path = TARGET / f'{item["body_id"]}.swc'
        assert sha(path) == item["sha256"]
        swc = np.loadtxt(path, comments="#")
        by_step = {str(step): cable_samples(swc, swc[:, 2:5], step)
                   for step in STEPS_UM}
        targets[item["body_id"]] = by_step
    reg_manifest = REG / "source_manifest.json"
    for item in json.loads(reg_manifest.read_text())["files"]:
        assert sha(REG / item["name"]) == item["sha256"]
    os.environ["FLYBRAINS_DATA"] = str(REG)
    os.environ["PATH"] = str(REG / "elastix_runtime") + os.pathsep + os.environ["PATH"]
    import flybrains  # noqa: F401
    import navis
    route, _ = navis.transforms.registry.find_bridging_path("JRCFIB2022Mraw", "MANC")
    assert route == prior["route"]
    rows = []
    for idx, body_id in enumerate(ids, 1):
        path = SOURCE / f"{body_id}.swc"
        assert sha(path) == source_items[body_id]["sha256"]
        swc = np.loadtxt(path, comments="#")
        mapped_um = np.asarray(navis.xform_brain(swc[:, 2:5].copy(),
                                                  source="JRCFIB2022Mraw", target="MANC")) / 1000
        assert np.isfinite(mapped_um).all()
        row = {"malecns_body_id": body_id,
               "malecns_type": str(selected.loc[selected.bodyId == body_id, "type"].iloc[0]),
               "steps": {}}
        for step in STEPS_UM:
            key = str(step)
            source_points, source_geom = cable_samples(swc, mapped_um, step)
            source_tree = cKDTree(source_points)
            step_result = {"source_geometry": source_geom, "targets": {}}
            for target_id, by_step in targets.items():
                target_points, target_geom = by_step[key]
                forward = cKDTree(target_points).query(source_points)[0]
                reverse = source_tree.query(target_points)[0]
                step_result["targets"][str(target_id)] = {
                    "source_to_target_median_um": float(np.median(forward)),
                    "target_to_source_median_um": float(np.median(reverse)),
                    "bidirectional_median_mean_um": float((np.median(forward) + np.median(reverse)) / 2),
                    "target_geometry": target_geom,
                }
            row["steps"][key] = step_result
        rows.append(row)
        print(f"{idx}/{len(ids)} body {body_id}", flush=True)
    rankings = {str(step): {str(target_id): [r["malecns_body_id"] for r in sorted(
        rows, key=lambda r: r["steps"][str(step)]["targets"][str(target_id)]["bidirectional_median_mean_um"])]
        for target_id in targets} for step in STEPS_UM}
    report = {"scope": "Cable-resampled cross-release morphology specificity; no identity proof",
              "selection": prior["selection"], "malecns_release": "v1.0",
              "manc_release": target["release"], "steps_um_predeclared": STEPS_UM,
              "method": "SWC parent segments sampled at segment-midpoint grid with max spacing step; median nearest-point distance in both directions; equal-weight mean of medians",
              "annotation_sha256": sha(ANNOT), "source_manifest_sha256": sha(src_manifest),
              "target_manifest_sha256": sha(dst_manifest),
              "transform_manifest_sha256": sha(reg_manifest), "prior_report_sha256": sha(PRIOR),
              "route": route, "rows": rows, "rankings": rankings,
              "validates_manc_v1_identity": False}
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({s: {t: v[:5] for t, v in m.items()} for s, m in rankings.items()}, indent=2))


if __name__ == "__main__":
    main()
