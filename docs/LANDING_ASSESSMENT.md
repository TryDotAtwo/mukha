# Landing assessment contract

`src/landing.rs` consumes privileged physics measurements, never policy inputs.
`faithful-fly assess-landing INPUT.json OUTPUT.json` evaluates a trace with format
`faithful-fly.landing-trace.v1`. Input fields are defined by the strict serde
structs; unknown fields are rejected. Output retains the input SHA-256 and source
label. Labels are not authenticated provenance.

Each contact transition requires pre-contact vertical and horizontal speeds.
Post-solver clamped velocity cannot stand in for impact speed. Every impact must
meet absolute vertical speed <=2 m/s, horizontal speed <=1 m/s and distance <=50 m.
Destruction before success fails the episode. Success requires ten continuous
seconds of sampled contact, within 50 m, with speed and angular speed below the
explicit stability thresholds. A bounce, drift or excess motion resets that
timer. Trace time starts at zero while airborne. Consecutive physics tick IDs,
strictly increasing timestamps and a configured maximum gap <=100 ms are required.
The whole input is validated, including trailing records after a result.

Stability thresholds are an engineering operational definition, not supplied
biology or calibrated KSP physics. Fixtures use 0.1 m/s and 0.01 rad/s. Final
evaluation must preregister these thresholds and record every physics state and
contact event, not only rendered frames. The evaluator cannot detect omitted
intermediate events if a producer forges consecutive tick IDs.

`assess_series` separately checks exactly three distinct seed IDs, 100 distinct
start IDs and all 300 terminal seed/start pairs. It rejects duplicates, missing
or unfinished trials, unexpected IDs and mixing native/KSP environments.
`series_threshold_passed` requires >=90 in EACH seed. These aggregation functions
are exposed through `faithful-fly assess-landing-series SERIES.json OUTPUT.json`.
The series file uses `faithful-fly.landing-series.v2`, a `plan` with
`environment` (`Native` or `Ksp`), three `training_seeds`, 100 `start_ids`,
and the authoritative `stability` thresholds,
plus 300 `trials` entries with `seed`, `start_id`, and a distinct relative
`trace` path. Each trace uses the existing landing-trace format and a matching
`source` (`native` or `ksp`). Each trace must carry exactly the plan's stability
thresholds or the entire series is rejected; scoring uses the plan value.
Version 1 series are rejected. The CLI evaluates every original trace, rejects
missing or duplicate pairs and duplicate trace paths, and records SHA-256 for
the series file and each trace in its output. This does not authenticate that
the traces came from KSP, that the starts were preregistered, or that the fly
physically generated the applied commands.

Version 3 series additionally require `training_checkpoint_sha256` (three
lowercase SHA-256 strings in seed order) and `start_state_sha256` (100 strings in
start order) in the plan. Each corresponding `landing-trace.v2` contains a
`binding` with its seed, start ID and both hashes. The assessor rejects missing
or mismatched bindings and reports `bound_to_declared_checkpoint_and_start`.
Version 2 remains readable as an explicitly unbound diagnostic series; it must
not be cited as proof of independent training or withheld starts. Version 3
checks consistency of declarations and bytes, not the authenticity of a
checkpoint, start state, KSP receipt, or preregistration timestamp.
The three checkpoint hashes and the 100 start hashes must each be distinct:
relabeling the same checkpoint with another seed or the same start state with
another ID is rejected even when all trace bindings match the reused hash.
This is a conservative artifact-identity requirement for v3. Distinct hashes
still cannot establish independent training or withholding; different metadata
or serialization alone can change a hash. Legacy v2 remains unbound.
Plan preregistration, authentic checkpoint and start-state artifacts,
independent training provenance and biological gate evidence remain required
before a series could establish the mission goal.

Seven Rust tests pass: exact duration/limits, hard-impact concealment, bouncing,
missing/nonfinite records, destruction/drift, and non-pooled seed counts with
environment separation, including rejection of a trace with altered series
stability thresholds. The series CLI test also checks a complete bound 300-trace
version 3 fixture and rejection of a substituted start-state hash. A synthetic
CLI trace produces success at 10.1 s in
`reports/landing_assessment_fixture.json`. It is diagnostic data, not a landing
performed by the fly. The vertical plant does not yet provide supported-body
stability physics, so it cannot supply this success evidence.
