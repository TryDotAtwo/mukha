"""Quantify published 13Balpha hysteresis against the current angle-only input.

This is a necessary sensory-input capability audit, not a full-CNS fit.
"""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
figure = root / "data/reference/agrawal2020/figure2g_digitized.csv"
figure_report = json.loads((root / "reports/agrawal_13b_figure2g.json").read_text())
assert hashlib.sha256(figure.read_bytes()).hexdigest() == figure_report["csv_sha256"]
spec_path = root / "configs/lf_tibia_passive_movement_probe.json"
spec = json.loads(spec_path.read_text())
source = (root / "tools/probe_lf_tibia_passive_movement.py").read_text()
assert "max(0.0, polarity * angle)" in source
assert "spec[\"sensor_gain_mv_per_rad\"]" in source
assert spec["sensor_gain_mv_per_rad"] > 0

with figure.open(newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))
curves = {}
raw_points = {}
for direction in ("extension", "flexion"):
    subset = [row for row in rows if row["direction"] == direction]
    curves[direction] = (np.array([float(row["angle_deg_approx"]) for row in subset]),
                         np.array([float(row["normalized_mean_approx"]) for row in subset]))
    raw_points[direction] = (np.array([float(row["pdf_x_pt"]) for row in subset]),
                             np.array([float(row["pdf_y_pt"]) for row in subset]))
    assert len(subset) == 11 and np.all(np.diff(curves[direction][0]) > 0)

base = figure_report["axis_calibration_pdf_points"]
anchor_variants = []
for shifts in itertools.product((-1.5, 1.5), repeat=4):
    x0 = base["x_0_deg"] + shifts[0]
    x180 = base["x_180_deg"] + shifts[1]
    y0 = base["y_0_normalized"] + shifts[2]
    y1 = base["y_1_normalized"] + shifts[3]
    assert x180 > x0 and y0 > y1
    variant = {}
    for direction, (x, y) in raw_points.items():
        variant[direction] = ((x - x0) * 180 / (x180 - x0), (y0 - y) / (y0 - y1))
    anchor_variants.append(variant)

comparisons = []
for angle in (90.0, 120.0, 150.0):
    means = {direction: float(np.interp(angle, *curves[direction])) for direction in curves}
    reference_gap = means["extension"] - means["flexion"]
    shared_gaps = [float(np.interp(angle, *variant["extension"]) -
                         np.interp(angle, *variant["flexion"])) for variant in anchor_variants]
    # Deliberately conservative: allow the two colored paths to use separate
    # axis-anchor perturbations, although they share axes in the actual panel.
    independent_gaps = [float(np.interp(angle, *extension["extension"]) -
                              np.interp(angle, *flexion["flexion"]))
                        for extension in anchor_variants for flexion in anchor_variants]
    comparisons.append({"angle_deg_approx": angle,
                        "reference_extension_normalized": means["extension"],
                        "reference_flexion_normalized": means["flexion"],
                        "reference_approach_gap_normalized": reference_gap,
                        "gap_range_shared_axis_perturbations": [min(shared_gaps), max(shared_gaps)],
                        "gap_range_independent_axis_perturbations": [min(independent_gaps), max(independent_gaps)],
                        "instantaneous_angle_formula_gap_at_equal_angle_mv": 0.0})

p = {"membrane_ms": 20.0, "synapse_ms": 5.0}
hold_ms = 1000.0  # source panel takes the middle second of each 3-s step
report = {"figure_csv_sha256": figure_report["csv_sha256"],
          "source_encoder_sha256": hashlib.sha256((root / "tools/probe_lf_tibia_passive_movement.py").read_bytes()).hexdigest(),
          "encoder_spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
          "protocol": "13Balpha Figure 2G; steady state measured in middle second of each 3-s angle hold",
          "comparisons": comparisons,
          "digitization_sensitivity": "All ±1.5-PDF-point endpoint perturbations; shared and independent axis cases. These ranges are neither confidence intervals nor animal variability.",
          "isolated_lif_decay_after_1s": {"membrane": math.exp(-hold_ms / p["membrane_ms"]),
                                          "synapse": math.exp(-hold_ms / p["synapse_ms"])},
          "result": "The inspected instantaneous f(angle) has no explicit approach-history state; the published 13Balpha figure means differ by approach.",
          "runtime_opposite_history_experiment_performed": False,
          "limitations": ["The full recurrent graph was not run on this protocol and could retain internal state.",
                          "Different angle histories produce different time-series inputs even when their final instantaneous values agree.",
                          "Figure curves are normalized group means, not individual voltage or raw recordings.",
                          "Digitization sensitivity does not measure between-animal uncertainty.",
                          "The old encoder offset, sign and gain are not calibrated to the Agrawal preparation.",
                          "An isolated LIF relaxation bound is not a bound on the complete recurrent CNS."],
          "biological_reaction_reproduced": False}
(root / "reports/agrawal_13b_hysteresis_gate.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(comparisons))
