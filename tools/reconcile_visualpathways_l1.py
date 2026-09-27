"""Reconcile same-connectome visualpathways L1 workbooks with pinned MaleCNS columns."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/visualpathways"
OLD = ROOT / "data/derived/malecns_optic_columns/assignments.csv"
OUT = ROOT / "reports/visualpathways_l1_column_reconciliation.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((SOURCE / "source_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        p = ROOT / entry["file"]
        assert p.stat().st_size == entry["bytes"] and sha(p) == entry["sha256"]
    old_report = json.loads((ROOT / "reports/optic_column_index.json").read_text(encoding="utf-8"))
    assert sha(OLD) == old_report["files"]["assignments.csv"]
    old = pd.read_csv(OLD).query("role == 'L1'")
    nodes_path = ROOT / "data/derived/malecns_v1_candidates/nodes.feather"
    graph_manifest = json.loads(nodes_path.with_name("manifest.json").read_text(encoding="utf-8"))
    assert sha(nodes_path) == graph_manifest["files"]["nodes.feather"]["sha256"]
    nodes = pd.read_feather(nodes_path, columns=["bodyId", "assignedOlHex1", "assignedOlHex2"])
    assert nodes.bodyId.is_unique
    graph_ids = set(nodes.bodyId.astype(int))
    result = {"scope": "Exact L1 body-ID/hex-coordinate reconciliation of two published same-connectome workbooks; no optical ray assignment",
              "new_source_commit": manifest["commit"], "source_manifest_sha256": sha(SOURCE / "source_manifest.json"),
              "old_assignments_sha256": sha(OLD), "nodes_sha256": sha(nodes_path),
              "sides": {}, "visual_input_enabled": False}
    for side, name, sheet in (("R", "ME_columnar-cells_location.xlsx", "Currated Columns"),
                              ("L", "ME_L_columnar-cells_location.xlsx", "Sheet1")):
        frame = pd.read_excel(SOURCE / name, sheet_name=sheet)
        frame = frame.rename(columns={"hex1_id": "hex1", "hex2_id": "hex2", "L1": "new_body_id"})
        frame = frame[["hex1", "hex2", "new_body_id"]]
        for key in ("hex1", "hex2", "new_body_id"):
            frame[key] = pd.to_numeric(frame[key], errors="coerce")
        assert frame[["hex1", "hex2"]].notna().all().all()
        assert not (frame[["hex1", "hex2"]] % 1).any().any()
        frame[["hex1", "hex2"]] = frame[["hex1", "hex2"]].astype(int)
        prior = old.loc[old.side.eq(side), ["hex1", "hex2", "body_id"]]
        new_with_annotation = (frame.loc[frame.new_body_id.notna()]
                               .drop_duplicates(["hex1", "hex2", "new_body_id"])
                               .merge(nodes, left_on="new_body_id", right_on="bodyId",
                                      how="left", validate="many_to_one"))
        old_with_annotation = prior.merge(nodes, left_on="body_id", right_on="bodyId",
                                           how="left", validate="one_to_one")
        def annotation_counts(rows):
            has = rows.assignedOlHex1.notna() & rows.assignedOlHex2.notna()
            match = (rows.hex1.eq(rows.assignedOlHex1)
                     & rows.hex2.eq(rows.assignedOlHex2))
            return {"with_both_annotation_coordinates": int(has.sum()),
                    "matching_annotation": int((has & match).sum()),
                    "conflicting_annotation": int((has & ~match).sum()),
                    "without_both_annotation_coordinates": int((~has).sum())}
        dup = frame.duplicated(["hex1", "hex2"], keep=False)
        new_unique = frame.loc[~dup].copy()
        joined = new_unique.merge(prior, on=["hex1", "hex2"], how="outer", indicator=True, validate="one_to_one")
        both = joined.loc[joined["_merge"].eq("both")]
        comparable = both.loc[both.new_body_id.notna() & both.body_id.notna()]
        exact = comparable.new_body_id.eq(comparable.body_id)
        old_id_to_coord = {(int(x.body_id), int(x.hex1), int(x.hex2)) for x in prior.itertuples(index=False)}
        new_id_to_coord = {(int(x.new_body_id), int(x.hex1), int(x.hex2)) for x in frame.itertuples(index=False)
                           if pd.notna(x.new_body_id)}
        old_id_rows = prior.rename(columns={"hex1": "old_hex1", "hex2": "old_hex2", "body_id": "new_body_id"})
        identity_join = frame.loc[frame.new_body_id.notna()].drop_duplicates("new_body_id").merge(
            old_id_rows, on="new_body_id", how="inner", validate="one_to_one")
        identity_join["delta_hex1"] = identity_join.hex1 - identity_join.old_hex1
        identity_join["delta_hex2"] = identity_join.hex2 - identity_join.old_hex2
        coordinate_shifts = (identity_join.groupby(["delta_hex1", "delta_hex2"])
                             .size().sort_values(ascending=False))
        result["sides"][side] = {
            "shared_l1_body_ids": len(identity_join),
            "new_vs_primary_annotation": annotation_counts(new_with_annotation),
            "old_vs_primary_annotation": annotation_counts(old_with_annotation),
            "new_only_l1_body_ids": int(frame.new_body_id.nunique() - len(identity_join)),
            "old_only_l1_body_ids": len(prior) - len(identity_join),
            "shared_id_coordinate_shift_counts": [
                {"delta_hex1": int(index[0]), "delta_hex2": int(index[1]), "count": int(count)}
                for index, count in coordinate_shifts.items()],
            "source_rows": len(frame), "source_unique_coordinates": len(frame.drop_duplicates(["hex1", "hex2"])),
            "source_duplicate_coordinate_rows": int(dup.sum()),
            "source_missing_l1": int(frame.new_body_id.isna().sum()),
            "source_l1_ids_absent_from_graph": sorted(set(frame.new_body_id.dropna().astype(int)) - graph_ids),
            "source_duplicate_l1_id_rows": int(frame.new_body_id.dropna().duplicated().sum()),
            "old_l1_rows": len(prior),
            "comparable_unique_coordinates": len(comparable),
            "exact_body_ids_at_same_coordinate": int(exact.sum()),
            "different_body_ids_at_same_coordinate": int((~exact).sum()),
            "new_only_unique_coordinates": int(joined["_merge"].eq("left_only").sum()),
            "old_only_coordinates": int(joined["_merge"].eq("right_only").sum()),
            "exact_body_id_coordinate_triples_all_rows": len(old_id_to_coord & new_id_to_coord),
            "mismatch_examples": comparable.loc[~exact, ["hex1", "hex2", "new_body_id", "body_id"]].head(12).to_dict("records"),
            "duplicate_examples": frame.loc[dup].head(12).to_dict("records"),
        }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["sides"], indent=2))


if __name__ == "__main__":
    main()

