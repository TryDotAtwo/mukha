"""Compare published FANC manual T1 SWCs to MANC candidates in one template."""

import hashlib
import json
import os
from pathlib import Path

import navis
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FANC = ROOT / "data/reference/fanc_2021_ti_extensor_template_swcs"
MANC = ROOT / "data/reference/ti_extensor_template_crosswalk"
REG = ROOT / "data/reference/ti_extensor_transform_inputs"
DERIVED = ROOT / "data/derived/fanc_2021_ti_extensor_vnc_unisex"
REPORT = ROOT / "reports/fanc_2021_manc_t1_extensor_nblast.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dotprops(xyz, ident, k):
    dp = navis.make_dotprops(xyz, k=k)
    dp.id = str(ident)
    dp.units = "1 um"
    return dp


def main():
    fanc_manifest = FANC / "source_manifest.json"
    manc_manifest = MANC / "source_manifest.json"
    reg_manifest = REG / "source_manifest.json"
    f = json.loads(fanc_manifest.read_text())
    m = json.loads(manc_manifest.read_text())
    r = json.loads(reg_manifest.read_text())
    assert len(f["files"]) == 2
    for item in r["files"]:
        assert sha(REG / item["name"]) == item["sha256"]
    os.environ["FLYBRAINS_DATA"] = str(REG)
    import flybrains  # noqa: F401; registers local H5 transform
    route, _ = navis.transforms.registry.find_bridging_path("JRCVNC2018F", "JRCVNC2018U")
    assert route == ["JRCVNC2018F", "JRCVNC2018U"]
    DERIVED.mkdir(parents=True, exist_ok=True)
    fanc = {}
    outputs = []
    for item in f["files"]:
        ident = item["neuron_id"]
        path = FANC / f"{ident}.swc"
        assert sha(path) == item["sha256"]
        raw = np.loadtxt(path, comments="#")
        assert raw.shape[1] == 7
        xyz = np.asarray(navis.xform_brain(raw[:, 2:5] / 1000,
                                           source="JRCVNC2018F", target="JRCVNC2018U"))
        assert xyz.shape == (len(raw), 3) and np.isfinite(xyz).all()
        fanc[ident] = xyz
        out = DERIVED / f"{ident}.npy"
        np.save(out, xyz)
        outputs.append({"fanc_neuron_id": ident, "nodes": len(xyz),
                        "path": str(out.relative_to(ROOT)).replace("\\", "/"),
                        "sha256": sha(out), "bbox_min_um": xyz.min(0).tolist(),
                        "bbox_max_um": xyz.max(0).tolist()})
    manc = {}
    for ident in (11657, 12704):
        item = next(x for x in m["items"] if x["id"] == ident and x["dataset"].startswith("MANC"))
        path = MANC / f"manc_{ident}.swc"
        assert sha(path) == item["sha256"]
        manc[ident] = np.loadtxt(path, comments="#")[:, 2:5]
    matrices = {}
    for k in (10, 20, 40):
        q = navis.NeuronList([dotprops(fanc[i], i, k) for i in sorted(fanc)])
        t = navis.NeuronList([dotprops(manc[i], i, k) for i in sorted(manc)])
        frame = navis.nblast(q, t, scores="mean", normalized=True,
                             smat="auto", n_cores=1, progress=False)
        matrices[str(k)] = {str(i): {str(j): float(frame.loc[str(i), str(j)])
                                  for j in frame.columns} for i in frame.index}
        print(k, matrices[str(k)], flush=True)
    report = {
        "scope": "Published manual FANC 2021 skeletons vs VFB MANC T1-left skeletons; candidate identity only",
        "fanc_manifest_sha256": sha(fanc_manifest),
        "manc_manifest_sha256": sha(manc_manifest),
        "transform_manifest_sha256": sha(reg_manifest),
        "transform_route": route,
        "fanc_source_unit_conversion": "nanometres / 1000 to JRCVNC2018F micrometres",
        "registered_fanc_files": outputs,
        "method": {"navis_version": navis.__version__, "dotprops_k": [10, 20, 40],
                   "scores": "mean", "normalized": True, "smat": "auto"},
        "matrices": matrices,
        "limitations": ["2021 FANC SWC to 2024 segment association is morphology-derived",
                        "VFB MANC individual SWC release not confirmed as v1.0",
                        "FANC atlas-to-template and VFB template equivalence lack same-cell landmark validation",
                        "FCWB-trained auto scoring matrix is not VNC-specific"],
        "fanc_seti_feti_assignment_verified": False,
        "fanc_to_manc_identity_verified": False,
        "motor_mapping_enabled": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
