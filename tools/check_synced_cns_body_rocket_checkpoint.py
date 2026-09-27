"""Extend a verified CNS/body checkpoint with one-way contact rocket state.

The body drives the diagnostic radial rocket by measured slider position.
Rocket acceleration is not fed back into this body replay.
"""

import argparse
import ctypes as ct
import hashlib
import json

import numpy as np

from flymimic_public_model import ROOT


BASE = ROOT / "data/derived/synced_cns_body_checkpoint_v1"
BASE_REPORT = ROOT / "reports/synced_cns_body_checkpoint.json"
BASE_RESUME = ROOT / "reports/synced_cns_body_resume.json"
ROCKET_DLL = ROOT / "build/rocket_vertical_checkpoint_abi.dll"
OUT = ROOT / "data/derived/synced_cns_body_rocket_checkpoint_v1"
REPORT = ROOT / "reports/synced_cns_body_rocket_checkpoint.json"
RESUME_REPORT = ROOT / "reports/synced_cns_body_rocket_resume.json"
SPLIT, END = 250, 500
DT = .0001


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def library():
    lib = ct.CDLL(str(ROCKET_DLL))
    lib.rocket_new.restype = ct.c_void_p
    lib.rocket_new_from_snapshot.argtypes = [ct.POINTER(ct.c_double)]
    lib.rocket_new_from_snapshot.restype = ct.c_void_p
    lib.rocket_snapshot.argtypes = [ct.c_void_p, ct.POINTER(ct.c_double)]
    lib.rocket_snapshot.restype = ct.c_int
    lib.rocket_advance.argtypes = [ct.c_void_p, ct.c_double, ct.c_double,
                                   ct.POINTER(ct.c_double)]
    lib.rocket_advance.restype = ct.c_int
    lib.rocket_delete.argtypes = [ct.c_void_p]
    return lib


def advance(lib, handle, commands):
    state = np.empty((len(commands), 5), dtype=np.float64)
    for i, q in enumerate(commands):
        assert lib.rocket_advance(handle, float(q), DT,
                                  state[i].ctypes.data_as(ct.POINTER(ct.c_double)))
    return state


def main(resume_only=False):
    base = json.loads(BASE_REPORT.read_text(encoding="utf-8"))
    base_resume = json.loads(BASE_RESUME.read_text(encoding="utf-8"))
    assert base_resume["checkpoint_report_sha256"] == sha(BASE_REPORT)
    assert base_resume["tail_all_eight_traces_exact"]
    for name, expected in base["files"].items():
        assert sha(BASE / name) == expected
    with np.load(BASE / "continuation.npz") as continuation:
        assert np.array_equal(continuation["original"], continuation["restored"])
        assert np.array_equal(continuation["original_events"], continuation["restored_events"])
        tail = continuation["original"].copy()
    assert tail.shape == (END - SPLIT, 8)
    archived_path = ROOT / "data/derived/lf_four_proprio_body_loop_v2/traces.npz"
    assert sha(archived_path) == base["source_trace_sha256"]
    with np.load(archived_path) as archived:
        slide = archived["four_sensory_motor_connected_slide_mm"][:END].copy()
    assert np.array_equal(slide[SPLIT:], tail[:, 1])
    commands = np.r_[0., slide[:-1]]
    assert len(commands) == END and np.all(np.isfinite(commands))
    lib = library()

    if resume_only:
        assert OUT.exists() and REPORT.exists() and not RESUME_REPORT.exists()
        prior = json.loads(REPORT.read_text(encoding="utf-8"))
        assert prior["rocket_dll_sha256"] == sha(ROCKET_DLL)
        assert prior["base_report_sha256"] == sha(BASE_REPORT)
        for name, expected in prior["files"].items():
            assert sha(OUT / name) == expected
        snapshot = np.load(OUT / "rocket_snapshot.npy")
        assert snapshot.shape == (6,)
        handle = lib.rocket_new_from_snapshot(snapshot.ctypes.data_as(ct.POINTER(ct.c_double)))
        assert handle
        try:
            tail_state = advance(lib, handle, commands[SPLIT:])
        finally:
            lib.rocket_delete(handle)
        original = np.load(OUT / "rocket_state_trace.npy")
        assert np.array_equal(tail_state, original[SPLIT:])
        result = {"scope": "Cross-process one-way rocket continuation from synchronized CNS/body tick",
                  "checkpoint_report_sha256": sha(REPORT),
                  "fresh_process": True, "fresh_rocket_handle": True,
                  "rocket_tail_state_exact": True,
                  "neural_body_tail_exact_from_prior_cross_process_test": True,
                  "rocket_feedback_to_body": False,
                  "biological_validation": False}
        RESUME_REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"cross_process_rocket_tail_exact": True}, indent=2))
        return

    assert not OUT.exists() and not REPORT.exists()
    handle = lib.rocket_new()
    assert handle
    snapshot = np.empty(6, dtype=np.float64)
    try:
        prefix = advance(lib, handle, commands[:SPLIT])
        assert lib.rocket_snapshot(handle, snapshot.ctypes.data_as(ct.POINTER(ct.c_double)))
        assert snapshot[0] == prefix[-1, 0] and snapshot[5] == 0
        suffix = advance(lib, handle, commands[SPLIT:])
    finally:
        lib.rocket_delete(handle)
    continuous = np.vstack((prefix, suffix))
    restored = lib.rocket_new_from_snapshot(snapshot.ctypes.data_as(ct.POINTER(ct.c_double)))
    assert restored
    try:
        replay = advance(lib, restored, commands[SPLIT:])
    finally:
        lib.rocket_delete(restored)
    assert np.array_equal(suffix, replay)
    ballistic = lib.rocket_new()
    assert ballistic
    try:
        zero = advance(lib, ballistic, np.zeros(END))
    finally:
        lib.rocket_delete(ballistic)
    differences = np.flatnonzero(continuous[:, 2] != zero[:, 2])
    first_effect = int(differences[0]) if len(differences) else None
    first_throttle = int(np.flatnonzero(commands > 0)[0]) if np.any(commands > 0) else None
    assert first_effect is not None and first_effect == first_throttle
    OUT.mkdir(parents=True)
    np.save(OUT / "rocket_snapshot.npy", snapshot)
    np.save(OUT / "rocket_state_trace.npy", continuous)
    report = {"scope": "One-way full-CNS/body contact-slider to native radial-rocket synchronized checkpoint",
              "base_report_sha256": sha(BASE_REPORT), "base_resume_report_sha256": sha(BASE_RESUME),
              "rocket_dll_sha256": sha(ROCKET_DLL),
              "rocket_source_sha256": sha(ROOT / "native/rocket_vertical_abi.cpp"),
              "checkpoint_tick": SPLIT, "end_tick": END, "dt_s": DT,
              "checkpoint_rocket_state": snapshot.tolist(),
              "rocket_state_fields": ["time_s", "altitude_m", "velocity_mps", "fuel_kg", "thrust_n", "contact_flag"],
              "command_phase": "body slide qpos at start of tick; first command zero, then previous after-step slide",
              "first_nonzero_throttle_tick": first_throttle,
              "first_velocity_difference_vs_ballistic_tick": first_effect,
              "final_velocity_difference_vs_ballistic_mps": float(continuous[-1, 2] - zero[-1, 2]),
              "rocket_tail_state_exact_new_handle": True,
              "rocket_feedback_to_body": False,
              "files": {p.name: sha(p) for p in OUT.iterdir()},
              "biological_validation": False,
              "limits": ["One-way rocket replay does not alter the neural/body continuation",
                         "Radial diagnostic rocket is not KSP and has no touchdown in this window",
                         "Unvalidated sensory encoder and motor-muscle transfer persist",
                         "No vision, training, full recorder, or landing outcome included"]}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("checkpoint_tick", "end_tick",
                      "first_nonzero_throttle_tick", "first_velocity_difference_vs_ballistic_tick",
                      "final_velocity_difference_vs_ballistic_mps")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-only", action="store_true")
    args = parser.parse_args()
    main(args.resume_only)
