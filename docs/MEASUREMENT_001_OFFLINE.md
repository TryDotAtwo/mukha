# Independent offline verification of measurement-001

The measurement ran once. Verification below only reads the retrieved archive;
it does not repeat the experiment, connect to Molab, or start GPU work.

The transfer update is an **incremental** Git bundle. It requires the previously
delivered complete `mukha-reviewed-469400f.bundle` (SHA256
`fe5b28c433acf1332967ac968bb4bd26b57bef431dbcb7d525b6251bafb62a70`).
Do not treat the update alone as a standalone repository.

Place the base bundle beside the unpacked transfer files. In an environment with
Git, Python, NumPy >=2.0 and SciPy already installed, run from that directory:

```sh
sha256sum -c SHA256SUMS
git clone mukha-reviewed-469400f.bundle repeat-repo
git -C repeat-repo bundle verify ../mukha-measurement-update.bundle
git -C repeat-repo fetch ../mukha-measurement-update.bundle refs/heads/astra1/molab-measurement-prep:refs/heads/measurement-reviewed
git -C repeat-repo switch measurement-reviewed
python -O repeat-repo/tools/review_astra3_measurement_archive.py --archive measurement-001.tar.gz --repo repeat-repo --output archive-review.json
tar -xzf measurement-001.tar.gz
python -O repeat-repo/tools/check_pang_measurement_result.py measurement-001
python -O repeat-repo/tools/review_astra3_measurement_contract.py --checker-tools repeat-repo/tools --run-dir measurement-001 --output contract-review.json
python -O -m unittest discover -s repeat-repo/tests -p test_pang_result_contract.py
```

Archive audit precedes extraction and checks pinned digest, safe paths, exact
12-file manifest, byte counts, source blobs and archived code commit. Expected:
8 numeric rows; 24 corrupt contracts rejected and 2 positive controls accepted;
4 targeted unittest methods pass. Remote environment was Python 3.13.11,
NumPy 2.4.6, SciPy 1.18.0; these versions are recorded, not silently installed.
No network or extra reference-input archive is needed for these checks.

Corrected checker76ad31a and independent controls863545b were reviewed by Astra3;
Astra2 and Astra3 separately approved the actual retrieved archive. Frame indices
are exact integers, not tolerant floats; schema and peak_policy are exact.

The result compares combined onset/end/phase conventions on eight processed
means with fixed restricted peaks. It is not biological validation, 64 trials,
ROI bootstrap, or closure of Gate B. The next proposed full O/E/C factorial asks
which measurement conventions and interactions cause the discrepancy. Revised
specification39387c3 resolves tolerance/denominator review findings and is included
as docs/PANG_WINDOW_FACTOR_PLAN.md and configs/pang_window_factor_plan.json.
Implementation and its independent reviews are still required before a new run;
the original run must not be repeated for checker-only fixes.
