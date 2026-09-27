"""Verify published MaleCNS right medulla column center pins, without optical assignment."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/malecns_eye_pins"
COLUMNS = ROOT / "data/derived/malecns_optic_columns/columns.csv"
OUT = ROOT / "data/derived/right_medulla_pins_v1"
REPORT = ROOT / "reports/malecns_right_medulla_pin_geometry.json"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    manifest = json.loads((SOURCE / "source_manifest.json").read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = ROOT / record["path"]
        assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"]
    old_report = json.loads((ROOT / "reports/optic_column_index.json").read_text(encoding="utf-8"))
    assert sha(COLUMNS) == old_report["files"]["columns.csv"]
    data = pd.read_csv(SOURCE / "ME_pindata.csv")
    assert list(data.columns) == ["Unnamed: 0", "hex1_id", "hex2_id",
                                   "bin_depth", "x", "y", "z", "roi"]
    assert len(data) == 892 * 121 and set(data.roi) == {"ME_R"}
    assert not data.duplicated(["hex1_id", "hex2_id", "bin_depth"]).any()
    assert np.isfinite(data[["x", "y", "z"]].to_numpy()).all()
    data = data.sort_values(["hex1_id", "hex2_id", "bin_depth"])
    groups = data.groupby(["hex1_id", "hex2_id"], sort=True)
    assert len(groups) == 892
    assert (groups.size() == 121).all()
    assert (groups.bin_depth.min() == 0).all() and (groups.bin_depth.max() == 120).all()
    coords = data[["x", "y", "z"]].to_numpy().reshape(892, 121, 3)
    steps = np.linalg.norm(np.diff(coords, axis=1), axis=2)
    assert np.isfinite(steps).all() and (steps > 0).all()
    arc = steps.sum(axis=1)
    displacement = coords[:, -1] - coords[:, 0]
    chord = np.linalg.norm(displacement, axis=1)
    assert (chord > 0).all() and (arc >= chord - 1e-8).all()
    keys = list(groups.size().index)
    old = pd.read_csv(COLUMNS).query("side == 'R'")
    assert set(keys) == set(zip(old.hex1.astype(int), old.hex2.astype(int)))
    rows = []
    for i, (h1, h2) in enumerate(keys):
        direction = displacement[i] / chord[i]
        rows.append({"hex1": int(h1), "hex2": int(h2),
                     **{f"start_{axis}": float(coords[i, 0, j]) for j, axis in enumerate("xyz")},
                     **{f"end_{axis}": float(coords[i, -1, j]) for j, axis in enumerate("xyz")},
                     **{f"internal_axis_{axis}": float(direction[j]) for j, axis in enumerate("xyz")},
                     "centerline_arc_source_units": float(arc[i]),
                     "endpoint_chord_source_units": float(chord[i]),
                     "chord_over_arc": float(chord[i] / arc[i])})
    OUT.mkdir(parents=True, exist_ok=True)
    axes = OUT / "axes.csv"
    pd.DataFrame(rows).to_csv(axes, index=False, float_format="%.17g")
    report = {
        "scope": "Verified right medulla anatomical centerlines, not ommatidial optical rays",
        "source_manifest_sha256": sha(SOURCE / "source_manifest.json"),
        "source_pindata_sha256": sha(SOURCE / "ME_pindata.csv"),
        "accepted_columns_sha256": sha(COLUMNS),
        "source_rows": len(data), "columns": len(keys), "depth_bins_per_column": 121,
        "exact_right_column_coverage": True,
        "step_norm_source_units": {"min": float(steps.min()), "median": float(np.median(steps)),
                                   "max": float(steps.max())},
        "chord_over_arc": {"min": float(np.min(chord / arc)),
                           "median": float(np.median(chord / arc)),
                           "max": float(np.max(chord / arc))},
        "axes_csv_sha256": sha(axes),
        "interpretation": "Source center pins include smoothing/filling. Endpoint direction follows internal medulla depth; it is not a measured optical axis, lacks eye-to-body registration, and cannot be used to stimulate photoreceptors.",
        "neuron_to_ray_assigned": False,
        "visual_input_enabled": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("source_rows", "columns",
          "depth_bins_per_column", "exact_right_column_coverage", "chord_over_arc")}, indent=2))


if __name__ == "__main__":
    main()

