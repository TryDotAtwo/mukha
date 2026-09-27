"""Extract six author-plotted Fig. 3G arculum paths; these are not raw trials."""

import hashlib
import json
import math
import statistics
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/mamiya2023/mamiya_2023.pdf"
OUT = ROOT / "reports/mamiya_arculum_individual_fig3g.json"
PDF_SHA = "fdde57f0eb41120dd6ed69d6f7e9810ccbf9ebfeedcba2e0f5eafba38c777cac"
GREY = (0.800000011920929,) * 3
EXPECTED_SEGMENTS = (71, 73, 80, 67, 68, 69)
SCALE_PDF_POINTS_PER_10_UM = 34.816009521484375


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PDF_SHA
    page = fitz.open(SOURCE)[5]
    drawings = [(index, drawing) for index, drawing in enumerate(page.get_drawings())
                if drawing["color"] == GREY
                and drawing["width"] is not None
                and abs(drawing["width"] - 0.726) < 0.01
                and 210 < drawing["rect"].x0 < 260
                and 300 < drawing["rect"].x1 < 370
                and 550 < drawing["rect"].y0 < 600
                and 570 < drawing["rect"].y1 < 610]
    assert [index for index, _ in drawings] == list(range(692, 698))
    assert tuple(len(drawing["items"]) for _, drawing in drawings) == EXPECTED_SEGMENTS
    um_per_point = 10 / SCALE_PDF_POINTS_PER_10_UM
    paths = []
    for index, drawing in drawings:
        assert all(item[0] == "l" for item in drawing["items"])
        segments = [[(float(item[1].x), float(item[1].y)),
                     (float(item[2].x), float(item[2].y))]
                    for item in drawing["items"]]
        assert max(math.dist(a[1], b[0]) for a, b in zip(segments, segments[1:])) < 1e-6
        plot_points = [segments[0][0]] + [segment[1] for segment in segments]
        x0, y0 = plot_points[0]
        relative = [[(x - x0) * um_per_point, (y - y0) * um_per_point]
                    for x, y in plot_points]
        endpoint = relative[-1]
        paths.append({
            "drawing_index": index,
            "segments": len(segments),
            "plot_start_pdf_points": [x0, y0],
            "points_um_relative_to_own_start": relative,
            "endpoint_displacement_um": endpoint,
            "endpoint_distance_um": math.hypot(*endpoint),
            "sampled_polyline_length_um": sum(math.dist(a, b) for a, b in zip(relative, relative[1:])),
        })
    distances = [path["endpoint_distance_um"] for path in paths]
    result = {
        "source_url": "https://faculty.washington.edu/tuthill/docs/mamiya_2023.pdf",
        "source_sha256": PDF_SHA,
        "figure": "3G, PDF page zero-based 5",
        "scale_bar_um": 10.0,
        "scale_bar_pdf_points": SCALE_PDF_POINTS_PER_10_UM,
        "coordinate_convention": "Plot x right and y down; each path translated to its own first point",
        "individual_paths": paths,
        "endpoint_distance_range_um": [min(distances), max(distances)],
        "endpoint_distance_median_um": statistics.median(distances),
        "limitation": "These are six author-plotted paths from female flies. Vertex spacing is PDF graphic sampling, not time or knee angle. No trial-wise angle alignment, biological strain, or male geometry registration is implied.",
        "biological_validation": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"paths": len(paths), "endpoint_distance_range_um": result["endpoint_distance_range_um"],
                      "endpoint_distance_median_um": result["endpoint_distance_median_um"]}, indent=2))


if __name__ == "__main__":
    main()
