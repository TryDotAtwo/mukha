# Raw annotation verification of the motor export

The generation-pinned 14,483,314-byte MaleCNS annotation Feather was fetched
directly from the published GCS source. Its SHA-256 matches the source lock.
The independent audit reconstructs the declared Traced OR nonempty superclass
population and sorts body IDs. Its 167,216-element uint64 NPY representation
matches the archived graph-ID SHA-256 exactly. This does not inspect graph edges.

All 815 motor indices and 12,225 source-field values (15 fields per cell) match
the exported motor CSV; the complete source motor population equals the export.
There are 381 leg motor annotations. Both curated extensor groups contain the
same four cells reported by the earlier export audit. Every rootSide is null
for those four cells; somaSide does not establish effector laterality.

The source also assigns predicted MANC ID 10256 to both 815344 (Ti extensor MN)
and 800163 (IN19A002). This directly reproduces the previously documented
prediction multiplicity. It does not determine which prediction is correct.
Neither this check nor agreement with curated group labels establishes a
cell-to-cell cross-specimen identity, fast/slow motor unit, or activation law.

## Reproduction

Install numpy and pyarrow in an isolated environment (executed with numpy
2.5.3 and pyarrow 25.0.1). Fetch the exact `pinned_url` in
`reports/astra3_motor_source.json`; retain the original Feather basename.

```sh
python tools/audit_astra3_motor_source.py --source /path/to/body-annotations-male-cns-v1.0-minconf-0.5.feather
python tools/check_astra3_motor_source_controls.py --source /path/to/body-annotations-male-cns-v1.0-minconf-0.5.feather
```

The report is `reports/astra3_motor_source.json`. Negative controls alter
graph index, curated group and rootSide in an in-memory export while also
updating its recorded digest. These must fail semantic comparison with the
unchanged raw source; source-byte corruption must fail before parsing. The
controls write no source files. No graph simulation, physiology, or KSP run
was performed; gate D remains open.
