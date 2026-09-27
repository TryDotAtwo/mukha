"""Audit published FANC/MANC matching coverage for T1 tibia extensors."""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/reference/fanc_manc_crosswalk/Supplemental_file13_other_MANC_FANC_matching.tsv"
TARGETS = ROOT / "data/reference/manc_motor/elife-96084-supp3-v1.csv"
OUTPUT = ROOT / "reports/published_fanc_manc_ti_extensor_audit.json"
SOURCE_SHA = "2d6598b55e690dbe5433f18311b8c74b1707d4044b22670fc41ce2fd87c3f9a7"
TARGETS_SHA = "c46e3cec1a5114b8d981d5f0383012c8e7fcdebd6c4e3eaffe4ac3ba1def2e94"


def verified_rows(path, digest, delimiter):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise ValueError(f"source hash mismatch: {path}: {actual}")
    return list(csv.DictReader(raw.decode("utf-8-sig").splitlines(), delimiter=delimiter))


def main():
    matches = verified_rows(SOURCE, SOURCE_SHA, "\t")
    targets = verified_rows(TARGETS, TARGETS_SHA, ",")
    t1 = [r for r in targets if r["target"] == "Ti extensor" and r["group"] in {"11657", "11706"}]
    assert {r["bodyid"] for r in t1} == {"11657", "13115", "12704", "11706"}
    matched = [r for r in matches if r["manc_match_id"] in {x["bodyid"] for x in t1}]
    all_ti = [r for r in matches if r["class"] == "MN" and "Ti extensor" in r["type"]]
    report = {
        "scope": "Coverage of one published FANC/MANC matching supplement; absence is not evidence of no biological match",
        "source_url": "https://raw.githubusercontent.com/flyconnectome/2023neckconnective/main/Supplemental_files/Supplemental_file13_other_MANC_FANC_matching.tsv",
        "source_sha256": SOURCE_SHA,
        "manc_target_source_sha256": TARGETS_SHA,
        "published_match_rows": len(matches),
        "manc_t1_extensor_rows": [{k: r[k] for k in ("bodyid", "group", "type", "target")} for r in t1],
        "t1_extensor_match_rows": matched,
        "all_tibia_extensor_match_rows": all_ti,
        "fanc_mn39_40_to_manc_id_resolved": False,
        "malecns_seti_feti_identity_resolved": False,
        "motor_mapping_enabled": False,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{len(matches)} rows; T1 matches {len(matched)}; all Ti extensor rows {len(all_ti)}")


if __name__ == "__main__":
    main()
