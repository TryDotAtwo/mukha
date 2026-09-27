"""Verify recorded FlyMimic head matrices drive synthetic receptor fixture."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/visual_body_pose_source.json"
FIXTURE = ROOT / "configs/visual_body_pose_fixture.json"
RUN = ROOT / "reports/visual_body_pose_fixture.json"
RESUMED = ROOT / "reports/visual_body_pose_resumed.json"
REPORT = ROOT / "reports/visual_body_pose_verification.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source, fixture, run, resumed = [json.loads(path.read_text(encoding="utf-8"))
                                     for path in (SOURCE, FIXTURE, RUN, RESUMED)]
    assert sha(FIXTURE) == source["fixture_sha256"]
    frames, records = fixture["frames"], run["frames"]
    assert frames[1]["rgb"] == frames[2]["rgb"]
    assert frames[1]["local_to_world"] == source["head_matrix_source"]
    assert frames[2]["local_to_world"] == source["head_matrix_yaw_180"]
    assert records[1]["rgb_f32le_sha256"] == records[2]["rgb_f32le_sha256"]
    assert records[1]["state_soa"][14:16] == [100000., 0.]
    assert records[2]["state_soa"][14:16] == [0., 100000.]
    assert records[1]["state_soa"][0] > records[1]["state_soa"][1]
    assert records[2]["state_soa"][1] > records[2]["state_soa"][0]
    assert run["full_state_continuation_exact"]
    assert run["final_snapshot_sha256"] == resumed["final_snapshot_sha256"]
    checkpoint = ROOT / "reports" / run["checkpoint_file"]
    assert sha(checkpoint) == run["checkpoint_sha256"]
    report = {"passed": True, "source_pose_hash": sha(SOURCE),
              "fixture_hash": sha(FIXTURE), "run_hash": sha(RUN),
              "resumed_hash": sha(RESUMED),
              "same_image_photon_rates": [records[1]["state_soa"][14:16],
                                          records[2]["state_soa"][14:16]],
              "fresh_process_final_state_identical": True,
              "scope": "Published FlyMimic source head orientation under prescribed root yaw drives synthetic two-ray panorama-to-receptor fixture; not registered MaleCNS vision or body dynamics."}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
