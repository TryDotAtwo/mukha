"""Check source-pinned VFB arculum/tendon OBJ meshes in their native frame."""

import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/reference/mamiya2023/xray"
OUT = ROOT / "reports/mamiya_xray_surfaces.json"
SOURCES = {
    "arculum_outline": ("2efd", "b432684ccea69453bcd7a7445f970ec401ac98cc1ee2cbd64baab6eefc563e99"),
    "feco_medial_tendon": ("2efe", "00fa8f391e677223570dfa85938752bc608df206f9ae0bc9b3cc1ce1b275aa24"),
    "feco_lateral_tendon": ("2eff", "cd53e5ffcfb4cef835c3d7fcb572d4cbc218ef8ffa2f3702da40f197fd1a25c6"),
}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    meshes = {}
    manifest = {}
    for name, (suffix, expected_sha) in SOURCES.items():
        path = DEST / f"{name}.obj"
        url = f"https://www.virtualflybrain.org/data/VFB/i/0010/{suffix}/VFB_00120000/volume_man.obj"
        if not path.exists():
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            assert hashlib.sha256(data).hexdigest() == expected_sha, name
            path.write_bytes(data)
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected_sha, name
        mesh = trimesh.load(path, process=False)
        assert isinstance(mesh, trimesh.Trimesh), name
        assert len(mesh.vertices) and len(mesh.faces)
        swc_path = DEST / f"{name}.swc"
        swc = np.array([[float(value) for value in line.split()[2:5]]
                        for line in swc_path.read_text(encoding="utf-8").splitlines()
                        if line and not line.startswith("#")])
        assert np.all(swc >= mesh.bounds[0] - 0.01) and np.all(swc <= mesh.bounds[1] + 0.01), name
        meshes[name] = mesh
        manifest[name] = {
            "url": url,
            "sha256": expected_sha,
            "bytes": len(data),
            "vertices": len(mesh.vertices),
            "triangles": len(mesh.faces),
            "watertight": bool(mesh.is_watertight),
            "bounds_um": mesh.bounds.tolist(),
            "swc_nodes_inside_mesh_axis_aligned_bounds": True,
        }
    arculum_tree = cKDTree(meshes["arculum_outline"].vertices)
    for name in ("feco_medial_tendon", "feco_lateral_tendon"):
        tendon = meshes[name]
        distances, nearest_indices = arculum_tree.query(tendon.vertices)
        tendon_index = int(distances.argmin())
        arculum_index = int(nearest_indices[tendon_index])
        manifest[name]["nearest_vertex_to_arculum"] = {
            "distance_um": float(distances[tendon_index]),
            "tendon_xyz_um": tendon.vertices[tendon_index].tolist(),
            "arculum_xyz_um": meshes["arculum_outline"].vertices[arculum_index].tolist(),
        }
    report = {
        "scope": "Static VFB OBJ geometry only, in the native micrometer coordinate frame",
        "source_dataset": "https://www.virtualflybrain.org/term/biomechanical-origins-of-proprioceptive-maps-in-the-drosophila-leg-mamiya2022/",
        "meshes": manifest,
        "distance_limit": "Nearest mesh VERTEX pairs; they provide only an upper bound on surface separation when meshes do not intersect, not a surface distance or proof of physical attachment",
        "biological_validation": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: manifest[name]["nearest_vertex_to_arculum"]["distance_um"]
                      for name in ("feco_medial_tendon", "feco_lateral_tendon")}, indent=2))


if __name__ == "__main__":
    main()
