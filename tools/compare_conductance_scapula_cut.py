"""Compare intact and temporary Scapula-to-Roundup conductance cuts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "malecns_conductance_candidate_probe_reset"
OUT = ROOT / "reports/malecns_conductance_scapula_cut_comparison.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    graph_hash = sha(ROOT / "data/derived/malecns_v1_candidates/manifest.json")
    dll_hash = sha(ROOT / "build/fly_cuda_conductance.dll")
    cross_hash = sha(ROOT / "reports/tastekin2026_malecns_crosswalk.json")
    rows = []
    for reversal in (-70, -48):
        for sign in (1, -1):
            pair = {}
            hashes = {}
            for condition, suffix in (("intact", ""), ("cut", "_cut_scapula_roundup")):
                path = ROOT / f"reports/{PREFIX}{suffix}_e{reversal}_u{sign}.json"
                report = json.loads(path.read_text())
                if (report["graph_manifest_sha256"] != graph_hash or
                    report["dll_sha256"] != dll_hash or
                    report["crosswalk_sha256"] != cross_hash or
                    len(report["results"]) != 1):
                    raise ValueError("Provenance mismatch: " + str(path))
                trial = report["results"][0]
                if (trial["reversal_inh_mv"] != reversal or
                    trial["unclear_sign"] != sign or
                    (condition == "cut" and
                     (trial["input_condition"] != "combined" or
                      not trial["cut_scapula_roundup"] or
                      trial["cut_edge_count"] != 3 or
                      trial["cut_contact_sum"] != 251))):
                    raise ValueError("Trial mismatch: " + str(path))
                pair[condition] = trial
                hashes[condition] = sha(path)
            a, b = pair["intact"], pair["cut"]
            rows.append({"reversal_inh_mv": reversal, "unclear_sign": sign,
                         "roundup_spikes_intact": a["group_spike_counts"]["Roundup"],
                         "roundup_spikes_cut": b["group_spike_counts"]["Roundup"],
                         "roundup_cut_minus_intact": b["group_spike_counts"]["Roundup"] - a["group_spike_counts"]["Roundup"],
                         "g2n1_spikes_intact": a["group_spike_counts"]["G2N-1"],
                         "g2n1_spikes_cut": b["group_spike_counts"]["G2N-1"],
                         "input_spikes_intact": a["input_spikes"],
                         "input_spikes_cut": b["input_spikes"],
                         "report_sha256": hashes})
    result = {"scope": "Conditional full-network causal diagnostic with three in-memory conductance cuts; not physiological validation",
              "graph_manifest_sha256": graph_hash, "dll_sha256": dll_hash,
              "crosswalk_sha256": cross_hash, "rows": rows,
              "roundup_rescue_all_variants": all(row["roundup_cut_minus_intact"] > 0 for row in rows),
              "biological_validation_passed": False}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
