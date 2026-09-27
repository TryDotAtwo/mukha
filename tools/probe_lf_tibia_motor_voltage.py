"""Record motor membrane response in the frozen positive-angle diagnostic."""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda


SOURCE = ROOT / "reports/lf_tibia_passive_movement.json"
SPEC = ROOT / "configs/lf_tibia_passive_movement_probe.json"
OUT = ROOT / "data/derived/lf_tibia_motor_voltage_v1"
REPORT = ROOT / "reports/lf_tibia_motor_voltage.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    source_report = json.loads(SOURCE.read_text(encoding="utf-8"))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert sha(SPEC) == source_report["spec_sha256"]
    expected_path = ROOT / "data/derived/lf_tibia_passive_movement_v1/positive_angle_half_wave_events.npy"
    assert sha(expected_path) == next(x["events_sha256"] for x in source_report["cases"]
                                      if x["case"] == "positive_angle_half_wave")
    angle_path = ROOT / "data/derived/lf_tibia_passive_movement_v1/prescribed_angle_rad.npy"
    assert sha(angle_path) == source_report["angle_sha256"]
    angle = np.load(angle_path)
    n, edges, _, row, col, weight = graph_arrays()
    sensory = np.zeros(n, dtype=np.uint8)
    drive = np.zeros(n, dtype=np.float64)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)
    motor_v = np.empty(len(angle), dtype=np.float64)
    motor_syn = np.empty(len(angle), dtype=np.float64)
    events = []
    lib, directory = load_cuda()
    brain = lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                 weight.ctypes.data, sensory.ctypes.data,
                                 Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
    if not brain:
        raise RuntimeError(lib.ff_cuda64_probe_error())
    try:
        for tick, q in enumerate(angle):
            drive.fill(0)
            drive[spec["sensor_graph_index"]] = spec["sensor_gain_mv_per_rad"] * max(0., q)
            if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data, voltage.ctypes.data,
                                     synapse.ctypes.data, spikes.ctypes.data):
                raise RuntimeError(lib.ff_cuda64_probe_error())
            motor_v[tick] = voltage[spec["motor_graph_index"]]
            motor_syn[tick] = synapse[spec["motor_graph_index"]]
            events.extend((tick, int(index)) for index in np.flatnonzero(spikes))
    finally:
        lib.ff_cuda64_destroy(brain)
        directory.close()
    assert np.array_equal(np.asarray(events, dtype=np.uint32).reshape(-1, 2),
                          np.load(expected_path))
    OUT.mkdir(parents=True)
    vpath = OUT / "motor_voltage_mv.npy"
    spath = OUT / "motor_synaptic_input.npy"
    np.save(vpath, motor_v)
    np.save(spath, motor_syn)
    report = {"source_report_sha256": sha(SOURCE), "spec_sha256": sha(SPEC),
              "archived_events_sha256": sha(expected_path),
              "exact_neural_replay": True,
              "motor_body_id": spec["motor_body_id"],
              "motor_graph_index": spec["motor_graph_index"],
              "motor_voltage_min_mv": float(motor_v.min()),
              "motor_voltage_max_mv": float(motor_v.max()),
              "motor_voltage_max_tick": int(motor_v.argmax()),
              "model_spike_threshold_mv": -45.0,
              "motor_synaptic_input_min": float(motor_syn.min()),
              "motor_synaptic_input_max": float(motor_syn.max()),
              "motor_voltage_sha256": sha(vpath),
              "motor_synaptic_input_sha256": sha(spath),
              "biological_validation": False}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in
                      ("motor_voltage_min_mv", "motor_voltage_max_mv",
                       "motor_voltage_max_tick", "motor_synaptic_input_max")}, indent=2))


if __name__ == "__main__":
    main()
