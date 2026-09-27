"""Map a prescribed FlyMimic knee trace to Mamiya 2023 Fig. 3G kinematics.

The result is a 2D population-mean plot-coordinate observation, not a tendon
attachment, mechanical simulation, individual-fly measurement or neural drive.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
body_path = root / "data/derived/flymimic_prescribed_tibia_cycle_v1/kinematics.npz"
body_report = json.loads((root / "reports/flymimic_prescribed_tibia_cycle.json").read_text())
assert hashlib.sha256(body_path.read_bytes()).hexdigest() == body_report["trace_sha256"]
source_path = root / "reports/mamiya_arculum_centroid_fig3g.json"
source = json.loads(source_path.read_text())
pdf = root / "data/reference/mamiya2023/mamiya_2023.pdf"
assert hashlib.sha256(pdf.read_bytes()).hexdigest() == source["source_sha256"]

with np.load(body_path) as body:
    time = body["time_s"].copy()
    knee = body["actual_interior_angle_deg"].copy()
assert len(time) == len(knee) == 5001
angles = np.asarray(source["point_angle_estimate_deg"], dtype=np.float64)
xy = np.asarray(source["mean_path_points_um_relative_to_first"], dtype=np.float64)
assert xy.shape == (len(angles), 2) and np.all(np.diff(angles) > 0)
assert angles[0] < knee.min() and knee.max() < angles[-1], "extrapolation forbidden"
source_arc_um = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
observed_xy = np.column_stack([np.interp(knee, angles, xy[:, column]) for column in (0, 1)])
observed_arc = np.interp(knee, angles, source_arc_um)
assert np.isfinite(observed_xy).all() and np.isfinite(observed_arc).all()
assert np.array_equal(observed_xy[0], observed_xy[-1])
assert np.array_equal(observed_arc[0:1], observed_arc[-1:])

out_dir = root / "data/derived/flymimic_arculum_observation_v1"
assert not out_dir.exists()
out_dir.mkdir(parents=True)
out = out_dir / "observation.npz"
np.savez_compressed(out, time_s=time, knee_interior_angle_deg=knee,
                    arculum_plot_x_um=observed_xy[:, 0],
                    arculum_plot_y_um=observed_xy[:, 1],
                    arculum_plot_path_coordinate_um=observed_arc)
report = {"scope": "Angle-indexed observation from Mamiya 2023 Fig. 3G on a prescribed FlyMimic cycle",
          "source_report_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
          "body_trace_sha256": body_report["trace_sha256"],
          "body_report_sha256": hashlib.sha256((root / "reports/flymimic_prescribed_tibia_cycle.json").read_bytes()).hexdigest(),
          "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
          "source_angle_range_deg": [float(angles[0]), float(angles[-1])],
          "body_angle_range_deg": [float(knee.min()), float(knee.max())],
          "arculum_plot_x_range_um": [float(observed_xy[:, 0].min()), float(observed_xy[:, 0].max())],
          "arculum_plot_y_range_um": [float(observed_xy[:, 1].min()), float(observed_xy[:, 1].max())],
          "arculum_plot_path_coordinate_range_um": [float(observed_arc.min()), float(observed_arc.max())],
          "interpolation": "Linear in estimated source angle; no extrapolation",
          "limitations": ["Source is a figure mean from female flies, not a male specimen measurement.",
                          "Source figure angles are colorbar estimates, not raw per-frame angles.",
                          "2D plot coordinates have no registered FlyMimic anatomical axes or attachment point.",
                          "The lookup has no direction dependence and therefore cannot model FeCO hysteresis.",
                          "No arculum mass, force, cap-cell strain, sensor current or neural response is inferred."],
          "mechanical_sensor_implemented": False,
          "biological_response_validated": False}
(root / "reports/flymimic_arculum_observation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: report[key] for key in ("body_angle_range_deg", "arculum_plot_x_range_um",
                                                "arculum_plot_y_range_um", "arculum_plot_path_coordinate_range_um")}))
