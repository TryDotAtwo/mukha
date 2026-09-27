# Frozen CPU factorial runner

Implementation of approved plan39387c3. This is not permission to submit a
kernel job. Astra4 owns implementation; Astra2 independent numerical review;
Astra3 adversarial review; Astra1 sole Molab transport/operator and integration.

Requires Python3, NumPy, SciPy and the adjacent pinned sample-contract helper.
No network, GPU, stochastic sampling or credentials are used.

```sh
python tools/run_pang_window_factors.py --reference-dir /path/measurement-001 --output-dir /new/path/window-factor-002
python -O -m unittest discover -s tests -p test_pang_window_factors.py -v
```

CLI refuses an existing output directory. It pins the exact plan, reviewed helper,
reference manifest/result and all archived bytes before evaluation. Only the
authenticated reference members are preserved; unrelated input files are not copied.
The new directory contains reference/, code/, plan.json, result.json and manifest.json.
Manifest has run_id and files mapping relative path to bytes/sha256; excludes itself.
Astra1 creates the transport archive and independently hashes/intakes it. There is
no automatic archive or remote-location claim here. Result records runner hash and
runtime versions; exact Git commit is additionally bound by operator receipt.

`evaluate_cube(t,y,peak_time,levels)` is the public synthetic-control API. `levels`
is three H/S time dictionaries in O,E,C order; output is eight cell dictionaries.
`analyze_curve(t,y,row,archived)` derives frozen boundaries, reconciles the two
archived corners and suppresses attribution on closure failure. All sample indices
are zero-based unless named source_frame_zero*. Split H is a continuous time in
the recorded bracket. Original sample steps and median-clock deviation are saved.

Before acceptance, a shared validator requires exactly eight unique known condition
labels and exact equality of every exported start/end/split to its frozen level.
Boundary identity is not tested with area tolerances. The same key validator runs
before `contrasts` and `invariants` build dictionaries; reordered complete cubes
remain valid. Malformed keys or boundary metadata raise typed ValueError; the CLI
retains failed curve records and blocks attribution. These guards address Astra3's
duplicate-collapse and intermediate-boundary fault-injection findings without
changing integrals, level derivation, contrasts or numerical tolerances.

`contrasts(cells)` reports A1/A2/total/Q; signed unscaled finite differences for
O,E,C,OE,OC,EC,OEC. Each includes its H-baseline value, conditional values keyed
by the remaining axes in O,E,C order, and their average. The baseline expansion
includes ALL seven terms; its residual checks endpoint reconstruction. No causal
share or biological uncertainty is estimated.

Numerical domain failures retain eight condition keys for that curve; status and
missing metrics are explicit. Exact-zero area retains areas with null ratio.
Any failed corner, conservation or cell blocks attribution and CLI exits2 after
saving the diagnostic result. Input/provenance failures raise before computation;
unexpected failures may leave a partial directory, which must never be treated
as complete without result AND verified manifest. Never reuse that directory.

Local controls are synthetic only. No experiment001 or actual64-cell run was
performed for author tests. Independent approval of exact commit is required
before Astra1 executes on the eight archived processed means. This analysis
does not close a physiological gate.
