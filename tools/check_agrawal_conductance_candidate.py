"""Independent numerical check of an isolated conductance hypothesis.

The source figure establishes the direction of a voltage intervention, not
conductance size, reversal potential, or a MaleCNS cell assignment.
"""
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT / "data/reference/agrawal2020/fig2_supp1.jpg"
EXE = ROOT / "build/agrawal_conductance_candidate.exe"
SOURCE = ROOT / "native/agrawal_conductance_candidate.cpp"
REPORT = ROOT / "reports/agrawal_conductance_candidate.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(dt, shift, gmax):
    v, g = -60.0, 0.0
    for _ in range(round(100.0 / dt)):
        decay_m = math.exp(-(1.0 + g) * dt / 10.0)
        steady = (-60.0 + shift) / (1.0 + g)  # E_rev = 0 mV
        v = steady + (v - steady) * decay_m
        decay_s = math.exp(-dt / 5.0)
        g = g * decay_s + gmax * 0.5 * (1.0 - decay_s)
    return v, g


rows = []
for line in subprocess.check_output([str(EXE)], cwd=ROOT, text=True).splitlines():
    dt, shift, on, off, g = map(float, line.split())
    assert dt in (0.2, 0.1, 0.05) and shift in (-5.0, 5.0)
    expected_on, expected_g = reference(dt, shift, 0.02)
    expected_off, _ = reference(dt, shift, 0.0)
    assert abs(on - expected_on) < 2e-12
    assert abs(off - expected_off) < 2e-12
    assert abs(g - expected_g) < 2e-12
    rows.append({"dt_ms": dt, "baseline_shift_mv": shift,
                 "on_mv": on, "off_mv": off, "g_at_100ms": g,
                 "evoked_mv": on - off})
assert len(rows) == 6 and len({(r["dt_ms"], r["baseline_shift_mv"]) for r in rows}) == 6
comparisons = []
for dt in (0.2, 0.1, 0.05):
    hyper = next(r["evoked_mv"] for r in rows if r["dt_ms"] == dt and r["baseline_shift_mv"] == -5)
    depol = next(r["evoked_mv"] for r in rows if r["dt_ms"] == dt and r["baseline_shift_mv"] == 5)
    assert hyper > depol > 0
    comparisons.append({"dt_ms": dt, "hyperpolarized_evoked_mv": hyper,
                        "depolarized_evoked_mv": depol,
                        "depolarized_over_hyperpolarized": depol / hyper})
assert max(r["depolarized_over_hyperpolarized"] for r in comparisons) - min(
    r["depolarized_over_hyperpolarized"] for r in comparisons) < 1e-5
report = {
    "source_figure_url": "https://iiif.elifesciences.org/lax/60299%2Felife-60299-fig2-figsupp1-v2.tif/full/full/0/default.jpg",
    "source_figure_sha256": sha(IMAGE),
    "source_panel": "Figure 2 supplement 1E/F; paired depolarization decreases 13Balpha joint-motion response amplitude",
    "native_source_sha256": sha(SOURCE), "native_exe_sha256": sha(EXE),
    "hypothesis": "A nonnegative excitatory conductance with E_rev=0 mV changes receiver voltage by g*(E_rev-V); steady release is 0.5.",
    "conditional_parameters": {"rest_mv": -60.0, "reversal_mv": 0.0,
                               "gmax_dimensionless": 0.02, "release": 0.5,
                               "membrane_tau_ms": 10.0, "synapse_tau_ms": 5.0},
    "numerical_oracle": "Independent Python recurrence matched six native outputs to <2e-12",
    "comparisons": comparisons,
    "source_qualitative_direction_matched": True,
    "biological_fit": False,
    "male_cns_enabled": False,
    "limitations": ["The panel provides paired response changes but no conductance or reversal calibration.",
                    "Single isolated cell; no source-backed sensory transduction, cell identity, full graph, or alternative electrical-coupling test.",
                    "A qualitative direction match cannot distinguish this mechanism from other voltage-dependent mechanisms."]}
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(comparisons))
