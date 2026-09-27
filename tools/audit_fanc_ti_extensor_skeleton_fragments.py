"""Skeletonize simplified FANC meshes and measure disconnected components."""

import hashlib
import json
from pathlib import Path

import numpy as np
import skeletor
import trimesh


ROOT = Path(__file__).resolve().parents[1]
SIMPLIFIED = ROOT / "reports/fanc_ti_extensor_simplification.json"
OUTPUT = ROOT / "data/derived/fanc_ti_extensor_skeletons"
REPORT = ROOT / "reports/fanc_ti_extensor_skeleton_fragments.json"


def components(edges, n):
    groups = trimesh.graph.connected_components(edges, nodes=np.arange(n))
    sizes = sorted((len(g) for g in groups), reverse=True)
    return {"count": len(sizes), "largest_vertices": sizes[:10],
            "largest_fraction": sizes[0] / n,
            "top_two_fraction": sum(sizes[:2]) / n}


def main():
    source = json.loads(SIMPLIFIED.read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = []
    for item in source["results"]:
        path = ROOT / item["output"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        arrays = np.load(path)
        mesh = trimesh.Trimesh(vertices=arrays["vertices"], faces=arrays["faces"], process=False)
        mesh_comp = components(mesh.edges, len(mesh.vertices))
        skeleton = skeletor.skeletonize.by_wavefront(mesh, waves=1, step_size=1, progress=False)
        assert len(skeleton.vertices) and len(skeleton.edges)
        skel_comp = components(skeleton.edges, len(skeleton.vertices))
        out = OUTPUT / f'{item["segment_id"]}_wavefront.npz'
        np.savez_compressed(out, vertices=skeleton.vertices, edges=skeleton.edges)
        result.append({
            "segment_id": item["segment_id"],
            "input_mesh_components": mesh_comp,
            "skeleton_vertices": len(skeleton.vertices),
            "skeleton_edges": len(skeleton.edges),
            "skeleton_components": skel_comp,
            "output": str(out.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        })
        print(item["segment_id"], mesh_comp["count"], skel_comp["count"], flush=True)
    report = {
        "scope": "Diagnostic wavefront skeletonization of decimated source meshes; fragmented representation",
        "source_report_sha256": hashlib.sha256(SIMPLIFIED.read_bytes()).hexdigest(),
        "skeletor_version": skeletor.__version__,
        "method": "by_wavefront(waves=1, step_size=1)",
        "results": result,
        "suitable_for_nblast_identity": False,
        "motor_mapping_enabled": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
