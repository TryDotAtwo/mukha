"""Bind the local FP64 author-graph replay to the archived Brian comparison."""

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "build/shiu_local3070.json"
SPIKES = ROOT / "build/shiu_local3070.spikes.bin"
CHECKPOINT = ROOT / "build/shiu_local3070.checkpoint"
COMPARISON = ROOT / "reports/shiu_native64_comparison.json"
PROTOCOL = ROOT / "configs/shiu_sugar_pilot.json"
GRAPH_MANIFEST = ROOT / "data/derived/shiu_2024/manifest.json"
EXE = ROOT / "build/rust-cuda64/release/faithful-fly.exe"
DLL = ROOT / "build/fly_cuda64.dll"
OUT = ROOT / "reports/shiu_local3070_replay.json"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    trace = json.loads(TRACE.read_text())
    archived = json.loads(COMPARISON.read_text())
    checks = {
        "complete_10000_ticks": trace["complete"] and trace["completed_ticks"] == 10000,
        "same_protocol": trace["protocol_sha256"] == sha(PROTOCOL) == archived["protocol_sha256"],
        "same_author_graph": trace["graph_manifest_sha256"] == sha(GRAPH_MANIFEST),
        "exact_archived_events": sha(SPIKES) == archived["spike_files"]["shiu_native64_pilot.spikes.bin"],
        "same_event_count": trace["network_spikes"] == archived["gpu_spikes"],
        "same_target_count": len(trace["target_spike_ticks"]) == archived["target_spike_count"],
        "archived_brian_comparison_passed": archived["numerical_comparison_passed"] is True,
        "checkpoint_hash_matches_trace": sha(CHECKPOINT) == trace["checkpoint_sha256"],
    }
    gpu = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
        text=True).strip().splitlines()[0]
    result = {
        "scope": "Local cross-hardware numerical replay of original Shiu author graph; no biological replication or MaleCNS transfer",
        "checks": checks, "passed": all(checks.values()), "gpu": gpu,
        "exe_sha256": sha(EXE), "cuda_dll_sha256": sha(DLL),
        "protocol_sha256": sha(PROTOCOL), "graph_manifest_sha256": sha(GRAPH_MANIFEST),
        "trace_sha256": sha(TRACE), "spikes_sha256": sha(SPIKES),
        "checkpoint_sha256": sha(CHECKPOINT),
        "network_spikes": trace["network_spikes"],
        "target_spikes": len(trace["target_spike_ticks"]),
        "wall_seconds": trace["wall_seconds"],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
