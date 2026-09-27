"""Inventory direct MaleCNS R1-R6 to author-assigned L1 column edges."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
ASSIGN = ROOT / "data/derived/malecns_optic_columns/assignments.csv"
OUT = ROOT / "data/derived/r16_l1_column_edges_v1"
REPORT = ROOT / "reports/malecns_r16_l1_column_edges.json"
FILES = ("nodes.feather", "body_ids.npy", "indptr.npy", "indices.npy",
         "synapse_counts.npy", "source_rows.npy")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    manifest = json.loads((GRAPH / "manifest.json").read_text(encoding="utf-8"))
    for name in FILES:
        path = GRAPH / name
        assert path.stat().st_size == manifest["files"][name]["bytes"]
        assert sha(path) == manifest["files"][name]["sha256"]
    optic = json.loads((ROOT / "reports/optic_column_index.json").read_text(encoding="utf-8"))
    assert sha(ASSIGN) == optic["files"]["assignments.csv"]
    nodes = pd.read_feather(GRAPH / "nodes.feather", columns=["bodyId", "type", "rootSide"])
    body = np.load(GRAPH / "body_ids.npy", mmap_mode="r")
    assert np.array_equal(nodes.bodyId.to_numpy(), body)
    ptr = np.load(GRAPH / "indptr.npy", mmap_mode="r")
    pre = np.load(GRAPH / "indices.npy", mmap_mode="r")
    contacts = np.load(GRAPH / "synapse_counts.npy", mmap_mode="r")
    source_rows = np.load(GRAPH / "source_rows.npy", mmap_mode="r")
    assert len(ptr) == len(nodes) + 1 and int(ptr[-1]) == len(pre) == len(contacts) == len(source_rows)
    assign = pd.read_csv(ASSIGN).query("role == 'L1'")
    assert len(assign) == 1764 and assign.body_id.is_unique
    is_receptor = nodes.type.eq("R1-R6").to_numpy()
    receptors = np.flatnonzero(is_receptor)
    assert len(receptors) == 3377
    by_body = {int(x): i for i, x in enumerate(body)}
    edge_rows = []
    receptor_columns = defaultdict(set)
    receptor_contacts = defaultdict(int)
    for target in assign.itertuples(index=False):
        post = by_body[int(target.body_id)]
        lo, hi = int(ptr[post]), int(ptr[post + 1])
        for edge in range(lo, hi):
            source_index = int(pre[edge])
            if not is_receptor[source_index]:
                continue
            side = nodes.rootSide.iat[source_index]
            edge_rows.append({
                "r16_body_id": int(body[source_index]),
                "r16_graph_index": source_index,
                "r16_root_side": side,
                "l1_body_id": int(target.body_id),
                "l1_graph_index": post,
                "column": target.column,
                "column_side": target.side,
                "hex1": int(target.hex1),
                "hex2": int(target.hex2),
                "synapse_contacts": int(contacts[edge]),
                "csr_edge_index": edge,
                "source_edge_row": int(source_rows[edge]),
            })
            receptor_columns[source_index].add(target.column)
            receptor_contacts[source_index] += int(contacts[edge])
    edge_frame = pd.DataFrame(edge_rows).sort_values(
        ["r16_body_id", "l1_body_id"]).reset_index(drop=True)
    assert edge_frame.csr_edge_index.is_unique
    assert (edge_frame.synapse_contacts > 0).all()
    assert (edge_frame.r16_root_side == edge_frame.column_side).all()
    summary = []
    for index in receptors:
        ix = int(index)
        count = len(receptor_columns[ix])
        summary.append({"r16_body_id": int(body[ix]), "r16_graph_index": ix,
                        "root_side": nodes.rootSide.iat[ix],
                        "assigned_l1_column_count": count,
                        "assigned_l1_contacts": receptor_contacts[ix],
                        "status": "none" if count == 0 else "single" if count == 1 else "multiple"})
    summary_frame = pd.DataFrame(summary).sort_values("r16_body_id").reset_index(drop=True)
    counts = {str(k): int(v) for k, v in summary_frame.status.value_counts().items()}
    assert sum(counts.values()) == len(receptors)
    OUT.mkdir(parents=True, exist_ok=True)
    edge_path = OUT / "direct_edges.csv"
    map_path = OUT / "receptor_status.csv"
    edge_frame.to_csv(edge_path, index=False)
    summary_frame.to_csv(map_path, index=False)
    report = {
        "scope": "Exact direct R1-R6 to author-assigned L1 graph rows; candidate column paths only, not receptor optical axes",
        "graph_manifest_sha256": sha(GRAPH / "manifest.json"),
        "assignment_sha256": sha(ASSIGN),
        "receptor_cells": len(receptors),
        "assigned_l1_cells": len(assign),
        "direct_edge_rows": len(edge_frame),
        "direct_contacts": int(edge_frame.synapse_contacts.sum()),
        "assigned_l1_with_direct_r16_input": int(edge_frame.l1_body_id.nunique()),
        "assigned_l1_without_direct_r16_input": int(len(assign) - edge_frame.l1_body_id.nunique()),
        "receptor_target_degree_counts": {str(k): int(v) for k, v in
             edge_frame.groupby("r16_body_id").l1_body_id.nunique().value_counts().sort_index().items()},
        "receptor_status_counts": counts,
        "cross_side_edge_rows": int((edge_frame.r16_root_side != edge_frame.column_side).sum()),
        "direct_edges_csv_sha256": sha(edge_path),
        "receptor_status_csv_sha256": sha(map_path),
        "interpretation": "Single assigned L1 target gives one direct anatomical path to an existing medulla hex column. It does not identify an R1-R6 ommatidium, its optical axis, transmission sign/gain, or all potentially missing contacts. Multiple targets are retained without ranking.",
        "optical_rays_assigned": 0,
        "visual_input_enabled": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("receptor_cells", "assigned_l1_cells",
         "direct_edge_rows", "direct_contacts", "receptor_status_counts",
         "cross_side_edge_rows")}, indent=2))


if __name__ == "__main__":
    main()

