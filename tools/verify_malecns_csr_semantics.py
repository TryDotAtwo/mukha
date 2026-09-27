"""Verify the retained MaleCNS CSR's structure, beyond manifest byte hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
REPORT = ROOT / "reports/malecns_csr_semantics.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    manifest_path = GRAPH / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["format"] == "flyrocket.incoming-csr.v1"
    assert manifest["orientation"] == "row=postsynaptic; indices=presynaptic"
    assert not (GRAPH / "INCOMPLETE").exists()
    n, e = int(manifest["nodes"]), int(manifest["edges"])
    for name, record in manifest["files"].items():
        assert Path(name).name == name
        path = GRAPH / name
        assert path.stat().st_size == record["bytes"], name
        assert digest(path) == record["sha256"], name

    arrays = {name: np.load(GRAPH / (name + ".npy"), mmap_mode="r", allow_pickle=False)
              for name in ("body_ids", "indptr", "indices", "synapse_counts", "source_rows")}
    body, row, col, counts, source = (arrays[name] for name in arrays)
    assert [(a.shape, a.dtype.str) for a in arrays.values()] == [
        ((n,), "<u8"), ((n + 1,), "<u8"), ((e,), "<u4"),
        ((e,), "<u8"), ((e,), "<u8")]
    assert int(row[0]) == 0 and int(row[-1]) == e
    assert np.all(row[1:] >= row[:-1]), "nonmonotonic row pointers"
    assert len(np.unique(body)) == n, "duplicate body ID"
    assert np.all(col < n), "out-of-range presynaptic index"

    # A globally adjacent pair is required to increase only within one row.
    # This also proves that the manifest's duplicate-pair count is zero.
    boundary = np.asarray(row[1:-1], dtype=np.int64)
    for start in range(0, e - 1, 1_000_000):
        stop = min(start + 1_000_000, e - 1)
        left = np.asarray(col[start:stop], dtype=np.int64)
        right = np.asarray(col[start + 1:stop + 1], dtype=np.int64)
        same_row = np.ones(stop - start, dtype=bool)
        cuts = boundary[(boundary > start) & (boundary <= stop)] - start - 1
        same_row[cuts] = False
        assert np.all(left[ same_row] < right[same_row]), "unsorted or repeated presynaptic index"

    assert np.all(counts > 0), "nonpositive retained contact count"
    contact_sum = sum(int(np.sum(counts[start:start + 1_000_000], dtype=np.uint64))
                      for start in range(0, e, 1_000_000))
    assert contact_sum == manifest["retained_synapse_count_sum"]
    assert len(np.unique(source)) == e, "source row reused"
    self_edges = sum(int(np.count_nonzero(col[int(row[i]):int(row[i + 1])] == i))
                     for i in range(n))
    assert self_edges == manifest["self_edges_preserved"]
    isolated = int(np.count_nonzero((row[1:] == row[:-1]) &
                                    (np.bincount(col, minlength=n) == 0)))
    assert isolated == manifest["isolated_nodes_preserved"]
    result = {"scope": "Byte hashes and structural semantics of the retained incoming CSR; no physiological sign or complete-neuron claim",
              "graph_manifest_sha256": digest(manifest_path), "nodes": n, "edges": e,
              "retained_contacts": contact_sum, "self_edges": self_edges,
              "isolated_nodes": isolated, "row_monotonic": True,
              "indices_in_range": True, "rows_strictly_sorted": True,
              "unique_body_ids": True, "unique_source_rows": True,
              "passed": True}
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
