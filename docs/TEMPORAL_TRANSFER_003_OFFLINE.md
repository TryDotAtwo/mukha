# temporal-transfer-003: recorded local result and offline reproduction

Original reviewed implementation297201d6a0f2946f0e7b4eae86bf356025219fc1;
runner SHA25656a4dde910687e8adfc9a538c939cbe202f8184e1cb1dbe57ecc83ed27d17f4e.
Executed once, LOCAL synchronous CPU after both exact prelaunch approvals.
Official Molab session discovery failed before experiment submission; no retry
or claimed remote execution. Location/returncode/file hashes are preserved in
reports/temporal_transfer_003_operator_receipt.json. The numerical code and
source inputs were unchanged by the execution-venue fallback.

Recorded archive reports/recorded_runs/temporal-transfer-003.tar.gz:
SHA256 c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb,
336371 bytes;11 manifest entries plus manifest.json. It includes8 MATs, code,
compiled config and results. The full publication bundle includes this archive,
so no private path, token, previous bundle or external data download is needed.

## Inspect or optionally reproduce

After restoring mukha-full.bundle as described in PUBLICATION_SUMMARY.md, from
the restored repository, verify the exact archive before extraction:

```sh
python -c 'import hashlib,pathlib; p=pathlib.Path("reports/recorded_runs/temporal-transfer-003.tar.gz"); raise SystemExit(0 if hashlib.sha256(p.read_bytes()).hexdigest()=="c74de270799633ed056d8b5e6a61a383a4a96797243e3a0453ec28e8ad2af4bb" else 1)'
mkdir temporal-reference
tar -xzf reports/recorded_runs/temporal-transfer-003.tar.gz -C temporal-reference
```

Read result.json, config.json and manifest.json in temporal-reference/
temporal-transfer-003. Independent reproduction, only when explicitly desired:

```sh
python -O tools/run_pang_temporal_transfer.py --input-dir temporal-reference/temporal-transfer-003/inputs --output-dir independent-temporal-reproduction
```

Destination must not exist. Runtime used Python3.12.11, NumPy2.5.3, SciPy1.18.1;
dependencies must already be installed for offline execution. No installation
or network access is performed by the runner. This command computes a NEW local
reproduction; it is not automatically run merely to inspect the archive.
No trial/animal bootstrap, window test or calibrated stimulus simulation occurs.

## Outcome and limitation

H1 wins five declared transfer curves, loses L2/highLum/light. The predeclared
all-six advantage is FALSE. Sum of normalized error improvement is+0.1074468;
that aggregate cannot erase the failed transfer. Selected tau values (~16.10ms
L1 and22.37ms L2) are effective grid parameters, not identified biological time
constants. Training fit alone is not evidence for predictive superiority.
Neither memory necessity nor recurrent topology is established: static
nonlinearity, observation transform and cohort/illumination confounds remain.
Actual result review status is tracked separately in the summary/peer reports;
prelaunch synthetic checks are not a substitute for that review.
