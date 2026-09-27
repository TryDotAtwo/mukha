"""Check whether candidate left-front sensory cells can inherit CxHP8 tuning.

This compares source nerve annotations only. It does not classify SNppxx.
"""

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NODES = ROOT / "data/derived/malecns_v1_candidates/nodes.feather"
RAW = ROOT / "data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather"
OUT = ROOT / "reports/lf_cxhp8_nerve_boundary.json"
BODY_IDS = (817697, 821306, 908487, 912317)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    nodes = pd.read_feather(NODES)
    raw = pd.read_feather(RAW)
    assert nodes.bodyId.is_unique and raw.bodyId.is_unique
    assert len(nodes) == 167216
    records = []
    for body_id in BODY_IDS:
        retained = nodes.loc[nodes.bodyId.eq(body_id)]
        original = raw.loc[raw.bodyId.eq(body_id)]
        assert len(retained) == len(original) == 1
        a, b = retained.iloc[0], original.iloc[0]
        for field in ("class", "subclass", "type", "entryNerve", "rootSide"):
            av = None if pd.isna(a[field]) else str(a[field])
            bv = None if pd.isna(b[field]) else str(b[field])
            assert av == bv, (body_id, field, av, bv)
        assert a["entryNerve"] == "ProLN" and a["rootSide"] == "L"
        records.append({"body_id": body_id, "graph_index": int(a.compact_index),
                        "subclass": str(a["subclass"]),
                        "type": None if pd.isna(a["type"]) else str(a["type"]),
                        "entry_nerve": str(a["entryNerve"])})
    result = {
        "question": "Can the FANC CxHP8 sensory tuning be assigned to the four direct MaleCNS left-front extensor partners by nerve identity?",
        "source": "https://www.nature.com/articles/s41467-026-69333-z",
        "source_statement": "CxHP8 axons uniquely enter the VNC through VProN in the FANC leg X-ray analysis; the MANC hair-plate axons could not be identified specifically.",
        "source_sha256": {str(path.relative_to(ROOT)).replace('\\', '/'): sha256(path)
                          for path in (NODES, RAW)},
        "records": records,
        "cxhp8_reported_entry_nerve": "VProN",
        "all_candidate_entry_nerves": sorted({r["entry_nerve"] for r in records}),
        "cxhp8_transfer_supported_by_nerve": False,
        "interpretation": "The ProLN annotation conflicts with a CxHP8/VProN identity. This excludes direct CxHP8 tuning transfer, not every hair-plate possibility and not other sensory modalities.",
        "biological_validation": False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"body_ids": BODY_IDS,
                      "candidate_entry_nerves": result["all_candidate_entry_nerves"],
                      "cxhp8_transfer_supported_by_nerve": False}, indent=2))


if __name__ == "__main__":
    main()
