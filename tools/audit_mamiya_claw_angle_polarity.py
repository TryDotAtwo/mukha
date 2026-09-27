"""Describe claw calcium-versus-angle polarity without assigning MaleCNS cells."""
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT

BASE = ROOT / "data/derived/mamiya2018_recordings_v1"
REPORT = ROOT / "reports/mamiya_claw_angle_polarity.json"
PROTOCOLS = ("RampAndHold_FlexFirst", "RampAndHold_ExtFirst")
REGIONS = ("XBranch", "YBranch", "ZBranch")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = BASE / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    entries = []
    summaries = []
    for region in REGIONS:
        path = BASE / f"R73D10_GCaMP6f_{region}.npz"
        assert digest(path) == manifest["files"][path.name]
        with np.load(path, allow_pickle=False) as arrays:
            for protocol in PROTOCOLS:
                response = arrays[protocol + "_DFF"]
                angle = arrays[protocol + "_Angle"]
                flies = arrays[protocol + "_Fly"]
                clusters = arrays[protocol + "_Cluster"]
                assert response.shape == angle.shape == (20, 451)
                assert len(flies) == len(clusters) == 20
                contrasts = []
                for row in range(20):
                    valid = np.isfinite(response[row]) & np.isfinite(angle[row])
                    assert valid.sum() > 100
                    a = angle[row, valid]
                    y = response[row, valid]
                    low, high = np.quantile(a, [.1, .9])
                    assert high > low
                    lower = float(np.median(y[a <= low]))
                    upper = float(np.median(y[a >= high]))
                    delta = upper - lower
                    contrasts.append(delta)
                    entries.append({"region": region, "protocol": protocol,
                                    "fly_id_within_file": int(flies[row]),
                                    "cluster_id_within_trial": int(clusters[row]),
                                    "source_row": row, "angle_low_decile_max_deg": float(low),
                                    "angle_high_decile_min_deg": float(high),
                                    "dff_median_at_low_angle": lower,
                                    "dff_median_at_high_angle": upper,
                                    "high_minus_low_angle_dff": delta})
                signed = np.sign(contrasts)
                fly_counts = []
                for fly in np.unique(flies):
                    rows = np.flatnonzero(flies == fly)
                    assert len(rows) == 2 and len(set(clusters[rows])) == 2
                    signs = signed[rows]
                    fly_counts.append(bool(signs[0] * signs[1] < 0))
                summaries.append({"region": region, "protocol": protocol,
                                  "positive_high_minus_low": int((signed > 0).sum()),
                                  "negative_high_minus_low": int((signed < 0).sum()),
                                  "zero": int((signed == 0).sum()),
                                  "fly_trials_with_opposite_cluster_signs": int(sum(fly_counts)),
                                  "fly_trials": len(fly_counts)})
    report = {"source_archive_sha256": manifest["source_archive_sha256"],
              "source_manifest_sha256": digest(manifest_path),
              "source_file_sha256": {f"R73D10_GCaMP6f_{r}.npz": manifest["files"][f"R73D10_GCaMP6f_{r}.npz"] for r in REGIONS},
              "contrast": "Within each pixel-cluster row: median delta F/F at frames in top angle decile minus median at bottom angle decile; all finite pairs, no temporal model.",
              "angle_interpretation": "Source labels average tibia angle per frame; this audit does not register it to FlyMimic q or MaleCNS SNpp50.",
              "summaries": summaries, "rows": entries,
              "limits": ["Clusters are based on response similarity and are not cell identities.",
                         "Repeated rows within fly/protocol are not independent animals.",
                         "Angle, time, and movement direction covary; contrast is descriptive, not a fitted encoder.",
                         "No membrane voltage, spike rate, MaleCNS cell correspondence, or gain is observed."],
              "runtime_enabled": False}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
