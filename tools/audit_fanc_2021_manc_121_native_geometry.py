"""Compare FANC 2021 manual trees to MANC 1.2.1 native SWCs; exploratory only."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
FANC = ROOT / "data/reference/fanc_2021_t1_motor_swcs"
MANC = ROOT / "data/reference/manc_121_ti_extensor_native_swcs"
REG = ROOT / "data/reference/ti_extensor_transform_inputs"
OUT = ROOT / "reports/fanc_2021_manc_121_native_geometry.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantiles(x):
    return {"median_um": float(np.median(x)), "p90_um": float(np.quantile(x, .9))}


def main():
    source = json.loads((FANC / "source_manifest.json").read_text())
    target = json.loads((MANC / "source_manifest.json").read_text())
    assert target["release"] == "MANC 1.2.1, not MANC 1.0"
    os.environ["FLYBRAINS_DATA"] = str(REG)
    import flybrains  # noqa: F401
    import navis
    route, _ = navis.transforms.registry.find_bridging_path("FANC", "MANC")
    assert route == ["FANC", "MANC"]
    manc = {}
    for item in target["files"]:
        path = MANC / f'{item["body_id"]}.swc'
        assert sha(path) == item["sha256"]
        arr = np.loadtxt(path, comments="#")
        manc[item["body_id"]] = arr[:, 2:5]
    results = []
    for ident in (581, 9001):
        item = next(x for x in source["files"] if f"(neuron {ident})" in x["name"])
        path = FANC / item["name"]
        assert sha(path) == item["sha256"]
        fanc_nm = np.loadtxt(path, comments="#")[:, 2:5]
        transformed_um = np.asarray(navis.xform_brain(fanc_nm, source="FANC", target="MANC")) / 1000
        row = {"fanc_neuron_id": ident, "nodes": len(fanc_nm), "candidates": []}
        for body_id, points in manc.items():
            f_to_m = cKDTree(points).query(transformed_um)[0]
            m_to_f = cKDTree(transformed_um).query(points)[0]
            row["candidates"].append({"manc_body_id": body_id,
                                      "fanc_to_manc": quantiles(f_to_m),
                                      "manc_to_fanc": quantiles(m_to_f)})
        results.append(row)
    report = {"scope": "Exploratory cross-release native-space proximity; no cell identity proof",
              "fanc_release": "2021 manual", "manc_release": target["release"],
              "route": route, "source_manifest_sha256": sha(FANC / "source_manifest.json"),
              "target_manifest_sha256": sha(MANC / "source_manifest.json"),
              "source_and_target_native_swc_units": "nm FANC; um MANC",
              "results": results, "validates_manc_v1_identity": False}
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
