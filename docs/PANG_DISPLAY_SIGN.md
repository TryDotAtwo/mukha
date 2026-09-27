# Author phase-ratio display contract

The pinned author plotting and significance scripts multiply `areaRatio` by
**minus one**, for both dark and light responses. They do not take its absolute
value. This preserves a negative displayed ratio when the signed first area and
net tail have the same sign. The distinction matters for cancellation-sensitive
L1 examples and must be preserved in a faithful source comparison.

At author commit `7fa5829e37d566e02beaaa87efd6a0f1de4e48c0`, under
`imaging-analysis/HHY_stimulusSpecificAnalysisScripts/`:

- `returnMetricSAF.m` extracts each bootstrap element's selected metric/contrast.
- `plot_shortFlash_bootstrappedMetrics_compareGenotypes_L2Project.m` negates
  dark area1, light area2 and both contrasts' areaRatio, then computes means
  and quantiles. Both genotype and light-versus-dark sections follow this rule.
- `computeSignificance_shortFlash_bootstrappedMetrics_L2Project.m` uses the same
  transformation before means/quantiles and its nonoverlapping-CI heuristic.

The three source files have pinned Git blob IDs, SHA-256 and selected source-line
receipts in `reports/pang_display_sign.json`. This is static code inspection,
not execution of MATLAB or reproduction of any specific published figure.

## Executed discriminating controls

Four analytical sign cases preserve positive display ratios for opposite signs
and negative display ratios for equal signs. Invalid/zero denominators fail.
Synthetic raw bootstrap ratios `[-2, 1]` have mean `0.5` after negation and `1.5`
after absolute value, demonstrating that abs cannot replace the source transform
even when aggregating rather than displaying a single ratio.

Applying only this algebra to the **same historical processed-mean areas** gives
L1 highLum light `-0.044968`, whereas the historical absolute ratio is `+0.044968`.
The other seven control examples are positive under the source sign convention.
These illustrations retain historical timing/zero interpolation; they are not
author bootstrap reconstructions and do not repair absent ROI/cohort metadata.

Reproduce with standard-library Python:

```sh
python tools/audit_pang_display_sign.py --fetch
python -O tools/audit_pang_display_sign.py
```

The first command acquires three small immutable code files; subsequent runs are
offline. Source hashes and arithmetic checks remain active under optimization.
No source dataset or original report is overwritten. Gate B remains open. The
next source-faithful comparison must combine the correct sampled boundaries,
signed integrals and **negative signed ratio**, using matched ROI/time inputs;
opposite-only metrics remain explicitly separate sensitivity diagnostics.
