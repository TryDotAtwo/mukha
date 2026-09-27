"""Check the SI/mm cabin-frame acceleration contract of the native rocket ABI."""
import ctypes
import hashlib
import json

from flymimic_public_model import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    dll = ROOT / "build/rocket_vertical_abi.dll"
    lib = ctypes.CDLL(str(dll))
    lib.rocket_new.restype = ctypes.c_void_p
    lib.rocket_delete.argtypes = [ctypes.c_void_p]
    lib.rocket_current_state.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double)]
    lib.rocket_current_state.restype = ctypes.c_int
    lib.rocket_world_gravity.argtypes = [ctypes.c_void_p]
    lib.rocket_world_gravity.restype = ctypes.c_double
    lib.rocket_effective_g.argtypes = [ctypes.c_void_p]
    lib.rocket_effective_g.restype = ctypes.c_double
    lib.rocket_advance.argtypes = [ctypes.c_void_p, ctypes.c_double,
                                   ctypes.c_double, ctypes.POINTER(ctypes.c_double)]
    lib.rocket_advance.restype = ctypes.c_int
    results = []
    for q_mm in (0., .09, .3):
        handle = lib.rocket_new()
        assert handle
        state = (ctypes.c_double * 5)()
        try:
            for tick in range(100):
                assert lib.rocket_current_state(handle, state)
                t, altitude, velocity, fuel, thrust = tuple(state)
                g = lib.rocket_world_gravity(handle)
                effective = lib.rocket_effective_g(handle)
                expected = -1000. * thrust / (1000. + fuel)
                assert abs(effective - expected) < 1e-12
                assert abs(g + 6.5e10 / (200000. + altitude)**2) < 1e-12
                assert abs(t - tick * .0001) < 1e-12
                assert lib.rocket_advance(handle, q_mm, .0001, state)
            results.append({"q_mm": q_mm, "final_time_s": state[0],
                            "final_altitude_m": state[1],
                            "final_thrust_N": state[4],
                            "final_effective_g_mm_s2": lib.rocket_effective_g(handle)})
        finally:
            lib.rocket_delete(handle)
    assert results[0]["final_effective_g_mm_s2"] == 0.
    assert results[1]["final_effective_g_mm_s2"] < 0.
    assert results[2]["final_effective_g_mm_s2"] < results[1]["final_effective_g_mm_s2"]
    report = {"cases": results, "checks": "100 ticks each; SI/mm conversion, radial gravity, time sync, thrust ordering",
              "abi_sha256": sha(dll),
              "executed_source_sha256": sha(ROOT / "tools/check_rocket_cabin_frame.py"),
              "scope": "ABI arithmetic and timing only; does not validate MuJoCo body contacts or KSP."}
    path = ROOT / "reports/rocket_cabin_frame_check.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
