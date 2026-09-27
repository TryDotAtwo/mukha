"""Apply the published MaleCNS v1.0 -> JRCVNC2018U registration.

Outputs point coordinates only: a nonlinear warp does not preserve SWC radii.
"""

import hashlib
import json
import os
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/malecns_v1_ti_extensor_skeletons"
REG = ROOT / "data/reference/ti_extensor_transform_inputs"
OUT = ROOT / "data/reference/ti_extensor_v1_vnc_registered"
REPORT = ROOT / "reports/ti_extensor_v1_vnc_registration.json"


def check(path, expected_size, expected_hash):
    raw = path.read_bytes()
    assert len(raw) == expected_size, str(path)
    assert hashlib.sha256(raw).hexdigest() == expected_hash, str(path)


def main():
    reg_manifest = json.loads((REG / "source_manifest.json").read_text())
    src_manifest = json.loads((SOURCE / "source_manifest.json").read_text())
    for item in reg_manifest["files"]:
        check(REG / item["name"], item["bytes"], item["sha256"])
    for item in src_manifest["items"]:
        check(SOURCE / f'{item["bodyId"]}.swc', item["bytes"], item["sha256"])

    import flybrains  # noqa: F401; registers the pinned transforms
    import navis

    path, _ = navis.transforms.registry.find_bridging_path(
        "JRCFIB2022Mraw", "JRCVNC2018U"
    )
    assert path == reg_manifest["route"].split(" -> "), path
    OUT.mkdir(parents=True, exist_ok=True)
    previous = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    cached = {x["bodyId"]: x for x in previous.get("results", [])}
    results = []
    for item in src_manifest["items"]:
        ident = item["bodyId"]
        raw = np.loadtxt(SOURCE / f"{ident}.swc", comments="#")
        assert raw.ndim == 2 and raw.shape[1] == 7
        assert len(np.unique(raw[:, 0])) == len(raw)
        dst = OUT / f"{ident}.npy"
        old = cached.get(ident)
        if (old and dst.exists() and old["nodes"] == len(raw) and
                hashlib.sha256(dst.read_bytes()).hexdigest() == old["sha256"]):
            xyz = np.load(dst)
            print(f"reused verified {ident}: {len(raw)} nodes", flush=True)
        else:
            xyz = navis.xform_brain(
                raw[:, 2:5].copy(), source="JRCFIB2022Mraw", target="JRCVNC2018U"
            )
            xyz = np.asarray(xyz, dtype=np.float64)
            np.save(dst, xyz)
            print(f"registered {ident}: {len(raw)} nodes", flush=True)
        assert xyz.shape == (len(raw), 3) and np.isfinite(xyz).all()
        results.append({
            "bodyId": ident,
            "nodes": len(raw),
            "output": str(dst.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
            "bbox_min_um": xyz.min(axis=0).tolist(),
            "bbox_max_um": xyz.max(axis=0).tolist(),
        })

    report = {
        "scope": "Published coordinate registration only; identity and muscle mapping unverified",
        "source_manifest_sha256": hashlib.sha256((SOURCE / "source_manifest.json").read_bytes()).hexdigest(),
        "transform_manifest_sha256": hashlib.sha256((REG / "source_manifest.json").read_bytes()).hexdigest(),
        "route": path,
        "results": results,
        "biological_gate_passed": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(REPORT, flush=True)


if __name__ == "__main__":
    main()
