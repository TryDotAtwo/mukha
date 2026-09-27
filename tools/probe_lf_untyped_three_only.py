"""Withhold external drive from SNpp50 in the uncalibrated circuit diagnostic.

The cell and all its graph connections remain present; this is an input-drive
ablation, not a cellular silencing or deletion experiment.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda


SOURCE = ROOT / "reports/lf_four_direct_proprio_inputs.json"
SPEC = ROOT / "configs/lf_tibia_passive_movement_probe.json"
ANGLE = ROOT / "data/derived/lf_tibia_passive_movement_v1/prescribed_angle_rad.npy"
OUT = ROOT / "data/derived/lf_untyped_three_drive_withheld_v2"
REPORT = ROOT / "reports/lf_untyped_three_drive_withheld_v2.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not REPORT.exists()
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert source["spec_sha256"] == sha(SPEC)
    assert source["angle_sha256"] == sha(ANGLE)
    assert source["sensory_body_ids"] == [817697, 821306, 908487, 912317]
    angle = np.load(ANGLE)
    n, edges, _, row, col, weight = graph_arrays()
    body = np.load(ROOT / "data/derived/malecns_v1_candidates/body_ids.npy", mmap_mode="r")
    candidates = source["sensory_graph_indices"][:3]
    assert [int(body[i]) for i in candidates] == source["sensory_body_ids"][:3]
    motor = spec["motor_graph_index"]
    assert int(body[motor]) == 815344
    sensory = np.zeros(n, dtype=np.uint8)
    drive = np.zeros(n, dtype=np.float64)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)
    motor_v = np.empty(len(angle), dtype=np.float64)
    events = []
    sensor_ticks = {str(int(body[i])): [] for i in candidates}
    motor_ticks = []
    typed_index = int(source["sensory_graph_indices"][3])
    assert int(body[typed_index]) == 912317
    typed_spike_ticks = []
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
            drive[candidates] = spec["sensor_gain_mv_per_rad"] * max(0.0, q)
            if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data, voltage.ctypes.data,
                                     synapse.ctypes.data, spikes.ctypes.data):
                raise RuntimeError(lib.ff_cuda64_probe_error())
            motor_v[tick] = voltage[motor]
            events.extend((tick, int(i)) for i in np.flatnonzero(spikes))
            for i in candidates:
                if spikes[i]:
                    sensor_ticks[str(int(body[i]))].append(tick)
            if spikes[motor]:
                motor_ticks.append(tick)
            if spikes[typed_index]:
                typed_spike_ticks.append(tick)
    finally:
        lib.ff_cuda64_destroy(brain)
        directory.close()
    OUT.mkdir(parents=True)
    event_path = OUT / "events.npy"
    voltage_path = OUT / "motor_voltage_mv.npy"
    np.save(event_path, np.asarray(events, dtype=np.uint32).reshape(-1, 2))
    np.save(voltage_path, motor_v)
    executed_sources = (ROOT / "tools/probe_lf_untyped_three_only.py",
                        ROOT / "tools/flymimic_public_model.py",
                        ROOT / "tools/probe_live_cns_flymimic.py")
    result = {"question": "Does the artificial three-cell response persist when external drive to typed SNpp50 912317 is withheld?",
              "source_report_sha256": sha(SOURCE), "spec_sha256": sha(SPEC),
              "angle_sha256": sha(ANGLE),
              "runtime_graph_sha256": sha(ROOT / "build/brain_body_graph.bin"),
              "runtime_dll_sha256": sha(ROOT / "build/fly_cuda64.dll"),
              "executed_source_sha256": {str(path.relative_to(ROOT)).replace('\\', '/'): sha(path)
                                         for path in executed_sources},
              "input_drive_withheld_body_id": 912317,
              "cell_and_connections_retained": True,
              "typed_snpp50_spike_ticks": typed_spike_ticks,
              "stimulated_body_ids": source["sensory_body_ids"][:3],
              "gain_mv_per_rad_each": spec["sensor_gain_mv_per_rad"],
              "events": len(events), "sensor_spike_ticks": sensor_ticks,
              "motor_spike_ticks": motor_ticks,
              "motor_voltage_max_mv": float(motor_v.max()),
              "events_sha256": sha(event_path), "motor_voltage_sha256": sha(voltage_path),
              "biological_validation": False,
              "limitations": ["The three stimulated cells have unmeasured tuning.",
                              "Only the external drive to SNpp50 was withheld; the cell and its connections remain in the graph.",
                              "This is a model input sensitivity test, not a cellular silencing experiment or biological reflex validation."]}
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"events": len(events), "sensory_spikes": {k: len(v) for k, v in sensor_ticks.items()},
                      "motor_spikes": len(motor_ticks), "first_motor_tick": motor_ticks[0] if motor_ticks else None}, indent=2))


if __name__ == "__main__":
    main()
