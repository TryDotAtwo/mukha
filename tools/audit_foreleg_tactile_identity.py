"""Bound the MaleCNS foreleg bristle population before mapping foot contact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NODES = ROOT / "data/derived/malecns_v1_candidates/nodes.feather"
MANIFEST = ROOT / "data/derived/malecns_v1_candidates/manifest.json"
OUT = ROOT / "reports/foreleg_tactile_identity.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert sha(NODES) == manifest["files"]["nodes.feather"]["sha256"]
    nodes = pd.read_feather(NODES)
    assert len(nodes) == manifest["nodes"]
    front = nodes.loc[(nodes.entryNerve == "ProLN") &
                      (nodes.subclass == "mechanosensory bristle")].copy()
    assert front.bodyId.is_unique
    names = ("type", "mancType", "subclass", "class", "synonyms",
             "matchingNotes", "entryNerve")
    explicit_tarsomere = front[list(names)].astype(str).apply(
        lambda col: col.str.contains(r"tarsomer|\bta[1-5]\b|\bt5\b|\blf_tarsus5\b",
                                     case=False, regex=True)).any(axis=1)
    report = {
        "scope": "MaleCNS v1.0 annotated foreleg mechanosensory-bristle candidates; no peripheral receptor assignment",
        "graph_manifest_sha256": sha(MANIFEST),
        "nodes_feather_sha256": sha(NODES),
        "selection": {"entryNerve": "ProLN", "subclass": "mechanosensory bristle"},
        "candidate_rows": len(front),
        "type_count": int(front.type.nunique()),
        "type_rows": {str(k): int(v) for k, v in front.type.value_counts().sort_index().items()},
        "with_manc_body_id": int(front.mancBodyid.notna().sum()),
        "without_manc_body_id": int(front.mancBodyid.isna().sum()),
        "explicit_tarsomere_rows_in_checked_columns": int(explicit_tarsomere.sum()),
        "checked_columns": list(names),
        "approved_lf_tarsus5_body_ids": [],
        "decision": "No individual body ID has a source-supported lf_tarsus5 receptor assignment from these annotations alone.",
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
