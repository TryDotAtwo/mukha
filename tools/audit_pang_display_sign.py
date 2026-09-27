"""Pin author display/significance sign transforms; no MATLAB execution.

--fetch acquires three immutable small M files. Later runs are offline.
Processed-mean examples preserve their historical timing and are NOT bootstrap
replication. A sign transform cannot fix missing ROI/timing provenance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "7fa5829e37d566e02beaaa87efd6a0f1de4e48c0"
FILES = {
    "plot_shortFlash_bootstrappedMetrics_compareGenotypes_L2Project.m":
        "e2e33072ceb1ff3ab197b2505141eb44635ace6a",
    "computeSignificance_shortFlash_bootstrappedMetrics_L2Project.m":
        "2c86f7ff80e437c6b5a0aabf87343cdd8e7c60dd",
    "returnMetricSAF.m": "7a56bb14fa73b274700db992e6f49209e5cdbfd2",
}


def signed_display_ratio(area1, area2):
    if not all(map(math.isfinite, (area1, area2))) or area1 == 0:
        raise ValueError("Finite areas and nonzero denominator required")
    return -area2 / area1


def controls():
    cases = [(2., -1., .5), (-2., 1., .5), (2., 1., -.5), (-2., -1., -.5)]
    for first, second, expected in cases:
        if signed_display_ratio(first, second) != expected:
            raise ValueError("Synthetic display-sign control failed")
    for first, second in [(0., 1.), (float("nan"), 1.), (1., float("inf"))]:
        try:
            signed_display_ratio(first, second)
        except ValueError:
            continue
        raise ValueError("Invalid ratio input accepted")
    # Two artificial bootstrap ratios. Negation is linear; absolute value is not.
    raw = [-2., 1.]
    negated_mean = sum(-x for x in raw) / 2
    absolute_mean = sum(abs(x) for x in raw) / 2
    if negated_mean != .5 or absolute_mean != 1.5:
        raise ValueError("Mixed-sign bootstrap illustration failed")
    return {"four_sign_cases": "pass", "invalid_inputs": "rejected",
            "synthetic_raw_ratios": raw, "mean_after_negation": negated_mean,
            "mean_after_absolute_value": absolute_mean}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    directory = ROOT / "data/reference/pang_display_sign"
    directory.mkdir(parents=True, exist_ok=True)
    sources = []
    for name, blob in FILES.items():
        url = f"https://raw.githubusercontent.com/ClandininLab/L1L2-recurrent-feedback/{COMMIT}/imaging-analysis/HHY_stimulusSpecificAnalysisScripts/{name}"
        path = directory / name
        if path.exists():
            payload = path.read_bytes()
        elif args.fetch:
            with urlopen(url, timeout=30) as response:
                payload = response.read(100_000)
        else:
            raise FileNotFoundError(f"Initial acquisition needs --fetch: {path}")
        digest = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
        if digest != blob:
            raise ValueError(f"Author source blob mismatch: {name}")
        if not path.exists():
            path.write_bytes(payload)
        code = payload.decode()
        snippets = []
        for index, line in enumerate(code.splitlines(), 1):
            if any(term in line for term in ("areaRatio", "dataMatrix = dataMatrix * -1",
                                              "dataMatrix(:,i) = -1*", "mean(dataMatrix",
                                              "quantile(dataMatrix")):
                snippets.append({"line": index, "text": line.strip()})
        sources.append({"name": name, "url": url, "git_blob": blob,
                        "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
                        "selected_source_lines": snippets})
    historical_path = ROOT / "reports/pang_author_curve_audit.json"
    historical = json.loads(historical_path.read_text())
    examples = []
    for row in historical["curves"]:
        if "_CDM_" in row["file"]:
            continue
        first = row["phase1_area_deltaF_over_F_seconds"]
        second = row["phase2_signed_area_deltaF_over_F_seconds"]
        displayed = signed_display_ratio(first, second)
        examples.append({"file": row["file"], "row": row["row"],
                         "historical_absolute_ratio": row["phase2_to_phase1_absolute_area_ratio"],
                         "negative_signed_ratio_on_same_historical_areas": displayed,
                         "absolute_hides_sign": displayed < 0})
    result = {
        "source_commit": COMMIT, "sources": sources, "controls": controls(),
        "executed_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "historical_input_sha256": hashlib.sha256(historical_path.read_bytes()).hexdigest(),
        "source_transform": {"dark": {"area1": -1, "area2": 1, "areaRatio": -1},
                             "light": {"area1": 1, "area2": -1, "areaRatio": -1}},
        "transform_order": "returnMetricSAF extracts bootstrap metric values; negate selected metrics; then mean and quantile",
        "scope": "Static inspection of these pinned scripts plus arithmetic controls; no general MATLAB interpretation",
        "processed_mean_illustrations": examples,
        "limitations": ["No claim these scripts produced a specific published panel",
                        "Historical processed-mean areas retain different boundaries from author ROI bootstrap",
                        "No physiological latency, calibrated optical input, fly-level uncertainty or model score",
                        "Author significance script's nonoverlapping-CI heuristic is described, not endorsed as a statistical test"],
    }
    out = ROOT / "reports/pang_display_sign.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"report": str(out), "examples": len(examples),
                      "negative_display_ratio": [x["file"] for x in examples if x["absolute_hides_sign"]]}))


if __name__ == "__main__":
    main()
