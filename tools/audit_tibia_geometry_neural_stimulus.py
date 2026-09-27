"""Register the existing neural tibia stimulus to the pinned FlyMimic geometry.

This checks a geometric correspondence only; the encoder remains unmeasured.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT


TRACE = ROOT / "data/derived/flymimic_prescribed_tibia_cycle_v1/kinematics.npz"
OLD = ROOT / "data/derived/lf_tibia_passive_movement_v1/prescribed_angle_rad.npy"
SPEC = ROOT / "configs/lf_tibia_passive_movement_probe.json"
OUT = ROOT / "reports/tibia_geometry_neural_stimulus_audit.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    geometry = np.load(TRACE)
    old = np.load(OLD)
    t = geometry["time_s"][:-1]
    actual = geometry["actual_interior_angle_deg"][:-1]
    baseline = float(geometry["actual_interior_angle_deg"][0])
    relative_rad = np.deg2rad(actual - baseline)
    assert len(t) == len(old) == spec["ticks"]
    assert np.allclose(t, np.arange(len(old)) * spec["dt_ms"] / 1000, atol=1e-14)
    difference = relative_rad - old
    gain = spec["sensor_gain_mv_per_rad"]
    drive_errors = {}
    for case, sign in (("positive_angle_half_wave", 1),
                       ("negative_angle_half_wave", -1)):
        geometric_drive = gain * np.maximum(0, sign * relative_rad)
        previous_drive = gain * np.maximum(0, sign * old)
        drive_errors[case] = {
            "max_abs_drive_difference_mv": float(np.max(np.abs(
                geometric_drive - previous_drive))),
            "active_ticks_geometric": int(np.count_nonzero(geometric_drive)),
            "active_ticks_previous": int(np.count_nonzero(previous_drive)),
        }
    report = {
        "scope": "Geometric registration of existing full-CNS diagnostic stimulus to the FlyMimic source body",
        "geometry_trace_sha256": sha(TRACE),
        "old_neural_angle_sha256": sha(OLD),
        "neural_spec_sha256": sha(SPEC),
        "sample_count": len(old),
        "sample_alignment": "first 5000 of 5001 body positions; t=0 through 0.4999 s",
        "angle_reference": "actual 3D interior angle at t=0; larger angle is extension",
        "max_abs_relative_angle_difference_deg": float(np.rad2deg(np.max(np.abs(difference)))),
        "max_abs_relative_angle_difference_rad": float(np.max(np.abs(difference))),
        "drive_errors": drive_errors,
        "sensor_transfer_measured": False,
        "sensory_cell_polarity_identified": False,
        "biological_response_validated": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"angle_error_deg": report["max_abs_relative_angle_difference_deg"],
                      "drive_errors": drive_errors}, indent=2))


if __name__ == "__main__":
    main()
