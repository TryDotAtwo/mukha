"""Directional-tangent morphology comparison in registered VNC space.

Uses the default navis/FCWB NBLAST matrix for descriptive rankings only.
"""

import hashlib
import json
from pathlib import Path

import navis
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "reports/ti_extensor_v1_vnc_registration.json"
DATA = ROOT / "data/reference/ti_extensor_template_crosswalk"
OUT = ROOT / "reports/ti_extensor_v1_nblast.json"


def dotprops(points, ident, k):
    dp = navis.make_dotprops(points, k=k)
    dp.id = str(ident)
    dp.units = "1 um"
    return dp


def score(query, target):
    frame = navis.nblast(navis.NeuronList(query), navis.NeuronList(target),
                         scores="mean", normalized=True, smat="auto",
                         n_cores=1, progress=False)
    return {str(i): {str(j): float(frame.loc[str(i), str(j)])
                     for j in frame.columns} for i in frame.index}


def main():
    registration = json.loads(REG.read_text())
    source_manifest = json.loads((DATA / "source_manifest.json").read_text())
    male = {}
    for item in registration["results"]:
        path = ROOT / item["output"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        male[item["bodyId"]] = np.load(path)
    vfb = {}
    for item in source_manifest["items"]:
        if item["template"] != "JRC2018UnisexVNC":
            continue
        name = ("malecns_v09_" if item["dataset"].startswith("MaleCNS")
                else "manc_") + str(item["id"]) + ".swc"
        path = DATA / name
        raw = path.read_bytes()
        assert len(raw) == item["bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        vfb[(item["dataset"], item["id"])] = np.loadtxt(path,
                                                           comments="#")[:, 2:5]

    matrices = {}
    for k in (10, 20, 40):
        sides = {}
        for side, male_ids, manc_ids in (("left", (815344, 800636), (11657, 12704)),
                                         ("right", (815678, 804257), (11706, 13115))):
            q = [dotprops(male[i], i, k) for i in male_ids]
            t = [dotprops(next(x for (ds, ident), x in vfb.items()
                               if ident == i and ds.startswith("MANC")), i, k)
                 for i in manc_ids]
            sides[side] = score(q, t)
        matrices[str(k)] = sides

    sanity = {}
    for ident in (815344, 815678):
        ref = next(x for (ds, i), x in vfb.items()
                   if i == ident and ds.startswith("MaleCNS"))
        q = dotprops(male[ident], ident, 20)
        t = dotprops(ref, f"v09_{ident}", 20)
        sanity[str(ident)] = score([q], [t])[str(ident)][f"v09_{ident}"]

    report = {
        "scope": "Descriptive morphology ranking, not confirmed individual identity or muscle innervation",
        "registration_report_sha256": hashlib.sha256(REG.read_bytes()).hexdigest(),
        "vfb_manifest_sha256": hashlib.sha256((DATA / "source_manifest.json").read_bytes()).hexdigest(),
        "navis_version": navis.__version__,
        "dotprops_k": [10, 20, 40],
        "nblast": {"scores": "mean", "normalized": True, "smat": "auto",
                   "caveat": "navis auto uses FCWB-trained scoring matrix, not VNC-specific calibration"},
        "same_cell_v1_v09_positive_control_k20": sanity,
        "same_side_two_by_two_scores": matrices,
        "interpretation": "Both proposed mappings rank first across k=10,20,40, but 815678->11706 has a small margin over 13115. VFB MANC SWC release is not confirmed as v1.0. No correspondence accepted for motor output.",
        "biological_gate_passed": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
