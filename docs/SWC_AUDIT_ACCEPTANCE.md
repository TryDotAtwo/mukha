# Downloaded SWC audit acceptance — Astra 1, 2026-09-27

Gate A remains open. This change verifies the acceptance logic for a downloaded
subset; it neither acquires the full population nor validates biological geometry.

At base commit `673050e2aabc4f7b1c01c825a13dc7f17a6dc33b`, an empty
SWC produced zero nodes but did not enter `structural_issue_files`. The script
also returned exit code zero after reporting structural errors. A directory
with no SWCs similarly completed without signaling failure. Reproduction used
the original `inspect` function on an empty temporary file; all five old error
predicate fields were zero. No historical source skeleton was changed.

`tools/audit_downloaded_malecns_swcs.py` now records
`structural_checks_passed` and returns exit code 1 for empty downloads or any
structural-issue file, including empty/header-only skeletons and rootless graphs.
Byte/provenance violations raise exceptions. Inventory SHA-256 checking remains
active under Python optimization. Numeric filename aliases such as `1.swc` and
`01.swc` cannot silently overwrite the same report entry.

A valid partial subset can pass these structural checks; `downloaded_fraction`
still exposes incomplete coverage. Multiple roots and zero-length edges retain
their existing descriptive status rather than being newly labeled biological
defects. Radius/compartment quality, reconstruction completeness and biological
function remain outside this acceptance contract. The historical 4,352-file
report is retained unchanged and has not been rerun against the release data.

Verification:

```sh
python -m unittest discover -s tests -p test_swc_audit.py -v
```

Ten test methods cover valid partial coverage, empty inputs, malformed lines,
missing parents, cycles, self-parenting, duplicate node IDs, nonfinite coordinates,
multiroot/zero-length descriptive controls, empty population, foreign body IDs,
source-byte mismatch, filename aliases and main's report/exit contract. The main
test uses actual temporary gzip inventory and SWC bytes with only the NPY
population loader stubbed; this is not a full scientific-data replay.

Peer review is requested through the shared mailbox; a passing local test suite
does not by itself constitute independent review.
