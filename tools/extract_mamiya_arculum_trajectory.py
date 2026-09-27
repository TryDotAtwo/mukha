"""Extract the plotted mean arculum-centroid path in Mamiya 2023 Fig. 3G.

The author PDF contains the colored mean as vector line segments and the
10-micrometer scale bar as a vector line. This is plot extraction, not raw
per-fly measurement or FeCO strain reconstruction.
"""

import hashlib
import io
import json
import math
from pathlib import Path

import fitz
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/mamiya2023/mamiya_2023.pdf"
OUT = ROOT / "reports/mamiya_arculum_centroid_fig3g.json"
EXPECTED_SHA256 = "fdde57f0eb41120dd6ed69d6f7e9810ccbf9ebfeedcba2e0f5eafba38c777cac"


def line_points(drawing):
    if len(drawing["items"]) != 1 or drawing["items"][0][0] != "l":
        return None
    _, start, end = drawing["items"][0]
    return (float(start.x), float(start.y)), (float(end.x), float(end.y))


def image_rgb(image):
    return Image.open(io.BytesIO(image)).convert("RGB")


def label_rows(page, pixels_per_pdf_point):
    """Locate the white 160/90/20 figure labels to the right of the colorbar."""
    clip = fitz.Rect(318, 615, 370, 705)
    scale = pixels_per_pdf_point
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    bands = []
    start = None
    for y in range(image.height):
        white = sum(all(value > 220 for value in image.getpixel((x, y)))
                    for x in range(25 * scale, 50 * scale))
        active = white >= 2
        if active and start is None:
            start = y
        if not active and start is not None:
            if 3.5 * scale < y - start < 6.5 * scale and y < 81 * scale:
                bands.append((start, y - 1))
            start = None
    assert len(bands) == 3, bands
    return [clip.y0 + (first + last) / (2 * scale)
            for first, last in bands]


def angle_from_colorbar(page, colors):
    # In the author Figure 3G colorbar the visible labels, top to bottom,
    # are 160, 90, 20 degrees. Their rasterized glyph centers set the ticks.
    label_angles = (160.0, 90.0, 20.0)
    label_y = label_rows(page, 8)
    alternate_ticks = [label_rows(page, scale) for scale in (6, 10, 12)]
    render_scale_tick_delta = max(abs(a - b) for ticks in alternate_ticks
                                  for a, b in zip(label_y, ticks))
    assert render_scale_tick_delta < 0.15
    mean_y = sum(label_y) / 3
    mean_angle = sum(label_angles) / 3
    slope = sum((y - mean_y) * (a - mean_angle)
                for y, a in zip(label_y, label_angles)) / sum(
                    (y - mean_y) ** 2 for y in label_y)
    intercept = mean_angle - slope * mean_y
    residuals = [slope * y + intercept - angle
                 for y, angle in zip(label_y, label_angles)]
    assert max(abs(value) for value in residuals) < 1
    bar = image_rgb(fitz.open(SOURCE).extract_image(186)["image"])
    assert bar.size == (21, 291)
    placements = page.get_image_rects(186)
    assert placements and all(rect == placements[0] for rect in placements)
    rect = placements[0]
    assert 620 < rect.y0 < 630 and 690 < rect.y1 < 700
    bar_rgb = [tuple(value / 255 for value in bar.getpixel((10, y)))
               for y in range(bar.height)]
    rows, matches = [], []
    for color in colors:
        distances = [math.dist(color, rgb) for rgb in bar_rgb]
        row = min(range(len(distances)), key=distances.__getitem__)
        rows.append(row)
        matches.append(distances[row])
    assert all(a > b for a, b in zip(rows, rows[1:]))
    assert max(matches) < 0.01
    y_pdf = [rect.y0 + row / (bar.height - 1) * rect.height for row in rows]
    angles = [slope * y + intercept for y in y_pdf]
    return {
        "visible_colorbar_labels_deg_top_to_bottom": label_angles,
        "label_y_pdf_points": label_y,
        "tick_render_scale_max_pdf_point_delta": render_scale_tick_delta,
        "linear_tick_fit_max_abs_error_deg": max(abs(value) for value in residuals),
        "colorbar_image_xref": 186,
        "colorbar_pixel_rows": rows,
        "color_match_max_rgb01_distance": max(matches),
        "segment_angle_estimate_deg": angles,
        "method": "Nearest RGB match of each vector segment to the PDF colorbar, then linear interpolation between the rasterized 160/90/20-degree tick labels. Figure-resolution estimates, not raw recorded angles.",
    }


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA256
    document = fitz.open(SOURCE)
    assert len(document) == 40
    drawings = document[5].get_drawings()  # Printed article page 5, PDF page 6.
    scale_bars = []
    segments = []
    for drawing in drawings:
        points = line_points(drawing)
        if points is None:
            continue
        (x0, y0), (x1, y1) = points
        color = drawing["color"]
        width = drawing["width"]
        if (color == (1.0, 1.0, 1.0) and width is not None
                and abs(width - 0.969) < 0.01 and abs(y1 - y0) < 0.001
                and 250 < x0 < 280 and 290 < x1 < 310 and 600 < y0 < 615):
            scale_bars.append((x0, x1))
        if (color is not None and width is not None
                and abs(width - 2.906) < 0.01
                and 220 < x0 < 350 and 220 < x1 < 350
                and 550 < y0 < 590 and 550 < y1 < 590):
            segments.append((points, tuple(float(v) for v in color)))
    assert len(scale_bars) == 1 and len(segments) == 64
    scale_pdf_points_per_10_um = scale_bars[0][1] - scale_bars[0][0]
    assert 34 < scale_pdf_points_per_10_um < 36
    for previous, following in zip(segments, segments[1:]):
        assert math.dist(previous[0][1], following[0][0]) < 0.003
    path = [segments[0][0][0]] + [segment[0][1] for segment in segments]
    um_per_pdf_point = 10 / scale_pdf_points_per_10_um
    x_origin, y_origin = path[0]
    path_um = [[(x - x_origin) * um_per_pdf_point,
                (y - y_origin) * um_per_pdf_point] for x, y in path]
    endpoint = path_um[-1]
    color_angle = angle_from_colorbar(document[5], [color for _, color in segments])
    point_angles = ([color_angle["segment_angle_estimate_deg"][0]]
                    + [(a + b) / 2 for a, b in zip(
                        color_angle["segment_angle_estimate_deg"],
                        color_angle["segment_angle_estimate_deg"][1:])]
                    + [color_angle["segment_angle_estimate_deg"][-1]])
    result = {
        "source_url": "https://faculty.washington.edu/tuthill/docs/mamiya_2023.pdf",
        "source_sha256": EXPECTED_SHA256,
        "pdf_page_zero_based": 5,
        "figure": "3G",
        "figure_description": "Author-plotted colored mean arculum centroid trajectory during full tibia movement; six individual fly trajectories are shown separately in white.",
        "scale_bar_um": 10.0,
        "scale_bar_pdf_points": scale_pdf_points_per_10_um,
        "mean_path_segments": len(segments),
        "mean_path_points_um_relative_to_first": path_um,
        "segment_colors_rgb01": [list(color) for _, color in segments],
        "colorbar_angle_estimation": color_angle,
        "point_angle_estimate_deg": point_angles,
        "endpoint_displacement_um": endpoint,
        "endpoint_distance_um": math.hypot(*endpoint),
        "coordinate_convention": "Plot x increases right; plot y increases down. First colored point is at the flexed end, last at the extended end, as labeled in Figure 3G. No anatomical 3D registration.",
        "limitations": [
            "Vector figure extraction gives the plotted population mean, not six raw per-fly trajectories or uncertainty.",
            "Colorbar-derived angles are estimated from printed tick positions and cannot replace exact per-frame tibia angles.",
            "Centroid displacement is not medial-tendon displacement, claw dendritic strain, or SNpp50 firing.",
            "The physiology used female flies and has not been registered to the male FlyMimic geometry.",
        ],
        "biological_validation": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("source_sha256", "mean_path_segments",
                                            "scale_bar_pdf_points",
                                            "endpoint_displacement_um",
                                            "endpoint_distance_um")}, indent=2))


if __name__ == "__main__":
    main()
