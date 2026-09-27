"""Full-MaleCNS neural response to a source-shaped prescribed tibia trajectory.

Prescribed kinematics and an unmeasured one-cell encoder are diagnostic only.
No central direct drive, body mechanics, EMG observation, or motor calibration.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda


SPEC = ROOT / "configs/lf_tibia_passive_movement_probe.json"
OUT = ROOT / "data/derived/lf_tibia_passive_movement_v1"
REPORT = ROOT / "reports/lf_tibia_passive_movement.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["ticks"] == 5000 and spec["dt_ms"] == 0.1
    assert spec["frequency_hz"] == 2.0 and spec["angle_peak_to_peak_deg"] == 20.0
    n, edge_count, _, row, col, weight = graph_arrays()
    graph_path = ROOT / "build/brain_body_graph.bin"
    time_ms = np.arange(spec["ticks"], dtype=np.float64) * spec["dt_ms"]
    angle_rad = np.deg2rad(spec["angle_peak_to_peak_deg"] / 2) * np.sin(
        2 * np.pi * spec["frequency_hz"] * time_ms / 1000)
    assert abs(angle_rad.max() - angle_rad.min() - np.deg2rad(20)) < 1e-6
    lib, directory = load_cuda()
    sensory = np.zeros(n, dtype=np.uint8)
    drive = np.zeros(n, dtype=np.float64)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)
    OUT.mkdir(parents=True)
    np.save(OUT / "prescribed_angle_rad.npy", angle_rad)
    results = []
    try:
        for case, polarity in (("sensor_off", 0), ("positive_angle_half_wave", 1),
                               ("negative_angle_half_wave", -1)):
            brain = lib.ff_cuda64_create(n, edge_count, row.ctypes.data, col.ctypes.data,
                                         weight.ctypes.data, sensory.ctypes.data,
                                         Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
            if not brain:
                raise RuntimeError(lib.ff_cuda64_probe_error())
            events = []
            sensor_spikes = []
            motor_spikes = []
            try:
                for tick, angle in enumerate(angle_rad):
                    drive.fill(0)
                    drive[spec["sensor_graph_index"]] = (
                        spec["sensor_gain_mv_per_rad"] * max(0.0, polarity * angle))
                    if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data, voltage.ctypes.data,
                                             synapse.ctypes.data, spikes.ctypes.data):
                        raise RuntimeError(lib.ff_cuda64_probe_error())
                    fired = np.flatnonzero(spikes)
                    events.extend((tick, int(index)) for index in fired)
                    if spikes[spec["sensor_graph_index"]]:
                        sensor_spikes.append(tick)
                    if spikes[spec["motor_graph_index"]]:
                        motor_spikes.append(tick)
            finally:
                lib.ff_cuda64_destroy(brain)
            path = OUT / f"{case}_events.npy"
            np.save(path, np.asarray(events, dtype=np.uint32).reshape(-1, 2))
            results.append({"case": case, "polarity": polarity,
                            "all_graph_events": len(events),
                            "sensor_spike_ticks": sensor_spikes,
                            "motor_spike_ticks": motor_spikes,
                            "events_sha256": sha(path)})
    finally:
        directory.close()
    report = {"scope": "Single prescribed tibia cycle through one hypothetical sensory encoder and full native MaleCNS; neural-only diagnostic",
              "spec_sha256": sha(SPEC), "runtime_graph_sha256": sha(graph_path),
              "angle_sha256": sha(OUT / "prescribed_angle_rad.npy"),
              "cases": results, "biological_gate_passed": False,
              "limitations": ["No measured SNpp50 voltage or firing-rate transfer",
                              "20-degree movement interpreted as peak-to-peak",
                              "Angle sign not registered to published limb or FlyMimic",
                              "No body mechanics or muscle EMG readout",
                              "No direct central stimulation or background drive"]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{"case": case["case"], "events": case["all_graph_events"],
                       "sensor_spikes": len(case["sensor_spike_ticks"]),
                       "motor_spikes": len(case["motor_spike_ticks"])}
                      for case in results], indent=2))


if __name__ == "__main__":
    main()
