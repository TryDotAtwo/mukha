"""Check source MaleCNS left-front sensory MANC IDs against MANC v1.0 labels."""

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MALECNS = ROOT / "data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather"
MANC = ROOT / "data/reference/manc_v1_motor_crosswalk/manc-v1.0-neuron-properties.feather"
OUT = ROOT / "reports/malecns_lf_sensory_manc_v1_crosswalk.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar(value):
    return None if pd.isna(value) else value


def main():
    a = pd.read_feather(MALECNS)
    b = pd.read_feather(MANC)
    assert a.bodyId.is_unique and b.bodyId.is_unique
    group = a[(a.entryNerve == "ProLN") & (a.rootSide == "L")
              & (a["subclass"] == "chordotonal organ")].sort_values("bodyId")
    assert len(group) == 23
    lookup = b.set_index("bodyId")
    rows = []
    for _, cell in group.iterrows():
        manc_id = scalar(cell.mancBodyid)
        target = lookup.loc[int(manc_id)] if manc_id is not None and int(manc_id) in lookup.index else None
        rows.append({
            "malecns_body_id": int(cell.bodyId),
            "malecns_type": scalar(cell.type),
            "malecns_class": scalar(cell["class"]),
            "malecns_mancBodyid": None if manc_id is None else int(manc_id),
            "manc_v1_type": None if target is None else scalar(target.type),
            "manc_v1_class": None if target is None else scalar(target["class"]),
            "manc_v1_entryNerve": None if target is None else scalar(target.entryNerve),
            "found_manc_id": target is not None,
            "manc_type_present": target is not None and scalar(target.type) is not None,
            "same_type": None if target is None else cell.type == target.type,
            "target_is_sensory": None if target is None else target["class"] in ("sensory neuron", "sensory ascending"),
        })
    available = [r for r in rows if r["malecns_mancBodyid"] is not None]
    resolved = [r for r in available if r["found_manc_id"]]
    report = {
        "scope": "Source-annotation MANC v1.0 ID check for all 23 MaleCNS left-ProLN chordotonal cells",
        "malecns_source_sha256": sha(MALECNS),
        "manc_v1_source_sha256": sha(MANC),
        "counts": {
            "malecns_cells": len(rows),
            "with_mancBodyid": len(available),
            "resolved_in_manc_v1": len(resolved),
            "with_manc_type": sum(r["manc_type_present"] for r in resolved),
            "same_type": sum(r["same_type"] is True for r in resolved),
            "target_sensory_class": sum(r["target_is_sensory"] is True for r in resolved),
            "target_nonsensory_class": sum(r["target_is_sensory"] is False for r in resolved),
        },
        "rows": rows,
        "interpretation": "mancBodyid is not a validated individual identity crosswalk for this group",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], indent=2))


if __name__ == "__main__":
    main()
