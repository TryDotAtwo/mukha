"""Trace direct and two-edge taste-to-MN9 paths in the pinned MaleCNS CSR."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/malecns_v1_candidates"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((GRAPH / "manifest.json").read_text())
    for name in ("body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy"):
        if sha(GRAPH / name) != manifest["files"][name]["sha256"]:
            raise ValueError("CSR hash mismatch: " + name)
    ids = np.load(GRAPH / "body_ids.npy")
    row = np.load(GRAPH / "indptr.npy")
    col = np.load(GRAPH / "indices.npy")
    weight = np.load(GRAPH / "synapse_counts.npy")
    nt = pd.read_feather(GRAPH / "neurotransmitters.feather").set_index("body").reindex(ids).consensus_nt.fillna("missing_annotation")
    cross = json.loads((ROOT / "reports/tastekin2026_malecns_crosswalk.json").read_text())
    by_id = {int(body): ix for ix, body in enumerate(ids)}
    masks = {
        "sweet_LB3c": set(cross["populations"]["sweet_candidate_LB3c"]["body_ids"]),
        "bitter_LB1a_d": set(cross["populations"]["bitter_candidate_LB1a_d"]["body_ids"]),
    }
    neurons = []
    for target in (10331, 16949):
        ix = by_id[target]
        edge_ix = np.arange(int(row[ix]), int(row[ix + 1]), dtype=np.int64)
        source_ix = col[edge_ix]
        source_ids = ids[source_ix]
        direct = {}
        two_edge = {}
        for label, inputs in masks.items():
            direct[label] = [int(x) for x in source_ids if int(x) in inputs]
            intermediates = []
            for mid in source_ix:
                incoming = ids[col[int(row[mid]):int(row[mid + 1])]]
                hits = [int(x) for x in incoming if int(x) in inputs]
                if hits:
                    intermediates.append({"intermediate_body_id": int(ids[mid]),
                                          "sensory_body_ids": hits,
                                          "contacts_to_mn9": int(weight[edge_ix[np.flatnonzero(source_ix == mid)[0]]])})
            two_edge[label] = intermediates
        strongest = sorted(({"body_id": int(ids[col[e]]), "contacts": int(weight[e]),
                             "consensus_nt": str(nt.iloc[col[e]])} for e in edge_ix),
                           key=lambda item: (-item["contacts"], item["body_id"]))[:20]
        neurons.append({"mn9_body_id": target, "incoming_edges": len(edge_ix),
                        "incoming_contacts": int(weight[edge_ix].sum()),
                        "presynaptic_nt_counts": dict(Counter(str(nt.iloc[x]) for x in source_ix)),
                        "direct_taste_source_ids": direct,
                        "two_edge_intermediates": two_edge,
                        "strongest_incoming": strongest})
    report = {"scope": "Exact anatomical graph paths, without functional signs or dynamical inference",
              "graph_manifest_sha256": sha(GRAPH / "manifest.json"),
              "crosswalk_sha256": sha(ROOT / "reports/tastekin2026_malecns_crosswalk.json"),
              "mn9": neurons}
    dest = ROOT / "reports/tastekin2026_mn9_anatomy.json"
    dest.write_text(json.dumps(report, indent=2) + "\n")
    for entry in neurons:
        print(entry["mn9_body_id"], entry["incoming_edges"], entry["incoming_contacts"],
              {k: len(v) for k, v in entry["two_edge_intermediates"].items()})


if __name__ == "__main__":
    main()
