"""Pin the two annotated front-leg tibia-extensor serial groups.

This is an annotation audit, not a neuron-to-muscle activation map.
"""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/manc_motor/elife-96084-supp6-v1.csv"
OUTPUT = ROOT / "reports/tibia_extensor_serial_groups.json"
SHA256 = "b56b0563f6a6000b2a43fbc7ebec46297668e8e3b6c6d596843d5ad5aab83a65"
EXPECTED = {11657: 10347, 11706: 10737}


def main():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != SHA256:
        raise ValueError("Supplementary file 6 digest mismatch")
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    groups = {}
    for group, serial in EXPECTED.items():
        members = [row for row in rows if int(row["group"]) == group]
        if len(members) != 2:
            raise ValueError(f"Group {group} has {len(members)} members, expected two")
        if {int(row["serial"]) for row in members} != {serial}:
            raise ValueError(f"Group {group} serial identity changed")
        if {row["soma_side"] for row in members} != {"LHS", "RHS"}:
            raise ValueError(f"Group {group} lacks one member on each soma side")
        for row in members:
            if (row["type"], row["subclass"], row["target"]) != (
                "Ti extensor MN", "fl", "Ti extensor"
            ):
                raise ValueError(f"Unexpected annotation for body {row['bodyid']}")
        groups[str(group)] = {
            "serial_group": serial,
            "members": [
                {"bodyid": int(row["bodyid"]), "soma_side": row["soma_side"]}
                for row in sorted(members, key=lambda row: row["soma_side"])
            ],
            "type": "Ti extensor MN",
            "subclass": "fl",
            "target": "Ti extensor",
        }
    report = {
        "source_url": "https://cdn.elifesciences.org/articles/96084/elife-96084-supp6-v1.csv",
        "source_sha256": digest,
        "groups": groups,
        "interpretation": "Two distinct annotated serial groups, each with left and right members",
        "fast_slow_identity": None,
        "published_reconstruction_warning": {
            "serial_group": 10347,
            "source": "https://elifesciences.org/articles/96084/figures",
            "scope": "Figure 5 supplement 1 depicts one less-well-reconstructed member; this audit does not assign which side",
        },
        "malecns_individual_crosswalk_verified": False,
        "flymimic_activation_mapping_enabled": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(OUTPUT), "groups": list(groups)}, sort_keys=True))


if __name__ == "__main__":
    main()
