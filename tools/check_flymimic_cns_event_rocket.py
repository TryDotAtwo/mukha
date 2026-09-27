"""Audit recorded-CNS-event muscle/contact trace through native rocket plant."""
import csv
import hashlib
import json
import subprocess

import numpy as np

from flymimic_public_model import ROOT

OUT = ROOT / "data/derived/flymimic_cns_event_contact_v1"
TRACES = OUT / "traces.npz"
INPUT = OUT / "rocket_slide_input.csv"
OUTPUT = OUT / "rocket_replay.csv"
EXE = ROOT / "build/flymimic_rocket_replay.exe"
REPORT = ROOT / "reports/flymimic_cns_event_rocket_local.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prior = json.loads((ROOT / "reports/flymimic_cns_event_contact_local.json").read_text())
    assert sha(TRACES) == prior["trace_sha256"] and len(prior["cases"]) == 8
    labels = [f"{case['variant']}_contact_{int(case['contact'])}_motor_{int(case['motor_connected'])}"
              for case in prior["cases"]]
    with np.load(TRACES) as arrays:
        slides = [np.asarray(arrays[label + "_slide_mm"]) for label in labels]
    with INPUT.open("w", newline="", encoding="ascii") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        for case_id, slide in enumerate(slides):
            assert slide.shape == (1000,) and np.isfinite(slide).all()
            for tick, q in enumerate(np.r_[0., slide[:-1]]):
                writer.writerow((case_id, tick, format(q, ".17g")))
    subprocess.run([str(EXE), str(INPUT.relative_to(ROOT)), str(OUTPUT.relative_to(ROOT)), "8"],
                   check=True, cwd=ROOT)
    with OUTPUT.open(newline="", encoding="ascii") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 8000
    data = {field: np.asarray([float(row[field]) for row in rows]).reshape(8, 1000)
            for field in ("case_id", "tick", "time", "q_start_mm", "throttle",
                          "altitude_m", "velocity_mps", "fuel_kg", "thrust_n")}
    for case_id, slide in enumerate(slides):
        np.testing.assert_array_equal(data["case_id"][case_id], case_id)
        np.testing.assert_array_equal(data["tick"][case_id], np.arange(1000))
        np.testing.assert_array_equal(data["q_start_mm"][case_id], np.r_[0., slide[:-1]])
        np.testing.assert_array_equal(data["throttle"][case_id],
                                      np.clip(data["q_start_mm"][case_id] / .3, 0, 1))
        np.testing.assert_allclose(data["time"][case_id],
                                   (np.arange(1000) + 1) * .0001, rtol=0, atol=1e-12)
    engine_error = fuel_error = 0.
    for case_id in range(8):
        target = data["throttle"][case_id] * 20000.
        thrust = data["thrust_n"][case_id]
        previous = np.r_[0., thrust[:-1]]
        expected = target + (previous - target) * np.exp(-.0001 / .3)
        impulse = target * .0001 + (previous - target) * .3 * (-np.expm1(-.0001 / .3))
        fuel = data["fuel_kg"][case_id]
        engine_error = max(engine_error, float(np.max(abs(thrust - expected))))
        fuel_error = max(fuel_error, float(np.max(abs(fuel -
                                                   (np.r_[100., fuel[:-1]] - impulse / 3000.)))))
    assert engine_error < 1e-9 and fuel_error < 1e-12
    baseline = data["velocity_mps"][0]
    for case_id in (0, 1, 2, 4, 5, 6):
        assert np.all(data["throttle"][case_id] == 0)
        for field in ("altitude_m", "velocity_mps", "fuel_kg", "thrust_n"):
            np.testing.assert_array_equal(data[field][0], data[field][case_id])
    active = [3, 7]
    active_results = []
    for case_id in active:
        first_throttle = int(np.flatnonzero(data["throttle"][case_id] > 0)[0])
        assert first_throttle > prior["cases"][case_id]["first_contact_tick"]
        effect = float(np.max(abs(data["velocity_mps"][case_id] - baseline)))
        assert effect > 0
        active_results.append({"variant": prior["cases"][case_id]["variant"],
                               "first_throttle_tick": first_throttle,
                               "max_throttle": float(data["throttle"][case_id].max()),
                               "max_velocity_effect_mps": effect})
    report = {"passed": True, "dt_seconds": .0001, "steps_per_case": 1000,
              "source_contact_report_sha256": sha(ROOT / "reports/flymimic_cns_event_contact_local.json"),
              "six_controls_rocket_traces_identical": True,
              "maximum_engine_recurrence_error_n": engine_error,
              "maximum_fuel_recurrence_error_kg": fuel_error,
              "active": active_results,
              "sampling": "MuJoCo slide position after one step enters native rocket at next step",
              "scope": "Recorded artificial-drive CNS events, hypothetical muscle filter/mapping, one-way native rocket replay; no biological response validation or KSP landing.",
              "hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                         for path in (TRACES, EXE, INPUT, OUTPUT)}}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(active_results, indent=2))


if __name__ == "__main__":
    main()
