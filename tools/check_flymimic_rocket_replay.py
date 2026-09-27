"""Audit one-way FlyMimic slide-to-native-rocket diagnostic replay."""
import csv
import hashlib
import json
import subprocess

import numpy as np

from flymimic_public_model import ROOT

TRACES = ROOT / "data/derived/flymimic_passive_throttle_v1/traces.npz"
OUT = ROOT / "data/derived/flymimic_passive_throttle_v1"
SOURCE = ROOT / "native/flymimic_rocket_replay.cpp"
EXE = ROOT / "build/flymimic_rocket_replay.exe"
INPUT = OUT / "rocket_slide_input.csv"
OUTPUT = OUT / "rocket_replay.csv"
REPORT = ROOT / "reports/flymimic_rocket_replay_local.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    contact_report = json.loads((ROOT / "reports/flymimic_passive_throttle_local.json").read_text())
    assert sha(TRACES) == contact_report["trace_sha256"]
    with np.load(TRACES) as arrays:
        slides = []
        for contact in (0, 1):
            for pulse in (0, 1):
                q_end = arrays[f"contact_{contact}_pulse_{pulse}_slide_mm"]
                assert q_end.shape == (1000,) and np.isfinite(q_end).all()
                slides.append(np.r_[0., q_end[:-1]])
    with INPUT.open("w", newline="", encoding="ascii") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        for case_id, q in enumerate(slides):
            for tick, value in enumerate(q):
                writer.writerow((case_id, tick, format(value, ".17g")))
    # MSVC narrow fopen cannot open the Cyrillic absolute workspace path.
    subprocess.run([str(EXE), str(INPUT.relative_to(ROOT)), str(OUTPUT.relative_to(ROOT))],
                   check=True, cwd=ROOT)
    with OUTPUT.open(newline="", encoding="ascii") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 4000
    values = {key: np.asarray([float(row[key]) for row in rows]).reshape(4, 1000)
              for key in ("case_id", "tick", "time", "q_start_mm", "throttle",
                          "altitude_m", "velocity_mps", "fuel_kg", "thrust_n")}
    for case_id, q in enumerate(slides):
        np.testing.assert_array_equal(values["case_id"][case_id], case_id)
        np.testing.assert_array_equal(values["tick"][case_id], np.arange(1000))
        np.testing.assert_array_equal(values["q_start_mm"][case_id], q)
        np.testing.assert_array_equal(values["throttle"][case_id], np.clip(q / .3, 0, 1))
        np.testing.assert_allclose(values["time"][case_id],
                                   (np.arange(1000) + 1) * .0001, rtol=0, atol=1e-12)
    for field in ("altitude_m", "velocity_mps", "fuel_kg", "thrust_n", "throttle"):
        for case_id in (1, 2):
            np.testing.assert_array_equal(values[field][0], values[field][case_id])
    engine_error = 0.
    fuel_error = 0.
    for case_id in range(4):
        target = values["throttle"][case_id] * 20000.
        thrust = values["thrust_n"][case_id]
        previous_thrust = np.r_[0., thrust[:-1]]
        expected_thrust = target + (previous_thrust - target) * np.exp(-.0001 / .3)
        impulse = target * .0001 + (previous_thrust - target) * .3 * (-np.expm1(-.0001 / .3))
        fuel = values["fuel_kg"][case_id]
        expected_fuel = np.r_[100., fuel[:-1]] - impulse / 3000.
        engine_error = max(engine_error, float(np.max(np.abs(thrust - expected_thrust))))
        fuel_error = max(fuel_error, float(np.max(np.abs(fuel - expected_fuel))))
    assert engine_error < 1e-9 and fuel_error < 1e-12
    active = 3
    first_nonzero = int(np.flatnonzero(values["throttle"][active] > 0)[0])
    first_contact = contact_report["cases"][3]["first_contact_tick"]
    assert first_nonzero > first_contact
    velocity_effect = float(np.max(np.abs(values["velocity_mps"][active] -
                                          values["velocity_mps"][0])))
    assert velocity_effect > 0
    report = {
        "passed": True, "case_count": 4, "steps_per_case": 1000,
        "dt_seconds": .0001,
        "sampling": "post-step MuJoCo slide q at previous tick is native rocket input at next tick",
        "first_contact_tick": first_contact, "first_nonzero_throttle_tick": first_nonzero,
        "maximum_throttle": float(values["throttle"][active].max()),
        "maximum_velocity_effect_mps": velocity_effect,
        "maximum_engine_recurrence_error_n": engine_error,
        "maximum_fuel_recurrence_error_kg": fuel_error,
        "three_control_rocket_traces_identical": True,
        "no_hidden_rocket_input": True,
        "scope": "One-way measured FlyMimic contact-to-rocket diagnostic; prescribed muscle pulse, no neural command, rocket-to-body feedback, cockpit or KSP landing.",
        "hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                   for path in (TRACES, SOURCE, EXE, INPUT, OUTPUT)}
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("passed", "first_contact_tick",
                      "first_nonzero_throttle_tick", "maximum_throttle",
                      "maximum_velocity_effect_mps")}, indent=2))


if __name__ == "__main__":
    main()
