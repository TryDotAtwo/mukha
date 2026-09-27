"""Independent panorama oracle for body-local ray rotation in native sampler."""
import ctypes as ct
import hashlib
import json

import numpy as np

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT / "build/retina.dll"
REPORT = ROOT / "reports/retina_orientation.json"


def oracle(image, rays, matrix):
    height, width, _ = image.shape
    result = []
    for x, y, z in rays @ matrix.T:
        u = (np.arctan2(y, x) / (2 * np.pi) + .5) * width - .5
        v = (.5 - np.arctan2(z, np.hypot(x, y)) / np.pi) * height - .5
        x0 = int(np.floor(u))
        dx = u - x0
        v = np.clip(v, 0., height - 1.)
        y0 = int(np.floor(v))
        y1 = min(y0 + 1, height - 1)
        dy = v - y0
        left, right = x0 % width, (x0 + 1) % width
        result.append(((1-dx)*(1-dy)*image[y0, left] + dx*(1-dy)*image[y0, right]
                       + (1-dx)*dy*image[y1, left] + dx*dy*image[y1, right]))
    return np.asarray(result, dtype=np.float32)


def main():
    rng = np.random.default_rng(9215)
    rays = rng.normal(size=(80, 3))
    rays /= np.linalg.norm(rays, axis=1)[:, None]
    rays = np.ascontiguousarray(rays, dtype=np.float64)
    image = rng.uniform(0., 10., size=(19, 37, 3)).astype(np.float32)
    lib = ct.CDLL(str(DLL))
    lib.fv_create.argtypes = [ct.POINTER(ct.c_double), ct.c_size_t, ct.c_uint32, ct.c_uint32]
    lib.fv_create.restype = ct.c_void_p
    lib.fv_destroy.argtypes = [ct.c_void_p]
    lib.fv_sample.argtypes = [ct.c_void_p, ct.POINTER(ct.c_float), ct.c_size_t,
                              ct.POINTER(ct.c_float), ct.c_size_t]
    lib.fv_sample_oriented.argtypes = [ct.c_void_p, ct.POINTER(ct.c_float), ct.c_size_t,
                                       ct.POINTER(ct.c_double), ct.POINTER(ct.c_float), ct.c_size_t]
    handle = lib.fv_create(rays.ctypes.data_as(ct.POINTER(ct.c_double)), len(rays), image.shape[1], image.shape[0])
    assert handle
    try:
        output = np.full((len(rays), 3), -17., dtype=np.float32)
        image_ptr = image.ctypes.data_as(ct.POINTER(ct.c_float))
        output_ptr = output.ctypes.data_as(ct.POINTER(ct.c_float))
        matrices = {
            "identity": np.eye(3),
            "yaw_90": np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]]),
            "pitch_45": np.array([[2**-.5, 0., 2**-.5], [0., 1., 0.], [-2**-.5, 0., 2**-.5]]),
        }
        errors = {}
        for label, mat in matrices.items():
            mat = np.ascontiguousarray(mat, dtype=np.float64)
            status = lib.fv_sample_oriented(handle, image_ptr, image.size,
                                            mat.ctypes.data_as(ct.POINTER(ct.c_double)),
                                            output_ptr, output.size)
            assert status == 0
            expected = oracle(image, rays, mat)
            errors[label] = float(np.max(np.abs(output - expected)))
            assert errors[label] < 2e-6
        static = np.empty_like(output)
        assert lib.fv_sample(handle, image_ptr, image.size,
                             static.ctypes.data_as(ct.POINTER(ct.c_float)), static.size) == 0
        ident = np.ascontiguousarray(matrices["identity"])
        assert lib.fv_sample_oriented(handle, image_ptr, image.size,
                                      ident.ctypes.data_as(ct.POINTER(ct.c_double)),
                                      output_ptr, output.size) == 0
        assert np.array_equal(static, output)
        invalid = np.diag([-1., 1., 1.]).astype(np.float64)
        output.fill(-17.)
        assert lib.fv_sample_oriented(handle, image_ptr, image.size,
                                      invalid.ctypes.data_as(ct.POINTER(ct.c_double)),
                                      output_ptr, output.size) == 4
        assert np.all(output == -17.)
        report = {"rays": len(rays), "panorama_width": image.shape[1],
                  "panorama_height": image.shape[0], "seed": 9215,
                  "oracle_max_absolute_error_by_rotation": errors,
                  "identity_exactly_matches_static_sampler": True,
                  "reflection_rejected_without_output_mutation": True,
                  "dll_sha256": hashlib.sha256(DLL.read_bytes()).hexdigest(),
                  "source_sha256": hashlib.sha256((ROOT / "native/retina.cpp").read_bytes()).hexdigest(),
                  "scope": "Dynamic body-local to panorama ray rotation only; no MaleCNS cell mapping, calibrated optics or receptor-to-CNS coupling."}
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        lib.fv_destroy(handle)


if __name__ == "__main__":
    main()
