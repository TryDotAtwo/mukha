"""Screen a DAN-tonic plus two timed local plasticity hypothesis.

Only three nonnegative amplitudes are fitted to six already-seen WT means.
Time constants come from the separate published second-messenger recordings.
This is a model-class rejection/retention test, not a MaleCNS learning rule.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parents[1]
MBON = ROOT / "reports/handler2019_fig2_timing_data.json"
MESSENGER = ROOT / "reports/handler2019_causal_messenger_kernel.json"
WORKBOOK = ROOT / "data/reference/handler2019/Handler2019_Fig2Fig5_Data.xlsx"
OUT = ROOT / "reports/handler2019_tonic_two_pathway_screen.json"

mbon = json.loads(MBON.read_text(encoding="utf-8"))
second = json.loads(MESSENGER.read_text(encoding="utf-8"))
workbook_sha = hashlib.sha256(WORKBOOK.read_bytes()).hexdigest()
assert workbook_sha == mbon["workbook_sha256"] == second["source_workbook_sha256"]
x = np.asarray([c["isi_s"] for c in mbon["conditions"]], np.float64)
y = np.asarray([c["mean_delta"] for c in mbon["conditions"]], np.float64)
sem = np.asarray([c["sem_delta"] for c in mbon["conditions"]], np.float64)
assert x.tolist() == [-6.0, -1.2, -0.6, 0.0, 0.5, 6.0]
assert np.all(sem > 0)
tau_d = float(second["analyses"][0]["fitted_parameters"][2])
tau_p = float(second["analyses"][1]["fitted_parameters"][2])


def design(times, potentiation_tau=tau_p, depression_tau=tau_d):
    delay = np.maximum(-times, 0.0)
    er_shape = np.where(times < 0, np.e * delay / potentiation_tau *
                        np.exp(-delay / potentiation_tau), 0.0)
    camp_shape = np.exp(-np.abs(times) / depression_tau)
    return np.column_stack((np.ones(len(times)), er_shape, -camp_shape))


def fit(matrix, target, scale=None):
    if scale is None:
        scale = np.ones(len(target))
    coefficients, _ = nnls(matrix / scale[:, None], target / scale)
    return coefficients


A = design(x)
coeff = fit(A, y)
prediction = A @ coeff
weighted = fit(A, y, sem)
weighted_prediction = A @ weighted
loo = []
for holdout in range(len(x)):
    keep = np.arange(len(x)) != holdout
    local = fit(A[keep], y[keep])
    loo.append({"held_out_isi_s": float(x[holdout]),
                "prediction": float(A[holdout] @ local),
                "observed": float(y[holdout]),
                "tonic_dan_only_coefficient": float(local[0])})

# Exact constraint signs from the primary Handler Figure 6 text and the
# cross-protocol Cohn gamma4 DAN-only induction. These are not fitted targets.
mutants = {
    "dop_r1_null_forward_0p5s": float(coeff[0]),
    "dop_r2_null_backward_1p2s": float(-coeff[2] * np.exp(-1.2 / tau_d)),
    "dan_only_induction": float(coeff[0]),
}
tau_sensitivity = []
for candidate_p in np.geomspace(0.3, 3.0, 20):
    for candidate_d in np.geomspace(0.3, 3.0, 20):
        trial_a = design(x, candidate_p, candidate_d)
        trial_coeff = fit(trial_a, y)
        trial_pred = trial_a @ trial_coeff
        tau_sensitivity.append({"tau_p_s": float(candidate_p), "tau_d_s": float(candidate_d),
                                "rmse": float(np.sqrt(np.mean((trial_pred-y)**2))),
                                "tonic_coefficient": float(trial_coeff[0])})
best_retrospective = min(tau_sensitivity, key=lambda row: row["rmse"])
report = {
    "source_workbook_sha256": workbook_sha,
    "secondary_analysis_hashes": {
        "handler2019_fig2_timing_data.json": hashlib.sha256(MBON.read_bytes()).hexdigest(),
        "handler2019_causal_messenger_kernel.json": hashlib.sha256(MESSENGER.read_bytes()).hexdigest()},
    "hypothesis": "delta response = tonic DopR2-like DAN term + delayed DopR2-like KC-after-DAN term - DopR1-like KC/DAN coincidence term",
    "model_class_assumptions": [
        "DAN-only potentiation is assigned provisionally to the positive tonic branch; Cohn 2015 did not establish receptor identity for this term.",
        "Deleting a receptor deletes its entire associated branch without compensation.",
        "MBON calcium-response change is a monotone proxy for synaptic efficacy change; this transfer is unverified."],
    "time_constants_from_prior_second_messenger_screen_s": {
        "potentiation_er_like": tau_p, "depression_camp_like": tau_d},
    "isi_s": x.tolist(), "observed_mean_delta": y.tolist(),
    "observed_sem": sem.tolist(),
    "unweighted_nonnegative_coefficients": coeff.tolist(),
    "unweighted_predictions": prediction.tolist(),
    "unweighted_rmse": float(np.sqrt(np.mean((prediction - y) ** 2))),
    "sem_weighted_nonnegative_coefficients": weighted.tolist(),
    "sem_weighted_predictions": weighted_prediction.tolist(),
    "leave_one_isi_out_retrospective": loo,
    "leave_one_isi_out_mae": float(np.mean([abs(t["prediction"] - t["observed"]) for t in loo])),
    "unweighted_residual_in_sem": ((prediction - y) / sem).tolist(),
    "fixed_tau_key_mismatches_over_2_sem": [float(x[i]) for i in range(len(x))
                                             if abs((prediction[i] - y[i]) / sem[i]) > 2],
    "tonic_term_robust_to_sem_weighting_and_loo": bool(weighted[0] > 0 and all(
        entry["tonic_dan_only_coefficient"] > 0 for entry in loo)),
    "retrospective_free_tau_grid": {"range_s": [0.3, 3.0], "points_per_axis": 20,
                                    "best": best_retrospective,
                                    "interpretation": "A descriptive 400-combination search on the same six WT means; not an independently selected model or source-derived time constants."},
    "qualitative_intervention_predictions": mutants,
    "qualitative_sign_status": "Structural sign consistency only: nonnegative fitted branches and receptor deletion force these signs whenever the tonic coefficient is positive; no independent knockout or DAN-only amplitudes were fitted or predicted robustly.",
    "primary_source_signs": {"dop_r1_null_forward_0p5s": "positive (weak)",
                             "dop_r2_null_backward_1p2s": "negative",
                             "dan_only_induction": "positive in Cohn 2015 gamma4 protocol"},
    "biological_validation": False,
    "plasticity_enabled": False,
    "limitations": ["The six wild-type intervals were already inspected; leave-one-ISI-out is retrospective diagnosis, not held-out validation.",
                    "The second-messenger time constants themselves have unstable ER leave-one-ISI-out behavior.",
                    "No Figure 6 receptor-null preparation-level values or Cohn quantitative records enter the fit.",
                    "Even matching all signs would not establish a molecular local rule or MaleCNS contact-level transfer."]}
OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"coefficients": coeff.tolist(), "predicted": prediction.tolist(),
                  "residual_in_sem": report["unweighted_residual_in_sem"],
                  "loo_mae": report["leave_one_isi_out_mae"],
                  "intervention_predictions": mutants}))
