"""Audit published Neuroglancer retinotopy layer against accepted right columns."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/visualpathways/retinotopy"
COLUMNS = ROOT / "data/derived/malecns_optic_columns/columns.csv"
OUT = ROOT / "reports/visualpathways_retinotopy_layer_boundary.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((SOURCE / "source_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        file = ROOT / entry["file"]
        assert file.stat().st_size == entry["bytes"] and sha(file) == entry["sha256"]
    column_report = json.loads((ROOT / "reports/optic_column_index.json").read_text(encoding="utf-8"))
    assert sha(COLUMNS) == column_report["files"]["columns.csv"]
    state = json.loads((SOURCE / "neuroglancer-state.json").read_text(encoding="utf-8"))
    props = json.loads((SOURCE / "right-column-properties.json").read_text(encoding="utf-8"))
    annotation = json.loads((SOURCE / "tbar-annotation-info.json").read_text(encoding="utf-8"))
    layer = next(x for x in state["layers"] if x.get("name") == "ME(R)-columns-r-theta")
    tbar = next(x for x in state["layers"] if x.get("name") == "retinotopy_tbar_olr_points")
    assert layer["type"] == "segmentation" and tbar["type"] == "annotation"
    assert len(props["inline"]["properties"]) == 1
    assert props["inline"]["properties"][0]["id"] == "label"
    ids = props["inline"]["ids"]
    labels = props["inline"]["properties"][0]["values"]
    assert len(ids) == len(labels) == 892
    assert len(set(ids)) == len(ids) and len(set(labels)) == len(labels)
    pairs = {tuple(map(int, label.split(","))) for label in labels}
    columns = pd.read_csv(COLUMNS).query("side == 'R'")
    prior_pairs = set(zip(columns.hex1.astype(int), columns.hex2.astype(int)))
    assert len(columns) == len(prior_pairs) == 892
    assert pairs == prior_pairs
    assert set(layer["segments"]) == set(ids)
    assert set(layer["segmentColors"]) == set(ids)
    fields = {x["id"]: x["type"] for x in annotation["properties"]}
    assert all(fields.get(x) == "float32" for x in ("hex1", "hex2", "r", "theta"))
    result = {
        "scope": "Published right medulla column labels and retinotopic T-bar annotation schema; no receptor ray calibration",
        "source_manifest_sha256": sha(SOURCE / "source_manifest.json"),
        "accepted_columns_sha256": sha(COLUMNS),
        "right_column_count": len(prior_pairs),
        "right_column_labels_exact_match": True,
        "layer_type": layer["type"],
        "layer_has_numeric_r_theta_per_column": any(x["id"] in ("r", "theta")
             for x in props["inline"]["properties"]),
        "segment_color_count": len(layer["segmentColors"]),
        "tbar_layer_type": tbar["type"],
        "tbar_annotation_properties": fields,
        "tbar_r_theta_properties_present": "r" in fields and "theta" in fields,
        "interpretation": "The column layer supplies exact hex labels and display colors. Numeric r/theta belong to a separate predicted retinotopic T-bar annotation, not to measured photoreceptor optical axes or a per-column ray table.",
        "male_cns_neuron_to_ray_assigned": False,
        "visual_input_enabled": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("right_column_count",
       "right_column_labels_exact_match", "layer_has_numeric_r_theta_per_column",
       "tbar_r_theta_properties_present")}, indent=2))


if __name__ == "__main__":
    main()

