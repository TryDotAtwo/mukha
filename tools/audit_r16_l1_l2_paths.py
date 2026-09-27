"""Reconcile direct R1-R6 paths through L1 and L2 medulla columns."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
L1_EDGES = ROOT / "data/derived/r16_l1_column_edges_v1/direct_edges.csv"
OUT = ROOT / "data/derived/r16_l1_l2_paths_v1"
REPORT = ROOT / "reports/malecns_r16_l1_l2_paths.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    graph_manifest = json.loads((GRAPH / "manifest.json").read_text(encoding="utf-8"))
    for name in ("nodes.feather", "body_ids.npy", "indptr.npy", "indices.npy",
                 "synapse_counts.npy", "source_rows.npy"):
        path = GRAPH / name
        assert path.stat().st_size == graph_manifest["files"][name]["bytes"]
        assert sha(path) == graph_manifest["files"][name]["sha256"]
    l1_report = json.loads((ROOT / "reports/malecns_r16_l1_column_edges.json").read_text(encoding="utf-8"))
    assert sha(L1_EDGES) == l1_report["direct_edges_csv_sha256"]
    nodes = pd.read_feather(GRAPH / "nodes.feather",
                           columns=["bodyId", "type", "instance", "rootSide",
                                    "assignedOlHex1", "assignedOlHex2"])
    body = np.load(GRAPH / "body_ids.npy", mmap_mode="r")
    assert np.array_equal(nodes.bodyId.to_numpy(), body)
    ptr = np.load(GRAPH / "indptr.npy", mmap_mode="r")
    pre = np.load(GRAPH / "indices.npy", mmap_mode="r")
    counts = np.load(GRAPH / "synapse_counts.npy", mmap_mode="r")
    source_rows = np.load(GRAPH / "source_rows.npy", mmap_mode="r")
    assert int(ptr[-1]) == len(pre) == len(counts) == len(source_rows)
    is_r16 = nodes.type.eq("R1-R6").to_numpy()
    receptors = np.flatnonzero(is_r16)
    assert len(receptors) == 3377
    assert l1_report["graph_manifest_sha256"] == sha(GRAPH / "manifest.json")
    accepted_columns_path = ROOT / "data/derived/malecns_optic_columns/columns.csv"
    optic_report = json.loads((ROOT / "reports/optic_column_index.json").read_text(encoding="utf-8"))
    assert sha(accepted_columns_path) == optic_report["files"]["columns.csv"]
    accepted = pd.read_csv(accepted_columns_path)
    accepted_columns = set(zip(accepted.side, accepted.hex1.astype(int), accepted.hex2.astype(int)))
    l1 = pd.read_csv(L1_EDGES)
    l1_paths = defaultdict(set)
    for row in l1.itertuples(index=False):
        l1_paths[int(row.r16_body_id)].add((row.column_side, int(row.hex1), int(row.hex2)))
    l2_cells = nodes.loc[nodes.type.eq("L2")].copy()
    assert l2_cells.instance.str.fullmatch(r"L2_[LR]").all()
    l2_cells = l2_cells.dropna(subset=["assignedOlHex1", "assignedOlHex2"])
    assert len(l2_cells) == 1767
    l2_edges = []
    l2_paths = defaultdict(set)
    l2_target_ids = set()
    for post in l2_cells.index:
        post = int(post)
        side = nodes.instance.iat[post][-1]
        h1 = int(nodes.assignedOlHex1.iat[post])
        h2 = int(nodes.assignedOlHex2.iat[post])
        for edge in range(int(ptr[post]), int(ptr[post + 1])):
            src = int(pre[edge])
            if not is_r16[src]:
                continue
            assert nodes.rootSide.iat[src] == side
            receptor_id = int(body[src])
            l2_target_ids.add(int(body[post]))
            l2_paths[receptor_id].add((side, h1, h2))
            l2_edges.append({"r16_body_id": receptor_id, "r16_graph_index": src,
                             "l2_body_id": int(body[post]), "l2_graph_index": post,
                             "side": side, "hex1": h1, "hex2": h2,
                             "synapse_contacts": int(counts[edge]),
                             "csr_edge_index": edge, "source_edge_row": int(source_rows[edge])})
    l2_frame = pd.DataFrame(l2_edges).sort_values(
        ["r16_body_id", "l2_body_id"]).reset_index(drop=True)
    assert l2_frame.csr_edge_index.is_unique and (l2_frame.synapse_contacts > 0).all()
    rows = []
    for index in receptors:
        receptor_id = int(body[index])
        one, two = l1_paths[receptor_id], l2_paths[receptor_id]
        if len(one) == len(two) == 1:
            status = "both_agree" if one == two else "single_conflict"
        elif len(one) == 1 and not two:
            status = "l1_only"
        elif len(two) == 1 and not one:
            status = "l2_only"
        elif not one and not two:
            status = "none"
        else:
            status = "multiple_or_mixed"
        coordinate = next(iter(one or two)) if status in ("both_agree", "l1_only", "l2_only") else None
        rows.append({"r16_body_id": receptor_id, "r16_graph_index": int(index),
                     "root_side": nodes.rootSide.iat[int(index)],
                     "l1_column_count": len(one), "l2_column_count": len(two),
                     "status": status,
                     "supported_side": coordinate[0] if coordinate else "",
                     "supported_hex1": coordinate[1] if coordinate else "",
                     "supported_hex2": coordinate[2] if coordinate else "",
                     "supported_coordinate_in_accepted_index":
                         coordinate in accepted_columns if coordinate else False})
    status_frame = pd.DataFrame(rows).sort_values("r16_body_id").reset_index(drop=True)
    status_counts = {str(k): int(v) for k, v in status_frame.status.value_counts().items()}
    assert status_counts.get("single_conflict", 0) == 0
    OUT.mkdir(parents=True, exist_ok=True)
    edge_path = OUT / "l2_direct_edges.csv"
    status_path = OUT / "receptor_path_status.csv"
    l2_frame.to_csv(edge_path, index=False)
    status_frame.to_csv(status_path, index=False)
    report = {
        "scope": "Direct graph R1-R6 anatomical paths to L1 and L2; no optical-axis assignment or enabled visual drive",
        "graph_manifest_sha256": sha(GRAPH / "manifest.json"),
        "l1_edge_csv_sha256": sha(L1_EDGES),
        "accepted_columns_sha256": sha(accepted_columns_path),
        "l2_cell_count_with_primary_hex": len(l2_cells),
        "l2_direct_edge_rows": len(l2_frame),
        "l2_direct_contacts": int(l2_frame.synapse_contacts.sum()),
        "l2_cells_with_direct_r16_input": len(l2_target_ids),
        "receptor_status_counts": status_counts,
        "single_path_coordinates_outside_accepted_index": int(
            (status_frame.status.isin(("both_agree", "l1_only", "l2_only"))
             & ~status_frame.supported_coordinate_in_accepted_index).sum()),
        "l2_direct_edges_csv_sha256": sha(edge_path),
        "receptor_path_status_csv_sha256": sha(status_path),
        "interpretation": "Both-agree cells have two distinct direct graph paths with the same annotated medulla hex. The cell annotations and graph share source provenance, so this is internal consistency, not independent optical calibration. Missing paths do not prove absent biology under minconf filtering.",
        "optical_rays_assigned": 0,
        "visual_input_enabled": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("l2_cell_count_with_primary_hex",
        "l2_direct_edge_rows", "l2_direct_contacts", "l2_cells_with_direct_r16_input",
        "receptor_status_counts")}, indent=2))


if __name__ == "__main__":
    main()

