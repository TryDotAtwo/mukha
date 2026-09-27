"""Measure whether pinned KC->MBON contact ROIs identify gamma4 contacts."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/derived/mb_synapse_locations_v1/molab_full/contacts-00000-04759.parquet"
RECON = ROOT / "reports/malecns_mb_synapse_reconciliation.json"
NODES = ROOT / "data/derived/malecns_v1_candidates/nodes.feather"
OUT = ROOT / "reports/malecns_gamma4_contact_roi_boundary.json"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    reconciliation = json.loads(RECON.read_text(encoding="utf-8"))
    assert sha(SOURCE) == reconciliation["pinned_full_file"]["data_sha256"]
    table = pq.read_table(SOURCE, columns=["body_post", "primary_post"]).to_pandas()
    assert len(table) == reconciliation["observed_contacts"] == 463640
    nodes = pd.read_feather(NODES, columns=["bodyId", "class", "instance"])
    mbons = nodes.loc[nodes["class"].eq("MBON"), ["bodyId", "instance"]]
    assert len(mbons) == 97 and mbons.bodyId.is_unique
    assert set(table.body_post) <= set(mbons.bodyId)
    candidates = mbons.loc[mbons.instance.str.contains("y4", regex=False, na=False)]
    assert len(candidates) == 6
    rows = []
    for item in candidates.itertuples(index=False):
        subset = table.loc[table.body_post.eq(item.bodyId), "primary_post"]
        counts = Counter(subset.astype(str))
        rows.append({"bodyId": int(item.bodyId), "instance": item.instance,
                     "contacts": len(subset), "primary_post_counts": dict(sorted(counts.items()))})
    roi_labels = sorted(set(table.primary_post.astype(str)))
    gamma_lobe_contacts = sum(sum(n for label, n in row["primary_post_counts"].items()
                                  if label.startswith("gL(")) for row in rows)
    total = sum(row["contacts"] for row in rows)
    result = {
        "scope": "Contact-level ROI resolution for MaleCNS MBON instance names containing y4; anatomical boundary only",
        "source_contact_sha256": sha(SOURCE),
        "reconciliation_sha256": sha(RECON),
        "nodes_sha256": sha(NODES),
        "candidate_count": len(rows),
        "candidate_contacts": total,
        "candidate_gamma_lobe_contacts": gamma_lobe_contacts,
        "candidate_gamma_lobe_fraction": gamma_lobe_contacts / total,
        "all_primary_post_labels": roi_labels,
        "has_explicit_gamma4_primary_post_label": any("g4" in x.lower() or "gamma4" in x.lower() for x in roi_labels),
        "per_candidate": rows,
        "conclusion": "Primary ROI labels identify gamma lobe gL, not gamma4 subcompartment. Instance names identify candidate MBONs but do not assign individual KC contacts to gamma4 or a local DAN field.",
        "plasticity_enabled": False,
        "biological_gate_passed": False,
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("candidate_count", "candidate_contacts",
          "candidate_gamma_lobe_contacts", "candidate_gamma_lobe_fraction",
          "has_explicit_gamma4_primary_post_label")}, indent=2))


if __name__ == "__main__":
    main()

