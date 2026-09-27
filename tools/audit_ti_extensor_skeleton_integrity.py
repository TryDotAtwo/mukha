"""Verify pinned MaleCNS Ti-extensor SWCs before cross-volume matching."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/malecns_v1_ti_extensor_skeletons"


def audit(path):
    a = np.loadtxt(path)
    assert a.ndim == 2 and a.shape[1] == 7 and np.isfinite(a).all()
    node = a[:, 0].astype(np.int64)
    parent = a[:, 6].astype(np.int64)
    assert np.array_equal(node, a[:, 0]) and np.array_equal(parent, a[:, 6])
    assert len(np.unique(node)) == len(node)
    lookup = {int(value): i for i, value in enumerate(node)}
    roots = np.flatnonzero(parent < 0)
    assert len(roots) >= 1
    assert all(int(value) in lookup for value in parent[parent >= 0])
    parent_index = np.array([lookup.get(int(value), -1) for value in parent], dtype=np.int64)
    assert not np.any(parent_index == np.arange(len(node)))
    root_for = np.full(len(node), -1, dtype=np.int64)
    for i in range(len(node)):
        trail = []
        seen = set()
        j = i
        while root_for[j] < 0 and parent_index[j] >= 0:
            assert j not in seen, "SWC cycle"
            seen.add(j)
            trail.append(j)
            j = int(parent_index[j])
        root = int(root_for[j]) if root_for[j] >= 0 else j
        root_for[j] = root
        for k in trail:
            root_for[k] = root
    unique, counts = np.unique(root_for, return_counts=True)
    assert len(unique) == len(roots)
    edge = parent_index >= 0
    cable_um = np.linalg.norm(a[edge, 2:5] - a[parent_index[edge], 2:5], axis=1) * 0.008
    return {
        "nodes": len(node),
        "roots": len(roots),
        "component_node_counts_descending": sorted(map(int, counts), reverse=True),
        "largest_component_node_fraction": float(counts.max() / len(node)),
        "total_skeleton_cable_um": float(cable_um.sum()),
        "bbox_extent_um": (np.ptp(a[:, 2:5], axis=0) * 0.008).tolist(),
    }


def run():
    manifest = json.loads((SOURCE / "source_manifest.json").read_text())
    results = {}
    for entry in manifest["items"]:
        path = SOURCE / f'{entry["bodyId"]}.swc'
        raw = path.read_bytes()
        assert len(raw) == entry["bytes"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        results[str(entry["bodyId"])] = audit(path)
    report = {
        "scope": "MaleCNS v1.0 SWC geometry integrity, no cross-volume registration or motor identity acceptance",
        "source_manifest_sha256": hashlib.sha256((SOURCE / "source_manifest.json").read_bytes()).hexdigest(),
        "coordinate_unit": "8 nm voxels; derived lengths in micrometers",
        "cells": results,
        "matched_to_manc_skeleton": False,
        "biological_gate_passed": False,
    }
    out = ROOT / "reports/malecns_ti_extensor_skeleton_integrity.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
