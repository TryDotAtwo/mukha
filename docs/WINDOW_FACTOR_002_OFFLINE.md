# Reproduce or review the recorded window-factor-002

One CPU foreground Molab run completed after explicit Astra2 numerical and
Astra3 defensive approvals of f61ef73c869a0d54170b3e4212c1a5605dc4af4b.
It is measurement-convention attribution, not biological gate closure.
The original measurement001 was not repeated.

Recorded archive SHA256:
af79f4143614bb275c84605b8627b4faf28301cad61aad4d8f4c20425c8cd444
(40875 bytes;17 manifested files plus manifest.json).
The artifact contains original reference bytes, plan, code and64 result records.
Operator receipt separately binds location/transport, exact commit and exit0.
Integrity checks do not establish execution location by themselves.

## Restore reviewed source

The new update bundle requires the previously delivered full469400f bundle.
Place both bundles in the same directory and run:

```sh
git clone -b astra1/reviewed-integration mukha-reviewed-469400f.bundle repeat-repo
git -C repeat-repo bundle verify ../mukha-window-factor-update.bundle
git -C repeat-repo fetch ../mukha-window-factor-update.bundle refs/heads/astra1/molab-measurement-prep:refs/heads/window-factor-reviewed
git -C repeat-repo switch window-factor-reviewed
```

## Check the delivered result without repeating the experiment

From the delivery directory after restoring the repository:

```sh
sha256sum -c SHA256SUMS
python -O repeat-repo/tools/check_pang_factor_result.py window-factor-002.tar.gz
PANG_FACTOR_ARCHIVE=window-factor-002.tar.gz python -O -m unittest discover -s repeat-repo/tests -p test_pang_factor_result_checker.py
tar -xzf window-factor-002.tar.gz
```

The checker requires the exact recorded archive digest and independently
reconstructs2152 numerical comparisons without importing the production runner
or boundary helper. Eight decoded-result corruption controls must reject.
Astra2 has approved the actual numbers; Astra3 independently approved the
archive/provenance/structure and all192 frozen-boundary copies. Their reports
are in reports/ and the transfer delivery. Neither claims independent live
kernel observation or biological validation.

## Optional independent LOCAL reproduction of the new experiment

This section launches the NEW factor analysis locally, not experiment001 and not
a Molab/GPU job. It is supplied for the user's independent reproduction, not
automatically executed by the operator during packaging.
Use a trusted verified extraction of window-factor-002.tar.gz. In an environment
with Python, NumPy and SciPy already installed (recorded remote versions:
Python3.13.11, NumPy2.4.6, SciPy1.18.0), from the directory containing the extracted
window-factor-002 and repeat-repo:

```sh
python -O repeat-repo/tools/run_pang_window_factors.py --reference-dir window-factor-002/reference --output-dir offline-window-factor-002
```

The output directory must NOT exist. Input/helper/plan digests are verified
before evaluation. Exit0 means internal acceptance; exit2 preserves an
attribution-blocked diagnostic. Neither is independent review. Do not silently
change tolerances or retry into an existing directory. Results contain runtime
versions and run IDs, so compare scientific fields, not whole-file byte identity.

The archived code can alternatively be restored without Git: copy code/*.py
to a fresh source/tools directory and plan.json to
source/configs/pang_window_factor_plan.json, then use that runner with the same
reference directory. Code files must retain their archived digests.

## Meaning and limits

O=start, E=end, C=phase split are frozen once per processed curve; only their
H/S selections vary. All64 cells and both archived corners passed the runner's
frozen tests. Signed Q=-A2/A1 and all seven interaction terms are preserved.
Do not interpret the three baseline main effects as a complete additive causal
explanation: pair/triple interactions must also be included. No64 animal trials,
ROI uncertainty or biological model validation is implied. Post-run independent
review is tracked separately in the operator receipt and peer result reports.
