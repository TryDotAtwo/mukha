"""Remote GPU regression for conductance failure semantics; run only in MoLab."""
import argparse
import ctypes as C
import json
import math
import struct
from pathlib import Path

class Params(C.Structure):
    _fields_ = [(k, C.c_double) for k in (
        "dt_ms", "rest_mv", "reset_mv", "threshold_mv", "membrane_ms",
        "synapse_ms", "reversal_exc_mv", "reversal_inh_mv"
    )] + [("refractory_ticks", C.c_uint32), ("delay_ticks", C.c_uint32)]

def load(path):
    lib = C.CDLL(str(Path(path).resolve()))
    lib.fc_create.argtypes = [C.c_uint32, C.c_uint64, C.POINTER(C.c_uint64),
        C.POINTER(C.c_uint32), C.POINTER(C.c_double), C.POINTER(C.c_double),
        C.POINTER(C.c_uint8), Params, C.c_uint32]
    lib.fc_create.restype = C.c_void_p
    lib.fc_advance.argtypes = [C.c_void_p, C.c_uint32, C.POINTER(C.c_double),
        C.POINTER(C.c_double), C.POINTER(C.c_double), C.POINTER(C.c_double),
        C.POINTER(C.c_uint8)]
    lib.fc_advance.restype = C.c_int
    lib.fc_reset.argtypes = [C.c_void_p]
    lib.fc_reset.restype = C.c_int
    lib.fc_destroy.argtypes = [C.c_void_p]
    lib.fc_error.restype = C.c_char_p
    return lib

def create(lib, kind):
    if kind == "conductance":
        n, row, col, we = 3, [0, 0, 0, 2], [0, 1], [1e308, 1e308]
        p = Params(.1, -65., -65., -50., 20., 5., 0., -70., 0, 1)
    elif kind == "direct":
        n, row, col, we = 1, [0, 0], [], []
        p = Params(.1, 0., 0., float.fromhex("0x1.fffffffffffffp+1023"),
                   20., 5., 0., -70., 0, 1)
    else:
        n, row, col, we = 2, [0, 0, 1], [0], [.01]
        p = Params(.1, -65., -65., -50., 20., 5., 0., -70., 2, 1)
    handle = lib.fc_create(n, len(col), (C.c_uint64 * len(row))(*row),
        (C.c_uint32 * len(col))(*col), (C.c_double * len(we))(*we),
        (C.c_double * len(we))(*([0.] * len(we))), (C.c_uint8 * n)(),
        p, 8)
    if not handle:
        raise RuntimeError(lib.fc_error().decode())
    return handle, n

def advance(lib, handle, n, drive):
    assert len(drive) % n == 0
    size = len(drive)
    outputs = [(C.c_double * size)(*([-12345.] * size)) for _ in range(3)]
    spikes = (C.c_uint8 * size)(*([237] * size))
    rc = lib.fc_advance(handle, size // n, (C.c_double * size)(*drive),
                       *outputs, spikes)
    error = lib.fc_error().decode()
    values = [list(a) for a in outputs] + [list(spikes)]
    return rc, error, values

def unchanged(values):
    return all(x == -12345. for seq in values[:3] for x in seq) and all(
        x == 237 for x in values[3])

def finite(values):
    return all(math.isfinite(x) for seq in values[:3] for x in seq)

def fingerprint(values):
    return b"".join(struct.pack("<d", x) for seq in values[:3] for x in seq) + bytes(values[3])

def overflow(lib, kind, enforce):
    handle, n = create(lib, kind)
    try:
        drive = [1e308, 1e308] if kind == "direct" else [100., 100., 0.] + [0.] * 6
        rc, error, values = advance(lib, handle, n, drive)
        record = {"case": kind, "status": rc, "error": error,
                  "all_outputs_finite": finite(values),
                  "outputs_untouched": unchanged(values)}
        if enforce:
            assert rc != 0 and "nonfinite neural state" in error, record
            assert unchanged(values), record
            rc2, error2, values2 = advance(lib, handle, n, [0.] * n)
            assert rc2 != 0 and "reset required" in error2 and unchanged(values2)
            assert lib.fc_reset(handle) == 0
            rc3, _, values3 = advance(lib, handle, n, [0.] * (4*n))
            assert rc3 == 0 and finite(values3)
            record.update(retry_rejected=True, explicit_reset_recovers=True)
        else:
            assert rc == 0 and not finite(values), "Baseline did not reproduce the defect"
        return record
    finally:
        lib.fc_destroy(handle)

def ordinary(lib):
    handle, n = create(lib, "ordinary")
    try:
        seq = [20., 0.] + [0.] * 6 + [20., 0.] + [0.] * 6
        rc, error, values = advance(lib, handle, n, seq)
        assert rc == 0 and finite(values), error
        assert sum(values[3]) > 0
        return values
    finally:
        lib.fc_destroy(handle)

def bad_input(lib):
    handle, n = create(lib, "ordinary")
    try:
        rc, error, values = advance(lib, handle, n, [float("nan"), 0.])
        assert rc != 0 and "nonfinite direct drive" in error and unchanged(values)
        rc, _, values = advance(lib, handle, n, [0., 0.])
        assert rc == 0 and finite(values)
        return {"case": "input_rejected_before_mutation", "passed": True}
    finally:
        lib.fc_destroy(handle)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    candidate, baseline = load(args.library), load(args.baseline)
    report = {"scope": "Tiny conductance GPU arithmetic failure contract; no full-graph physiology, checkpoint or performance claim",
              "baseline": [overflow(baseline, k, False) for k in ("direct", "conductance")],
              "candidate": [overflow(candidate, k, True) for k in ("direct", "conductance")]}
    report["candidate"].append(bad_input(candidate))
    assert fingerprint(ordinary(candidate)) == fingerprint(ordinary(baseline))
    report["ordinary_same_device_bit_exact"] = True
    report["passed"] = True
    Path(args.report).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, allow_nan=False), flush=True)

if __name__ == "__main__":
    main()
