"""Audit anatomical KC-to-KC subtype connectivity in the accepted MaleCNS CSR.

This does not identify axonal synapses, mAChR-B expression, or plasticity.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
OUT = ROOT / "reports/malecns_kc_lateral_subtypes.json"
GROUPS = ("gamma", "alpha_beta", "alpha_prime_beta_prime", "unresolved")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def group(type_name):
    if type_name.startswith("KCg"):
        return "gamma"
    if type_name.startswith("KCab"):
        return "alpha_beta"
    if type_name.startswith("KCa'b'"):
        return "alpha_prime_beta_prime"
    return "unresolved"


def main():
    manifest_path = GRAPH / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    names = ("nodes.feather", "indptr.npy", "indices.npy", "synapse_counts.npy")
    for name in names:
        path = GRAPH / name
        assert path.stat().st_size == manifest["files"][name]["bytes"]
        assert digest(path) == manifest["files"][name]["sha256"]
    nodes = pd.read_feather(GRAPH / "nodes.feather", columns=["compact_index", "class", "type"])
    n = len(nodes)
    assert n == manifest["nodes"]
    assert np.array_equal(nodes.compact_index.to_numpy(), np.arange(n, dtype=np.uint32))
    kc = nodes["class"].eq("Kenyon_Cell").to_numpy()
    types = nodes["type"].fillna("").to_numpy()
    labels = np.array([group(str(types[i])) if kc[i] else "not_kc" for i in range(n)])
    ptr = np.load(GRAPH / "indptr.npy", mmap_mode="r")
    pre = np.load(GRAPH / "indices.npy", mmap_mode="r")
    contacts = np.load(GRAPH / "synapse_counts.npy", mmap_mode="r")
    assert len(ptr) == n + 1 and len(pre) == len(contacts) == manifest["edges"]
    population = {g: int(np.sum(labels == g)) for g in GROUPS}
    rows = {(a, b): {"edge_rows": 0, "contacts": 0} for a in GROUPS for b in GROUPS}
    inbound = np.zeros(n, dtype=np.int32)
    outbound = np.zeros(n, dtype=np.int32)
    self_rows = 0
    for post in np.flatnonzero(kc):
        start, end = int(ptr[post]), int(ptr[post + 1])
        source = np.asarray(pre[start:end])
        weights = np.asarray(contacts[start:end])
        mask = kc[source]
        source, weights = source[mask], weights[mask]
        inbound[post] = len(source)
        np.add.at(outbound, source, 1)
        self_rows += int(np.sum(source == post))
        post_label = labels[post]
        for pre_label in GROUPS:
            part = labels[source] == pre_label
            rows[(pre_label, post_label)]["edge_rows"] += int(np.sum(part))
            rows[(pre_label, post_label)]["contacts"] += int(np.sum(weights[part], dtype=np.uint64))
    summary = []
    for g in GROUPS:
        members = labels == g
        summary.append({"subtype": g, "cells": population[g],
                        "mean_distinct_kc_inputs": float(inbound[members].mean()) if population[g] else None,
                        "mean_distinct_kc_outputs": float(outbound[members].mean()) if population[g] else None,
                        "median_distinct_kc_inputs": float(np.median(inbound[members])) if population[g] else None})
    pair_rows = [{"presynaptic_subtype": a, "postsynaptic_subtype": b, **rows[(a, b)]}
                 for a in GROUPS for b in GROUPS]
    total_rows = sum(r["edge_rows"] for r in pair_rows)
    total_contacts = sum(r["contacts"] for r in pair_rows)
    assert total_rows == int(inbound[kc].sum()) == int(outbound[kc].sum()) == 642933
    assert total_contacts == 1153845
    report = {
        "scope": "Original accepted graph KC-to-KC anatomy by source type label; no axonal location, receptor localization, physiology or plasticity inference",
        "graph_manifest_sha256": digest(manifest_path),
        "checked_file_sha256": {name: manifest["files"][name]["sha256"] for name in names},
        "type_mapping": {"KCg*": "gamma", "KCab*": "alpha_beta", "KCa'b'*": "alpha_prime_beta_prime", "other": "unresolved"},
        "population": summary,
        "directed_subtype_pairs": pair_rows,
        "total_kc_kc_edge_rows": total_rows,
        "total_kc_kc_contacts": total_contacts,
        "self_edge_rows": self_rows,
        "interpretation_limit": "Source connectivity includes directed chemical rows only; group names are MaleCNS annotations. Cross-study species/sex/release and anatomical compartment differences prevent direct numeric validation against other connectomes.",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"population": summary, "total_rows": total_rows,
                      "total_contacts": total_contacts, "self_rows": self_rows}))


if __name__ == "__main__":
    main()
