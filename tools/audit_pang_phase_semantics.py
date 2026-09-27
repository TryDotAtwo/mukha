"""Separate net post-crossing area from opposite-polarity area; no model fit.

Run with --fetch once to acquire four small, commit/blob-pinned author MATs.
Subsequent runs are offline. Historical reports are never overwritten.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "7fa5829e37d566e02beaaa87efd6a0f1de4e48c0"
FILES = {
    "L1_highLum.mat": "7c392525939485066bd2488004c495656cfd90a3",
    "L1_lowLum.mat": "e4b75cf1cee86c7c46ddaca3f2a6d427605b28e5",
    "L2_highLum.mat": "745fc159b808f14b7876cdfcdfad12a96ea7473a",
    "L2_lowLum.mat": "1d6cc9f26c015a85c5dfbbce687d4449a79b65fc",
}
AUTHOR_CODE = {
    "compute_bootstrappedMetrics.m": "6d59a6ee4bc0ce6ac39f3e122bb972e19ccb7422",
    "computeFrameZero1.m": "6ec2fd08c4324e36a337f1c6a3f49ebd024d6bd6",
    "computeFrameZero2.m": "5c4edb0ebc108f65b7745382fffd696c301e8324",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_blob(content, expected):
    actual = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    require(actual == expected, "Source Git blob mismatch")


def pieces(t, y):
    """Exact signed integrals of linear segments split at every strict zero."""
    result = []
    for a, b, u, v in zip(t[:-1], t[1:], y[:-1], y[1:]):
        if u * v < 0:
            z = a - u * (b - a) / (v - u)
            result.extend([(a, z, u * (z - a) / 2),
                           (z, b, v * (b - z) / 2)])
        else:
            result.append((a, b, (u + v) * (b - a) / 2))
    return result


def metric(t, y, polarity):
    t, y = np.asarray(t, float), np.asarray(y, float)
    if (t.ndim != 1 or y.ndim != 1 or len(t) != len(y) or len(t) < 2 or polarity not in (-1, 1)
            or not np.isfinite(t).all() or not np.isfinite(y).all()
            or not (np.diff(t) > 0).all()):
        raise ValueError("Expected finite increasing paired samples and polarity +/-1")
    peak = int(np.argmax(polarity * y))
    if polarity * y[peak] <= 0:
        return {"crossing": None}
    crossing = next((i for i in range(peak + 1, len(t))
                     if polarity * y[i] <= 0), None)
    if crossing is None:
        return {"crossing": None}
    a, b = crossing - 1, crossing
    z = float(t[a] - y[a] * (t[b] - t[a]) / (y[b] - y[a]))
    left_t, left_y = np.r_[t[:crossing], z], np.r_[y[:crossing], 0.0]
    right_t, right_y = np.r_[z, t[crossing:]], np.r_[0.0, y[crossing:]]
    # Exact-zero samples can duplicate the boundary; zero-width terms add zero.
    first = sum(p[2] for p in pieces(left_t, left_y))
    tail = pieces(right_t, right_y)
    net = sum(p[2] for p in tail)
    opposite = sum(abs(p[2]) for p in tail if polarity * p[2] < 0)
    returned = sum(abs(p[2]) for p in tail if polarity * p[2] > 0)
    lobe = 0.0
    for _, _, area in tail:
        if polarity * area > 0:
            break
        lobe += abs(area)
    require(math.isclose(polarity * net, returned - opposite, abs_tol=1e-14),
            "Signed tail conservation failed")
    return {"crossing": z, "phase1_signed": float(first), "tail_net_signed": float(net),
            "tail_opposite_absolute": float(opposite), "tail_return_absolute": float(returned),
            "first_opposite_lobe_absolute": float(lobe),
            "legacy_abs_net_ratio": abs(net / first) if first else None,
            "opposite_only_ratio": opposite / abs(first) if first else None}


def controls():
    # Independent hand-integrated triangles: crossings at 2/3 and 4/3.
    t, y = [0., 1., 2.], [2., -1., 2.]
    r = metric(t, y, 1)
    for field, expected in {"phase1_signed": 2/3, "tail_net_signed": 1/3,
                            "tail_opposite_absolute": 1/3,
                            "tail_return_absolute": 2/3}.items():
        require(math.isclose(r[field], expected, abs_tol=1e-14), f"Triangle check: {field}")
    inverted = metric(t, [-v for v in y], -1)
    require(inverted["opposite_only_ratio"] == r["opposite_only_ratio"], "Polarity check")
    refined = metric([0., .5, 1., 1.5, 2.], [2., .5, -1., .5, 2.], 1)
    for field in r:
        require(math.isclose(r[field], refined[field], abs_tol=1e-14), "Subdivision check")
    for response in ([1, 2, 1], [0, 0, 0], [-1, -2, -1]):
        require(metric([0, 1, 2], response, 1)["crossing"] is None, "No-phase check")
    require(metric([0, 1, 2], [1, 0, -1], 1)["crossing"] == 1, "Exact-zero check")
    try:
        verify_blob(b"changed cached bytes", FILES["L1_highLum.mat"])
    except ValueError:
        pass
    else:
        raise ValueError("Corrupt cached blob was accepted")
    return {"analytic_triangle": r, "polarity_inversion": "pass",
            "linear_subdivision": "pass", "no_crossing": "pass",
            "zero_response": "pass", "absent_requested_polarity": "pass",
            "exact_zero_crossing": "pass", "corrupt_cached_blob_rejected": "pass"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    checks = controls()
    source = ROOT / "data/reference/pang_phase_semantics"
    source.mkdir(parents=True, exist_ok=True)
    old_path = ROOT / "reports/pang_author_curve_audit.json"
    old = json.loads(old_path.read_text())
    code_receipts = []
    for name, blob in AUTHOR_CODE.items():
        url = f"https://raw.githubusercontent.com/ClandininLab/L1L2-recurrent-feedback/{COMMIT}/imaging-analysis/HHY_stimulusSpecificAnalysisScripts/{name}"
        path = source / name
        if not path.exists():
            if not args.fetch:
                raise FileNotFoundError(f"{path}: use --fetch for initial acquisition")
            with urlopen(url, timeout=30) as response:
                content = response.read(100_000)
            verify_blob(content, blob)
            path.write_bytes(content)
        content = path.read_bytes()
        verify_blob(content, blob)
        code_receipts.append({"name": name, "url": url, "git_blob": blob,
                              "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})
    rows, receipts = [], []
    for name, blob in FILES.items():
        url = f"https://raw.githubusercontent.com/ClandininLab/L1L2-recurrent-feedback/{COMMIT}/computational-model/data/{name}"
        path = source / name
        if not path.exists():
            if not args.fetch:
                raise FileNotFoundError(f"{path}: use --fetch for initial acquisition")
            with urlopen(url, timeout=30) as response:
                content = response.read(100_000)
            verify_blob(content, blob)
            path.write_bytes(content)
        content = path.read_bytes()
        verify_blob(content, blob)
        receipts.append({"name": name, "url": url, "git_blob": blob,
                         "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})
        data = loadmat(path)
        t = data["t"].ravel()
        y = data["meanResp"]
        require(y.shape == (2, 63) and len(t) == 63, f"Invalid MAT shape: {name}")
        end = int(np.searchsorted(t, t[2] + .25, side="right") - 1)
        for row, polarity in [(0, -1), (1, 1)]:
            r = metric(t[2:end + 1], y[row, 2:end + 1], polarity)
            prior = next(x for x in old["curves"] if x["file"] == name and x["row"] == row)
            for field, old_field in [("phase1_signed", "phase1_area_deltaF_over_F_seconds"),
                                     ("tail_net_signed", "phase2_signed_area_deltaF_over_F_seconds")]:
                require(math.isclose(r[field], prior[old_field], rel_tol=1e-10, abs_tol=1e-14),
                        f"Historical integral mismatch: {name} row {row} {field}")
            r.update(file=name, row=row, label=prior["label"],
                     tail_net_has_first_phase_sign=polarity * r["tail_net_signed"] > 0,
                     analysis_start_s=float(t[2]), analysis_end_s=float(t[end]))
            rows.append(r)
    report = {"source_commit": COMMIT, "sources": receipts, "controls": checks,
              "author_code_sources": code_receipts,
              "author_code_interpretation": {
                  "area2": "signed trapz(frameZero2:endPhase2) * 100 * ifi; cancellation is source behavior",
                  "ratio": "signed area2/area1, without absolute value in compute_bootstrappedMetrics.m",
                  "boundaries": "sample-based frameZero2; derivative-based frameZero1; endPhase2=floor(.25/ifi)",
                  "scope": "Static source inspection, not MATLAB execution or bootstrap reconstruction",
                  "conclusion": "Do not replace author net-tail metric with opposite-only metric; keep sensitivity definitions separate"},
              "historical_report_sha256": hashlib.sha256(old_path.read_bytes()).hexdigest(),
              "executed_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "numpy_version": np.__version__, "rows": rows,
              "claim": "Net post-crossing integral is distinct from opposite-polarity area; historical arithmetic reproduced for eight control curves",
              "limitations": ["Same historical nominal onset/window, not physical flash timing",
                              "New area definitions are a sensitivity audit, not a paper-metric replacement",
                              "No animal-level uncertainty, calibration, model fit or biological gate pass"]}
    out = ROOT / "reports/pang_phase_semantics.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(out), "rows": len(rows),
                      "same_sign_tail": [r["file"] for r in rows if r["tail_net_has_first_phase_sign"]]}))


if __name__ == "__main__":
    main()
