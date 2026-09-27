"""Verify identical-image pose intervention and fresh-process continuation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/visual_head_pose_fixture.json"
RUN = ROOT / "reports/visual_head_pose_fixture.json"
RESUMED = ROOT / "reports/visual_head_pose_resumed.json"
REPORT = ROOT / "reports/visual_head_pose_verification.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config, run, resumed = (json.loads(p.read_text(encoding="utf-8"))
                            for p in (CONFIG, RUN, RESUMED))
    frames, records = config["frames"], run["frames"]
    assert len(frames) == len(records) == 4
    assert frames[1]["rgb"] == frames[2]["rgb"]
    assert frames[1]["local_to_world"] != frames[2]["local_to_world"]
    assert records[1]["rgb_f32le_sha256"] == records[2]["rgb_f32le_sha256"]
    assert records[1]["state_soa"][14:16] == [100000., 0.]
    assert records[2]["state_soa"][14:16] == [0., 100000.]
    assert records[1]["state_soa"][0] > records[1]["state_soa"][1]
    assert records[2]["state_soa"][1] > records[2]["state_soa"][0]
    assert run["full_state_continuation_exact"]
    assert run["final_snapshot_sha256"] == resumed["final_snapshot_sha256"]
    assert resumed["final_frame"] == 4
    checkpoint = ROOT / "reports" / run["checkpoint_file"]
    assert sha(checkpoint) == run["checkpoint_sha256"]
    report = {"passed": True, "identical_image_frames": [2, 3],
              "recorded_photon_rates_by_frame": [r["state_soa"][14:16] for r in records],
              "same_process_replay_exact": True, "fresh_process_replay_exact": True,
              "config_sha256": sha(CONFIG), "run_sha256": sha(RUN),
              "resumed_sha256": sha(RESUMED), "checkpoint_sha256": sha(checkpoint),
              "scope": "Synthetic two-ray, engineering RGB-photon fixture tests body-pose-dependent optical input and receptor continuity; no biological registration or full-CNS coupling."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
