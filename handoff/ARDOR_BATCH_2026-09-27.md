# Four-peer reviewed continuation

This is a local source/evidence checkpoint, not a biological gate pass or a
public push. The existing solution is reused. Four independent chats exchanged
actual nonce acknowledgements and reviewed each other's commits using separate
copies. No automatic continuation of idle chats is established.

## First reviewed increments

| Scope | Author revision | Independent review |
| --- | --- | --- |
| Gate A SWC acceptance | `f24bf280d1a0d3cdf1d54e296d7d09b9c63ad00a` | Astra 4: ten tests, approval |
| Gate F declared checkpoint/start uniqueness | `af63926550123e26b21c0e91fe9d5b8e8e1ee0cb` | Astra 4: eight Rust tests, approval |
| Gate D complete motor groups/draft identity | `0cc39a857c5e35a8e83a5f94df8cf4cd0aa4e1f7` (includes two prior commits) | Astra 2: six tests, independent publisher downloads, three mutation probes now rejected |
| Gate B Pang phase/source semantics | `328f9ef` (includes `3df82b3`, `92a9016`) | Astra 1: eight source curves, independent quadrature, zero-response and cached-source fixes, direct MATLAB source reading |
| Gate B downstream display signs | `a3a44e1` | Astra 1: fresh source acquisition, exact report reproduction, direct source-transform order review |

SWC acceptance now rejects empty downloads/files and malformed topology with a
nonzero exit code. A valid partial subset remains explicitly partial. Motor
group membership is not a one-to-one cross-dataset identity. Landing hash
uniqueness is a conservative declaration rule, not proof of independent training.

Pang source clarification: the author MATLAB computes a **signed net-tail area**
and signed area2/area1; plotting/statistical consumers negate the ratio before
means/quantiles. They do not replace it with an absolute value. Opposite-only
area is a sensitivity diagnostic, not a corrected source metric. The original
processed-mean script uses different boundaries and cannot reconstruct ROI
bootstrap statistics. No MATLAB, biological model or KSP execution occurred.

## Reviewed follow-ups

Astra 1's `725a863` (including `be1a494`) restores four exact generation-pinned
SWCs from public GCS: 651,982 bytes and 19,183 nodes. Independent undirected
component counting matches the historical topology summaries, including three
multiroot files. Fresh receipts do not prove byte identity to the unavailable
historical manifest. Astra 3 approved after fresh generation-pinned acquisition,
offline optimized execution, exact report reproduction and independent union-find
component counting. Gate A remains open.

Astra 2's `3639331da4d60e0d91f171196ca317b8c1b7c32e` translates the sampled
MATLAB boundary/area contract on synthetic controls. Astra 4 approved after six
tests, source-formula inspection and exact report reproduction under `-O`.
It preserves a restricted one-based/sample-based contract and explicitly
documents wrapper differences from MATLAB errors/NaNs. It is not execution of
MATLAB, peak selection, ROI bootstrap or biological scoring.

Astra 3's `9582021cd6a57037583d9ca1bc3c48a11f92bc85` compares all 815 exported
motor annotations with the pinned raw MaleCNS Feather, reconstructs the exact
167,216-ID population hash and checks 12,225 annotation fields. Astra 2 approved
the source audit and negative controls independently. This does not revalidate
raw edges, physiology or individual cross-specimen identity.

## Reproduction entry points

```sh
python -m unittest discover -s tests -p test_swc_audit.py -v
cargo test --locked
python -m unittest discover -s tools -p test_astra3_motor_evidence.py -v
python tools/audit_astra3_motor_evidence.py
python tools/audit_swc_source_pilot.py --fetch
python tools/audit_pang_phase_semantics.py --fetch
python tools/audit_pang_display_sign.py --fetch
python -m unittest discover -s tests -p test_pang_sample_contract.py -v
python tools/audit_pang_sample_contract.py --source-dir data/reference/pang_phase_semantics
```

Pang phase audit requires NumPy/SciPy. `--fetch` is an explicit bounded public
source acquisition; subsequent runs use checked cached files offline. The git
bundle carries source and reports, not the large GitHub release datasets or
ignored downloaded references. Do not overwrite existing experiment data when
restoring. The source pilot restores generations from its committed report.

## Next decisions

Use the sampled source contract and display sign together before any model
comparison. Obtain matching ROI/time/optical metadata before claiming physiology.
For anatomy, verified raw labels/topology do not establish motor effector side,
cross-specimen identity, kinetics or complete population morphology. Continue
bounded source/measurement checks with declared uncertainty; do not enable the
disabled motor mapping or substitute a convenient smaller neuronal population.
