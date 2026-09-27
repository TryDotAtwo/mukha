"""Check published Tastekin Table S1 IDs against the pinned MaleCNS population.

Subtype-to-modality associations are hypotheses from the paper, not molecular
measurements of each reconstructed neuron or physiological validation of a model.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

import openpyxl
import pyarrow.feather as feather


ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data/reference/tastekin2026/mmc2.xlsx"
NODES = ROOT / "data/derived/malecns_v1_candidates/nodes.feather"
EXPECTED_TABLE_SHA256 = "7b28d5f3ae45d68c510b8a3616700f0df2a5a6f2e2d2dba490d172939f2b64c9"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(sheet):
    source = sheet.values
    header = next(source)
    return [dict(zip(header, row)) for row in source]


def main():
    digest = sha256(TABLE)
    if digest != EXPECTED_TABLE_SHA256:
        raise ValueError("Tastekin supplement SHA256 mismatch")
    graph_manifest = json.loads((NODES.parent / "manifest.json").read_text())
    graph = feather.read_table(NODES).to_pandas().set_index("bodyId", verify_integrity=True)
    book = openpyxl.load_workbook(TABLE, read_only=True, data_only=True)
    grns = [r for r in rows(book["GRNs"]) if r["Connectome"] == "maleCNS"]
    mns = [r for r in rows(book["MNs"]) if r["Connectome"] == "maleCNS"]
    if len({r["Body_ID"] for r in grns}) != len(grns):
        raise ValueError("Duplicate maleCNS GRN Body_ID")
    if len({r["Body_ID"] for r in mns}) != len(mns):
        raise ValueError("Duplicate maleCNS MN Body_ID")
    lb = [r for r in grns if r["Subclass"] == "Labellar Bristle"]
    missing_grns = [r for r in grns if r["Body_ID"] not in graph.index]
    if any(r["Subtype"] != "-" for r in missing_grns):
        raise ValueError("A typed MaleCNS GRN is absent from the graph")
    subtype_counts = dict(sorted(Counter(r["Subtype"] for r in lb).items()))
    masks = {
        "bitter_candidate_LB1a_d": {"LB1a", "LB1b", "LB1c", "LB1d"},
        "sweet_candidate_LB3c": {"LB3c"},
        "sweet_broad_LB3b_c_with_low_salt_overlap": {"LB3b", "LB3c"},
    }
    populations = {}
    for name, subtypes in masks.items():
        selected = [r for r in lb if r["Subtype"] in subtypes]
        present = [r for r in selected if r["Body_ID"] in graph.index]
        mismatches = [{"body_id": r["Body_ID"], "table_subtype": r["Subtype"],
                       "graph_type": str(graph.at[r["Body_ID"], "type"])}
                      for r in present if str(graph.at[r["Body_ID"], "type"]) != r["Subtype"]]
        populations[name] = {
            "table_count": len(selected), "graph_count": len(present),
            "body_ids": sorted(int(r["Body_ID"]) for r in present),
            "missing_body_ids": sorted(int(r["Body_ID"]) for r in selected if r["Body_ID"] not in graph.index),
            "annotation_mismatches": mismatches,
        }
    mn9 = [r for r in mns if r["Type"] == "MN9"]
    report = {
        "source": "Tastekin et al., Cell (2026), Table S1 (mmc2.xlsx)",
        "doi": "https://doi.org/10.1016/j.cell.2026.08.016",
        "supplement_url": "https://ars.els-cdn.com/content/image/1-s2.0-S0092867426009438-mmc2.xlsx",
        "supplement_sha256": digest,
        "nodes_sha256": sha256(NODES),
        "graph_manifest": graph_manifest,
        "malecns_grn_rows": len(grns),
        "malecns_grn_in_graph": sum(r["Body_ID"] in graph.index for r in grns),
        "malecns_grn_missing_body_ids": sorted(int(r["Body_ID"]) for r in grns if r["Body_ID"] not in graph.index),
        "malecns_grn_missing_subtypes": dict(Counter(r["Subtype"] for r in missing_grns)),
        "labellar_subtype_counts": subtype_counts,
        "populations": populations,
        "mn9": [{"body_id": int(r["Body_ID"]), "root_side": r["Root_Side"],
                  "in_graph": r["Body_ID"] in graph.index,
                  "graph_type": str(graph.at[r["Body_ID"], "type"]) if r["Body_ID"] in graph.index else None}
                 for r in mn9],
        "interpretation": "Paper-level receptor associations provide candidate sensory masks; no per-cell receptor assay or MaleCNS response has been verified here.",
    }
    if len(mn9) != 2 or {r["Body_ID"] for r in mn9} != {10331, 16949}:
        raise ValueError("Unexpected MN9 crosswalk")
    output = ROOT / "reports/tastekin2026_malecns_crosswalk.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "graph_manifest"}, indent=2))


if __name__ == "__main__":
    main()
