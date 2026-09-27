"""Verify four immutable full-graph conductance sensitivity results."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "malecns_conductance_candidate_probe_reset"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    graph_hash = sha(ROOT / "data/derived/malecns_v1_candidates/manifest.json")
    dll_hash = sha(ROOT / "build/fly_cuda_conductance.dll")
    crosswalk_hash = sha(ROOT / "reports/tastekin2026_malecns_crosswalk.json")
    entries = []
    for reversal in (-70, -48):
        for unclear in (1, -1):
            path = ROOT / f"reports/{PREFIX}_e{reversal}_u{unclear}.json"
            report = json.loads(path.read_text())
            if (report["graph_manifest_sha256"] != graph_hash or
                report["dll_sha256"] != dll_hash or
                report["crosswalk_sha256"] != crosswalk_hash or
                len(report["results"]) != 1):
                raise ValueError("Full-graph report provenance mismatch")
            result = report["results"][0]
            if (result["reversal_inh_mv"] != reversal or
                result["unclear_sign"] != unclear or
                result["input_spikes"] < 610):
                raise ValueError("Unexpected trial identity or insufficient driven input spikes")
            if not min(-52, reversal) <= result["non_input_voltage_min_mv"] <= result["non_input_voltage_max_mv"] <= 0:
                raise ValueError("Voltage boundedness violation")
            entries.append({"reversal_inh_mv": reversal, "unclear_sign": unclear,
                            "all_spikes": result["all_spikes"],
                            "input_spikes": result["input_spikes"],
                            "additional_input_spikes_beyond_direct_drive": result["input_spikes"] - 610,
                            "voltage_range_non_input_mv": [result["non_input_voltage_min_mv"],
                                                           result["non_input_voltage_max_mv"]],
                            "group_spike_counts": result["group_spike_counts"],
                            "report_sha256": sha(path)})
    output = {"scope": "Four separate-process full MaleCNS numerical conductance variants, no physiological validation",
              "graph_manifest_sha256": graph_hash, "dll_sha256": dll_hash,
              "input_crosswalk_sha256": crosswalk_hash, "variants": entries,
              "numerical_bounds_passed": True,
              "biological_validation_passed": False}
    dest = ROOT / "reports/malecns_conductance_candidate_summary.json"
    dest.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(entries, indent=2))


if __name__ == "__main__":
    main()
