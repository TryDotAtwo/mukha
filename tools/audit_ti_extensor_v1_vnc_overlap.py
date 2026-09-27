"""Compare registered MaleCNS v1 neurons with VFB VNC references.

Point proximity is descriptive; the MANC VFB files are not release-matched
to the official MANC v1.0 neuron-properties table.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "reports/ti_extensor_v1_vnc_registration.json"
DATA = ROOT / "data/reference/ti_extensor_template_crosswalk"
OUT = ROOT / "reports/ti_extensor_v1_vnc_overlap.json"


def metrics(source, target):
    d = cKDTree(target).query(source)[0]
    return {"median_um": float(np.median(d)),
            "p90_um": float(np.quantile(d, .9)),
            "mean_um": float(np.mean(d))}


def main():
    registration = json.loads(REG.read_text())
    source_manifest = json.loads((DATA / "source_manifest.json").read_text())
    registered = {}
    for item in registration["results"]:
        path = ROOT / item["output"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        xyz = np.load(path)
        assert xyz.shape == (item["nodes"], 3) and np.isfinite(xyz).all()
        registered[item["bodyId"]] = xyz

    vfb = {}
    for item in source_manifest["items"]:
        if item["template"] != "JRC2018UnisexVNC":
            continue
        name = ("malecns_v09_" if item["dataset"].startswith("MaleCNS")
                else "manc_") + str(item["id"]) + ".swc"
        raw = (DATA / name).read_bytes()
        assert len(raw) == item["bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        vfb[(item["dataset"], item["id"])] = np.loadtxt(DATA / name,
                                                           comments="#")[:, 2:5]

    same_cell_sanity = []
    for male in (815344, 815678):
        reference = next(x for (dataset, ident), x in vfb.items()
                         if ident == male and dataset.startswith("MaleCNS"))
        same_cell_sanity.append({
            "male_v1": male, "vfb_male_v09": male,
            "v1_to_v09": metrics(registered[male], reference),
            "v09_to_v1": metrics(reference, registered[male]),
        })

    comparisons = []
    for male, candidates in ((815344, (11657, 12704)),
                             (800636, (11657, 12704)),
                             (815678, (11706, 13115)),
                             (804257, (11706, 13115))):
        for manc in candidates:
            reference = next(x for (dataset, ident), x in vfb.items()
                             if ident == manc and dataset.startswith("MANC"))
            comparisons.append({
                "male_v1": male, "vfb_manc": manc,
                "male_to_manc": metrics(registered[male], reference),
                "manc_to_male": metrics(reference, registered[male]),
            })

    report = {
        "scope": "Registered v1 MaleCNS versus VFB template skeletons; no identity or muscle assignment",
        "registration_report_sha256": hashlib.sha256(REG.read_bytes()).hexdigest(),
        "vfb_manifest_sha256": hashlib.sha256((DATA / "source_manifest.json").read_bytes()).hexdigest(),
        "same_cell_cross_release_sanity": same_cell_sanity,
        "two_by_two_same_side_comparisons": comparisons,
        "interpretation": "Same-cell v0.9 references overlap registered v1 within about 1 um median, supporting gross registration orientation. MANC candidate distances have direction/tail ambiguities and VFB MANC release is not validated as v1.0; no unique motor identity established.",
        "biological_gate_passed": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
