# Public motor evidence consistency audit

The selected MaleCNS cells 815344 and 815678 belong to different curated
groups. Auditing the complete exported group membership yields four cells:

| Curated group | MaleCNS body | Graph index | Annotated soma side |
| --- | --- | --- | --- |
| 11657 | 804257 | 148012 | R |
| 11657 | 815344 | 156979 | L |
| 11706 | 800636 | 145248 | L |
| 11706 | 815678 | 157213 | R |

All four have empty rootSide and all four occur in the disabled knee draft.
Soma side is annotation metadata, not proven effector laterality. This does
not identify either group as SETi/FETi or approve a neuron-to-muscle map.
The diagnostic pair alone is insufficient to represent both full groups.

The predicted ID of 815344 (10256) has no match in the exported target join;
815678 predicts 22126 with target Tergotr. Curated Ti extensor group labels
therefore cannot be replaced by these predicted individual identities.

Run from the repository root:

```sh
python tools/audit_astra3_motor_evidence.py --output reports/astra3_motor_evidence.json
python -m unittest discover -s tools -p test_astra3_motor_evidence.py
```

The audit checks all 815 candidate entries and the 381-row leg joins,
historically pinned export digests, repeated identity fields, empty approval
fields, exact group membership and all 24 disabled draft entries. Negative
controls reject duplicate IDs, edited predicted targets and enabled or
calibrated draft entries. The JSON records every input digest.

Astra 2 independently reproduced the initial report and exposed missing draft
identity checks. The corrected audit also requires 24 unique known draft
body IDs and joins every graph index, curated group and muscle annotation
back to the curated table. Negative controls cover corrupted indices, groups,
muscles, unknown IDs and duplicate entries.

Scope: consistency of public derived CSVs and JSON only. The public clone
does not include the raw Feather/graph data; this run does not revalidate
their provenance or publisher source bytes. Historical digest anchors are
not independent proof of authenticity. No simulation or KSP was run.

Gate D remains open: individual identity, effector side, fast/slow identity,
activation kinetics/gain and motor-unit aggregation require independent
evidence. See MOTOR_MAPPING_EVIDENCE.md for the prior anatomical work.

## Publisher-source follow-up

Fresh public downloads of Cheong supplementary files 3 and 6 match the
historical source SHA-256 values exactly. The optional `--publisher-dir DIR`
accepts those files named `supp3.csv` and `supp6.csv`, verifies both digests,
and checks both MANC groups, targets, serial IDs, soma-side labels and the
two predicted-ID lookup results directly. No network request happens inside
the audit. Download URLs:

- https://cdn.elifesciences.org/articles/96084/elife-96084-supp3-v1.csv
- https://cdn.elifesciences.org/articles/96084/elife-96084-supp6-v1.csv

`reports/astra3_motor_publisher_check.json` records this additional executed
check. It strengthens MANC source support but does not revalidate raw
MaleCNS annotations, cross-specimen identities or physiology.
