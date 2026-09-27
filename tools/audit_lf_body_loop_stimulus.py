"""Check the executed FlyMimic knee trajectory against the intended reflex stimulus."""

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/lf_four_proprio_body_loop_v2.json"
TRACES = ROOT / "data/derived/lf_four_proprio_body_loop_v2/traces.npz"
OUT = ROOT / "reports/lf_four_proprio_body_stimulus_audit.json"
CASES = ("sensory_blocked", "four_sensory_motor_connected",
         "four_sensory_motor_disconnected")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(x, reference, dt_s):
    dx = np.diff(x)
    relative = x - reference
    return {
        "first_saved_knee_rad": float(x[0]),
        "last_saved_knee_rad": float(x[-1]),
        "saved_peak_to_peak_deg": float(np.rad2deg(np.ptp(x))),
        "saved_net_change_deg": float(np.rad2deg(x[-1] - x[0])),
        "min_relative_to_relaxed_deg": float(np.rad2deg(relative.min())),
        "max_relative_to_relaxed_deg": float(np.rad2deg(relative.max())),
        "strictly_decreasing_saved_steps": int(np.count_nonzero(dx < 0)),
        "strictly_increasing_saved_steps": int(np.count_nonzero(dx > 0)),
        "step_intervals": len(dx),
        "max_abs_step_velocity_deg_per_s": float(np.rad2deg(np.max(np.abs(dx))) / dt_s),
        "fraction_above_relaxed_angle": float(np.mean(relative > 0)),
    }


def main():
    assert not OUT.exists()
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert source["ticks"] == 5000 and source["dt_ms"] == .1
    assert source["initial_perturbation_deg"] == 10.0
    assert source["central_direct_drive"] is False
    assert sha(TRACES) == source["trace_sha256"]
    dt_s = source["dt_ms"] / 1000
    reference = source["initial_knee_reference_rad"]
    data = np.load(TRACES)
    cases = {}
    for case in CASES:
        x = data[f"{case}_knee_rad"]
        assert len(x) == source["ticks"] and np.isfinite(x).all()
        cases[case] = summarize(x, reference, dt_s)
    blocked = data["sensory_blocked_knee_rad"]
    disconnected = data["four_sensory_motor_disconnected_knee_rad"]
    report = {
        "scope": "Actual joint trajectory in the existing 500-ms closed body-loop diagnostic",
        "source_report_sha256": sha(SOURCE), "source_traces_sha256": sha(TRACES),
        "published_protocol_reference": "Akitake et al. 2015, 2-Hz sinusoidal tibia movement, approximately 20 degrees",
        "published_protocol_url": "https://www.nature.com/articles/ncomms8288",
        "trajectory_is_the_published_protocol": False,
        "reason": "The body-loop input is a one-time +10-degree initial displacement followed by free dynamics, not prescribed 2-Hz cyclic motion",
        "cases": cases,
        "sensory_blocked_and_motor_disconnected_knee_traces_exactly_equal": bool(np.array_equal(blocked, disconnected)),
        "passive_half_wave_encoder_would_remain_active_fraction": float(np.mean(blocked > reference)),
        "biological_reflex_validated": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passive": cases["sensory_blocked"],
                      "same_passive_knee_without_motor": report["sensory_blocked_and_motor_disconnected_knee_traces_exactly_equal"]}, indent=2))


if __name__ == "__main__":
    main()
