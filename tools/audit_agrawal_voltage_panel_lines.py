"""Read two explicit cell-pair line examples from Agrawal Figure 2 supplement 1E.

Figure pixels are illustrative constraints, not raw physiological recordings.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT / "data/reference/agrawal2020/fig2_supp1.jpg"
REPORT = ROOT / "reports/agrawal_voltage_panel_lines.json"
EXPECTED_SHA = "73de398fb86593e1e3775b1bfaf5a460af634d66d193ee6c61cb71884b411845"
assert hashlib.sha256(IMAGE.read_bytes()).hexdigest() == EXPECTED_SHA
image = cv2.imdecode(np.frombuffer(IMAGE.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
assert image is not None and image.shape[:2] == (2072, 1004)
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
roi = hsv[1620:1950, 115:455]
red = cv2.inRange(roi, (0, 80, 80), (12, 255, 255)) | cv2.inRange(roi, (170, 80, 80), (179, 255, 255))
blue = cv2.inRange(roi, (85, 70, 70), (120, 255, 255))


def lines(mask, threshold=20, min_length=25, max_gap=10):
    raw = cv2.HoughLinesP(mask, 1, np.pi / 180, threshold=threshold,
                          minLineLength=min_length, maxLineGap=max_gap)
    assert raw is not None
    return [(int(x1 + 115), int(y1 + 1620), int(x2 + 115), int(y2 + 1620))
            for x1, y1, x2, y2 in raw[:, 0]]


def select(mask, intended, settings=(20, 25, 10), max_distance=12):
    candidates = lines(mask, *settings)
    # Endpoints identify one long line for each color. Multiple Hough traces
    # of the same line are allowed; choose the nearest without fabricating data.
    distances = [sum(abs(a - b) for a, b in zip(item, intended)) for item in candidates]
    index = int(np.argmin(distances))
    assert distances[index] <= max_distance, (intended, candidates[index], distances[index])
    return candidates[index]


examples = [
    ("extension_red", select(red, (130, 1702, 419, 1837))),
    ("flexion_blue", select(blue, (162, 1777, 300, 1901))),
]


def physical(line, x0=124.0, x1=455.0, y12=1594.0, y4=1840.0):
    xa, ya, xb, yb = line
    va = -70.0 + (xa - x0) * 60.0 / (x1 - x0)
    vb = -70.0 + (xb - x0) * 60.0 / (x1 - x0)
    ra = 12.0 - (ya - y12) * 8.0 / (y4 - y12)
    rb = 12.0 - (yb - y12) * 8.0 / (y4 - y12)
    k = (ra - rb) / (vb - va)
    reversal = va + ra / k
    return va, vb, ra, rb, k, reversal


rng = np.random.default_rng(20260926)
summaries = []
for name, line in examples:
    central = physical(line)
    variants = []
    for _ in range(20000):
        changed = [float(v + rng.uniform(-3, 3)) for v in line]
        anchors = [124 + rng.uniform(-3, 3), 455 + rng.uniform(-3, 3),
                   1594 + rng.uniform(-3, 3), 1840 + rng.uniform(-3, 3)]
        values = physical(changed, *anchors)
        if values[4] > 0:
            variants.append(values)
    variants = np.asarray(variants)
    assert len(variants) == 20000
    summaries.append({"name": name, "hough_line_pdf_image_pixels": line,
                      "endpoint_voltage_mv": list(central[:2]),
                      "endpoint_response_mv": list(central[2:4]),
                      "effective_linear_gain": central[4],
                      "single_linear_reversal_intercept_mv": central[5],
                      "sampled_range_gain": [float(variants[:, 4].min()), float(variants[:, 4].max())],
                      "sampled_range_reversal_intercept_mv": [float(variants[:, 5].min()), float(variants[:, 5].max())]})

separated = (summaries[0]["sampled_range_reversal_intercept_mv"][0]
             > summaries[1]["sampled_range_reversal_intercept_mv"][1])
assert separated
detector_sensitivity = []
for threshold, min_length, max_gap in ((15, 20, 8), (20, 25, 10), (25, 30, 12)):
    settings = (threshold, min_length, max_gap)
    per_color = {}
    for name, mask, intended in (("extension_red", red, (130, 1702, 419, 1837)),
                                 ("flexion_blue", blue, (162, 1777, 300, 1901))):
        line = select(mask, intended, settings, max_distance=60)
        per_color[name] = {"selected_segment_pixels": line,
                           "linear_zero_response_intercept_mv": physical(line)[5]}
    detector_sensitivity.append({"hough_threshold": threshold,
                                 "min_length_pixels": min_length,
                                 "max_gap_pixels": max_gap,
                                 "lines": per_color})
assert all(x["lines"]["extension_red"]["linear_zero_response_intercept_mv"] > 0
           and x["lines"]["flexion_blue"]["linear_zero_response_intercept_mv"] < 0
           for x in detector_sensitivity)

report = {
    "source_figure_sha256": EXPECTED_SHA,
    "source_url": "https://iiif.elifesciences.org/lax/60299%2Felife-60299-fig2-figsupp1-v2.tif/full/full/0/default.jpg",
    "panel": "Figure 2 supplement 1E, two illustrative long colored cell-pair lines",
    "pixel_axis_anchors": {"x_minus70_mv": 124, "x_minus10_mv": 455,
                           "y_12_mv_response": 1594, "y_4_mv_response": 1840},
    "examples": summaries,
    "detector_setting_sensitivity": detector_sensitivity,
    "selected_lines_share_one_linear_zero_response_intercept_under_reading": False,
    "sensitivity": "20,000 deterministic uniform perturbations per selected line: each line endpoint and axis anchor independently +/-3 pixels. Three Hough settings also inspect potentially different segments. These are reading/detection sensitivities, not biological uncertainty or confidence intervals.",
    "reversal_intercept_interpretation": "The E where a straight line through each illustrated pair extrapolates to zero response, if response=k*(E-V). It is not a measured channel reversal potential; differing intercepts do not uniquely identify the underlying mechanism.",
    "full_cell_population_fit": False,
    "biological_mechanism_identified": False}
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summaries))
