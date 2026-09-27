"""Diagnostic, uncalibrated joint drive of four direct proprioceptive inputs.

This is a circuit-capability sensitivity test, not a physiological encoder or
an assignment of the three uncertain cells to the SNpp50 subtype.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda


SOURCE = ROOT / "reports/lf_tibia_passive_movement.json"
SPEC = ROOT / "configs/lf_tibia_passive_movement_probe.json"
ANGLE = ROOT / "data/derived/lf_tibia_passive_movement_v1/prescribed_angle_rad.npy"
OUT = ROOT / "data/derived/lf_four_direct_proprio_inputs_v1"
REPORT = ROOT / "reports/lf_four_direct_proprio_inputs.json"
SENSORY_IDS = (817697, 821306, 908487, 912317)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert sha(SPEC) == source["spec_sha256"]
    assert sha(ANGLE) == source["angle_sha256"]
    angle = np.load(ANGLE)
    assert angle.shape == (5000,)
    n, edges, _, row, col, weight = graph_arrays()
    body_ids = np.load(ROOT / "data/derived/malecns_v1_candidates/body_ids.npy", mmap_mode="r")
    indices = [int(np.flatnonzero(body_ids == body)[0]) for body in SENSORY_IDS]
    assert all(int(body_ids[index]) == body for body, index in zip(SENSORY_IDS, indices))
    assert indices[-1] == spec["sensor_graph_index"]
    motor = spec["motor_graph_index"]
    assert int(body_ids[motor]) == spec["motor_body_id"]
    drive = np.zeros(n, dtype=np.float64)
    sensory = np.zeros(n, dtype=np.uint8)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)
    motor_v = np.empty(len(angle), dtype=np.float64)
    motor_syn = np.empty(len(angle), dtype=np.float64)
    sensory_ticks = {str(body): [] for body in SENSORY_IDS}
    motor_ticks = []
    events = []
    lib, directory = load_cuda()
    brain = lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                 weight.ctypes.data, sensory.ctypes.data,
                                 Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
    if not brain:
        directory.close()
        raise RuntimeError(lib.ff_cuda64_probe_error())
    try:
        for tick, q in enumerate(angle):
            drive.fill(0)
            drive[indices] = spec["sensor_gain_mv_per_rad"] * max(0.0, q)
            if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data, voltage.ctypes.data,
                                     synapse.ctypes.data, spikes.ctypes.data):
                raise RuntimeError(lib.ff_cuda64_probe_error())
            motor_v[tick] = voltage[motor]
            motor_syn[tick] = synapse[motor]
            events.extend((tick, int(index)) for index in np.flatnonzero(spikes))
            for body, index in zip(SENSORY_IDS, indices):
                if spikes[index]:
                    sensory_ticks[str(body)].append(tick)
            if spikes[motor]:
                motor_ticks.append(tick)
    finally:
        lib.ff_cuda64_destroy(brain)
        directory.close()
    OUT.mkdir(parents=True)
    paths = {"events": OUT / "events.npy", "motor_voltage_mv": OUT / "motor_voltage_mv.npy",
             "motor_synaptic_input": OUT / "motor_synaptic_input.npy"}
    np.save(paths["events"], np.asarray(events, dtype=np.uint32).reshape(-1, 2))
    np.save(paths["motor_voltage_mv"], motor_v)
    np.save(paths["motor_synaptic_input"], motor_syn)
    report = {
        "question": "Can the current full graph reach candidate motor threshold when all four direct proprioceptive partners receive the same strong hypothetical positive-angle drive?",
        "source_report_sha256": sha(SOURCE), "spec_sha256": sha(SPEC),
        "angle_sha256": sha(ANGLE), "runtime_graph_sha256": sha(ROOT / "build/brain_body_graph.bin"),
        "sensory_body_ids": SENSORY_IDS, "sensory_graph_indices": indices,
        "motor_body_id": int(body_ids[motor]), "motor_graph_index": motor,
        "sensor_gain_mv_per_rad_each": spec["sensor_gain_mv_per_rad"],
        "case": "positive-angle synchronous four-cell diagnostic",
        "all_graph_events": len(events), "sensory_spike_ticks": sensory_ticks,
        "motor_spike_ticks": motor_ticks,
        "motor_voltage_min_mv": float(motor_v.min()),
        "motor_voltage_max_mv": float(motor_v.max()),
        "motor_voltage_max_tick": int(motor_v.argmax()),
        "motor_synaptic_input_max": float(motor_syn.max()),
        "model_spike_threshold_mv": -45.0,
        "output_sha256": {name: sha(path) for name, path in paths.items()},
        "biological_validation": False,
        "limitations": ["Three cells have no source-backed angle encoder or FeCO functional subtype",
                        "The common gain and synchronous phase are deliberately artificial",
                        "Global synaptic gains and motor excitability are not physiologically calibrated",
                        "A motor spike would establish model circuit capability only; absence would reject this one drive hypothesis only"]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"events": len(events), "sensory_spikes": {k: len(v) for k, v in sensory_ticks.items()},
                      "motor_spikes": len(motor_ticks), "motor_v_max_mv": report["motor_voltage_max_mv"]}, indent=2))


if __name__ == "__main__":
    main()
