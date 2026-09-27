"""Validate the FANC→female-template route against same-cell published SWCs."""

import hashlib
import json
import os
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "data/reference/fanc_2021_t1_motor_swcs"
TEMPLATE = ROOT / "data/reference/fanc_2021_ti_extensor_template_swcs"
REG = ROOT / "data/reference/ti_extensor_transform_inputs"
OUT = ROOT / "reports/fanc_2021_template_registration_validation.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(d):
    return {"median_um": float(np.median(d)),
            "p90_um": float(np.quantile(d, .9)),
            "max_um": float(np.max(d))}


def main():
    native_manifest = NATIVE / "source_manifest.json"
    template_manifest = TEMPLATE / "source_manifest.json"
    reg_manifest = REG / "source_manifest.json"
    native_spec = json.loads(native_manifest.read_text())
    template_spec = json.loads(template_manifest.read_text())
    reg_spec = json.loads(reg_manifest.read_text())
    for item in reg_spec["files"]:
        assert sha(REG / item["name"]) == item["sha256"]
    os.environ["FLYBRAINS_DATA"] = str(REG)
    os.environ["PATH"] = str(REG / "elastix_runtime") + os.pathsep + os.environ["PATH"]
    import flybrains  # noqa: F401
    import navis
    route, _ = navis.transforms.registry.find_bridging_path("FANC", "JRCVNC2018F")
    assert route == ["FANC", "FANCum_fixed", "JRCVNC2018F_reflected", "JRCVNC2018F"]
    results = []
    for item in template_spec["files"]:
        ident = item["neuron_id"]
        native_item = next(x for x in native_spec["files"] if f"(neuron {ident})" in x["name"])
        native_path = NATIVE / native_item["name"]
        template_path = TEMPLATE / f"{ident}.swc"
        assert sha(native_path) == native_item["sha256"]
        assert sha(template_path) == item["sha256"]
        a = np.loadtxt(native_path, comments="#")
        b = np.loadtxt(template_path, comments="#")
        assert a.shape == b.shape and a.shape[1] == 7
        assert np.array_equal(a[:, 0], b[:, 0]) and np.array_equal(a[:, 6], b[:, 6])
        transformed = np.asarray(navis.xform_brain(a[:, 2:5], source="FANC", target="JRCVNC2018F"))
        error = np.linalg.norm(transformed - b[:, 2:5] / 1000, axis=1)
        results.append({"fanc_neuron_id": ident, "nodes": len(a),
                        "pointwise_error": stats(error),
                        "node_and_parent_sequences_identical": True})
        print(ident, results[-1]["pointwise_error"], flush=True)
    report = {
        "scope": "Same-cell check of FANC 2021 native→published female VNC template registration",
        "native_manifest_sha256": sha(native_manifest),
        "template_manifest_sha256": sha(template_manifest),
        "transform_manifest_sha256": sha(reg_manifest),
        "route": route,
        "published_template_swc_units": "nm; divide by 1000 for flybrains micrometres",
        "results": results,
        "validates_2024_mesh_to_2021_swc_identity": False,
        "validates_manc_cell_identity": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
