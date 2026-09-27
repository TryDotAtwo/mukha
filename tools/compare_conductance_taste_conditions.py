"""Compare predeclared conductance variants without selecting a favorable one."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "malecns_conductance_candidate_probe_reset"
OUT = ROOT / "reports/malecns_conductance_taste_comparison.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    graph_hash = sha(ROOT / "data/derived/malecns_v1_candidates/manifest.json")
    dll_hash = sha(ROOT / "build/fly_cuda_conductance.dll")
    cross_hash = sha(ROOT / "reports/tastekin2026_malecns_crosswalk.json")
    comparisons = []
    for reversal in (-70, -48):
        for unclear in (1, -1):
            trials = {}
            hashes = {}
            for condition in ("sweet", "combined"):
                part = "_sweet" if condition == "sweet" else ""
                path = ROOT / f"reports/{PREFIX}{part}_e{reversal}_u{unclear}.json"
                report = json.loads(path.read_text())
                if (report["graph_manifest_sha256"] != graph_hash or
                    report["dll_sha256"] != dll_hash or
                    report["crosswalk_sha256"] != cross_hash or
                    len(report["results"]) != 1):
                    raise ValueError("Trial provenance mismatch")
                trial = report["results"][0]
                if trial["reversal_inh_mv"] != reversal or trial["unclear_sign"] != unclear:
                    raise ValueError("Trial identity mismatch")
                if condition == "sweet" and (trial["input_condition"] != "sweet" or
                                               trial["sweet_population_spikes"] < 230):
                    raise ValueError("Sweet trial mismatch")
                trials[condition] = trial
                hashes[condition] = sha(path)
            s, c = trials["sweet"], trials["combined"]
            comparisons.append({"reversal_inh_mv": reversal, "unclear_sign": unclear,
                                "roundup_spikes_sweet": s["group_spike_counts"]["Roundup"],
                                "roundup_spikes_combined": c["group_spike_counts"]["Roundup"],
                                "roundup_delta_combined_minus_sweet": c["group_spike_counts"]["Roundup"] - s["group_spike_counts"]["Roundup"],
                                "g2n1_spikes_sweet": s["group_spike_counts"]["G2N-1"],
                                "g2n1_spikes_combined": c["group_spike_counts"]["G2N-1"],
                                "bitter_population_spikes_during_sweet_only": s["bitter_population_spikes"],
                                "sweet_population_spikes_during_sweet_only": s["sweet_population_spikes"],
                                "sweet_driven_total_input_spikes_combined": c["input_spikes"],
                                "report_sha256": hashes})
    report = {"scope": "Predeclared four-variant sweet versus combined conditional-model comparison; no quantitative or qualitative biological replication claim",
              "graph_manifest_sha256": graph_hash, "dll_sha256": dll_hash,
              "crosswalk_sha256": cross_hash, "comparisons": comparisons,
              "roundup_suppression_in_all_variants": all(x["roundup_delta_combined_minus_sweet"] < 0 for x in comparisons),
              "biological_validation_passed": False}
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(comparisons, indent=2))


if __name__ == "__main__":
    main()
