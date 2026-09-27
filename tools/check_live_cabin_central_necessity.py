"""Compare matched live cabin runs with and without artificial central drive."""
import hashlib
import json
import numpy as np

from flymimic_public_model import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    runs = {}
    for mode, suffix in (("periodic", ""), ("none", "_no_central")):
        report_path = ROOT / "reports" / f"live_cabin_claw{suffix}_v2_local.json"
        trace_path = ROOT / "data/derived" / f"live_cabin_claw{suffix}_v2/traces.npz"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["central_drive"] == mode
        assert report["trace_sha256"] == sha(trace_path)
        assert report["executed_source_sha256"] == sha(ROOT / "tools/probe_live_cabin_claw.py")
        for case in report["cases"]:
            event_path = trace_path.parent / f"{case['case']}_events.npy"
            assert sha(event_path) == case["event_sha256"]
        runs[mode] = (report, np.load(trace_path), sha(report_path))
    active = runs["periodic"][1]
    quiet = runs["none"][1]
    assert np.array_equal(active["blocked_slide_mm"], active["negative_slide_mm"])
    for case in ("blocked", "negative", "motor_off", "contact_off"):
        assert not np.any(quiet[f"{case}_global_spike_count"])
        assert not np.any(quiet[f"{case}_contacts"])
        assert not np.any(quiet[f"{case}_slide_mm"])
        assert not np.any(quiet[f"{case}_throttle"])
    result = {"artificial_central_drive_required_for_activity_in_this_100ms_fixture": True,
              "periodic_negative_sensor_spikes": int(np.sum(active["negative_sensor_spike"])),
              "none_negative_sensor_spikes": int(np.sum(quiet["negative_sensor_spike"])),
              "none_negative_peak_sensor_drive_mv": float(np.max(quiet["negative_sensor_mv"])),
              "periodic_report_sha256": runs["periodic"][2],
              "none_report_sha256": runs["none"][2],
              "executed_source_sha256": sha(ROOT / "tools/check_live_cabin_central_necessity.py"),
              "scope": "Declared 100-ms fixture only; no inference that the animal requires this stimulus."}
    path = ROOT / "reports/live_cabin_central_necessity_v2.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
