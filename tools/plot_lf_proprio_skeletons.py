"""Shared-coordinate projections of seven source-pinned MaleCNS SWC skeletons."""

import hashlib
import json

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

from flymimic_public_model import ROOT


SOURCE = ROOT / "data/reference/malecns_v1_lf_proprio_skeletons"
OUT = ROOT / "previews/lf_proprio_skeletons_v1.png"
REPORT = ROOT / "reports/lf_proprio_skeleton_geometry.json"
LABELS = {817697: "SNppxx", 821306: "SNppxx", 908487: "untyped",
          912317: "SNpp50", 815843: "SNpp51", 817680: "SNpp51", 935383: "SNpp51"}
VIEWS = ((2, 4, "X-Z"), (3, 4, "Y-Z"), (2, 3, "X-Y"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((SOURCE / "source_manifest.json").read_text(encoding="utf-8"))
    arrays = {}
    details = []
    for entry in manifest["entries"]:
        body = entry["body_id"]
        path = SOURCE / f"{body}.swc"
        assert sha(path) == entry["sha256"]
        points = np.loadtxt(path, comments="#")
        assert points.ndim == 2 and points.shape[1] == 7
        ids = points[:, 0].astype(int)
        parents = points[:, 6].astype(int)
        assert len(np.unique(ids)) == len(ids)
        id_to_row = {int(value): i for i, value in enumerate(ids)}
        parent_rows = np.asarray([id_to_row.get(int(value), -1) for value in parents])
        assert int((parents < 0).sum()) == 1
        assert np.all((parents < 0) | (parent_rows >= 0))
        arrays[body] = (points, parent_rows)
        details.append({"body_id": body, "source_sha256": entry["sha256"],
                        "nodes": len(points),
                        "bounding_box_swc_units": {axis: [float(points[:, j].min()),
                                                          float(points[:, j].max())]
                                                   for axis, j in (("x", 2), ("y", 3), ("z", 4))},
                        "coordinate_units_nm": 8})
    fig, axes = plt.subplots(len(arrays), len(VIEWS), figsize=(12, 19),
                             constrained_layout=True)
    for row_index, (body, (points, parent_rows)) in enumerate(arrays.items()):
        color = "#2563eb" if LABELS[body] == "SNpp50" else (
            "#64748b" if LABELS[body] == "SNpp51" else "#ea580c")
        for column, (xcol, ycol, title) in enumerate(VIEWS):
            ax = axes[row_index, column]
            segments = np.asarray([[points[i, [xcol, ycol]],
                                    points[parent_rows[i], [xcol, ycol]]]
                                   for i in range(len(points)) if parent_rows[i] >= 0])
            ax.add_collection(LineCollection(segments, colors=color, linewidths=.45,
                                              alpha=.75))
            ax.autoscale()
            ax.set_aspect("equal", adjustable="box")
            ax.set_xlim(48000, 68000) if xcol == 2 else ax.set_xlim(54000, 68000)
            ax.set_ylim(64000, 84000) if ycol == 4 else ax.set_ylim(54000, 68000)
            ax.tick_params(labelsize=6)
            if row_index == 0:
                ax.set_title(title)
            if column == 0:
                ax.set_ylabel(f"{body}\n{LABELS[body]}", fontsize=9)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=180)
    plt.close(fig)
    report = {"source_manifest_sha256": sha(SOURCE / "source_manifest.json"),
              "image_sha256": sha(OUT), "image_path": str(OUT.relative_to(ROOT)).replace("\\", "/"),
              "scope": "Shared axes of native v1.0 SWC centerline projections; visual morphology aid, not a cell-type classifier",
              "skeletons": details}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"skeletons": len(details), "image": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
