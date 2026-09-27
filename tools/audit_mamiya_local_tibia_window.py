"""Describe author claw calcium observations in the body's 20-degree window.

Descriptive only: source calcium clusters are not MaleCNS cell identities.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT


SOURCE = ROOT / "data/derived/mamiya2018_recordings_v1"
BODY = ROOT / "reports/flymimic_prescribed_tibia_cycle.json"
OUT = ROOT / "reports/mamiya_local_tibia_window.json"
PROTOCOLS = ("RampAndHold_FlexFirst", "RampAndHold_ExtFirst")
REGIONS = ("XBranch", "YBranch", "ZBranch")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = SOURCE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    body = json.loads(BODY.read_text(encoding="utf-8"))
    center = body["body_origin_angle_baseline_deg"]
    lo, hi = center - 10, center + 10
    rows = []
    summaries = []
    for region in REGIONS:
        path = SOURCE / f"R73D10_GCaMP6f_{region}.npz"
        assert sha(path) == manifest["files"][path.name]
        with np.load(path) as z:
            for protocol in PROTOCOLS:
                angle, dff = z[protocol + "_Angle"], z[protocol + "_DFF"]
                flies, clusters = z[protocol + "_Fly"], z[protocol + "_Cluster"]
                assert angle.shape == dff.shape == (20, 451)
                scoped = []
                for i in range(20):
                    valid = np.isfinite(angle[i]) & np.isfinite(dff[i])
                    lower = dff[i, valid & (angle[i] >= lo) & (angle[i] < center)]
                    upper = dff[i, valid & (angle[i] >= center) & (angle[i] <= hi)]
                    sufficient = len(lower) >= 3 and len(upper) >= 3
                    delta = float(np.median(upper) - np.median(lower)) if sufficient else None
                    entry = {"region": region, "protocol": protocol,
                             "fly_id_within_file": int(flies[i]),
                             "cluster_id_within_trial": int(clusters[i]),
                             "low_half_samples": len(lower),
                             "high_half_samples": len(upper),
                             "high_minus_low_median_dff": delta}
                    rows.append(entry)
                    scoped.append(entry)
                valid_entries = [r for r in scoped if r["high_minus_low_median_dff"] is not None]
                opposite = 0
                for fly in np.unique(flies):
                    pair = [r for r in scoped if r["fly_id_within_file"] == fly]
                    if len(pair) == 2 and all(r["high_minus_low_median_dff"] is not None for r in pair):
                        opposite += pair[0]["high_minus_low_median_dff"] * pair[1]["high_minus_low_median_dff"] < 0
                summaries.append({"region": region, "protocol": protocol,
                                  "rows_with_both_halves_at_least_3_samples": len(valid_entries),
                                  "positive_contrast": sum(r["high_minus_low_median_dff"] > 0 for r in valid_entries),
                                  "negative_contrast": sum(r["high_minus_low_median_dff"] < 0 for r in valid_entries),
                                  "paired_flies_with_opposite_contrasts": int(opposite)})
    report = {"scope": "Descriptive author GCaMP cluster contrast within FlyMimic's chosen 20-degree movement window",
              "source_manifest_sha256": sha(manifest_path), "body_report_sha256": sha(BODY),
              "angle_window_deg": [lo, center, hi], "source_files": {
                  p.name: sha(p) for p in (SOURCE / f"R73D10_GCaMP6f_{r}.npz" for r in REGIONS)},
              "minimum_samples_per_half": 3, "summaries": summaries, "rows": rows,
              "limitations": ["Calcium fluorescence is not voltage or spikes",
                              "Angle covaries with time and movement direction in ramp-and-hold recordings",
                              "Clusters are not identified MaleCNS neurons",
                              "FlyMimic body-origin angle is not registered to source video angle",
                              "The selected body center is not an experimental setpoint"],
              "sensor_transfer_calibrated": False}
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
