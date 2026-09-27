"""Map fully reconciled KC->KC contacts to published primary_post ROIs.

This is a coarse anatomical localization, not a receptor or learning assay.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
SOURCE = ROOT / "data/derived/kc_synapse_locations_v1"
CSR = ROOT / "reports/malecns_kc_lateral_subtypes.json"
OUT = ROOT / "reports/malecns_kc_lateral_contact_rois.json"


def sha(path):
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
    state = json.loads((SOURCE / "progress.json").read_text(encoding="utf-8"))
    reconciliation = json.loads((SOURCE / "reconciliation.json").read_text(encoding="utf-8"))
    csr = json.loads(CSR.read_text(encoding="utf-8"))
    assert state["next_batch"] == reconciliation["processed_batches"] == 4759
    assert reconciliation["complete_and_reconciled"] and reconciliation["pair_mismatch_count"] == 0
    assert state["source"] == reconciliation["source"]
    assert state["graph_manifest_sha256"] == csr["graph_manifest_sha256"]
    assert sha(GRAPH / "manifest.json") == state["graph_manifest_sha256"]
    nodes = pd.read_feather(GRAPH / "nodes.feather", columns=["bodyId", "class", "type"])
    kcs = nodes.loc[nodes["class"].eq("Kenyon_Cell"), ["bodyId", "type"]]
    labels = {int(body): group(str(kind)) for body, kind in kcs.itertuples(index=False, name=None)}
    assert len(labels) == 4064
    counts = Counter()
    pair_totals = Counter()
    unknown_roi = 0
    frames = []
    coordinate_nulls = Counter()
    nonfinite_confidence = Counter()
    cursor = 0
    for entry in state["chunks"]:
        assert entry["start"] == cursor and cursor < entry["stop"] <= 4759
        cursor = entry["stop"]
        if not entry["rows"]:
            continue
        path = SOURCE / entry["file"]
        assert path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"]
        assert pq.ParquetFile(path).schema_arrow.names == [
            "x_pre", "y_pre", "z_pre", "body_pre", "conf_pre", "x_post",
            "y_post", "z_post", "body_post", "conf_post", "primary_post"]
        table = pq.read_table(path)
        assert table.num_rows == entry["rows"]
        frame = table.to_pandas()
        frames.append(frame)
        for column in ("x_pre", "y_pre", "z_pre", "x_post", "y_post", "z_post"):
            coordinate_nulls[column] += int(frame[column].isna().sum())
        for column in ("conf_pre", "conf_post"):
            nonfinite_confidence[column] += int((~np.isfinite(frame[column].to_numpy())).sum())
        for pre, post, roi in zip(table["body_pre"].to_pylist(),
                                  table["body_post"].to_pylist(),
                                  table["primary_post"].to_pylist()):
            a, b = labels[int(pre)], labels[int(post)]
            unknown_roi += roi is None or str(roi) == ""
            counts[(a, b, str(roi))] += 1
            pair_totals[(a, b)] += 1
    expected = {(r["presynaptic_subtype"], r["postsynaptic_subtype"]): r["contacts"]
                for r in csr["directed_subtype_pairs"]}
    assert cursor == state["next_batch"] == 4759
    assert all(pair_totals.get(key, 0) == value for key, value in expected.items())
    assert sum(pair_totals.values()) == reconciliation["observed_contacts"] == 1153845
    complete = pd.concat(frames, ignore_index=True)
    assert len(complete) == 1153845
    exact_duplicate_rows = int(complete.duplicated(keep="first").sum())
    rows = [{"presynaptic_subtype": a, "postsynaptic_subtype": b,
             "primary_post": roi, "contacts": value}
            for (a, b, roi), value in sorted(counts.items())]
    report = {"scope": "Complete source KC-to-KC partner contacts grouped by original type and primary_post; coarse anatomy only",
              "source_generation": state["source"]["generation"],
              "graph_manifest_sha256": state["graph_manifest_sha256"],
              "extraction_progress_sha256": sha(SOURCE / "progress.json"),
              "reconciliation_sha256": sha(SOURCE / "reconciliation.json"),
              "csr_subtype_report_sha256": sha(CSR),
              "contacts": rows,
              "total_contacts": sum(counts.values()),
              "unknown_primary_post_contacts": unknown_roi,
              "coordinate_null_counts": dict(coordinate_nulls),
              "nonfinite_confidence_counts": dict(nonfinite_confidence),
              "exact_duplicate_full_rows_retained": exact_duplicate_rows,
              "source_synapse_id_column_present": False,
              "gamma_to_gamma_total": pair_totals[("gamma", "gamma")],
              "gamma_to_gamma_gL": sum(value for (a, b, roi), value in counts.items()
                                       if a == b == "gamma" and roi in ("gL(L)", "gL(R)")),
              "interpretation_limit": "The source ROI gL is broad and does not identify gamma4, an axonal ultrastructure, mAChR-B, dopamine release, or a plasticity rule. The 11-column source has no separate synapse ID, so coordinate-identical records are retained."}
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"gamma_to_gamma_total": report["gamma_to_gamma_total"],
                      "gamma_to_gamma_gL": report["gamma_to_gamma_gL"],
                      "total_contacts": report["total_contacts"]}))


if __name__ == "__main__":
    main()
