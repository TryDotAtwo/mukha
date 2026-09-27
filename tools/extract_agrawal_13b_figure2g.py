"""Digitize the two publisher-vector mean curves in Agrawal 2020 Fig. 2G.

Axis anchors were read from the rendered page. This is a normalized figure
trace, not raw electrophysiology or an individual neuron's voltage recording.
"""
import csv
import hashlib
import json
from pathlib import Path

import fitz

root = Path(__file__).resolve().parents[1]
pdf = root / "data/reference/agrawal2020/elife-60299-v2.pdf"
source_sha = "8c69fc15a85e13740c38ad7488211423d9718febb0472144b4be3b16d303cf04"
assert hashlib.sha256(pdf.read_bytes()).hexdigest() == source_sha
page = fitz.open(pdf)[4]

# Manually read plotting-axis intersections in PDF points from the 2x preview.
# Allow roughly 1.5 PDF pt of axis-location error (2.5 deg, 0.015 response).
x_zero, x_180 = 426.5, 534.5
y_zero, y_one = 274.6, 166.5
colors = {"flexion": (0.9453129768371582, 0.35302698612213135, 0.14111299812793732),
          "extension": (0.0, 0.5722659826278687, 0.5722659826278687)}
plot_rect = fitz.Rect(438, 165, 526, 273)
rows = []
for direction, color in colors.items():
    paths = [path for path in page.get_drawings()
             if path["color"] == color and path["fill"] is None
             and len(path["items"]) == 10 and plot_rect.contains(path["rect"])]
    assert len(paths) == 1, (direction, len(paths))
    assert all(item[0] == "l" for item in paths[0]["items"])
    points = sorted({(round(float(point.x), 5), round(float(point.y), 5))
                     for item in paths[0]["items"] for point in item[1:3]})
    assert len(points) == 11
    for x, y in points:
        angle = (x - x_zero) * 180 / (x_180 - x_zero)
        response = (y_zero - y) / (y_zero - y_one)
        assert 0 <= angle <= 180 and 0 <= response <= 1.05
        rows.append((direction, angle, response, x, y))

out = root / "data/reference/agrawal2020/figure2g_digitized.csv"
with out.open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(("direction", "angle_deg_approx", "normalized_mean_approx", "pdf_x_pt", "pdf_y_pt"))
    writer.writerows(rows)

summary = {}
for direction in colors:
    points = [row for row in rows if row[0] == direction]
    summary[direction] = {"points": len(points),
                          "angle_range_deg": [points[0][1], points[-1][1]],
                          "response_range": [min(x[2] for x in points), max(x[2] for x in points)]}
report = {"source_url": "https://cdn.elifesciences.org/articles/60299/elife-60299-v2.pdf",
          "source_sha256": source_sha, "page_one_based": 5, "panel": "Figure 2G",
          "axis_calibration_pdf_points": {"x_0_deg": x_zero, "x_180_deg": x_180,
                                          "y_0_normalized": y_zero, "y_1_normalized": y_one},
          "estimated_axis_reading_uncertainty": {"angle_deg": 2.5, "normalized_response": 0.015},
          "csv_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
          "summary": summary,
          "scope": "Publisher vector mean curves, normalized population response; no raw voltage or individual-cell data",
          "model_fit_performed": False}
(root / "reports/agrawal_13b_figure2g.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(summary))
