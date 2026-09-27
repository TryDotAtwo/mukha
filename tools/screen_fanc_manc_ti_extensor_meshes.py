"""Screen registered FANC surface points against same-side MANC SWCs.

Surface-to-centerline distances are a gross anatomical screen, not NBLAST or
an identity assignment. The FANC mesh and transform release also differ.
"""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
FANC = ROOT / "data/reference/fanc_ti_extensor_meshes"
MANC = ROOT / "data/reference/ti_extensor_template_crosswalk"
REG = ROOT / "data/reference/ti_extensor_transform_inputs"
OUT = ROOT / "reports/fanc_manc_ti_extensor_surface_screen.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(a, b):
    distance = cKDTree(b).query(a, workers=-1)[0]
    return {"median_um": float(np.median(distance)),
            "p90_um": float(np.quantile(distance, .9))}


def main():
    mesh_report = json.loads((ROOT / "reports/fanc_ti_extensor_meshes.json").read_text())
    reg_report = json.loads((REG / "source_manifest.json").read_text())
    manc_manifest = json.loads((MANC / "source_manifest.json").read_text())
    os.environ["FLYBRAINS_DATA"] = str(REG)
    os.environ["PATH"] = str(REG / "elastix_runtime") + os.pathsep + os.environ["PATH"]
    import flybrains  # noqa: F401
    import navis

    route, _ = navis.transforms.registry.find_bridging_path("FANC", "JRCVNC2018U")
    assert route == ["FANC", "FANCum_fixed", "JRCVNC2018F_reflected", "JRCVNC2018F", "JRCVNC2018U"]
    assert any(x["name"] == "JRCVNC2018U_JRCVNC2018F.h5" for x in reg_report["files"])
    for item in reg_report["files"]:
        assert digest(REG / item["name"]) == item["sha256"]

    manc = {}
    for ident in (11657, 12704):
        item = next(x for x in manc_manifest["items"] if x["id"] == ident and x["dataset"].startswith("MANC"))
        path = MANC / f"manc_{ident}.swc"
        assert digest(path) == item["sha256"]
        manc[ident] = np.loadtxt(path, comments="#")[:, 2:5]

    rng = np.random.default_rng(20260924)
    result = []
    for spec in mesh_report["meshes"]:
        ident = spec["segment_id"]
        path = FANC / f"{ident}_fragment.bin"
        assert digest(path) == spec["fragment_sha256"]
        raw = path.read_bytes()
        n = int(np.frombuffer(raw, dtype="<u4", count=1)[0])
        xyz = np.frombuffer(raw, dtype="<f4", offset=4, count=3*n).reshape(-1, 3)
        pick = np.sort(rng.choice(n, size=min(4096, n), replace=False))
        sampled = xyz[pick].astype(np.float64)
        registered = np.asarray(navis.xform_brain(sampled, source="FANC", target="JRCVNC2018U"))
        assert registered.shape == sampled.shape and np.isfinite(registered).all()
        comparisons = {}
        for manc_id, points in manc.items():
            comparisons[str(manc_id)] = {
                "fanc_surface_to_manc_swc": summary(registered, points),
                "manc_swc_to_fanc_surface_sample": summary(points, registered),
            }
        result.append({"fanc_segment_id": ident, "sample_size": len(pick),
                       "sample_index_sha256": hashlib.sha256(pick.tobytes()).hexdigest(),
                       "registered_bbox_min_um": registered.min(axis=0).tolist(),
                       "registered_bbox_max_um": registered.max(axis=0).tolist(),
                       "comparisons": comparisons})
        print(ident, comparisons, flush=True)
    report = {
        "scope": "Gross surface-to-centerline anatomical screen; incomplete/unequal geometries, not cell identity",
        "transform_route": route,
        "mesh_report_sha256": digest(ROOT / "reports/fanc_ti_extensor_meshes.json"),
        "transform_manifest_sha256": digest(REG / "source_manifest.json"),
        "manc_manifest_sha256": digest(MANC / "source_manifest.json"),
        "source_release_limit": "FANC published mesh and v3 template transform; VFB MANC SWC dataset page states v1.2.1, not confirmed per-cell",
        "comparisons": result,
        "fanc_mn39_vs_mn40_assignment_verified": False,
        "fanc_to_manc_identity_verified": False,
        "motor_mapping_enabled": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
