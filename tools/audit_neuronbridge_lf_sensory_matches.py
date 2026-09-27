"""Audit public v0.9 NeuronBridge CDM matches for the unresolved afferent pair."""

import hashlib
import json
from pathlib import Path

import requests

from flymimic_public_model import ROOT


VERSION = "v3_10_0"
BASE = f"https://janelia-neuronbridge-data-prod.s3.amazonaws.com/{VERSION}/metadata"
IDS = (817697, 821306, 912317)
DEST = ROOT / "data/reference/neuronbridge_lf_sensory_v3_10_0"
OUT = ROOT / "reports/neuronbridge_lf_sensory_matches.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def get_raw(url, path):
    if path.exists():
        return path.read_bytes()
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)
    return response.content


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    sources = {}
    results = {}
    rankings = {}
    for body_id in IDS:
        lookup_url = f"{BASE}/by_body/{body_id}.json"
        lookup_raw = get_raw(lookup_url, DEST / f"{body_id}_by_body.json")
        lookup = json.loads(lookup_raw)
        images = [image for image in lookup["results"]
                  if image.get("publishedName") == f"male-cns:v0.9:{body_id}"]
        assert len(images) == 1
        image = images[0]
        assert image["anatomicalArea"] == "VNC" and image["gender"] == "m"
        match_url = f"{BASE}/cdsresults/{image['id']}.json"
        match_raw = get_raw(match_url, DEST / f"{body_id}_cdsresults.json")
        matches = json.loads(match_raw)
        assert matches["inputImage"]["id"] == image["id"]
        ordered = sorted(matches["results"], key=lambda item: item["normalizedScore"], reverse=True)
        unique_lines = []
        for row in ordered:
            if row["image"].get("anatomicalArea") != "VNC":
                continue
            name = row["image"].get("publishedName")
            if name and name not in unique_lines:
                unique_lines.append(name)
        rankings[body_id] = unique_lines
        sources[str(body_id)] = {
            "lookup_url": lookup_url, "lookup_sha256": sha(lookup_raw),
            "match_url": match_url, "match_sha256": sha(match_raw),
        }
        results[str(body_id)] = {
            "source_image_library": image["libraryName"],
            "source_image_published_name": image["publishedName"],
            "source_image_id": image["id"],
            "raw_match_count": len(matches["results"]),
            "top_25_distinct_lines": unique_lines[:25],
            "top_25_original_rows": [{"line": row["image"].get("publishedName"),
                                      "library": row["image"].get("libraryName"),
                                      "normalized_score": row["normalizedScore"]}
                                     for row in ordered[:25]],
        }
    overlaps = {}
    for position, left in enumerate(IDS):
        for right in IDS[position + 1:]:
            overlaps[f"{left}-{right}"] = {}
            for count in (10, 25, 50, 100):
                a = set(rankings[left][:count])
                b = set(rankings[right][:count])
                overlaps[f"{left}-{right}"][str(count)] = {
                    "shared_count": len(a & b), "jaccard": len(a & b) / len(a | b),
                }
    report = {
        "scope": "Public NeuronBridge color-depth VNC image matches for MaleCNS v0.9 IDs; comparison only, not peripheral receptor identification",
        "api_version": VERSION,
        "source_api_documentation": "https://link.springer.com/article/10.1186/s12859-024-05732-7",
        "source_files": sources,
        "results": results,
        "unique_line_overlap": overlaps,
        "limits": ["Matches use aligned v0.9 VNC projections, while the native simulation uses v1.0 graph and SWCs.",
                   "Broad LM driver images can label multiple cells and do not establish peripheral receptor identity or physiological tuning.",
                   "Ranking scores are search-algorithm outputs, not confidence or biological response measurements."],
        "biological_validation": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value["50"] for key, value in overlaps.items()}, indent=2))


if __name__ == "__main__":
    main()
