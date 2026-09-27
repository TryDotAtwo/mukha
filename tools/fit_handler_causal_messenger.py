"""Screen two causal event-trace kernels against Handler Fig. 5E means.

This is a model-class test on the six already-inspected wild-type ISIs. It
does not infer receptor concentrations, optical reporter kinetics, or a
MaleCNS synaptic update rule.
"""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/handler2019_fig5_second_messenger.json"
MBON = ROOT / "reports/handler2019_fig2_timing_data.json"
OUT = ROOT / "reports/handler2019_causal_messenger_kernel.json"


def camp_kernel(isi, params):
    """DAN baseline plus interaction at later event from decayed first trace."""
    baseline, gain, tau = params
    return baseline + gain * np.exp(-np.abs(isi) / tau)


def er_kernel(isi, params):
    """At KC, two DAN-driven first-order stages make a delayed gamma trace."""
    baseline, gain, tau = params
    delay = np.maximum(-isi, 0.0)
    shape = np.where(isi < 0, np.e * delay / tau * np.exp(-delay / tau), 0.0)
    return baseline + gain * shape


def fit(fn, x, y, bounds, initial):
    result = least_squares(lambda p: fn(x, p) - y, initial, bounds=bounds,
                           xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=5000)
    assert result.success, (result.status, result.nfev, result.message, result.x)
    return result.x


def inspect(name, fn, x, data, bounds, initial):
    y = data.mean(axis=1)
    params = fit(fn, x, y, bounds, initial)
    predicted = fn(x, params)
    loo = []
    for held_out in range(len(x)):
        mask = np.arange(len(x)) != held_out
        local = fit(fn, x[mask], y[mask], bounds, params)
        loo.append(float(fn(x[held_out:held_out + 1], local)[0]))
    sem = data.std(axis=1, ddof=1) / np.sqrt(data.shape[1])
    return {
        "modality": name,
        "parameter_names": ["reporter_baseline", "event_interaction_gain", "event_trace_tau_s"],
        "fitted_parameters": params.tolist(),
        "observed_means": y.tolist(),
        "observed_sem": sem.tolist(),
        "fitted_means": predicted.tolist(),
        "fit_rmse": float(np.sqrt(np.mean((predicted - y) ** 2))),
        "retrospective_leave_one_isi_out_predictions": loo,
        "retrospective_leave_one_isi_out_mae": float(np.mean(np.abs(np.asarray(loo) - y))),
    }


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = source["conditions"]
    x = np.asarray([row["isi_s"] for row in rows], dtype=np.float64)
    camp = np.asarray([row["raw_camp_per_preparation"] for row in rows])
    release = -np.asarray([row["raw_er_calcium_per_preparation"] for row in rows])
    assert x.tolist() == [-6.0, -1.2, -0.6, 0.0, 0.5, 6.0]
    assert camp.shape == (6, 6) and release.shape == (6, 7)
    analyses = [
        inspect("cAMP_FRET", camp_kernel, x, camp,
                ([0.0, 0.0, 0.05], [0.3, 0.3, 20.0]), [0.07, 0.08, 1.0]),
        inspect("negative_ER_lumen_GCaMP", er_kernel, x, release,
                ([-0.1, 0.0, 0.05], [0.1, 0.3, 20.0]), [-0.005, 0.08, 1.0]),
    ]
    mb = json.loads(MBON.read_text(encoding="utf-8"))
    assert mb["workbook_sha256"] == source["source_workbook_sha256"]
    target = np.asarray([row["mean_delta"] for row in mb["conditions"]])
    camp_parameters = np.asarray(analyses[0]["fitted_parameters"])
    er_parameters = np.asarray(analyses[1]["fitted_parameters"])
    camp_interaction = camp_kernel(x, camp_parameters) - camp_parameters[0]
    er_interaction = er_kernel(x, er_parameters) - er_parameters[0]
    design = np.column_stack((er_interaction, -camp_interaction))
    plasticity_fit = least_squares(lambda p: design @ p - target, [20.0, 10.0],
                                   bounds=(0, np.inf))
    assert plasticity_fit.success
    predicted_mbon = design @ plasticity_fit.x
    # Removing DopR1 leaves only the modeled ER branch. It has no forward
    # interaction by construction, while Fig. 6F reports weak potentiation.
    mutant_predictions = {
        "dop_r1_null_forward_0p5s": float(plasticity_fit.x[0] * er_interaction[4]),
        "dop_r2_null_backward_1p2s": float(-plasticity_fit.x[1] * camp_interaction[1]),
    }
    report = {
        "source_workbook_sha256": source["source_workbook_sha256"],
        "event_time_convention": "ISI = DAN onset minus KC onset; first-event traces decay until the second event.",
        "hypotheses": {
            "cAMP": "A DAN-evoked baseline plus a symmetric coincidence term exp(-abs(ISI)/tau). The coincidence term can be evaluated causally when the second stimulus occurs.",
            "ER_release": "At KC, a two-stage decaying DAN trace yields (delay/tau)*exp(1-delay/tau) if DAN preceded KC; otherwise zero, plus an optical baseline.",
        },
        "analyses": analyses,
        "minimal_two_branch_plasticity_screen": {
            "hypothesis": "At a paired KC contact, delta MBON response = positive ER interaction gain minus positive cAMP coincidence gain; knockout removes its receptor branch, with unchanged other branch and monotonic readout.",
            "fitted_nonnegative_gains_from_six_wild_type_mbon_means": plasticity_fit.x.tolist(),
            "wild_type_observed_mbon_means": target.tolist(),
            "wild_type_predicted_mbon_means": predicted_mbon.tolist(),
            "wild_type_rmse": float(np.sqrt(np.mean((predicted_mbon - target) ** 2))),
            "mutant_predictions": mutant_predictions,
            "mutant_observations": {"dop_r1_null_forward_0p5s": "weak potentiation",
                                    "dop_r2_null_backward_1p2s": "depression"},
            "accept_receptor_null_signs": (
                mutant_predictions["dop_r1_null_forward_0p5s"] > 0
                and mutant_predictions["dop_r2_null_backward_1p2s"] < 0
            ),
            "reason": "The ER interaction kernel is exactly zero for forward pairing, so DopR1-null forward predicts zero instead of the reported weak potentiation.",
        },
        "cross_protocol_challenge": {
            "primary_source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4732734/",
            "source_protocol": "Cohn et al. 2015: 58E02-positive gamma4/gamma5 DAN activation without KC stimulation during induction, with KC-evoked gamma4 MBON responses measured before and after.",
            "source_observation": "DAN activation alone potentiated KC-evoked gamma4 MBON signaling; temporally paired KC/DAN activation depressed it.",
            "candidate_dan_alone_prediction": "zero, because both modeled interaction terms require a KC/DAN pair",
            "candidate_matches_dan_alone": False,
            "transfer_caution": "Different study/protocol and optical/electrophysiological readouts; this is a qualitative cross-protocol challenge, not a numerical pooled fit.",
        },
        "fit_scope": "Six already-inspected wild-type ISI means. Leave-one-ISI-out is retrospective model diagnosis, not independent validation. No timecourse, receptor-null or contact-level fit.",
        "plasticity_enabled": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in analyses:
        print(item["modality"], "params", item["fitted_parameters"],
              "RMSE", item["fit_rmse"], "LOO_MAE", item["retrospective_leave_one_isi_out_mae"])
        print("observed", item["observed_means"])
        print("predicted", item["fitted_means"])
    screen = report["minimal_two_branch_plasticity_screen"]
    print("MBON RMSE", screen["wild_type_rmse"], "DopR1-null forward",
          screen["mutant_predictions"]["dop_r1_null_forward_0p5s"], "rejected")


if __name__ == "__main__":
    main()
