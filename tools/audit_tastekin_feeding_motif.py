"""Verify the source-labelled taste feeding motif in the unchanged MaleCNS CSR."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.feather as feather

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "data/derived/malecns_v1_candidates"
OUT = ROOT / "reports/tastekin2026_feeding_motif.json"
NAMED = {"Scapula": [11896, 12811, 12900], "Roundup": [26764, 523040],
         "Rounddown": [12364, 12752], "G2N-1": [31018, 89638]}
ROUTES = [("bitter_LB1a_d", "Scapula"), ("sweet_LB3c", "G2N-1"),
          ("Scapula", "Roundup"), ("Scapula", "Rounddown"),
          ("G2N-1", "Roundup"), ("Scapula", "G2N-1"),
          ("bitter_LB1a_d", "G2N-1")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    manifest = json.loads((G / "manifest.json").read_text())
    for name in ("body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy", "nodes.feather"):
        if sha(G / name) != manifest["files"][name]["sha256"]:
            raise ValueError("Graph hash mismatch: " + name)
    ids = np.load(G / "body_ids.npy")
    rows = np.load(G / "indptr.npy")
    cols = np.load(G / "indices.npy")
    counts = np.load(G / "synapse_counts.npy")
    index = {int(body): i for i, body in enumerate(ids)}
    nodes = feather.read_table(G / "nodes.feather").to_pandas().set_index("bodyId")
    for name, group in NAMED.items():
        for body in group:
            if name not in str(nodes.at[body, "synonyms"]):
                raise ValueError("Named cell mismatch")
    cross = json.loads((ROOT / "reports/tastekin2026_malecns_crosswalk.json").read_text())
    groups = dict(NAMED, sweet_LB3c=cross["populations"]["sweet_candidate_LB3c"]["body_ids"],
                  bitter_LB1a_d=cross["populations"]["bitter_candidate_LB1a_d"]["body_ids"])
    route_report = []
    for source_name, target_name in ROUTES:
        source_ids = set(groups[source_name])
        pairs = []
        for target in groups[target_name]:
            target_ix = index[target]
            for e in range(int(rows[target_ix]), int(rows[target_ix + 1])):
                source = int(ids[cols[e]])
                if source in source_ids:
                    pairs.append({"source_body_id": source, "target_body_id": target,
                                  "contacts": int(counts[e])})
        route_report.append({"source": source_name, "target": target_name,
                             "edge_count": len(pairs),
                             "contact_count": sum(item["contacts"] for item in pairs),
                             "edges": pairs})
    report = {"scope": "Pinned MaleCNS anatomical edge counts; cell-type aliases and GRN modalities are cross-specimen candidate mappings",
              "graph_manifest_sha256": sha(G / "manifest.json"),
              "crosswalk_sha256": sha(ROOT / "reports/tastekin2026_malecns_crosswalk.json"),
              "reference": "https://doi.org/10.7554/eLife.79887",
              "important_difference": "Unlike Shiu 2022 FAFB Figure 5 description, pinned MaleCNS has Scapula-to-G2N-1 candidate edges; this may reflect specimen/dataset or matching differences and does not establish functional inhibition.",
              "routes": route_report}
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    for route in route_report:
        print(route["source"], "->", route["target"], route["edge_count"], route["contact_count"])


if __name__ == "__main__":
    main()
