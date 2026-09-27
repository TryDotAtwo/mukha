"""Screen T1 IN13B anatomy without assigning Agrawal 13Balpha identities."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
base = root / "data/derived/malecns_v1_candidates"
files = {name: base / name for name in
         ("nodes.feather", "indptr.npy", "indices.npy", "synapse_counts.npy")}
n = pd.read_feather(files["nodes.feather"])
row = np.load(files["indptr.npy"], mmap_mode="r")
col = np.load(files["indices.npy"], mmap_mode="r")
count = np.load(files["synapse_counts.npy"], mmap_mode="r")
assert len(row) == len(n) + 1 and len(col) == len(count) == int(row[-1])
assert np.array_equal(n.compact_index.to_numpy(), np.arange(len(n)))

types = n.type.fillna("").astype(str).to_numpy()
sensory = n.subclass.fillna("").astype(str).str.contains("chordotonal", case=False).to_numpy()
front_leg = n.entryNerve.fillna("").isin(["ProLN", "ProCN"]).to_numpy()
claw_named = np.isin(types, ["SNpp50", "SNpp51"])
candidate = n.type.fillna("").str.startswith("IN13B") & n.somaNeuromere.eq("T1")

result = []
side_rows = {}
sensory_type_rows = {}
for node in n.loc[candidate].itertuples(index=False):
    index = int(node.compact_index)
    lo, hi = int(row[index]), int(row[index + 1])
    incoming = np.asarray(col[lo:hi], dtype=np.intp)
    counts = np.asarray(count[lo:hi], dtype=np.int64)
    is_front_chord = sensory[incoming] & front_leg[incoming]
    is_claw_named = is_front_chord & claw_named[incoming]
    for source_index in incoming[is_front_chord]:
        side_key = f"soma_{node.somaSide}_root_{n.rootSide.iloc[source_index]}_{n.entryNerve.iloc[source_index]}"
        side_rows[side_key] = side_rows.get(side_key, 0) + 1
        source_type = str(n.type.iloc[source_index])
        sensory_type_rows[source_type] = sensory_type_rows.get(source_type, 0) + 1
    result.append({
        "bodyId": int(node.bodyId), "type": str(node.type),
        "somaSide": str(node.somaSide), "somaNeuromere": str(node.somaNeuromere),
        "all_incoming_edge_rows": hi - lo,
        "front_leg_chordotonal_edge_rows": int(is_front_chord.sum()),
        "front_leg_chordotonal_synapses": int(counts[is_front_chord].sum()),
        "snpp50_51_front_leg_edge_rows": int(is_claw_named.sum()),
        "snpp50_51_front_leg_synapses": int(counts[is_claw_named].sum()),
        "snpp50_51_source_body_ids": sorted({int(n.bodyId.iloc[k]) for k in incoming[is_claw_named]}),
        "snpp50_51_source_root_sides": sorted({str(n.rootSide.iloc[k]) for k in incoming[is_claw_named]}),
    })

report = {
    "source_sha256": {key: hashlib.sha256(path.read_bytes()).hexdigest()
                      for key, path in files.items()},
    "reference_doi": "10.7554/eLife.60299",
    "scope": "MaleCNS IN13B with T1 soma; exact direct incoming CSR rows",
    "snpp50_51_status": "candidate claw names only; not a validated subtype assignment for every cell",
    "individual_cell_crosswalk_approved": False,
    "candidate_count": len(result),
    "candidates_with_front_leg_chordotonal_input": sum(x["front_leg_chordotonal_edge_rows"] > 0 for x in result),
    "candidates_with_snpp50_51_input": sum(x["snpp50_51_front_leg_edge_rows"] > 0 for x in result),
    "front_leg_chordotonal_edge_rows_by_side": dict(sorted(side_rows.items())),
    "front_leg_chordotonal_edge_rows_by_type": dict(sorted(sensory_type_rows.items())),
    "snpp50_51_candidate_soma_sides": sorted({x["somaSide"] for x in result
                                                if x["snpp50_51_front_leg_edge_rows"] > 0}),
    "candidates": sorted(result, key=lambda x: x["bodyId"]),
}
out = root / "reports/agrawal_13b_connectivity.json"
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: report[key] for key in
                  ("candidate_count", "candidates_with_front_leg_chordotonal_input",
                   "candidates_with_snpp50_51_input")}))
