# Photoreceptor reference and required graded interface

The existing Shiu LIF implementation is a spike-based reference. Its numerical
validation does not validate conversion of pixels into Poisson spikes. Drosophila
photoreceptor-lamina signalling includes graded potentials and continuous
transmission; a spike-only replacement requires a separate justified approximation.
See the primary study https://doi.org/10.3389/fncir.2016.00019.

The author FlyBrainLab/VisTrans implementation is pinned at
ba096778d4bd895a0e0fab02b9c519c5941bc82b. Its BSD-3-Clause license, 33 source
files and hashes are preserved by `tools/fetch_vistrans_reference.py` and
`reports/vistrans_reference_sources.json`. No dependency installer or source
module was executed during acquisition.

`PhotoreceptorModel.py` consumes photon rate and feedback current, and produces
membrane voltage. It contains a stochastic microvillus reaction cascade, summed
TRP current, five membrane gating variables and adaptation state. The default
configuration specifies 30,000 microvilli per photoreceptor. This is a published
model default, not a measurement for every MaleCNS receptor. The maximum outer
step is 0.1 ms, with ten membrane substeps. Its membrane kernel converts seconds
to milliseconds internally. Blindly sharing the LIF step's numeric units would
therefore introduce a factor-of-1000 error.

`tools/extract_photoreceptor_kernel.py` uses Python AST literal extraction to
materialize the unchanged author's FP64 CUDA membrane kernel and full license
under build/. No PyCUDA module is imported or run. The extraction report binds
both source and output hashes. This is preparation for a native reference run,
not evidence that phototransduction or its biological responses pass.

Required next checks: membrane voltage under fixed-current protocols against an
independent reference; stochastic reaction and photon-rate semantics; adaptation,
dark/noise/light responses against published data; graded synaptic coupling to
downstream cells; spectral/irradiance calibration of rendered images. Do not feed
RGB directly to this current-driven membrane kernel or invent spikes from its
output. Full MaleCNS topology must be retained across any mixed graded/spiking
implementation. No such mixed runtime is enabled yet.

## Membrane kernel runtime check

`tools/build_photoreceptor_probe.cmd` compiles the unchanged extracted kernel
with CUDA 12.5, FP64, sm_86 and --fmad=false. `native/photoreceptor_probe.cu`
drives four diagnostic currents: 0, 10, 100 and a 100 pulse on [0.2,0.4) s
(current values are author model units). Initial voltage is -81.9925 mV and
the five initial gates follow the author source. Each of 10,000 outer ticks
executes ten 10-microsecond membrane substeps; all six states are recorded.

`tools/check_photoreceptor_membrane.py` evaluates an independently written scalar
CPU version, including updated-gates-before-voltage ordering, against every
GPU state. Maximum voltage difference is 1.7763568394002505e-14 mV; every other
state differs by at most 5.56e-16. Report and executable/trace/source hashes:
`reports/photoreceptor_membrane_comparison.json`. This is actual CUDA execution,
not source-only inspection or a full phototransduction run.

Strong-current trials transiently reach +13.33421305304826 mV on both CPU and
GPU. The arbitrary injected-current range was not calibrated to physiological
light responses. This agreement establishes numerical transfer only; it neither
validates the high-current biological regime nor demonstrates sensory behaviour.
No clipping was introduced to hide the transient. Photon cascade, feedback,
graded coupling and biological response checks remain outstanding.

## Active cascade source audit

The transduction function contains two templates; the active SourceModule uses
`template_run`, not the earlier `template`. Extraction now selects that exact
literal, plus the summed-current and adaptation kernels. The Windows build needs
an external `using ushort = unsigned short` alias with a two-byte static assert;
the extracted author reaction body is unchanged. Build command:
`tools/build_phototransduction_objects.cmd`.

Despite double-valued membrane/input arrays, the active cascade uses float
reaction rates, calcium values, time and curand_uniform/logf. Thus this is mixed
precision, not an entirely FP64 photoreceptor. Seven molecular states are packed
into unsigned 16-bit fields. RNG state is per CUDA thread; an atomic warp work
queue assigns microvilli. RNG state is written back after processing. Snapshot
design must include molecular variables, membrane gates, voltage, adaptation
and RNG state; identical seeds alone do not establish scheduling-independent
replay. Shared warp work assignment and legacy current reduction also need
race/synchronization checks on the actual GPU before integration.

The source order is cascade -> summed TRP current plus feedback -> ten membrane
substeps -> adaptation update. Current conversion is explicit in the author
kernel: channel pA divided by 15.7 to obtain microampere/cm^2. These findings
describe source semantics, not a successful end-to-end phototransduction run.

## Current reduction race found and corrected

Actual RTX CUDA execution of `native/photocurrent_probe.cu` tests three receptors
with 30,000 microvilli each, patterned open-channel counts, negative/positive
voltages and feedback current. Direct CPU channel sums match GPU outputs.
However, Compute Sanitizer racecheck reports five warnings in the unmodified
author shared-memory warp reduction. Correct numeric output alone did not
establish synchronization safety. The original log is retained in
`reports/photocurrent_author_racecheck.log`.

`native/photocurrent_safe.cuh` retains the author license and current equation,
replacing only the final warp sum with register shfl_down_sync reduction. The
same three cases match exactly and racecheck reports zero errors and warnings.
`reports/photocurrent_reduction.json` binds source, executable, both logs and
numeric results. This validates this reduction fixture only; no claim is made
yet about the stochastic cascade's races or full photoreceptor correctness.

## First full-step execution

`native/phototransduction_probe.cu` initializes two 30,000-microvillus receptors,
XORWOW seed 19303, author molecular states and membrane gates. Photon rates are
0 and 100,000/s. A single 0.1 ms step executes cascade, corrected current sum,
membrane and adaptation on GPU. The original cascade produces two racecheck
warnings in shared warp work assignment; the negative log is retained.

`native/phototransduction_safe.cuh` replaces the shared work-index communication
with a register shuffle broadcast, keeping reaction bodies unchanged. A full
warp participates in each work broadcast, with out-of-range lanes skipping only
the reaction body. The same full-step fixture passes racecheck with zero errors
and warnings. Evidence: `reports/phototransduction_step.json`. Both voltages after
one step are -81.992495768975374 mV; this short test does not demonstrate a light
response or statistical equivalence. Partial-warp sizes, longer light/dark runs,
checkpoint replay, molecule bounds and other sanitizer checks remain unverified.

## 100 ms numerical photon pilot

The diagnostic accepts a bounded tick count (1..10,000) and records tick, both
voltages and both adaptation values as CSV. The 1,000-tick run at 0/100,000
photons/s, seed 19303 and 30,000 microvilli per receptor completed successfully.
Final dark/light voltages were -81.99249502243413 and -18.96694320127799 mV;
maximum light-minus-dark difference was 70.77329290677768 mV. Final adaptation
was 1 and 25.81005597007335. Every membrane state remained finite and each of the
five membrane gates remained within [0,1] at outer-step boundaries.

Evidence: `reports/phototransduction_100ms.json`, trace
`build/phototransduction_100ms.csv`. This demonstrates a numerical photon-driven
response, not a fit to measured responses. It is one seed and one intensity;
no stationarity, dose dependence or statistically validated fidelity is asserted.
The comparatively large response requires published-protocol comparison before
neural coupling. Runtime was 12 seconds including process startup, initialization
and per-step host logging; not an optimized throughput benchmark. Historical
single-step sanitizer reports bind their earlier executable, not this new build.

## Delayed light onset protocol

The author RFC #3 Figure 15 uses onset after 0.5 s dark and displays 2 s total.
The source PDF is locally hash-pinned by reports/photoreceptor_protocol_source.json.
The diagnostic now supports up to 20,000 ticks and an optional onset tick;
`build/phototransduction_safe_probe.exe 20000 5000` writes the full CSV to stdout.
One 100,000 photons/s case completed in 172.703 wall seconds, including per-step
host recording and startup, not a throughput benchmark. The dark control and
future illuminated receptor matched exactly before onset. The light peak was
-11.728220288882797 mV at 0.5346 s; the final 0.2 s mean was -32.82896532956547 mV
(standard deviation 0.7501655732447432 mV), while dark mean was -81.9925067208337.
The initial peak followed by a smaller late response is qualitatively consistent
with the published model protocol. No numeric curve fit, raw biological data
comparison, full intensity series or stationary-state assertion is made.
Evidence: reports/photoreceptor_onset.json, generated by
tools/check_photoreceptor_onset.py; plot build/photoreceptor_onset.png.

## Repeatability finding and separate RNG variant

Two 100 ms runs of the same thread-RNG executable with seed 19303 and identical
launch dimensions differed by up to 1.3175918293578803 mV in the illuminated
receptor. The dynamic work queue assigns different microvilli to thread-owned
random streams. Evidence is retained in reports/phototransduction_repeatability.json.
Fixing shared-memory races alone therefore did not provide repeatable trajectories.

The separate FF_ENTITY_RNG variant stores XORWOW state per microvillus and loads
and writes it around that microvillus's reaction update. Initialization uses the
microvillus index as sequence ID. The reaction equations are unchanged, but the
random stream assignment changes; no bitwise agreement with the author variant
or statistical equivalence is asserted. Build using
tools/build_phototransduction_replay_probe.cmd. Two 100 ms runs of this variant
produce identical CSV bytes for voltage and adaptation at every recorded tick.
Evidence: reports/phototransduction_entity_repeatability.json. These checks do
not cover all molecular states, checkpoint restore, other launch dimensions or
other GPUs; the new variant still requires its own sanitizer validation.

The entity-RNG executable subsequently passed memcheck, initcheck, racecheck and
synccheck on ten complete steps for two 30,000-microvillus receptors. A separate
artificial boundary fixture with 30,001 microvilli per receptor (60,002 total,
partial final warp) passed the same four checks. No biological microvillus count
was changed by this boundary test. Hash-bound evidence is in
reports/phototransduction_entity_sanitizers.json and
reports/phototransduction_tail_sanitizers.json. These short checks do not cover
all molecular states reached during sustained illumination or prove full-state
checkpoint replay. The previous paragraph's sanitizer-pending status is superseded
only for these two fixtures.

## In-memory checkpoint continuation

`tools/build_phototransduction_checkpoint_probe.cmd` enables a diagnostic snapshot
at tick 500 of a 1,000-tick run. After reaching tick 1,000, the driver restores
the snapshot into the same allocations and repeats ticks 501..1,000. It compares
3,720,160 bytes of final persistent state exactly: all packed molecular states,
membrane voltage/gates, adaptation, input, per-microvillus XORWOW and feedback.
Work counter and summed current are scratch, reset/recomputed before use;
immutable topology, reaction constants and simulation time remain in the driver.
`tools/check_photoreceptor_checkpoint.py` also compares every repeated recorded
voltage/adaptation sample. Both comparisons pass; evidence is hash-bound in
`reports/photoreceptor_checkpoint.json`.

This is trusted same-instance in-memory continuation, not a portable file format
or fresh-process restore. Raw RNG ABI compatibility, configuration identity,
checkpoint validation and externalized clock/protocol state still need a durable
checkpoint implementation before Molab export/resume can be claimed.

## Multi-block numerical trajectory comparison

`tools/build_phototransduction_parallel_probe.cmd` uses 16 blocks of 128 threads
with entity-owned RNG. At the same seed and 1,000 ticks, the voltage/adaptation
CSV is byte-identical to the single-block entity-RNG executable. Observed wall
times were 12.0668 and 1.37536 seconds respectively, including process startup,
allocation and per-tick host recording. These are two-receptor diagnostic timings,
not whole-brain or end-to-end performance. Evidence:
`reports/phototransduction_launch_equivalence.json`, including both executable
and trace hashes. Full molecular/RNG state equivalence across launch dimensions
has not yet been checked. Multi-block compilation of this diagnostic is rejected
unless entity RNG is enabled, since the legacy variant allocates only 128 RNGs.

Full persistent-state comparison now also passes on the checkpoint fixture:
the first continuation from tick 500 to 1,000 uses one block, and the restored
continuation uses 16. All 3,720,160 bytes, including molecular and XORWOW state,
match, as do every recorded voltage/adaptation sample. Build with
tools/build_phototransduction_launch_state_probe.cmd and run
tools/check_photoreceptor_launch_state.py. Evidence:
reports/photoreceptor_launch_state.json. This closes the full-state comparison
for this particular seed, intensity, two-receptor population and continuation;
it is not a proof across all launches, hardware or future configurations.


## Configurable diagnostic populations

`FF_PHOTORECEPTORS` now controls the population size (default 2). Host initial state, ownership, offsets and alternating dark/light stimulus are built for all cells; membrane and adaptation grids cover the whole population. Original index widths impose compile-time bounds (2..65535 cells and total microvilli <= INT_MAX). This is a synthetic diagnostic population, not a MaleCNS eye assignment or a claim that all photoreceptors share calibrated parameters.

On Molab Blackwell, populations of 2 and 130 cells, each with 30,000 microvilli, ran 1,000 ticks (100 ms). All light cells responded, including beyond 32/128-thread boundaries; dark cells agreed. The first pair's trajectory and nine final state components matched exactly across populations and matched the previous two-cell trace. A shorter 10 ms attempt did not satisfy the 1 mV response threshold and is retained as an unsuccessful short-duration test. Wall times 0.734/17.370 seconds include startup and logging and are not steady-state or full-retina performance measurements. See `reports/molab_photon_population.json`; exported state arrays: `build/photon_population_2.bin`, `build/photon_population_130.bin`.

The two-cell fresh-process checkpoint tests were rerun after this refactor and passed both onset cases and malformed-input rejection (`reports/molab_photon_population_checkpoint_regression.json`). Checkpoint tests at larger populations, full-scale resource measurements and anatomical visual coupling remain pending.
