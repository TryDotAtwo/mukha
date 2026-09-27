# static-control-004: one local exploratory comparison, model sweep stopped

Approved implementation5c826fe209170800619ccbf4d1829996d5f8610c; frozen
protocol704843a. Exact numerical approval Astra2 (evidence0d31749,8 analytic
cases) and protective approval Astra3 (message38,52 checks) preceded execution.

ONE actual calculation completed LOCAL synchronous foreground CPU, exit0,
Python3.12.11/NumPy2.5.3/SciPy1.18.1. No Molab retry or GPU. Initial invocation
with default Python failed at import numpy, before source data reading/fitting;
its failure receipt is preserved separately. Existing temporal003 interpreter
was then explicitly selected with unchanged code/config and no installation.
This was two process invocations, only one reached computation; no claim of
an error-free first invocation. See both reports/static_control_004*receipt.json.

## Complete preliminary result (independent actual-result reviews pending)

Es is original-grid trapezoid SSE divided by the curve's CONTROL energy.
Positive delta means the static model has lower error than the baseline.

| Cell / level / polarity | Es | E0-Es | E1-Es | vs both baselines |
| --- | ---: | ---: | ---: | --- |
| L1 high light | 1.16597867 | -1.03424664 | -1.07395676 | worse |
| L1 low dark | 0.38787397 | -0.02421117 | -0.05163279 | worse |
| L1 low light | 0.14815747 | +0.09712523 | +0.06123586 | improved |
| L2 high light | 2.58478170 | -2.32264671 | -2.26293191 | worse |
| L2 low dark | 0.80191273 | -0.06199404 | -0.11825693 | worse |
| L2 low light | 0.56706193 | -0.09522015 | -0.10309775 | worse |

Both training matrices have rank2 and select interior Hs:
L1 a=1.1882771096355287,d=-0.3432241025551631,s=0.02414729423762053;
L2 a=2.0457373543123065,d=-1.0498773778529324,s=0.027376522769934214.
Training errors0.116620581855538 and0.28153372456268977 do not establish
transfer superiority. Full candidates/parameters/arrays are in result.json.

Signed/magnitude out-of-training time fractions respectively are
0.048387/0.048387,0/0,0.032258/0.032258,0.064516/0.032258,0/0,
0.048387/0.016129 in table order. Maximum |c|/s_train ratios are
2.29046,0.79603,1.41651,1.65166,0.95705,1.36709. Full precision ranges and
fractions are preserved. These are diagnostics, not exclusion/refitting rules.

Thus neither restricted model uniformly dominates the other on all six reused
means. This cubic does not rescue the earlier failed transfer and its failure
does not reject all static maps or establish memory necessity. Stronger neural,
indicator, causal, animal-generalization and calibration claims remain open.
Original temporal003 all_six_improved=false is unchanged; static all-six versus
H1 is separately false. No new model classes, degree/search/split changes or
residual-selected fits follow this result: the frozen model-sweep stop rule is
now active. Independent arithmetic/provenance review is still required.

## Artifact and offline inspection

reports/recorded_runs/static-control-004.tar.gz:396953 bytes,
SHA25641cb1b831f81248fe3d591d68842147b2e5f1983a416cbd149ad0ac92d07ed4d.
Manifest binds6 files plus itself, including original baseline archive, two
scripts, protocol, configuration and complete result. Nested baseline contains
the exact eight original MATs and immutable H0/H1 predictions; no download or
private access is needed. Result SHA256:
2b53849cc007872d60ea145db72051822df8ec7204326f2a96cd396b8fad0dab.

Inspect without fitting:

```sh
sha256sum reports/recorded_runs/static-control-004.tar.gz
tar -tzf reports/recorded_runs/static-control-004.tar.gz
tar -xOzf reports/recorded_runs/static-control-004.tar.gz static-control-004/result.json
tar -xOzf reports/recorded_runs/static-control-004.tar.gz static-control-004/manifest.json
```

Independent arithmetic, provenance and interpretation reviews requested in
Astra1 message53. Prelaunch synthetic approvals are not post-run approvals.
