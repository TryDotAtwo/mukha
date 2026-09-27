"""Verify source skeletons and prevent direct comparison across template spaces."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/ti_extensor_template_crosswalk"


def run():
    manifest = json.loads((SOURCE / "source_manifest.json").read_text())
    entries = {}
    for item in manifest["items"]:
        if item["dataset"].startswith("MaleCNS v0.9"):
            continue  # This audit is for release-matched MaleCNS v1.0 geometry.
        prefix = "manc" if item["dataset"].startswith("MANC") else "malecns"
        path = SOURCE / f'{prefix}_{item["id"]}.swc'
        raw = path.read_bytes()
        assert len(raw) == item["bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        a = np.loadtxt(path)
        assert a.ndim == 2 and a.shape[1] == 7 and np.isfinite(a).all()
        entries[f'{prefix}_{item["id"]}'] = {
            "template": item["template"],
            "nodes": len(a),
            "bbox_min_um": np.min(a[:, 2:5], axis=0).tolist(),
            "bbox_max_um": np.max(a[:, 2:5], axis=0).tolist(),
        }
    templates = sorted({v["template"] for v in entries.values()})
    assert templates == ["JRC2018U", "JRC2018UnisexVNC"]
    result = {
        "scope": "Source and coordinate-space check; no morphology match or muscle assignment",
        "manifest_sha256": hashlib.sha256((SOURCE / "source_manifest.json").read_bytes()).hexdigest(),
        "templates": templates,
        "same_coordinate_frame_confirmed": False,
        "direct_cross_dataset_distance_allowed": False,
        "published_indirect_route_found": {
            "status": "executed_on_four_malecns_v1_skeletons",
            "registration_report": "reports/ti_extensor_v1_vnc_registration.json",
            "overlap_report": "reports/ti_extensor_v1_vnc_overlap.json",
            "flybrains_commit": "273333c8d8bf5adeebebd274e554621462e388bd",
            "vnc_alias_evidence": "VFB labels JRC2018UnisexVNC imagery as aligned to JRCVNC2018U",
            "steps": [
                "JRC2018U -> JRC2018F (Janelia H5)",
                "JRC2018F -> BANCum (reverse Elastix registration)",
                "BANCum -> JRCVNC2018F (forward Elastix registration)",
                "JRCVNC2018F -> JRCVNC2018U (Janelia H5)",
            ],
            "source_transform_file_ids": {
                "JRC2018U_JRC2018F.h5": 14371574,
                "JRCVNC2018U_JRCVNC2018F.h5": 28909212,
            },
            "source_urls": [
                "https://github.com/navis-org/navis-flybrains/blob/main/flybrains/core.py",
                "https://github.com/navis-org/navis-flybrains/blob/main/flybrains/download.py",
                "https://www.virtualflybrain.org/term/mvact1l-on-jrc2018unisexvnc-vfb_00108vfs/",
            ],
            "validation_required": "Pin transform files, execute route, check units/orientation and independent anatomical landmarks and same-type controls before comparing motor candidates",
        },
        "required_before_distance": "Raw files remain in different frames; use the verified registered v1 point arrays for descriptive distances, and independently validate anatomy before identity claims",
        "skeletons": entries,
        "biological_gate_passed": False,
    }
    path = ROOT / "reports/ti_extensor_template_space_boundary.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
