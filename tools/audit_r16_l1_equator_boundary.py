"""Assess whether accepted R1-R6 to L1 rows support an equator landmark."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EDGES = ROOT / "data/derived/r16_l1_column_edges_v1/direct_edges.csv"
ASSIGN = ROOT / "data/derived/malecns_optic_columns/assignments.csv"
OUT = ROOT / "data/derived/r16_l1_equator_boundary_v1/per_l1_counts.csv"
REPORT = ROOT / "reports/malecns_r16_l1_equator_boundary.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    edge_report = json.loads((ROOT / "reports/malecns_r16_l1_column_edges.json").read_text(encoding="utf-8"))
    optic_report = json.loads((ROOT / "reports/optic_column_index.json").read_text(encoding="utf-8"))
    assert sha(EDGES) == edge_report["direct_edges_csv_sha256"]
    assert sha(ASSIGN) == optic_report["files"]["assignments.csv"]
    edge = pd.read_csv(EDGES)
    l1 = pd.read_csv(ASSIGN).query("role == 'L1'")[["body_id", "column", "side", "hex1", "hex2"]]
    assert len(l1) == 1764 and l1.body_id.is_unique
    group = edge.groupby("l1_body_id").agg(
        distinct_r16=("r16_body_id", "nunique"),
        direct_edge_rows=("csr_edge_index", "size"),
        direct_contacts=("synapse_contacts", "sum")).reset_index()
    assert group.l1_body_id.is_unique
    profile = l1.merge(group, left_on="body_id", right_on="l1_body_id",
                       how="left", validate="one_to_one")
    for name in ("distinct_r16", "direct_edge_rows", "direct_contacts"):
        profile[name] = profile[name].fillna(0).astype(int)
    profile = profile.drop(columns=["l1_body_id"]).sort_values(["side", "hex1", "hex2"])
    assert int(profile.direct_edge_rows.sum()) == edge_report["direct_edge_rows"]
    assert int(profile.direct_contacts.sum()) == edge_report["direct_contacts"]
    distribution = {str(k): int(v) for k, v in
                    profile.distinct_r16.value_counts().sort_index().items()}
    assert sum(distribution.values()) == len(profile)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(OUT, index=False)
    report = {
        "scope": "Source-bound receptor-input count per author-assigned L1; equator landmark not accepted",
        "direct_edge_csv_sha256": sha(EDGES),
        "assignment_sha256": sha(ASSIGN),
        "assigned_l1": len(profile),
        "distinct_r16_count_distribution": distribution,
        "l1_with_zero_direct_r16": int(profile.distinct_r16.eq(0).sum()),
        "l1_with_six_direct_r16": int(profile.distinct_r16.eq(6).sum()),
        "l1_with_seven_or_eight_direct_r16": int(profile.distinct_r16.isin((7, 8)).sum()),
        "l1_with_more_than_eight_direct_r16": int(profile.distinct_r16.gt(8).sum()),
        "per_l1_csv_sha256": sha(OUT),
        "interpretation": "The published equatorial landmark method requires near-complete cartridge photoreceptor counts and morphology. This minconf=0.5 graph has many empty L1 inputs and some counts above eight; 7/8 here are candidates only and cannot establish an equator row.",
        "equator_landmark_accepted": False,
        "visual_registration_accepted": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("assigned_l1", "l1_with_zero_direct_r16",
        "l1_with_six_direct_r16", "l1_with_seven_or_eight_direct_r16",
        "l1_with_more_than_eight_direct_r16")}, indent=2))


if __name__ == "__main__":
    main()

