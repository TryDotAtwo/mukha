"""Compare selected left-front proprioceptor annotations across published releases."""

import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "data/raw/malecns_v1/body-annotations-male-cns-v1.0-minconf-0.5.feather"
REPORT = ROOT / "reports/lf_proprio_annotation_history.json"
IDS = (815843, 817680, 817697, 821306, 908487, 912317, 935383)
FIELDS = ("superclass", "class", "subclass", "type", "entryNerve", "rootSide", "mancType", "matchingNotes")
OBJECT = "v0.9/connectome-data/flat-connectome/body-annotations-male-cns-v0.9-minconf-0.5.feather"
URL = "https://storage.googleapis.com/flyem-male-cns/" + OBJECT


def selected(frame):
    rows = frame.set_index("bodyId")
    return {str(body): {field: None if pd.isna(rows.loc[body, field]) else str(rows.loc[body, field])
                        for field in FIELDS} for body in IDS}


def main():
    response = requests.get(URL, timeout=90)
    response.raise_for_status()
    prior_bytes = response.content
    prior = selected(pd.read_feather(io.BytesIO(prior_bytes)))
    current = selected(pd.read_feather(CURRENT))
    changes = {body: {field: [prior[body][field], current[body][field]]
                      for field in FIELDS if prior[body][field] != current[body][field]}
               for body in prior}
    report = {
        "v0.9_source": URL,
        "v0.9_sha256": hashlib.sha256(prior_bytes).hexdigest(),
        "v1.0_source": str(CURRENT.relative_to(ROOT)).replace("\\", "/"),
        "v1.0_sha256": hashlib.sha256(CURRENT.read_bytes()).hexdigest(),
        "fields": list(FIELDS),
        "v0.9": prior,
        "v1.0": current,
        "changes": {body: delta for body, delta in changes.items() if delta},
        "interpretation": "Historical labels do not establish functional tuning or justify reclassification."
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changed_bodies": list(report["changes"]), "report": str(REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
