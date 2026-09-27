"""Single-afferent input sensitivity in the full native MaleCNS graph.

The three unresolved cells are driven one at a time using the prior artificial
angle encoder. All cells and synapses remain intact; this does not identify a
receptor or establish a biological reflex.
"""

import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT
from probe_live_cns_flymimic import Parameters, graph_arrays, load_cuda


SOURCE = ROOT / "reports/lf_four_direct_proprio_inputs.json"
SPEC = ROOT / "configs/lf_tibia_passive_movement_probe.json"
ANGLE = ROOT / "data/derived/lf_tibia_passive_movement_v1/prescribed_angle_rad.npy"
OUT = ROOT / "data/derived/lf_untyped_single_drive_v1"
REPORT = ROOT / "reports/lf_untyped_single_drive_v1.json"


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
    candidates = [int(index) for index in source["sensory_graph_indices"][:3]]
    assert [int(body[i]) for i in candidates] == source["sensory_body_ids"][:3]
    typed_index = int(source["sensory_graph_indices"][3])
    assert int(body[typed_index]) == 912317
    motor = spec["motor_graph_index"]
    assert int(body[motor]) == 815344
    sensory = np.zeros(n, dtype=np.uint8)
    drive = np.zeros(n, dtype=np.float64)
    voltage = np.empty(n, dtype=np.float64)
    synapse = np.empty(n, dtype=np.float64)
    spikes = np.empty(n, dtype=np.uint8)
    lib, directory = load_cuda()
    OUT.mkdir(parents=True)
    trials = []
    try:
        for candidate in candidates:
            motor_v = np.empty(len(angle), dtype=np.float64)
            events = []
            driven_ticks, typed_ticks, motor_ticks = [], [], []
            brain = lib.ff_cuda64_create(n, edges, row.ctypes.data, col.ctypes.data,
                                         weight.ctypes.data, sensory.ctypes.data,
                                         Parameters(.1, -52, -52, -45, 20, 5, 22, 18), 1)
            if not brain:
                raise RuntimeError(lib.ff_cuda64_probe_error())
            try:
                for tick, q in enumerate(angle):
                    drive.fill(0)
                    drive[candidate] = spec["sensor_gain_mv_per_rad"] * max(0.0, q)
                    if lib.ff_cuda64_advance(brain, 1, drive.ctypes.data,
                                             voltage.ctypes.data, synapse.ctypes.data,
                                             spikes.ctypes.data):
                        raise RuntimeError(lib.ff_cuda64_probe_error())
                    motor_v[tick] = voltage[motor]
                    events.extend((tick, int(i)) for i in np.flatnonzero(spikes))
                    if spikes[candidate]:
                        driven_ticks.append(tick)
                    if spikes[typed_index]:
                        typed_ticks.append(tick)
                    if spikes[motor]:
                        motor_ticks.append(tick)
            finally:
                lib.ff_cuda64_destroy(brain)
            body_id = int(body[candidate])
            event_path = OUT / f"{body_id}_events.npy"
            voltage_path = OUT / f"{body_id}_motor_voltage_mv.npy"
            np.save(event_path, np.asarray(events, dtype=np.uint32).reshape(-1, 2))
            np.save(voltage_path, motor_v)
            trials.append({
                "externally_driven_body_id": body_id,
                "driven_graph_index": candidate,
                "event_count": len(events),
                "driven_spike_ticks": driven_ticks,
                "typed_snpp50_spike_ticks": typed_ticks,
                "motor_spike_ticks": motor_ticks,
                "motor_voltage_max_mv": float(motor_v.max()),
                "events_sha256": sha(event_path),
                "motor_voltage_sha256": sha(voltage_path),
            })
    finally:
        directory.close()
    result = {
        "question": "Which one of the three untyped direct afferents is sufficient for model motor spiking under the prior artificial encoder?",
        "source_report_sha256": sha(SOURCE),
        "spec_sha256": sha(SPEC),
        "angle_sha256": sha(ANGLE),
        "runtime_graph_sha256": sha(ROOT / "build/brain_body_graph.bin"),
        "runtime_dll_sha256": sha(ROOT / "build/fly_cuda64.dll"),
        "executed_source_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                                   for path in (ROOT / "tools/probe_lf_untyped_single_drive.py",
                                                ROOT / "tools/flymimic_public_model.py",
                                                ROOT / "tools/probe_live_cns_flymimic.py")},
        "cell_and_connections_retained": True,
        "gain_mv_per_rad_each": spec["sensor_gain_mv_per_rad"],
        "trials": trials,
        "biological_validation": False,
        "limitations": ["The stimulated cells have unresolved receptor modalities and no measured tuning.",
                        "This artificial input sensitivity test cannot validate a natural sensory reflex."],
    }
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{"body_id": x["externally_driven_body_id"],
                       "afferent_spikes": len(x["driven_spike_ticks"]),
                       "motor_spikes": len(x["motor_spike_ticks"]),
                       "first_motor_tick": x["motor_spike_ticks"][0] if x["motor_spike_ticks"] else None}
                      for x in trials], indent=2))


if __name__ == "__main__":
    main()
