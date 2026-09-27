"""Count connected components directly in the unmodified published meshes."""

import gc
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/fanc_ti_extensor_meshes.json"
OUT = ROOT / "reports/fanc_ti_extensor_original_components.json"


def main():
    spec = json.loads(SOURCE.read_text())
    results = []
    for item in spec["meshes"]:
        ident = item["segment_id"]
        path = ROOT / "data/reference/fanc_ti_extensor_meshes" / f"{ident}_fragment.bin"
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["fragment_sha256"]
        n = int(np.frombuffer(raw, dtype="<u4", count=1)[0])
        faces = np.frombuffer(raw, dtype="<u4", offset=4 + n * 12).reshape(-1, 3)
        assert n == item["vertex_count"] and len(faces) == item["triangle_count"]
        # Two edges per triangle are sufficient to represent its connectivity.
        rows = np.concatenate((faces[:, 0], faces[:, 0]))
        cols = np.concatenate((faces[:, 1], faces[:, 2]))
        graph = csr_matrix((np.ones(len(rows), dtype=np.uint8), (rows, cols)), shape=(n, n))
        count, labels = connected_components(graph, directed=False)
        sizes = np.sort(np.bincount(labels))[::-1]
        results.append({
            "segment_id": ident,
            "component_count": int(count),
            "largest_vertices": sizes[:10].tolist(),
            "largest_fraction": float(sizes[0] / n),
            "top_two_fraction": float(sizes[:2].sum() / n),
            "isolated_single_vertex_components": int(np.count_nonzero(sizes == 1)),
        })
        print(ident, count, results[-1]["largest_fraction"], flush=True)
        del raw, faces, rows, cols, graph, labels, sizes
        gc.collect()
    report = {
        "scope": "Exact graph components of original published triangle meshes, before decimation",
        "source_report_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "results": results,
        "fragment_reconnection_authorized": False,
        "fanc_manc_identity_verified": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
