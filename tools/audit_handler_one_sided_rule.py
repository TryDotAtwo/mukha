"""Falsification probe for a simple KC/DAN timing rule, not a CNS trainer.

Handler et al., Cell 2019, DOI 10.1016/j.cell.2019.05.040, Fig. 6.
Signs refer to MBON evoked calcium responses. Mapping weight to response is
explicitly assumed monotonic for this probe.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/malecns_handler_one_sided_rule.json"


def run_events(events, tau, dop_r1=True, dop_r2=True, learning=True):
    """Run an explicit stimulus sequence with reset traces and unit amplitudes."""
    events = sorted(events)
    last_kc = last_dan = None
    delta = 0.0
    for time, kind in events:
        if kind == "kc":
            if learning and dop_r2 and last_dan is not None:
                delta += math.exp(-(time - last_dan) / tau)
            last_kc = time
        else:
            if learning and dop_r1 and last_kc is not None:
                delta -= math.exp(-(time - last_kc) / tau)
            last_dan = time
    return delta


def run(isi, tau, dop_r1=True, dop_r2=True, learning=True):
    """ISI = DAN time minus KC time; positive means forward pairing."""
    return run_events([(0.0, "kc"), (isi, "dan")], tau, dop_r1, dop_r2, learning)


def sign(value):
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def main():
    taus = [0.1, 0.5, 1.0, 3.0, 10.0]
    conditions = {
        "wild_type_forward_0p5s": (0.5, True, True, "negative"),
        "wild_type_backward_1p2s": (-1.2, True, True, "positive"),
        "dop_r1_null_forward_0p5s": (0.5, False, True, "positive"),
        "dop_r2_null_backward_1p2s": (-1.2, True, False, "negative"),
    }
    rows = []
    for tau in taus:
        for name, (isi, r1, r2, observed) in conditions.items():
            prediction = sign(run(isi, tau, r1, r2))
            rows.append({"tau_s": tau, "condition": name, "observed_sign": observed,
                         "predicted_sign": prediction, "matches": prediction == observed})
    controls = {
        "learning_disabled_forward": run(0.5, 1.0, learning=False) == 0,
        "learning_disabled_backward": run(-1.2, 1.0, learning=False) == 0,
        "unpaired_kc": run_events([(0.0, "kc")], 1.0) == 0,
        "model_unpaired_dan_predicts_zero": run_events([(0.0, "dan")], 1.0) == 0,
    }
    # Under an additional additive, unchanged-readout assumption, the four
    # observed signs require both receptor branches at both timing orders.
    # These values are a satisfiability witness, not fitted biological rates.
    opposing_branch_witness = {
        "forward_r1": -2.0, "forward_r2": 1.0,
        "backward_r1": -1.0, "backward_r2": 2.0,
    }
    w = opposing_branch_witness
    witness_signs = {
        "wild_type_forward": sign(w["forward_r1"] + w["forward_r2"]),
        "dop_r1_null_forward": sign(w["forward_r2"]),
        "wild_type_backward": sign(w["backward_r1"] + w["backward_r2"]),
        "dop_r2_null_backward": sign(w["backward_r1"]),
    }
    report = {
        "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9012144/",
        "hypothesis": "KC then DAN: DopR1-dependent depression; DAN then KC: DopR2-dependent potentiation, with exponentially decaying eligibility; positive rates and time constants.",
        "readout_assumption": "MBON calcium-response change has the same sign as the local KC-to-MBON efficacy change.",
        "parameter_scope": "Positive amplitudes do not change signs; the sampled positive time constants verify timing calculations. Knockout mismatches hold for every positive time constant.",
        "rows": rows,
        "controls": controls,
        "cross_protocol_dan_alone_challenge": {
            "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4732734/",
            "observation": "Cohn et al. 2015 gamma4/gamma5 DAN activation without KC during induction potentiated later KC-evoked gamma4 MBON response.",
            "model_prediction": "zero",
            "matches": False,
            "scope": "Qualitative separate-study control, not a numerical fit to Handler conditions.",
        },
        "conditional_additive_constraints": {
            "assumption": "Receptor deletion removes only that branch, with unchanged other branch and monotonic readout.",
            "forward": "DopR1 contribution < -DopR2 contribution < 0",
            "backward": "DopR2 contribution > -DopR1 contribution > 0",
            "example_witness_not_fit": opposing_branch_witness,
            "witness_signs": witness_signs,
        },
        "accepts_all_constraints": all(row["matches"] for row in rows),
        "conclusion": "Reject this one-sided rule under its readout assumption; do not enable it in the MaleCNS graph.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{sum(r['matches'] for r in rows)}/{len(rows)} biological sign checks match; {report['conclusion']}")
    assert all(controls.values())
    assert witness_signs == {
        "wild_type_forward": "negative", "dop_r1_null_forward": "positive",
        "wild_type_backward": "positive", "dop_r2_null_backward": "negative",
    }
    assert not report["accepts_all_constraints"]


if __name__ == "__main__":
    main()
