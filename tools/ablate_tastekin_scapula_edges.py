"""Causal diagnostic of Scapula projections; source CSR is never modified."""
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
OUT = ROOT / "reports/tastekin2026_scapula_edge_ablation.json"
TARGETS = {"Roundup": [26764, 523040], "Rounddown": [12364, 12752],
           "G2N-1": [31018, 89638], "Scapula": [11896, 12811, 12900],
           "MN9": [10331, 16949]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    manifest = json.loads((G / "manifest.json").read_text())
    for name in ("body_ids.npy", "indptr.npy", "indices.npy", "synapse_counts.npy", "neurotransmitters.feather"):
        if sha(G / name) != manifest["files"][name]["sha256"]:
            raise ValueError("Graph hash mismatch: " + name)
    ids = np.load(G / "body_ids.npy")
    row = np.load(G / "indptr.npy")
    col = np.load(G / "indices.npy")
    contacts = np.load(G / "synapse_counts.npy")
    by_id = {int(body): i for i, body in enumerate(ids)}
    cross = json.loads((ROOT / "reports/tastekin2026_malecns_crosswalk.json").read_text())
    sweet = [by_id[x] for x in cross["populations"]["sweet_candidate_LB3c"]["body_ids"]]
    bitter = [by_id[x] for x in cross["populations"]["bitter_candidate_LB1a_d"]["body_ids"]]
    selected = sweet + bitter
    motif = json.loads((ROOT / "reports/tastekin2026_feeding_motif.json").read_text())
    ablated = {}
    for target in ("Roundup", "Rounddown"):
        route = next(x for x in motif["routes"] if x["source"] == "Scapula" and x["target"] == target)
        indices = []
        for pair in route["edges"]:
            post = by_id[pair["target_body_id"]]
            matches = [e for e in range(int(row[post]), int(row[post + 1]))
                       if int(ids[col[e]]) == pair["source_body_id"]]
            if len(matches) != 1 or int(contacts[matches[0]]) != pair["contacts"]:
                raise ValueError("Motif pair mismatch")
            indices.extend(matches)
        if len(indices) != 3:
            raise ValueError("Expected exactly three Scapula output edges")
        ablated[target] = indices
    nt = pd.read_feather(G / "neurotransmitters.feather").set_index("body").reindex(ids).consensus_nt.fillna("missing_annotation")
    common = {"acetylcholine": 1, "gaba": -1, "glutamate": -1, "histamine": -1,
              "dopamine": 0, "octopamine": 0, "serotonin": 0, "missing_annotation": 0}
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
    n = len(ids)
    cap = 20
    sense = np.zeros(n, np.uint8)
    drive = np.zeros((cap, n), np.float64)
    v = np.empty_like(drive)
    g = np.empty_like(drive)
    spikes = np.empty((cap, n), np.uint8)
    results = []
    try:
        for unclear in (1, -1):
            sign = nt.map(dict(common, unclear=unclear))
            if sign.isna().any():
                raise ValueError("Unknown transmitter sign")
            intact = np.asarray(contacts, np.float64) * np.asarray(sign, np.float64)[col] * .275
            for condition, cut in (("intact", []), ("cut_scapula_roundup", ablated["Roundup"]),
                                   ("cut_scapula_rounddown_control", ablated["Rounddown"])):
                weights = intact.copy()
                weights[cut] = 0
                handle = lib.ff_cuda64_create(n, len(col), row.ctypes.data, col.ctypes.data,
                                              weights.ctypes.data, sense.ctypes.data,
                                              params64(.1, -52, -52, -45, 20, 5, 22, 18), cap)
                if not handle:
                    raise RuntimeError(lib.ff_cuda64_probe_error().decode())
                events = {str(body): [] for bodies in TARGETS.values() for body in bodies}
                input_events = 0
                try:
                    for start in range(0, 1000, cap):
                        drive.fill(0)
                        for tick in range(start, start + cap):
                            if tick % 100 == 0:
                                drive[tick - start, selected] = 68.75
                        if lib.ff_cuda64_advance(handle, cap, drive.ctypes.data,
                                                 v.ctypes.data, g.ctypes.data, spikes.ctypes.data):
                            raise RuntimeError(lib.ff_cuda64_probe_error().decode())
                        input_events += int(spikes[:, selected].sum())
                        for body in events:
                            events[body].extend(int(start + t) for t in np.flatnonzero(spikes[:, by_id[int(body)]]))
                finally:
                    lib.ff_cuda64_destroy(handle)
                results.append({"unclear_sign": unclear, "condition": condition,
                                "input_spikes": input_events, "target_spike_ticks": events})
                print(unclear, condition, {name: sum(len(events[str(body)]) for body in bodies)
                                          for name, bodies in TARGETS.items()}, flush=True)
    finally:
        directory.close()
    original = json.loads((ROOT / "reports/tastekin2026_premotor_probe.json").read_text())
    for result in results:
        if result["condition"] != "intact":
            continue
        expected = next(x for x in original["results"]
                        if x["unclear_sign"] == result["unclear_sign"] and x["condition"] == "sweet_plus_bitter")
        if result["input_spikes"] != expected["input_spikes"]:
            raise ValueError("Input protocol changed")
        for group in ("Roundup", "G2N-1", "Scapula", "MN9"):
            for body in TARGETS[group]:
                source = expected["mn9_spike_ticks"] if group == "MN9" else expected["target_spike_ticks"]
                if result["target_spike_ticks"][str(body)] != source[str(body)]:
                    raise ValueError("Intact trace changed")
    report = {"scope": "Diagnostic edge-zeroing in a temporary weight copy; no source graph mutation, physiological claim, or learning",
              "graph_manifest_sha256": sha(G / "manifest.json"), "dll_sha256": sha(dll),
              "original_premotor_report_sha256": sha(ROOT / "reports/tastekin2026_premotor_probe.json"),
              "motif_report_sha256": sha(ROOT / "reports/tastekin2026_feeding_motif.json"),
              "ablated_edges": {name: [{"graph_edge_index": int(e), "source_body_id": int(ids[col[e]]),
                                        "target_body_id": int(ids[np.searchsorted(row, e, side="right") - 1]),
                                        "contacts": int(contacts[e])} for e in edges]
                                for name, edges in ablated.items()},
              "results": results}
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
