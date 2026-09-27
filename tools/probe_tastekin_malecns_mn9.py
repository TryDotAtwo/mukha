"""Source-linked full-graph taste perturbation; explicitly non-physiological drive."""
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from check_cuda_reference import Params

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "data/derived/malecns_v1_candidates"
CROSSWALK = ROOT / "reports/tastekin2026_malecns_crosswalk.json"
OUT = ROOT / "reports/tastekin2026_malecns_mn9_probe.json"
TICKS = 1000
CHUNK = 20


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    cross = json.loads(CROSSWALK.read_text())
    manifest = json.loads((GRAPH / "manifest.json").read_text())
    for name in ("body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy", "neurotransmitters.feather"):
        if sha(GRAPH / name) != manifest["files"][name]["sha256"]:
            raise ValueError(f"Graph source hash mismatch: {name}")
    ids = np.load(GRAPH / "body_ids.npy")
    row = np.load(GRAPH / "indptr.npy")
    col = np.load(GRAPH / "indices.npy")
    contacts = np.load(GRAPH / "synapse_counts.npy")
    index = {int(body): i for i, body in enumerate(ids)}
    sweet = [index[i] for i in cross["populations"]["sweet_candidate_LB3c"]["body_ids"]]
    bitter = [index[i] for i in cross["populations"]["bitter_candidate_LB1a_d"]["body_ids"]]
    targets = [index[x["body_id"]] for x in cross["mn9"]]
    labels = pd.read_feather(GRAPH / "neurotransmitters.feather").set_index("body").reindex(ids).consensus_nt.fillna("missing_annotation")
    params64 = type("Params64", (ct.Structure,), {"_fields_": [
        (name, ct.c_double if kind is ct.c_float else kind) for name, kind in Params._fields_]})
    directory = os.add_dll_directory(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5\bin")
    dll = ROOT / "build/fly_cuda64.dll"
    lib = ct.CDLL(str(dll))
    lib.ff_cuda64_probe_error.restype = ct.c_char_p
    lib.ff_cuda64_create.argtypes = [ct.c_uint32, ct.c_uint64] + [ct.c_void_p] * 4 + [params64, ct.c_uint32]
    lib.ff_cuda64_create.restype = ct.c_void_p
    lib.ff_cuda64_destroy.argtypes = [ct.c_void_p]
    lib.ff_cuda64_advance.argtypes = [ct.c_void_p, ct.c_uint32] + [ct.c_void_p] * 4
    sense = np.zeros(len(ids), np.uint8)
    drive = np.zeros((CHUNK, len(ids)), np.float64)
    voltage = np.empty_like(drive)
    synapse = np.empty_like(drive)
    spikes = np.empty((CHUNK, len(ids)), np.uint8)
    common = {"acetylcholine": 1, "gaba": -1, "glutamate": -1,
              "histamine": -1, "dopamine": 0, "octopamine": 0,
              "serotonin": 0, "missing_annotation": 0}
    results = []
    try:
        for unknown in (1, -1):
            sign = labels.map(dict(common, unclear=unknown))
            if sign.isna().any():
                raise ValueError("Unmapped neurotransmitter label")
            weight = np.asarray(contacts, np.float64) * np.asarray(sign, np.float64)[col] * 0.275
            for name, selected in (("baseline", []), ("sweet_LB3c", sweet),
                                   ("bitter_LB1a_d", bitter), ("sweet_plus_bitter", sweet + bitter)):
                handle = lib.ff_cuda64_create(len(ids), len(col), row.ctypes.data, col.ctypes.data,
                                              weight.ctypes.data, sense.ctypes.data,
                                              params64(.1, -52, -52, -45, 20, 5, 22, 18), CHUNK)
                if not handle:
                    raise RuntimeError(lib.ff_cuda64_probe_error().decode())
                total = 0
                active_input = 0
                mn9_events = {str(int(ids[t])): [] for t in targets}
                mn9_voltage = {str(int(ids[t])): [] for t in targets}
                try:
                    for start in range(0, TICKS, CHUNK):
                        drive.fill(0)
                        for tick in range(start, start + CHUNK):
                            if tick % 100 == 0:
                                drive[tick - start, selected] = 68.75
                        rc = lib.ff_cuda64_advance(handle, CHUNK, drive.ctypes.data,
                                                   voltage.ctypes.data, synapse.ctypes.data,
                                                   spikes.ctypes.data)
                        if rc:
                            raise RuntimeError(lib.ff_cuda64_probe_error().decode())
                        if not np.isfinite(voltage).all() or not np.isfinite(synapse).all():
                            raise ValueError("Nonfinite native state")
                        total += int(spikes.sum())
                        active_input += int(spikes[:, selected].sum())
                        for target in targets:
                            key = str(int(ids[target]))
                            mn9_events[key].extend(int(start + t) for t in np.flatnonzero(spikes[:, target]))
                            mn9_voltage[key].extend(float(v) for v in voltage[:, target])
                finally:
                    lib.ff_cuda64_destroy(handle)
                results.append({"unclear_sign": unknown, "condition": name,
                                "input_cell_count": len(selected), "input_spikes": active_input,
                                "all_graph_spikes": total, "mn9_spike_ticks": mn9_events,
                                "mn9_mean_voltage_mv": {k: float(np.mean(v)) for k, v in mn9_voltage.items()},
                                "mn9_final_voltage_mv": {k: v[-1] for k, v in mn9_voltage.items()}})
                print(name, unknown, total, {k: len(v) for k, v in mn9_events.items()}, flush=True)
    finally:
        directory.close()
    report = {
        "scope": "100-ms deterministic full MaleCNS graph engineering perturbation; not a reproduced biological taste protocol",
        "source_crosswalk_sha256": sha(CROSSWALK), "graph_manifest_sha256": sha(GRAPH / "manifest.json"),
        "native_dll_sha256": sha(dll), "dt_ms": 0.1, "ticks": TICKS,
        "input": "68.75-mV direct voltage jump to each selected GRN every 10 ms; no receptor transduction or dose calibration",
        "synapse_model": "uniform LIF, 0.275 mV per contact, transmitter sign hypotheses inherited from prior diagnostic",
        "results": results, "biological_response_reproduced": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
