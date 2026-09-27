"""Resolve the recorded tibia-angle direction in author claw calcium trials.

The result orients the author's angle scale, not MaleCNS cell polarity or
FlyMimic joint coordinates.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT


MANIFEST = ROOT / "reports/mamiya2018_recordings.json"
REPORT = ROOT / "reports/mamiya_claw_angle_direction.json"
FILES = ("R73D10_GCaMP6f_XBranch.npz", "R73D10_GCaMP6f_YBranch.npz",
         "R73D10_GCaMP6f_ZBranch.npz")
PROTOCOLS = (("RampAndHold_FlexFirst", "extended", "high"),
             ("RampAndHold_ExtFirst", "flexed", "low"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not REPORT.exists()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = []
    for name in FILES:
        path = ROOT / "data/derived/mamiya2018_recordings_v1" / name
        assert sha(path) == manifest["files"][name]
        with np.load(path) as source:
            for prefix, start_label, expected_end in PROTOCOLS:
                angle = source[prefix + "_Angle"]
                assert angle.shape[0] == 20
                start = np.nanmedian(angle[:, :3], axis=1)
                low = np.nanmin(angle, axis=1)
                high = np.nanmax(angle, axis=1)
                fraction = (start - low) / (high - low)
                assert np.isfinite(fraction).all()
                assert np.all(high - low > 100.0)
                if expected_end == "high":
                    assert np.all(fraction > 0.9)
                else:
                    assert np.all(fraction < 0.1)
                records.append({"file": name, "protocol": prefix,
                                "author_start_position": start_label,
                                "rows": int(len(fraction)),
                                "initial_position_fraction_min": float(fraction.min()),
                                "initial_position_fraction_median": float(np.median(fraction)),
                                "initial_position_fraction_max": float(fraction.max()),
                                "initial_angle_deg_median": float(np.median(start)),
                                "angle_min_deg_median": float(np.median(low)),
                                "angle_max_deg_median": float(np.median(high))})
    assert len(records) == 6 and sum(record["rows"] for record in records) == 120
    result = {"source_manifest_sha256": sha(MANIFEST),
              "source_archive_sha256": manifest["source_archive_sha256"],
              "source_npz_sha256": {name: manifest["files"][name] for name in FILES},
              "method": "For each calcium-cluster row, median first three measured-angle frames, normalized between its finite trial minimum and maximum; FlexFirst starts extended and ExtFirst starts flexed in author README.",
              "initial_frames": 3, "frame_rate_hz": manifest["frames_per_second_from_author_readme"],
              "records": records,
              "recorded_angle_direction": "High recorded degrees correspond to the extended tibia; low recorded degrees to the flexed tibia in all six R73D10 ramp-and-hold tables.",
              "malecns_snpp50_polarity_identified": False,
              "flymimic_joint_q_registration_identified": False,
              "limitations": ["Rows are response-derived pixel clusters, not individually traced axons",
                              "Anatomical matching of R73D10 clusters to MaleCNS SNpp50/SNpp51 is absent",
                              "No calcium-to-spike or calcium-to-voltage observation model has been fitted"]}
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": sum(x["rows"] for x in records),
                      "flex_first_initial_fraction_range": [min(x["initial_position_fraction_min"] for x in records if "FlexFirst" in x["protocol"]),
                                                            max(x["initial_position_fraction_max"] for x in records if "FlexFirst" in x["protocol"])],
                      "ext_first_initial_fraction_range": [min(x["initial_position_fraction_min"] for x in records if "ExtFirst" in x["protocol"]),
                                                           max(x["initial_position_fraction_max"] for x in records if "ExtFirst" in x["protocol"])]}, indent=2))


if __name__ == "__main__":
    main()
