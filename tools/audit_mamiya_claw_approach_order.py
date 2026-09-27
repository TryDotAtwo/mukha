"""Exploratory within-trial claw calcium contrast by approach and protocol.

No pixel-cluster cross-protocol identity, spike transduction or mechanics fit.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
base = root / "data/derived/mamiya2018_recordings_v1"
manifest_path = base / "manifest.json"
manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
manifest = json.loads(manifest_path.read_text())
assert manifest["source_archive_sha256"] == "31565245097ca8a9f572555aa32e7f20052ac2a1cd9dcc45ce1803c7858973d2"
regions = ("XBranch", "YBranch", "ZBranch")
protocols = ("RampAndHold_FlexFirst", "RampAndHold_ExtFirst")
targets = (97.0, 116.0, 135.0, 154.0)
all_rows = []
source_hashes = {}


def centered_plateau(angle, response, lo, hi, target):
    ix = np.flatnonzero(np.isfinite(angle[lo:hi]) &
                       (np.abs(angle[lo:hi] - target) <= 3.0)) + lo
    runs = np.split(ix, np.flatnonzero(np.diff(ix) > 1) + 1)
    longest = max(runs, key=len) if runs else np.array([], dtype=int)
    if len(longest) < 12:
        return None
    center = len(longest) // 2
    selected = longest[center - 4:center + 4]
    assert len(selected) == 8 and np.all(np.isfinite(response[selected]))
    return {"start_frame": int(selected[0]), "end_frame": int(selected[-1]),
            "median_angle_deg": float(np.median(angle[selected])),
            "median_dff": float(np.median(response[selected]))}


for region in regions:
    source = base / f"R73D10_GCaMP6f_{region}.npz"
    source_hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hashes[source.name] == manifest["files"][source.name]
    with np.load(source) as data:
        for protocol in protocols:
            angles = data[protocol + "_Angle"]
            responses = data[protocol + "_DFF"]
            flies = data[protocol + "_Fly"]
            clusters = data[protocol + "_Cluster"]
            assert angles.shape == responses.shape and angles.shape[0] == len(flies) == len(clusters)
            for row_index, (angle, response) in enumerate(zip(angles, responses)):
                turn = (int(np.nanargmin(angle)) if "FlexFirst" in protocol
                        else int(np.nanargmax(angle)))
                scale = float(np.percentile(response, 95) - np.percentile(response, 5))
                if not np.isfinite(scale) or scale <= 0:
                    continue
                for target in targets:
                    first = centered_plateau(angle, response, 0, turn + 1, target)
                    second = centered_plateau(angle, response, turn, len(angle), target)
                    if first is None or second is None:
                        continue
                    flex, extension = ((first, second) if "FlexFirst" in protocol
                                       else (second, first))
                    all_rows.append({"region": region, "protocol": protocol,
                                     "row_index": row_index, "fly_label": int(flies[row_index]),
                                     "cluster_label": int(clusters[row_index]),
                                     "target_angle_deg": target,
                                     "flexion_approach": flex, "extension_approach": extension,
                                     "response_scale_p95_minus_p5": scale,
                                     "extension_minus_flexion_dff": extension["median_dff"] - flex["median_dff"],
                                     "extension_minus_flexion_over_row_range":
                                         (extension["median_dff"] - flex["median_dff"]) / scale})

summaries = []
for target in targets:
    for protocol in protocols:
        subset = [r for r in all_rows if r["target_angle_deg"] == target and r["protocol"] == protocol]
        values = [r["extension_minus_flexion_over_row_range"] for r in subset]
        summaries.append({"target_angle_deg": target, "protocol": protocol,
                          "included_rows": len(values),
                          "median_normalized_approach_difference": float(np.median(values)) if values else None,
                          "positive_rows": sum(x > 0 for x in values)})

report = {"scope": "Exploratory descriptive R73D10 GCaMP pixel-cluster contrast, not receptor current",
          "source_manifest_sha256": manifest_sha, "source_npz_sha256": source_hashes,
          "frame_rate_hz_from_author_description": 8.01,
          "selection": "Within each direction half, longest contiguous ±3-degree plateau of at least 12 frames; middle 8 frames",
          "normalization": "Within-trial response 95th minus 5th percentile",
          "target_angles_deg": targets, "summaries": summaries, "rows": all_rows,
          "limitations": ["Target bins and analysis were explored after seeing these recordings, not a fresh validation set.",
                          "Matching fly/cluster row labels across protocols do not prove identical physical pixels or cells.",
                          "GCaMP dynamics, trial order and stimulus history confound tissue mechanics.",
                          "Cluster polarity does not identify a MaleCNS SNpp50 or SNpp51 cell."],
          "mechanical_hysteresis_calibrated": False,
          "male_cns_sensor_current_calibrated": False}
(root / "reports/mamiya_claw_approach_order.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"summaries": summaries, "row_records": len(all_rows)}))
