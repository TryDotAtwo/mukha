"""Verify the published FANC T1 tibia-extensor mesh fragments and geometry."""

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/reference/fanc_ti_extensor_meshes"
REPORT = ROOT / "reports/fanc_ti_extensor_meshes.json"
BUCKET = "https://storage.googleapis.com/lee-lab_female-adult-nerve-cord/meshes/FANC/FANC_neurons/meshes/"
INPUTS = {
    "648518346493238080": {
        "manifest_sha256": "3d9a601699ed293f80bafc162d4dd714943266b3b66884854ad96729bee19b04",
        "fragment_sha256": "d9a0ab526e1539a1a942f162e7d6252deec07e46122181aeafa0da1be11e0a8d",
        "manifest_generation": "1685135798532508",
        "fragment_generation": "1685135801215267",
    },
    "648518346495797355": {
        "manifest_sha256": "351f57099b98a84c525d64221939fa4aa6000f03dac3c1aa79a1f3525a6c870a",
        "fragment_sha256": "871ceac63ea3ed42b44a71000acbd693217fe4893d89c458a2d3aa79531ec5cd",
        "manifest_generation": "1685132518125363",
        "fragment_generation": "1685132519981130",
    },
}


def verified(path, digest):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise ValueError(f"hash mismatch: {path}: {actual}")
    return raw


def main():
    meshes = []
    for root_id, spec in INPUTS.items():
        manifest = verified(DATA / f"{root_id}_manifest.bin", spec["manifest_sha256"])
        fragment = verified(DATA / f"{root_id}_fragment.bin", spec["fragment_sha256"])
        assert len(manifest) == 40
        n_vertices = int(np.frombuffer(fragment, dtype="<u4", count=1)[0])
        vertices_end = 4 + n_vertices * 12
        assert vertices_end < len(fragment) and (len(fragment) - vertices_end) % 12 == 0
        xyz = np.frombuffer(fragment, dtype="<f4", offset=4, count=n_vertices * 3).reshape((-1, 3))
        assert np.isfinite(xyz).all()
        assert (xyz >= 0).all()
        faces = np.frombuffer(fragment, dtype="<u4", offset=vertices_end)
        assert faces.size and int(faces.max()) < n_vertices
        meshes.append({
            "segment_id": root_id,
            "source_manifest": BUCKET + root_id + ":0?generation=" + spec["manifest_generation"],
            "source_fragment": BUCKET + root_id + ":0:1?generation=" + spec["fragment_generation"],
            "source_files_are_gzip_encoded": True,
            "local_files_are_decompressed_http_payloads": True,
            **spec,
            "vertex_count": n_vertices,
            "triangle_count": int(faces.size // 3),
            "bbox_min_nm": xyz.min(axis=0).tolist(),
            "bbox_max_nm": xyz.max(axis=0).tolist(),
        })
    report = {
        "scope": "Source-pinned published 3D meshes for the FANC T1 tibia-extensor pair",
        "published_pair_source_report": "reports/fanc_ti_extensor_source_ids.json",
        "meshes": meshes,
        "fanc_mn39_vs_mn40_assignment_verified": False,
        "fanc_to_manc_registration_performed": False,
        "motor_mapping_enabled": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print([(m["segment_id"], m["vertex_count"], m["triangle_count"]) for m in meshes])


if __name__ == "__main__":
    main()
