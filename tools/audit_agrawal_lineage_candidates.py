"""Count MaleCNS annotation candidates for Agrawal 2020 lineages.

Lineage labels alone are not neuron identities or physiological crosswalks.
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
source = root / "data/derived/malecns_v1_candidates/nodes.feather"
nodes = pd.read_feather(source)
required = {"bodyId", "type", "mancBodyid", "mancType"}
assert required.issubset(nodes.columns)

lineages = {}
for lineage in ("13B", "09A", "10B"):
    prefix = "IN" + lineage
    types = nodes["type"].fillna("").astype(str)
    hits = nodes.loc[types.str.startswith(prefix)]
    lineages[lineage] = {
        "male_cns_rows": int(len(hits)),
        "distinct_male_cns_types": int(hits["type"].nunique()),
        "with_manc_body_id": int(hits["mancBodyid"].notna().sum()),
        "with_manc_type": int(hits["mancType"].notna().sum()),
        "type_counts": {str(k): int(v) for k, v in hits["type"].value_counts().sort_index().items()},
    }

report = {
    "source_nodes": str(source.relative_to(root)).replace("\\", "/"),
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "reference_doi": "10.7554/eLife.60299",
    "dataset_doi": "10.5061/dryad.k3j9kd55t",
    "query": "MaleCNS type starts with IN13B, IN09A, or IN10B",
    "lineages": lineages,
    "individual_cell_crosswalk_approved": False,
    "reason": "A developmental lineage contains many annotated types and individuals; the recorded cells have no established bodyId mapping here.",
}
out = root / "reports/agrawal_lineage_candidates.json"
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({k: {a: v[a] for a in ("male_cns_rows", "distinct_male_cns_types")} for k, v in lineages.items()}))
