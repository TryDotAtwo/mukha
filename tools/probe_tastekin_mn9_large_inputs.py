"""Track large presynaptic inputs during the unmodified full-graph taste probe."""
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from check_cuda_reference import Params

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "data/derived/malecns_v1_candidates"
OUT = ROOT / "reports/tastekin2026_mn9_large_inputs.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    graph = json.loads((G / "manifest.json").read_text())
    for name in ("body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy", "neurotransmitters.feather"):
        if sha(G / name) != graph["files"][name]["sha256"]:
            raise ValueError("Graph hash mismatch: " + name)
    cross = json.loads((ROOT / "reports/tastekin2026_malecns_crosswalk.json").read_text())
    ids = np.load(G / "body_ids.npy")
    rows = np.load(G / "indptr.npy")
    cols = np.load(G / "indices.npy")
    contacts = np.load(G / "synapse_counts.npy")
    by_id = {int(value): i for i, value in enumerate(ids)}
    nt = pd.read_feather(G / "neurotransmitters.feather").set_index("body").reindex(ids).consensus_nt.fillna("missing_annotation")
    signs = {"acetylcholine": 1, "gaba": -1, "glutamate": -1, "histamine": -1,
             "dopamine": 0, "octopamine": 0, "serotonin": 0,
             "missing_annotation": 0, "unclear": 1}
    signed = nt.map(signs)
    if signed.isna().any():
        raise ValueError("Unmapped NT")
    weights = np.asarray(contacts, np.float64) * np.asarray(signed, np.float64)[cols] * .275
    target = by_id[10331]
    incoming_edges = np.arange(int(rows[target]), int(rows[target + 1]), dtype=np.int64)
    top = sorted(incoming_edges, key=lambda e: (-abs(weights[e]), int(ids[cols[e]])))[:20]
    watch = np.array([int(cols[e]) for e in top], dtype=np.int64)
    sweet = [by_id[i] for i in cross["populations"]["sweet_candidate_LB3c"]["body_ids"]]
    bitter = [by_id[i] for i in cross["populations"]["bitter_candidate_LB1a_d"]["body_ids"]]
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
    cap = 20
    n = len(ids)
    sense = np.zeros(n, np.uint8)
    drive = np.zeros((cap, n), np.float64)
    v = np.empty_like(drive)
    g = np.empty_like(drive)
    spikes = np.empty((cap, n), np.uint8)
    results = []
    try:
        for name, chosen in (("sweet_LB3c", sweet), ("sweet_plus_bitter", sweet + bitter)):
            handle = lib.ff_cuda64_create(n, len(cols), rows.ctypes.data, cols.ctypes.data,
                                          weights.ctypes.data, sense.ctypes.data,
                                          params64(.1, -52, -52, -45, 20, 5, 22, 18), cap)
            if not handle:
                raise RuntimeError(lib.ff_cuda64_probe_error().decode())
            voltage = []
            conductance = []
            target_spikes = []
            source_spikes = {int(ids[ix]): [] for ix in watch}
            try:
                for start in range(0, 1000, cap):
                    drive.fill(0)
                    for tick in range(start, start + cap):
                        if tick % 100 == 0:
                            drive[tick - start, chosen] = 68.75
                    if lib.ff_cuda64_advance(handle, cap, drive.ctypes.data, v.ctypes.data,
                                             g.ctypes.data, spikes.ctypes.data):
                        raise RuntimeError(lib.ff_cuda64_probe_error().decode())
                    voltage.extend(float(x) for x in v[:, target])
                    conductance.extend(float(x) for x in g[:, target])
                    target_spikes.extend(int(start + x) for x in np.flatnonzero(spikes[:, target]))
                    for ix in watch:
                        source_spikes[int(ids[ix])].extend(int(start + x) for x in np.flatnonzero(spikes[:, ix]))
            finally:
                lib.ff_cuda64_destroy(handle)
            results.append({"condition": name, "mn9_spike_ticks": target_spikes,
                            "mn9_voltage_min_mv": min(voltage), "mn9_voltage_max_mv": max(voltage),
                            "mn9_voltage_mean_mv": float(np.mean(voltage)),
                            "mn9_synaptic_state_min_mv": min(conductance),
                            "mn9_synaptic_state_max_mv": max(conductance),
                            "top20_presynaptic_spike_ticks": source_spikes})
            print(name, min(voltage), max(voltage), len(target_spikes), flush=True)
    finally:
        directory.close()
    prior = json.loads((ROOT / "reports/tastekin2026_malecns_mn9_probe.json").read_text())
    for entry in results:
        previous = next(x for x in prior["results"] if x["condition"] == entry["condition"] and x["unclear_sign"] == 1)
        if entry["mn9_spike_ticks"] != previous["mn9_spike_ticks"]["10331"]:
            raise ValueError("Repeated target spike trace does not match prior run")
    report = {"scope": "Unmodified repeat with top-20 left-MN9 presynaptic source traces; no causal attribution or biological validation",
              "graph_manifest_sha256": sha(G / "manifest.json"), "dll_sha256": sha(dll),
              "prior_report_sha256": sha(ROOT / "reports/tastekin2026_malecns_mn9_probe.json"),
              "top20_edges": [{"body_id": int(ids[cols[e]]), "contacts": int(contacts[e]),
                               "signed_synaptic_state_impulse_mv": float(weights[e]),
                               "consensus_nt": str(nt.iloc[cols[e]])} for e in top],
              "results": results}
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
