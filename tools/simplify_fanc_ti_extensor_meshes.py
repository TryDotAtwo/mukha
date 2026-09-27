"""Create explicitly approximate meshes for exploratory FANC skeletonization."""

import gc
import hashlib
import json
from pathlib import Path

import fast_simplification
import numpy as np
from scipy.spatial import cKDTree
import trimesh


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/fanc_ti_extensor_meshes"
OUTPUT = ROOT / "data/derived/fanc_ti_extensor_simplified"
REPORT = ROOT / "reports/fanc_ti_extensor_simplification.json"
FACES = 200_000


def main():
    source_report = ROOT / "reports/fanc_ti_extensor_meshes.json"
    inputs = json.loads(source_report.read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260924)
    results = []
    for item in inputs["meshes"]:
        ident = item["segment_id"]
        source = SOURCE / f"{ident}_fragment.bin"
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["fragment_sha256"]
        n = int(np.frombuffer(raw, dtype="<u4", count=1)[0])
        assert n == item["vertex_count"]
        split = 4 + n * 12
        xyz = np.frombuffer(raw, dtype="<f4", offset=4, count=3*n).reshape(-1, 3)
        faces = np.frombuffer(raw, dtype="<u4", offset=split).reshape(-1, 3)
        sample = xyz[rng.choice(n, min(20_000, n), replace=False)].astype(np.float64)
        mesh = trimesh.Trimesh(vertices=xyz, faces=faces, process=False, validate=False)
        simple = mesh.simplify_quadric_decimation(face_count=FACES, aggression=7)
        print("decimation counts", ident, len(simple.vertices), len(simple.faces), flush=True)
        assert len(simple.faces) < len(faces) and len(simple.vertices) < n
        assert np.isfinite(simple.vertices).all()
        d = cKDTree(simple.vertices).query(sample, workers=-1)[0]
        out = OUTPUT / f"{ident}_f{FACES}.npz"
        np.savez_compressed(out, vertices=simple.vertices, faces=simple.faces)
        results.append({
            "segment_id": ident,
            "original_vertices": n,
            "original_faces": len(faces),
            "simplified_vertices": len(simple.vertices),
            "simplified_faces": len(simple.faces),
            "sample_to_simplified_vertex_median_nm": float(np.median(d)),
            "sample_to_simplified_vertex_p90_nm": float(np.quantile(d, .9)),
            "sample_to_simplified_vertex_p99_nm": float(np.quantile(d, .99)),
            "original_bbox_nm": [xyz.min(0).tolist(), xyz.max(0).tolist()],
            "simplified_bbox_nm": [simple.vertices.min(0).tolist(), simple.vertices.max(0).tolist()],
            "output": str(out.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        })
        print(ident, results[-1]["simplified_vertices"], results[-1]["sample_to_simplified_vertex_p99_nm"], flush=True)
        del raw, xyz, faces, mesh, simple, d
        gc.collect()
    report = {
        "scope": "Exploratory decimation; topology and fine neurites not yet validated",
        "source_report_sha256": hashlib.sha256(source_report.read_bytes()).hexdigest(),
        "fast_simplification_version": fast_simplification.__version__,
        "trimesh_version": trimesh.__version__,
        "requested_target_faces": FACES,
        "results": results,
        "biological_identity_verified": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
