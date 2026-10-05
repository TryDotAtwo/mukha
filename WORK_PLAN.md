# Faithful Fly / Mun — execution ledger

Accepted objective: full published MaleCNS neuronal reconstruction, biologically
tested spiking dynamics and local plasticity, physical fly/cockpit contact,
vision-only flight observations plus body senses, native Rust/C++/CUDA runtime,
Molab training, KSP evaluation, synchronized recordings. Biological fidelity
takes priority over a successful landing. No hidden autopilot, animated puppet,
telemetry-to-policy shortcut, or full-core task backpropagation in the main path.

## Gates (evidence required; implementation alone does not pass)

- [ ] A: immutable source provenance; Traced OR nonempty superclass population;
  all internal edges; ambiguous/excluded annotation ledger; boundary accounting;
  actual anatomical geometry with coverage recorded.
- [ ] B: Shiu original-dataset numerical and biological replication; separate
  MaleCNS transfer; sugar, bitter and antennal-grooming checks; Huang memory
  replication; calibration and held-out biological observations separated.

Local original-graph numerical replay (2026-09-27): the unchanged 10,000-tick
sugar protocol ran with the native FP64 CUDA backend on the local RTX 3070
Laptop GPU in 32.2 s. All 9,440 spike events reproduce the archived native
FP64/Brian2 journal byte for byte; the MN9 readout has 64 spikes. Protocol,
graph, executable, DLL, journal and checkpoint hashes are bound in
`reports/shiu_local3070_replay.json` by `tools/check_shiu_local_replay.py`.
This verifies this numerical trajectory on a second GPU environment. It is
still the original Shiu graph and one diagnostic seed, not MaleCNS biological
transfer or a measured behavioral response; gate B remains open.
- [ ] C: native forward agrees with reference; delay/refractory/reset correctness;
  checkpoint continuation; CUDA sanitizer; actual Molab full-loop measurements.
- [ ] D: NeuroMechFly/MuJoCo seated body, passive 3-axis stick and throttle;
  bounded joint actuation; contact interventions; visual and body-sensory inputs.
- [ ] E: validated local plasticity, visual cue and contact-operation curriculum;
  three training seeds, withheld trials, post-learning biological regression.
- [ ] F: native rocket environment, calibrated KSP bridge, actual applied control
  audit, no SAS/trim/autopilot, held-out KSP landing evaluation.
- [ ] Recordings: common clock and episode identity, measured neural activity and
  physical poses, complete event recording with backpressure, four video layouts.

Current graph recheck: `tools/verify_malecns_csr_semantics.py` verifies the
manifest hashes and structural invariants of all 167,216 retained nodes and
25,587,572 CSR edges (`reports/malecns_csr_semantics.json`). A fresh run of
`tools/verify_graph_semantics.py` independently compared every retained edge
with its original source row across the 151,856,684-row published
segment-to-segment table; it passed with 124,193,283 retained contacts
(`reports/graph_semantic_verification.json`). The [official MaleCNS download
page](https://male-cns.janelia.org/download/) calls that larger table a graph
of *all segments*, so its 311,833,243
contacts cannot be treated as a published-neuron count. Our population is
the 166,700 classified objects plus 516 traced but unclassified objects;
those 516 are retained explicitly rather than silently discarded. Neither
check validates geometry coverage, transmitter action or physiology; gate A
remains open.

Anatomical-geometry coverage audit (2026-09-26):
`tools/audit_malecns_geometry_coverage.py` verified the pinned annotation hash,
the exact 167,216-node graph population, and hashes in four local MaleCNS v1.0
SWC manifests. A soma or to-soma annotation point exists for 141,010 selected
objects; 26,206 lack both. The locally pinned SWCs cover 70 distinct selected
objects, leaving 167,146 without a local pinned skeleton. A point is not a
neurite morphology, and an SWC need not be complete. Gate A remains open:
whole-population anatomical geometry and its quality have not been established.
See `reports/malecns_geometry_coverage.json`.

Published SWC availability inventory (2026-09-26):
`tools/inventory_malecns_swc_bucket.py` walked all 212 public GCS metadata
pages for the MaleCNS v1.0 native SWC directory and saved a generation-pinned
inventory (`reports/malecns_swc_bucket_inventory.json` plus a hashed compressed
CSV). All 167,216 selected graph IDs have an SWC object listed, totaling
9,034,068,018 published bytes; all 70 existing locally pinned SWCs have the
same generations as the live inventory. This is availability metadata, not
downloaded-and-validated whole-population geometry. Gate A remains open until
the source skeleton bytes, structure, and coverage are checked.

SWC byte/structure acquisition pilot (2026-09-26):
`tools/fetch_malecns_v1_swcs.py` now downloads graph-selected files by the
inventoried GCS generation, verifies byte count and source MD5, and safely
resumes by checking existing files. The first 256 sorted graph IDs yielded
125,360,149 verified bytes. `tools/audit_downloaded_malecns_swcs.py` checked
3,591,378 SWC nodes: no malformed lines, missing parents, duplicate IDs,
cycles or nonfinite coordinates among these 256; 55 files have multiple roots.
This is 0.1531% of the selected population, and structural checks do not
establish biological morphology quality. See
`reports/malecns_downloaded_swc_audit.json`.

The same pinned acquisition was extended by 4,096 files (953,506,049 bytes)
to 4,352 local SWCs. A fresh complete audit of those files found 31,587,091
SWC nodes, zero structural-issue files under the defined syntax/parent/cycle/
finite-coordinate checks, and 588 multi-root files. This covers 2.6026% of
the selected population; morphology completeness is still unverified.

Landing evaluator contract correction (2026-09-26): An independent audit
reproduced that v1 series scoring accepted a per-trace stability threshold.
`src/landing.rs` now requires a v2 series plan with authoritative stability
thresholds, rejects any trace whose thresholds differ, and scores against the
plan. All seven targeted Rust landing tests pass, including one altered-trace
rejection. This closes the per-trace threshold loophole only; plan
preregistration, KSP origin and applied-command provenance remain open.

Near-equal LIF time-constant correction (2026-09-26): The independent audit
reproduced cancellation in the old exp-difference coefficient when τm≈τs.
`native/lif_coeff.h` now uses an expm1/exprel expression only for non-equal
time constants in the cancellation region; ordinary and exactly equal source
profiles retain the prior arithmetic. CPU and CUDA constructors use the same
coefficient, and models using the new branch add a numerical-semantics tag to
checkpoint identity. A compiled C++ probe matched an independent 80-digit ODE
integral across six cases (max absolute error 1.83e-17); a two-cell CUDA64
recurrence matched four cases (max error 6.11e-16) and rejected a checkpoint
with old identity without changing state. The CPU integration test passed.
Both CUDA DLL variants rebuilt; the archived full MaleCNS FP64 20/5 checkpoint
replay retained bit-exact states and 3,756/1,852 suffix events, and mixed-v3
tests passed. This fixes arithmetic for future heterogeneous profiles; it is
not biological validation. See `reports/lif_near_equal_tau.json` and
`reports/lif_near_equal_cuda.json`.

Local KSP bridge precheck (2026-09-26): KSP 1.12.5 build 03190 and kRPC
v0.6.0 assemblies are installed. Their shipped RPC schemas expose pause,
physics warp, raw control/trim reads and AutoPilot status, but no explicit
single-physics-step procedure. The last game log predates the mod; a pinned
Python client read-only probe found no responsive localhost server. No live
game, stepped time, applied commands, craft, or Mun episode is verified. See
`reports/ksp_local_preflight.json`, `reports/ksp_krpc_readonly_probe.json`,
and `docs/KSP_BRIDGE_PRECHECK.md`.

Matched-angle full-CNS diagnostic (2026-09-26): A 100-ms +10° versus -10°
history through the unchanged uncalibrated one-cell half-wave encoder, followed
by the same 0°/zero-drive 300-ms hold, produced 51 versus 0 events in the full
native graph. The maximum voltage difference fell from 19.069 mV at the first
hold step to 0.0000100 mV at 300 ms; 13 screened IN13B candidates produced no
spikes. This demonstrates short-lived numerical history in the recurrent model
under one diagnostic input, not the published 3-s graded 13Balpha response or
a biologically identified cell. Input and DLL hashes and all snapshots are in
`reports/agrawal_matched_angle_full_graph.json`; protocol and limitations are
in `tools/probe_agrawal_matched_angle_full_graph.py` and
`docs/BIOLOGICAL_NEXT_GATE.md`. Biological gate B remains open.

13Balpha voltage-intervention gate (2026-09-26): Agrawal Figure 2 supplement
1E/F reports smaller response changes after direct postsynaptic depolarization.
An executed FP64 two-cell native mixed-synapse check holds the source at -50 mV,
shifts the receiver baseline from -65 to -55 mV, and compares weight-one to
weight-zero controls. The 100-ms evoked shifts are equal to numerical precision
(both about 0.49497449 mV). This falsifies the current-based isolated-synapse
path for that qualitative intervention; it does not establish electrical
coupling or test a biologically calibrated full-network response. See
`reports/agrawal_voltage_driving_force_gate.json` and
`docs/BIOLOGICAL_NEXT_GATE.md`. Gate B remains open.

The corresponding publisher image is now pinned. An isolated compiled C++
conductance candidate with explicit unmeasured E_rev/gain produces a smaller
response after postsynaptic depolarization (0.54453 versus 0.64349 mV at
100 ms), matching the Figure 2 supplement 1E/F *direction*. An independent
Python recurrence verifies the numerical output at three time steps. This
does not fit response amplitudes, identify a chemical versus electrical route,
or assign any MaleCNS cell. See `reports/agrawal_conductance_candidate.json`.
An exploratory two-line digitization of Figure 2 supplement 1E gives disjoint
straight-line zero-response intercepts (+32.37 versus -25.59 mV) under sampled
±3-pixel reading perturbations. These are not measured reversals or a full
population fit; they prevent promoting the arbitrary shared E_rev=0 candidate
to a quantitative explanation. See `reports/agrawal_voltage_panel_lines.json`.

Local plasticity screening (2026-09-24): the isolated one-sided KC/DAN trace
rule is rejected against Handler et al. Figure 6 qualitative receptor-null
results (10/20 signs match across five positive time constants). It predicts
zero where DopR1-null forward pairing shows weak potentiation and where
DopR2-null backward pairing shows depression. This assumes the sign of local
efficacy follows the evoked MBON calcium response. The probe and full result
are in tools/audit_handler_one_sided_rule.py and
reports/malecns_handler_one_sided_rule.json. No contact efficacy was changed;
the biological transfer and plasticity gate remain open.

A pinned, redistributed Handler Figure 2/5 workbook is now locally available
under data/reference/handler2019. The Figure 2 gamma4 MBON sheet contains 31
paired pre/post preparations across six DAN-minus-KC stimulus intervals.
tools/analyze_handler_timing_data.py reconstructs every plotted delta and mean
from those pairs and records numerical intervals in
reports/handler2019_fig2_timing_data.json. This supplies a quantitative
wild-type timing target, but the workbook lacks Figure 6 receptor-null raw
preparations and does not identify MaleCNS per-contact parameters.
The same wild-type data reject the isolated monotonic backward eligibility
trace as a quantitative rule: -0.6 s gives a smaller response change than
-1.2 s in every cross-group preparation comparison (exploratory exact
one-sided permutation p=1/462). Next candidate needs a mechanism for the
near-overlap suppression and the receptor-null reversals, then independent
physiological checks before native graph integration.
The same workbook's Figure 5E/F second-messenger arithmetic is now reproduced
from 6 cAMP and 7 ER-calcium preparations per ISI. The six retrospective
normalized (-ER)-cAMP contrasts correlate with MBON response changes at
r=0.967 (reports/handler2019_fig5_second_messenger.json). This is a source
figure reconstruction, not an online local rule or independent validation:
normalization uses all future ISI conditions and imaging preparations differ.
The Figure 5D reporter observation windows are now reconstructed from the raw
0.1-s traces: inclusive endpoints give 41 cAMP and 11 ER-lumen samples, with
zero discrepancy across all preparations and six ISIs
(reports/handler2019_observation_windows.json). This fixes the source
comparison operator for a causal state model; it does not identify state
kinetics or authorize plasticity in the full graph.
An exploratory causal event-kernel screen on the six raw second-messenger
means now rejects the minimal two-branch transfer: the ER timing fit is
unstable under retrospective leave-one-ISI-out, and the resulting WT-fitted
plasticity model predicts zero in DopR1-null forward pairing where Handler
reports weak potentiation. The fitted tau values are not accepted biological
parameters. See reports/handler2019_causal_messenger_kernel.json; plasticity
remains disabled pending an independently tested local mechanism.
Cohn et al. 2015 adds a separate γ4 induction check: γ4/γ5 DAN activation
without KC during induction potentiated later KC-evoked γ4 MBON responses,
whereas temporal KC/DAN pairing depressed them. Both isolated candidate
rules predict zero for DAN-only induction and fail this qualitative
cross-protocol challenge. Preserve study/assay boundaries and compartment
specificity; do not silently require KC coincidence for every update.
The next bounded local-rule screen (`tools/screen_handler_tonic_two_pathway.py`,
`reports/handler2019_tonic_two_pathway_screen.json`) added a nonnegative tonic
DAN term to the two timed receptor-like branches. Time constants were fixed
from the separate Figure 5 messenger screen; only three amplitudes were fitted
to the already inspected six wild-type Figure 2 means. Its three intervention
directions are largely imposed by the chosen nonnegative branch structure,
not an independent receptor test. The -1.2 s and -0.6 s
predictions differ from their observed means by -3.38 and +2.40 SEM. The
tonic term becomes exactly zero under SEM-weighted fitting and in several
retrospective leave-one-ISI-out fits, so DAN-alone potentiation is not robust.
A 400-combination retrospective tau grid on those same WT means improves RMSE
only from 0.244 to 0.194 and chooses zero tonic term at its best point; the
grid is extra model selection on seen data, not a source-fixed or held-out fit.
This rejects *this fixed simple transfer* as a sufficient quantitative/local rule, not all DopR2
mechanisms. No MaleCNS weights were updated; receptor-null preparation-level
data, source-backed cell/compartment mapping and independent interventions
remain required.
MaleCNS KC lateral-subtype audit (2026-09-26): `tools/audit_kc_lateral_subtypes.py`
checks pinned graph files and partitions all 642,933 KC→KC rows by source KC
type. The 1,557 gamma KCs have 200.20 distinct KC inputs per cell on average;
305,841/311,707 (98.12%) incoming gamma rows originate in gamma KCs.
This is compatible with studying the lateral KC mechanism of Manoim et al.
2022, but does not localize synapses to axons, identify mAChR-B in MaleCNS,
or validate plasticity. See `reports/malecns_kc_lateral_subtypes.json` and
`docs/PLASTICITY_REFERENCE.md`. No graph weights were changed.
KC→KC coordinate extraction completed from generation-pinned MaleCNS synapse
partners: all 4,759 record batches scanned; 1,153,845 retained contacts match
all 642,933 directed CSR pairs exactly, with no pair-count mismatch. The
independent ROI/quality audit finds 413,441/507,343 gamma→gamma contacts
(81.49%) in broad `gL(L/R)`, versus 4.83% for alpha/beta→alpha/beta and
8.03% for alpha-prime/beta-prime within-group contacts. No null coordinates,
unknown ROI, nonfinite confidence or exact duplicate source rows were found.
The source lacks distinct synapse IDs, `gL` does not isolate gamma4 or prove
presynaptic axonal ultrastructure, and no receptor expression or plasticity
mechanism is inferred. See
`data/derived/kc_synapse_locations_v1/reconciliation.json` and
`reports/malecns_kc_lateral_contact_rois.json`. Biological gate remains open.

## Interfaces and invariants

Bound landing-series identity audit (2026-09-27, Astra 2): v3 series now reject
reused checkpoint hashes across seed labels and reused start-state hashes across
start IDs, including consistently altered trace bindings. The original synthetic
300-trace v2/v3 fixtures still pass. All eight default Rust tests pass; removing
the new guard makes the checkpoint-reuse regression fail because the old path
accepts it. This is a conservative artifact-identity contract, not proof of
independent training, withheld starts, or KSP origin. Gate F remains open.
Evidence and limits: `reports/landing_identity_audit.json`.

Rust orchestrates. C++ owns native/GPU buffers behind a C ABI. PyTorch is a
reference, not the native simulation loop. MuJoCo initially uses its native CPU
API. Raw observations and privileged assessment telemetry are separate types.
Only measured cockpit-control positions may create ordinary rocket commands.
Environment operations: reset, observe, advance, capture. Neural state persists
across decisions. Full resets are explicit episode events.

## Evaluation contract

First mission begins 2–3 km above a selected flat Mun site, descending 10–30 m/s,
horizontal speed <=10 m/s, tilt <=10 degrees. Use one fixed craft and preregister
100 withheld initial states. Success: vertical contact speed <=2 m/s, horizontal
<=1 m/s, target distance <=50 m, no breakage, stable for 10 seconds. Target >=90
successes per 100 for each of three training seeds. Native and KSP results are
separate. Failed biological gates prohibit presenting later demos as validated.

## Resources and persistence

First Molab block: <=30 min benchmark and <=1 hour biological pilot. Check actual
hardware before choosing a batch. Checkpoints every 10 minutes and gate boundary;
export and verify hashes before session loss. No paid provisioning is implied.
Reserve 50 GB for final assets/video; initial bounded work must fit available
space. No removal of unrelated user files. Never treat partial work as goal
completion. Source notebooks and all changes stay reproducible in this project.

Current implementation evidence (2026-09-15): full candidate graph built with
167,216 objects and 25,587,572 retained source rows; Rust verified all eight
artifact hashes. Five importer tests passed. Pinned original Shiu equations ran
under Brian2 2.9.0. PyTorch FP64/FP32 and native C++ FP32 match all 66 spikes of
the 1,200-step numerical fixture. Native checkpoint continuation is bit-exact;
corrupted payload is rejected. These are numerical checks, not full-brain
biological replication. A separate native CUDA/cuSPARSE replay also matches the
fixture on physical RTX 3070 Laptop hardware; memcheck, initcheck, racecheck and
synccheck passed for the same library hash (reports/cuda_sanitizers.json).
An initial uninitialized SpMV output read was found and fixed before these
passes. Persistent CUDA state/checkpoints now pass chunk-continuity, fresh-model
restore, invalid-input and four sanitizer checks (reports/cuda_state.json and
reports/cuda_state_sanitizers.json). The original Shiu graph is also exported
without filtering: 127,400 neurons and 14,687,178 rows. Full biological validation,
physical body, training and KSP remain outstanding. Rust now owns the CUDA
handle and drives bounded chunks; disk checkpoint restoration passes. A full
original Shiu sugar pilot (one seed, 1 second) ran in Rust/CUDA and Brian2.
The strict numerical comparison FAILED: 9,574 versus 9,440 network spikes, first
difference at tick 4,364. Diagnostic observed a near-threshold rounding-sensitive
event; see reports/shiu_sugar_pilot_comparison.json and shiu_precision_diagnostic.json.
Do not mark biological replication or full-network equivalence complete.

Precision investigation: an independent PyTorch FP64 GPU oracle, using exact
source integer counts before weight conversion, matched all 9,440 Brian2 spike
events for the same full-network sugar pilot. MN9 voltage maximum error was
4.05e-13 mV. Evidence: reports/shiu_torch64_comparison.json. This validates the
FP64 oracle for this pilot, not the native FP32 backend or the biological gate.
Next: implement and verify a native higher-precision reference path without
changing thresholds, topology, stimuli or acceptance criteria.

Controlled precision experiment completed: the same independent PyTorch code
in FP32 reproduced every native FP32 spike event and MN9 FP32 state exactly;
in FP64 it reproduced every Brian2 spike event. Evidence:
reports/shiu_precision_control.json. Precision alone is sufficient to explain
this pilot's divergence; do not generalize this to all inputs or biological
properties. Native FP64 is now implemented from the same source with a separate
double-precision C ABI, state, input, weights, parameters and checkpoint tag.
Rust feature `cuda64` reconstructs weights directly from signed integer counts.
The full native FP64 sugar pilot matched all 9,440 Brian2 events, with MN9
voltage error 4.05e-13 mV (reports/shiu_native64_comparison.json). The small
FP64 persistence fixture passes; the broader biological gate remains open.
All four sanitizer tools passed for the FP64 persistence fixture, tied to the
library hash in reports/cuda64_state_sanitizers.json. The shared-source FP32
persistence regression passed too. Full-graph memcheck is a separate run and
must have a terminal zero-error log before being counted.
Full-graph memcheck has now completed (127,400 neurons, 14,687,178 rows, 10,000
ticks): exit 0, zero errors and leaks in reports/cuda64_full_memcheck.log.
Its recorded spike events also match Brian2 exactly; instrumented timing is
labeled separately in reports/shiu_native64_memcheck_comparison.json.
Preregistered next pilot pair: configs/shiu_sugar100_bitter0_pilot.json and
configs/shiu_sugar100_bitter100_pilot.json, source notebook cells 23–24. Both
conditions set the sugar and bitter populations to zero refractory duration,
including the 0 Hz bitter control, following author.poi(). Both conditions now
match Brian2 on every native FP64 spike event. MN9 counts are 64 versus 4;
reports/shiu_bitter_pair.json records this one-seed paired result, not a complete
dose-response replication or a passed biological gate.

A second preregistered matched sugar/bitter pair ran on the original full Shiu
graph in Molab with Brian2 2.10.1 (FP64 NumPy, 10,000 ticks). Independent
stimulus seeds 19303/19304 were fixed and uploaded to private HF before either
network run. MN9 emitted 60 spikes with 100 Hz sugar alone and 7 with the same
sugar events plus 100 Hz bitter; all-network counts were 9,447 and 8,951.
The six protocol/report/spike objects passed byte-count and SHA256 retrieval
checks. Receipts and limitations: reports/shiu_bitter_pair_second_seed.json.
This confirms the response direction for a second input realization on the
original Shiu graph only; it does not validate MaleCNS physiology, a dose
curve, neural plasticity, or vision.

JON pilots preregistered from original notebook cells 50–54: 146 sensory neurons,
0/100 Hz, readouts id_DN1_1 and id_DN2_l. The Brian2 100 Hz run produced 18,012
network spikes and zero spikes in either readout. Native FP64 and Brian2 now
match every spike at 0, 100 and 220 Hz. Both descending readouts produce 0, 0
and 39 spikes respectively. The 220 Hz follow-up was chosen after the negative
100 Hz pilot, within the published dose range; it is not an independent
preregistered confirmation. reports/shiu_grooming_pilot.json preserves all three
conditions. One seed per condition does not complete biological validation;
no physical grooming response is claimed.

MaleCNS transfer inventory: MN9_L/MN9_R candidates, 163 labellar gustatory cells,
and 10 central taste-related synonyms. These remain unvalidated candidates;
see reports/malecns_transfer_audit.json and docs/TRANSFER_EVIDENCE.md. No sensory
mask, transmitter sign, or functional transfer was inferred from names alone.
The user reports being signed into Molab in the main browser. The native browser
tool currently fails before tab discovery with kernel-assets os error 3; the
separate automation browser has no authenticated session. No remote job started.

Physical body source acquisition completed: FlyGym 2.1.0 commit
ca65a510c2afe6ac61c51df4f274c8d190c2f95f and compatible MuJoCo 3.9.0 Windows
runtime are pinned in reports/body_reference_sources.json (98 source/asset files,
259 runtime files). Git blob hashes and the published runtime archive SHA256
were verified. Acquisition is not body execution: model composition, native
physics, cockpit contacts and neural motor mapping remain outstanding.

Native body diagnostic now executed: author FlyGym 2.1.0 ALL_BIOLOGICAL
skeleton, 126 joint DoFs, 69 bodies/geoms, static thorax, passive joints and no
actuators. Native C++/MuJoCo completed 10,000 ticks at 0.1 ms (one simulated
second), finite state and zero warnings. reports/body_export.json binds meshes
and XML; reports/body_native.json binds executable, runtime and export hashes.
This is passive-body execution only, not neural control or physical cockpit
causality. See docs/BODY_DIAGNOSTIC.md. Unicode filesystem loading required
passing unchanged mesh bytes through MjSpec assets during composition; exported
relative filenames load directly through the native C API.

Bounded motor diagnostic completed separately: 42 leg motors, native paired
baseline/pulse runs, 10,000 ticks. Applied force saturates at the configured 1
model unit; maximum joint displacement difference 0.097633885118314861 radians,
zero warnings. CSV verification confirms pre-pulse equality, finite poses,
declared timing and bounded forces (reports/body_motor_native.json). This is
explicit diagnostic input, not a neural controller. Contact with passive cockpit
controls and scientifically justified neural motor mapping remain outstanding.

First native contact bench completed: an unchanged anatomical lf_tarsus5 mesh
pushes an unactuated spring-damped slider. Four conditions cross motor pulse
with contact enabled/disabled. Only pulse plus contact moves the slider
(0.042211934829454983 mm maximum); the other three remain exactly zero. All
four 10,000-tick runs have zero warnings; CSV checks confirm finite values,
clock, pre-pulse equality and absence of motion without contact. Evidence:
reports/contact_native.json. This is a single engineering test fixture, not the
three-axis joystick/throttle cockpit or neural control. No tissue parameters or
motor-neuron mapping are inferred from this result.

Persistent physical runtime implemented in native/body.h and native/body.cpp:
bounded joint input, explicit reset, state snapshot and physical control position.
Nine ABI checks pass, including chunk equivalence and exact continuation after
same-model in-memory restore into a new instance (reports/body_abi.json).
Rust feature `body` owns the handle and drives 100 native chunks; all 100 sampled
control positions/times exactly match the standalone C++ contact diagnostic
(reports/body_rust_comparison.json). Native runtime contains no pulse controller;
the explicitly named Rust diagnostic supplies test inputs. This is not brain
integration. Portable authenticated checkpoints, general contact/body observation,
rocket-frame acceleration and the complete cockpit remain outstanding.

Motor interface inventory now joins all 815 motor annotations to the full graph;
381 are annotated as leg motor neurons (135 front, 116 middle, 130 hind).
360 have source MANC body-ID matches; 21 lack them. All 381 lack rootSide, so
somaSide is not promoted to effector side. No joint/sign/gain assignments were
enabled. reports/malecns_motor_audit.json and malecns_motor_candidates.csv bind
the evidence; docs/MOTOR_MAPPING_EVIDENCE.md tracks unresolved requirements.

Publisher MANC motor target supplement 3 is acquired and hash-pinned. Exact ID
join resolves 349/381 leg entries; 11 referenced IDs are absent and 21 have no
reference ID. Preserved 120 label disagreements, 53 limb-only target labels,
and missing confidence for every joined leg entry. Zero compared side-metadata
disagreements does not prove target laterality. No automatic actuator assignments
were made. Evidence: reports/motor_target_join.json and motor_target_conflicts.csv.

Correction after checking dataset-tooling documentation: mancBodyid is predicted;
mancGroup is curated. The 349 exact-ID lookups above are not confirmed identities.
Curated-group resolution yields 150 leg cells with agreeing named muscle targets,
39 with limb-only targets and 192 without curated groups. None is removed from
the graph. Author supplements 3 and 6 agree on targets for all 264 shared IDs.
Evidence: reports/curated_motor_resolution.json. Mechanical mapping remains off;
only the curated/explicitly hypothesized interface may proceed to validation.

Knee-axis calibration now checks anatomical opening-angle derivatives at five
near-neutral offsets and two finite-difference steps on all six legs. Positive
pitch closes the knee, negative opens it. Eighteen native 10 ms runs (zero,
positive and negative torque per leg) confirm physical joint response directions;
the persistent ABI regression still passes for the new library hash. Evidence:
reports/knee_axis_calibration.json and knee_torque_checks.json. A disabled draft
maps 24 curated flexor/extensor candidates onto six knee joints, with gains and
activation constants deliberately unspecified. Laterality and pure-axis muscle
approximation are explicit hypotheses, not validated physiology. Remaining 357
leg motor neurons stay in the full CNS and require interfaces for their actions.

Huang/Luo MB reference acquired at commit 5d7c08a9a88f923169a0c3008aca68af421e9a7f.
Research translation reproduces all 18 saved author Figure 5d numeric panels:
108 protocols, 1944 values, maximum error 7.105427357601002e-15. No fresh MATLAB
execution or parameter fit occurred; comparison uses the source FIG's CData.
This is an aggregate recurrent model, not a per-spike local plasticity rule.
Transfer to full MaleCNS remains an explicit unvalidated hypothesis; no CNS
weights were changed. Evidence: reports/huang_figure5d_comparison.json and
docs/PLASTICITY_REFERENCE.md.

Native C++ FP64 Huang reference now reproduces all 1944 author Figure 5d numeric
values (maximum error 7.105427357601002e-15). Twenty-one additional numerical
cases around the three-hour decay transition and through 24-hour rests match
the NumPy translation. These are aggregate-reference checks, not full-CNS local
plasticity or independent biological validation. Evidence:
reports/huang_native_figure5d_comparison.json and huang_decay_branch_checks.json.

Full MaleCNS chemistry audit now verifies source and graph arrays and aligns all
167,216 candidates. Of these, 3,142 have unclear consensus (589,524 outgoing
rows), 514 have no chemical record (zero internal outgoing rows). All uncertainty
and source fields are retained; no edge is dropped or assigned a physiological
sign. There are 20,128 individual-prediction/consensus differences. Evidence:
reports/malecns_neurochemistry_audit.json; interpretation in docs/NEUROCHEMISTRY.md.

Visual anatomical index acquired from the author's v1.0 column workbook and
joined to full-graph IDs: 1,772 columns, 1,764 L1, 1,299 R7 and 1,329 R8 cells.
All 924 missing slots and eight entirely empty columns remain explicit. One L1
hex-coordinate conflict (body 534860) is recorded without overwriting either
source. No optical ray map, phototransduction or visual brain input is enabled.
Evidence: reports/optic_column_index.json and docs/VISION_MAPPING.md.

R1-R6 anatomical column inference completed on original full-graph contacts:
3,235/3,377 cells have a common maximal column across multiple L1/L2/L3 anchor
types, 90 have one-type support, 42 no available anchor contacts, 10 tied or
disagreeing results. All 8,550 supporting graph rows and every column weight are
preserved; affected inputs flag the known L1 coordinate conflict. All candidates
remain disabled until optical/physiological validation. Evidence:
reports/r16_column_inference.json and docs/R16_COLUMN_INFERENCE.md.

First native mechanical diagnostic video recorded and verified: 90 frames,
1920x1080 at 30 fps, three simulated seconds across four independent physical
worlds (contact off/on crossed with diagnostic pulse off/on). Only contact plus
pulse moves the passive slider, maximum 0.042507060983613724 mm. All 360 frame
state snapshots are hash-bound with the video, executable and model export in
reports/contact_video.json. Native MuJoCo OpenGL used Intel UHD Graphics; this
is not a GPU performance benchmark. A decoded frame was visually inspected.
No brain, rocket, learning or scripted pose animation is in this diagnostic.
The journal records frame qpos, not a complete resumable experiment state.

Optical reference acquired from author eyemap_T4 commit
99d2a43123db636cedb55af9ff31a59657e7d17e. Export preserves all 1,709 measured
smoothed axes (857 left, 852 right) and cone/lens correspondence. Independent
geometry and unit-vector checks pass at maximum error 2.22e-16. Evidence:
reports/optical_reference_export.json. These are another specimen's directions;
no MaleCNS or body registration is asserted and no sensory input is enabled.

Author eye registration audited through all cone/lens/Mi1 index permutations:
778 FAFB matches reproduce stored rays exactly; 74 right lenses and one Mi1 row
are unmatched. The 39 auxiliary boundary rows are explicitly synthetic and
excluded from measured-ray registration, not mistaken for biological inputs.
Evidence: reports/eye_registration_audit.json. This establishes source semantics,
not a MaleCNS map; body IDs remain empty and sensory input remains disabled.

Native fixed-ray panorama sampling implemented behind a C ABI with precomputed
lookups and no allocation during sampling. All 1,709 optical reference rays plus
seven boundary directions agree with an independent Torch CPU image sampler to
1.1920928955078125e-7; analytic axis tests verify orientation separately. Invalid
pixels/dimensions and overlapping buffers are rejected without output mutation.
Evidence: reports/retina_native.json. This is linear RGB engineering sampling,
not compound-eye integration, phototransduction or enabled neural input.

VisTrans reference acquired at ba096778d4bd895a0e0fab02b9c519c5941bc82b with
BSD license and source hashes. Unchanged FP64 author membrane CUDA kernel now
executes four fixed-current protocols for 10,000 ticks (1 s), compared at all
six states against independent scalar CPU equations. Maximum voltage error
1.7763568394002505e-14 mV. Strong-current transient +13.33 mV occurs in both;
injected currents are diagnostic, not physiologically calibrated light stimuli.
Evidence: reports/photoreceptor_membrane_comparison.json. No photon cascade,
graded synaptic coupling or full MaleCNS visual physiology is enabled yet.

Photocurrent reduction tested on GPU with three 30,000-microvillus receptors.
Author output matches direct sums but racecheck finds five warp shared-memory
warnings. Adapted register shuffle reduction preserves the current formula and
matches direct sums, with zero racecheck errors/warnings on the same fixture.
Original negative evidence is retained; reports/photocurrent_reduction.json
binds both versions' evidence. Stochastic cascade execution remains pending.

First complete 0.1 ms photoreceptor step now executes on GPU for two receptors
with 30,000 microvilli each (0 and 100,000 photons/s). Original cascade work queue
has two racecheck warnings. Register warp-index broadcast removes them on this
fixture without editing reaction bodies. Evidence: reports/phototransduction_step.json.
This supersedes execution-pending above, but does not validate light responses,
partial warps, long trajectories or full MaleCNS sensory coupling.

Full photon pilot advanced to 100 ms (1,000 persistent steps, two receptors,
30,000 microvilli each). At 0/100,000 photons per second, final voltages were
-81.992495 and -18.966943 mV; adaptation changed only in the illuminated case.
Finite states and membrane gate bounds passed. Evidence:
reports/phototransduction_100ms.json. One seed/intensity is a numerical response,
not validated physiology; published light-protocol comparison remains required.

Author Figure 15 timing reproduced for a single intensity: 0.5 s dark followed
by 1.5 s at 100,000 photons/s, plus dark control. Before onset outputs match
exactly; light peak -11.7282 mV at 0.5346 s drops to a late-window mean -32.8290 mV.
Complete 20,000-row trace and plot recorded in reports/photoreceptor_onset.json.
Qualitative response agrees with published model behaviour; raw biological
recordings and numeric source curves are not yet compared. One seed only.

Repeated thread-RNG runs with identical seed/launch differed by 1.3176 mV;
negative evidence retained in reports/phototransduction_repeatability.json.
A separate per-microvillus RNG variant now produces byte-identical voltage and
adaptation CSVs across two 100 ms runs. Evidence:
reports/phototransduction_entity_repeatability.json. Reaction equations remain,
but random stream assignment changes. Full-state replay, checkpoint restore,
statistical equivalence and this variant's sanitizer checks remain outstanding.

Entity-RNG memcheck/initcheck/racecheck/synccheck now all pass on ten full steps,
both at 2 x 30,000 microvilli and an artificial 2 x 30,001 partial-warp boundary.
Reports: phototransduction_entity_sanitizers.json and
phototransduction_tail_sanitizers.json. Short-runtime checks do not establish
full-state replay, long-illumination coverage or statistical biological fidelity.

Entity-RNG in-memory checkpoint continuation now passes: snapshot at tick 500,
advance to 1,000, restore into the same instance and repeat. All 3,720,160 bytes
of persistent final state and every repeated recorded voltage/adaptation sample
match exactly. Evidence: reports/photoreceptor_checkpoint.json. This is not yet
a portable checkpoint or fresh-process restore; Molab resume remains incomplete.

Entity-RNG photon diagnostic now runs on 16 CUDA blocks with byte-identical
voltage/adaptation traces to the one-block 100 ms run. Observed wall time drops
from 12.0668 to 1.37536 s for two receptors, including startup and per-tick host
recording. Evidence: reports/phototransduction_launch_equivalence.json. No
whole-brain speedup or full molecular state equivalence is asserted.

The one-versus-16-block comparison is now extended to full persistent state:
from a common tick-500 checkpoint, both continuations to tick 1,000 yield all
3,720,160 bytes equal, including molecule and RNG state, and identical recorded
trajectories. Evidence: reports/photoreceptor_launch_state.json. Scope remains
one seed/intensity and two receptors; portable/fresh-process restore is pending.

Graded lamina/Neurodriver references acquired with immutable commits and licenses.
AST audit finds a concrete historical/current parameter-name mismatch on nine
MorrisLecar cells (V_K, g_Ca, g_K versus old V_k, G_Ca, G_k). Conductance template
is continuous and saturated; current reversal, scaling and delays require
separate semantics. Evidence: reports/graded_interface_audit.json. No cartridge
graph or parameter set is silently substituted for full MaleCNS.

Graded current/scaling semantics traced to author LPU and Aggregator. Five
compiled CPU fixtures pass threshold, linear/saturated conductance and reversal
sign cases. Historical scale multiplies both slope and saturation; current delay
loader expects seconds and stores a phase-dependent buffer offset. Evidence:
reports/graded_transfer_fixture.json. Dynamic delay/circuit implementation and
physiological transfer remain pending; this fixture is not a replacement graph.

Original MorrisLecar CUDA membrane template now runs four one-second current
protocols with explicit historical parameter-name translation. Independent CPU
equations match every recorded V/n sample: maximum voltage error 7.11e-15 mV.
Evidence: reports/morris_membrane_comparison.json. Numerical membrane validation
does not establish delayed circuit behaviour or biological MaleCNS calibration.

Native visual input integration: the image-only Rust path now connects C++ ray sampling and CUDA photoreceptors, with explicit engineering RGB coefficients. Four-image execution and a fresh-process checkpoint continuation pass with identical full final-state hashes (reports/visual_input_verification.json). This is not a MaleCNS optical mapping or a biological gate pass. See docs/VISUAL_INPUT_PIPELINE.md.

The visual incident-edge view now preserves all 99,411 incoming/outgoing/mutual
edge rows around all 6,098 ol_sensory candidates. Incoming edges reach 6,020 of
these objects, so the image-only fixture is insufficient for a full recurrent
CNS. Native photoreceptors now accept and checkpoint signed neural feedback;
independent membrane/adaptation comparison and current-build regressions pass.
Conductance calibration and actual mixed-network coupling remain disabled.
Evidence: docs/VISUAL_BOUNDARY.md and reports/photon_neural_feedback.json.

Dm9 physiological evidence is now pinned and bound to source IDs. Published
functional feedback does not justify blanket inhibitory glutamate weights;
calcium observations are distinct from membrane voltage. Narrow evidence families
annotate 7,842 of the 99,411 retained visual rows; all remain runtime-disabled.
273 Dm9 objects preserve source chemistry and full incoming/outgoing context.
Quantitative calibration and MaleCNS transfer are unperformed. See
`docs/DM9_PHYSIOLOGY.md` and `reports/dm9_physiology_evidence.json`.

Acquired pinned Christenson 2024 visual reference: 73 source/data files, all hashes verified; processed table has 6,205 rows across 14 cell-condition labels, no Dm9 observations. No author model executed or MaleCNS transfer enabled. See docs/CHREYESEES_REFERENCE.md and reports/chreyesees_data_audit.json.

Visual reference progress: checked two pinned author functions against independent FP64 NumPy (max error 1.23e-15); documented paper/source parameterization and solver-tolerance differences. Acquired publisher Extended Data 7 archive: 43,506 complete TeNT time traces among 441,331 rows, not the sought fitted weights. No biological fit or MaleCNS transfer claimed. See docs/CHREYESEES_REFERENCE.md.

Prepared immutable exploratory visual calibration partition: 3,772 calibration / 913 held-out / 1,520 perturbation rows. All original values preserved; independent tuple join confirms no exact stimulus overlap between calibration and holdout. Negative input values prohibit interpreting these columns as photon rates. Animal identities and original gamut selection remain unavailable. No fit or MaleCNS transfer performed.

Implemented native FP64 visual calibration arithmetic from Christenson methods: relative-capture logarithm and weighted uncentered response alignment, with invalid-data rejection and scale normalization. Independent PyTorch checks passed; report reports/visual_calibration_math.json. This does not identify the Parquet export transformation or fit neural parameters.

Started native rocket plant: radial curriculum dynamics with inverse-square gravity, analytical engine lag/impulse, variable fuel mass, depletion split, and first-contact event. Five independent DOP853/analytic diagnostics passed, including a ground crossing hidden inside an upward-reversing step. This is fixture-only C++ physics, not six-DOF flight, cockpit integration, KSP calibration, or a fly landing. See docs/ROCKET_ENVIRONMENT.md.

Implemented Rust landing assessment from privileged physics traces; checks pre-contact velocities, target distance, destruction and continuous sampled stability. Six tests and one explicitly synthetic CLI trace passed. Added strict 3x100 series aggregation unit tests that reject pooled/mixed/missing/duplicate trials; runner integration and provenance remain absent. No actual fly or KSP success. See docs/LANDING_ASSESSMENT.md.

Connected live native MuJoCo body/passive slider to radial rocket at common 0.1-ms steps. Four contact/pulse interventions (40,000 samples) pass: disconnected pulse and contact/no-pulse exactly match baseline; contact+pulse produces max throttle 0.14070645 and velocity effect 0.47649395 m/s. Start-of-step control sampling and analytical engine/fuel recurrences verified. No brain or rocket-to-body acceleration feedback yet. See reports/contact_rocket_causality.json.

Closed radial mechanical feedback implemented: effective cabin gravity = world gravity minus rocket acceleration, converted to body mm/s^2. 480,000 steps across four resolutions pass clock/force/contact-causality checks; freefall has zero effective weight. Feedback alters physical slider and rocket motion. Last refinement changes feedback velocity effect by 5.535%, so magnitude convergence remains unproven. No brain or biological sensor mapping. See reports/closed_mechanics_causality.json.

Extended mechanics refinement at 6.25/3.125/1.5625 us: 2,240,000 new records verified. Same executable for all three new runs. Feedback velocity effect 0.01893538/0.01919244/0.01937321 m/s; last change 0.9331%, meeting the 1% diagnostic comparison threshold for this one-second pair only. General convergence and production time step remain unestablished. Report reports/closed_mechanics_refinement.json preserves original coarse report separately.

Closed-mechanics in-memory continuation verified: snapshot at tick 3,000; fresh body mjData and rocket instance reproduce all 7,000 remaining steps exactly (971 MuJoCo integration state values plus all rocket fields). Same-process/model only, no portable file, neural/sensory/RNG state or recorder continuation. Report reports/mechanics_checkpoint.json.

Added versioned mechanical diagnostic file checkpoints with atomic writer, compiled-model fingerprint and corruption checksum. Fresh process resume at tick 3,000 to 10,000 produces byte-identical final file; six corrupt/mismatched cases rejected without overwriting output. Same-build/airborne only; external binary hashes required, full experiment state still absent. See reports/mechanics_file_checkpoint.json.

Verified and preserved 1,454 annotated proprioceptive candidates; 425 chordotonal objects, 392 via leg nerves and 33 ProCN. Front leg counts only 23L/13R in this annotation subset: not biological completeness. Functional encoder/joint/gain assignments remain null and disabled. Identified Lee 2025 FANC/FlyWire analysis source for follow-up, not transferred to MaleCNS. See docs/PROPRIOCEPTIVE_INPUT.md.

Pinned public Lee FeCO FANC data (7 files, 3.79 MB). Verified 99 distinct annotations; all 18,502 outgoing and 2,315 incoming synapse records join sensory IDs, no duplicate synapse IDs. Derived 2,117/304 pair tables count records, not scores; uncertain maybeclub retained. No CAVE credentials/code execution, no MaleCNS crosswalk or rate-model fit. See reports/feco_reference_audit.json.

Built exact MaleCNS proprioceptor incident-edge view: all 1,454 candidates, 209,361 retained edge rows and 1,183,473 contacts. All selected cells have incoming edges; independent CSR union and source-row/count checks pass, exported hashes verified. Population matches prior registry. This is anatomy only; all sensory profiles remain disabled and full graph is unchanged. See reports/proprioceptive_boundary.json.

Acquired author Mamiya 2018 physiological recordings and imported all 144 numeric arrays losslessly. Independent archive-to-NPZ validation passes: 12 files, 36 protocol tables, 771 response rows, 249,069 paired finite calcium/angle samples; 255 missing angles preserved. Pixel clusters are not individual neurons; cross-file animal identity and body-angle registration are unresolved. No calcium-to-spike conversion, parameter fit or MaleCNS sensory mapping performed. See reports/mamiya2018_validation.json and docs/PROPRIOCEPTIVE_INPUT.md.

Verified Figure 4 driver-to-population assignments and per-region fly counts for Mamiya recordings. Froze response-independent exploratory protocol partition: 244 ramp-and-hold calibration rows, 122 swing assessment rows, 405 broad-driver rows unassigned. All 771 source row identities unique/exhaustive and file hashes verified. Original response clustering and unresolved animal identity prevent claiming independent-animal validation. No parameter fitting or runtime sensory mapping enabled. See reports/feco_protocol_partition.json.

Executed first restricted club/hook motion-to-calcium pilot: nonnegative filtered directional velocity plus intercept, tau selected on ramp-and-hold only. All five regions fail swing transfer against the calibration-mean baseline (MSE ratio 1.45--12.63). Independent scipy.signal.lfilter reproduces predictions and errors. This is a rejected observation-model hypothesis; no runtime neural gains enabled. Exact missing-row exclusions and pre-fit specification preserved in data/derived/feco_motion_pilot_v1. See reports/feco_motion_pilot.json and its validation report.

Diagnosed failed sensory transfer without refitting: frame-derived median peak speeds rise from 119--126 to 360--365 deg/s, and swing median response peaks are overpredicted 1.95--4.62x. Paper motor ramp duration is shorter than imaging interval; exported frame-averaged angles cannot recover instantaneous speeds. Directly applying these gains to high-rate body velocity is invalid. Sampling/observation model remains required; saturation is not established. See reports/feco_transfer_diagnosis.json.

Implemented native held-drive observation state/integral arithmetic for explicit frame averaging. Six high-precision cases, independent pulse quadrature, subdivision consistency and four invalid cases pass. Maximum absolute segment error 1.39e-17; pulse mean error 7.11e-15. No biological kinetics claim or revised sensory fit. See reports/calcium_observation.json.

Added native exposure accumulator with explicit consecutive integer-nanosecond boundaries, held-input splitting at frame edges and retained filter state. Eight 8.01-Hz frames in both coarse and 0.1-ms stepping pass independent quadrature/subdivision checks; five invalid transitions rejected and invalid input leaves state unchanged. This is measurement infrastructure only, not calibrated sensory biology. See reports/exposure_observation.json.

Acquired and visually inspected author Mamiya supplement Figure S5B: independent four-speed calcium-response experiment does not support proportional velocity scaling. Pinned source and structured evidence recorded in reports/feco_speed_evidence.json. No point digitization or quantitative kinetics inferred; acquired MAT archive does not contain the four-speed sweep arrays. This supports retiring the failed linear pilot as a biological default, while preserving its negative result.

Pinned 31 Dallmann 2025 FeCO inhibition source files, all hashes checked. Inspected author thresholded motion/calcium predictor and documented finite-trace normalization, time-grid and source inconsistencies for faithful replication. Dryad metadata available; attempted calibration downloads return API401/public-web403, no data acquired. No author code executed or MaleCNS mapping enabled. See docs/FECO_INHIBITION_REFERENCE.md and reports/feco_inhibition_model_audit.json.

Ported author Dallmann hook_flex/hook_ext/club offline calcium predictor to C++ preserving first derivative duplication, strict threshold inequalities, inclusive linspace and finite-trace kernel normalization. Independent NumPy comparison passes 27 samples across three modes and exact-threshold cases; three invalid inputs rejected. MATLAB and biological data replication remain unperformed; not a streaming sensory encoder. See reports/dallmann_observation.json.

Ran native author-equation threshold predictor on real Mamiya recordings: fixed thresholds/kernel, regional affine fit only on ramp-and-hold; retrospective swing MSE improves 37.9--68.7% over constant baseline in all five club/hook regions. Native outputs independently agree with NumPy for every trace. This is exploratory comparison on a previously observed assessment set, not independent validation or exact Dryad replication. See reports/feco_threshold_pilot.json.

Audited author inhibition circuit identities against exact MaleCNS mancBodyid fields. Two source IDs have multiple matches; SNpp38 author hook selector conflicts with current six campaniform annotations. Preserved all candidates/notes and enabled none. This identifies a concrete cross-release mapping issue before sensory/circuit coupling. See reports/inhibition_crosswalk_candidates.json.

Built complete outgoing anatomical view for ten inhibition-circuit crosswalk candidates, preserving ambiguous alternatives and all weak edges. Verified original CSR endpoints, counts and source row IDs. All six IN09A012 candidates contact SNpp39/SNpp41; descending-to-candidate connections are recorded. These are anatomical observations, not approved identities or functional signs. See reports/inhibition_candidate_paths.json.

Preserved and verified original neurotransmitter evidence for ten inhibition candidates and 15 inter-candidate edges. Six IN09A012 source rows have GABA consensus/ground_truth annotations; DNg100 is ACh. Ambiguous MANC10107 alternatives differ (GABA versus ACh), so arbitrary ID selection could change circuit interpretation. No signs or physiological parameters assigned. See reports/inhibition_chemistry.json.

Extended source-equation C++ observation reference to all six Dallmann branches, with 54 NumPy comparisons and five invalid-input cases passing. External 9A mask is explicitly analysis-only, not allowed as hidden embodied-agent input. Claw source offset inconsistency remains preserved/documented. Full biological experiment not reproduced; public Dryad file downloads remain unavailable (403).

Executed inspected author network defaults/create_model on a 20-ms two-cell Brian2 2.9.0 NumPy fixture. Original reset works; diagnostic removal of w=0 leaves states/spikes exactly unchanged. Avoided an unjustified source correction. Optional cpuinfo helper unavailable but NumPy execution completed. Not biological replication or native equivalence. See reports/dallmann_network_compatibility.json.

Validated existing Torch/native CUDA LIF implementation against unmodified Dallmann author model on signed recurrent five-cell/1,200-step fixture. All 66 spikes match; GPU max voltage error 2.95e-5 mV, repeat bit-exact on physical RTX3070 Laptop. Existing simulation kernel can be reused for this tested equation/scheduling contract. Does not prove full-graph or biological equivalence. Separate author-selectable harness and reports preserve Shiu evidence.

Full-graph chemistry audit covers all 167,216 accepted objects and 25,587,572 edge rows exactly. 3,142 unclear-transmitter cells account for 589,524 outgoing rows / 2,051,771 contacts. 514 missing-annotation objects have zero outgoing rows. Preserved full unknown-ID registries and transmitter-group edge/contact totals; no signs assigned. Global default excitatory weights would hide a substantial assumption, and glutamate/modulatory receptor context remains separate. See reports/full_graph_chemistry_coverage.json.

Executed two full-MaleCNS FP32 CUDA diagnostics on RTX3070: all 167,216 objects and 25,587,572 CSR rows retained, 100 ms at 0.1-ms steps, deterministic DNg100-candidate drive. Declared uniform-LIF assumptions include blanket inhibitory glutamate and zero aminergic electrical weights (not biological defaults). Changing unclear-cell sign yields 5,001 vs 3,059 total spikes; 1,831 neuron counts differ, 9A-candidate events 8 vs 7. Input cell produces 7 vs 9 spikes despite identical 10 voltage injections, reflecting retained incoming network effects. Native finite-state checks passed; no full-graph reference comparison or biological pass. Preserved protocols, weight hashes, per-neuron counts and target events; not complete event recording. See reports/malecns_sign_diagnostic.json and validation report.

Repeated full-graph sign diagnostics with complete sparse spike recording, then ran native FP64 variants. FP32 per-cell counts reproduce original runs exactly. In inhibitory-unknown variant all 3,059 spike events match FP64; excitatory-unknown variant has equal 5,001 total spikes but event times differ, with final voltage/conductance differences up to 0.01454/0.10482 mV. Therefore count agreement alone is insufficient and blanket FP32 equivalence is not claimed. New v2 artifacts preserve complete event ticks/indices, counts, final states and hashes; original v1 evidence unchanged. See reports/malecns_precision_comparison.json.

Independent full-graph CPU reference completed both declared sign hypotheses: NumPy state updates plus SciPy CSR multiplication, exact graph/weight hashes, 167,216 objects, 25,587,572 rows, 1,000 steps. All 5,001 and 3,059 spike events match native FP64 CUDA exactly. Final voltage/synapse differences <=2.85e-14 mV. This establishes numerical equivalence for these two short diagnostic protocols, not physiological correctness or long-run equivalence. Artifacts in data/derived/malecns_cpu_reference_v1; reports/malecns_cpu_equivalence.json.

Full-graph FP64 checkpoint continuation verified for both sign hypotheses: save at tick 500 to flushed file, destroy CUDA handle, create new handle, reload, continue to 1,000 ticks. Every event and final v/g value is bit-exact against uninterrupted runs. This tests new-handle same-process continuation, not process portability or composite brain/body/sensory/plasticity state. Original baseline artifacts preserved; reports/malecns_full_checkpoint.json.

Fresh-process full-CNS FP64 resume verified: a separate Python process reconstructs each complete graph, checks source experiment/specification, library, checkpoint and weight SHA-256 values, loads tick 500 and advances only ticks 500--999. All 3,756 / 1,852 continuation spikes and final states exactly match uninterrupted baselines. Same machine/library only; composite body/sensory/plasticity experiment state and cross-platform portability untested. See reports/malecns_process_checkpoint.json.

Recorded-neural-event physical replay implemented: 14 spikes from actual full-graph FP64 diagnostic, selected by disabled 24-neuron knee draft, drive corresponding six knee axes through explicitly engineering 20-ms filter / 0.1-per-spike gain / unit clamp. MuJoCo compares enabled versus disconnected motor output for 100 ms; all 84,000 actuator samples checked, controls agree with independent analytic spike sums <=3.89e-16, disabled controls zero, maximum physical joint difference 0.01190 rad, no MuJoCo warnings. This is open-loop replay with unvalidated side/muscle assumptions, not a trained fly, validated muscle physiology or sensory feedback loop. Files native/motor_replay_probe.cpp, reports/motor_replay_spec.json and motor_replay_validation.json. Production knee mapping remains disabled.

Extracted native reusable motor filter with preallocated per-channel activity, per-actuator aggregation/clamp, explicit output disconnection and state-only restore. Refactored physical replay remains byte-identical across all 84,000 recorded rows (SHA256 92fc927b0cbb1de3d5a89160ec94d4f371c006b21b57a87a753d28a79ce2e224). Native probe passes 1,000 restored steps exactly, post-aggregation clamp, disconnection, and four invalid-state/shape checks preserving activity. Configuration/clock identity must be checked by checkpoint owner; not a complete checkpoint envelope or closed-loop coupling. See native/motor_filter.h.

Integrated full FP64 CUDA graph and MuJoCo in one C++ tick loop: neural advance -> mapped spikes -> native bounded motor filter -> body step. Two 100-ms conditions (output connected/disconnected), all 5,001 spikes each exactly match prior full-graph baseline; complete 84,000-row physical trace byte-identical to offline replay. Graph has all 167,216 objects/25,587,572 rows under previously declared unvalidated sign hypothesis. No Python in simulation loop. Source graph export 308 MB, hashes recorded. This is a direct native brain-to-body diagnostic, not closed sensory feedback, training, biological motor validation or a rocket flight. See reports/brain_body_native_diagnostic.json.

Extended native full-brain/body loop with radial rocket, passive-slider-only throttle and thrust-derived effective cabin gravity. Four 100-ms motor/contact interventions run without warnings; all neural events match prior baseline, control sampling and body/rocket clocks verified. Neural joint commands move joints, but slider remains at zero and all rocket traces exactly match disconnected ballistic baseline. Lever actuation NOT achieved; negative outcome preserved, no added direct rocket command or retuned gain. No sensory feedback, learned control or landing. See reports/brain_rocket_diagnostic.json.

Acquired and Git-blob-verified the published FlyMimic muscle-model XML and 72 meshes in Molab, pinned to commit 9ea1131; the complete source tarball and reports passed private-HF fresh-directory restoration. MuJoCo 3.14 compiled 15 muscle/tendon actuators. A 100-ms extensor-pulse diagnostic changed the left-front tibia angle by up to 0.411480 rad against the same model without the pulse, with no warnings. This is a candidate biomechanical reference, not a MaleCNS mapping or solved cabin contact. See docs/MUSCLE_REFERENCE.md.

Tested a passive throttle pad with the published FlyMimic model in Molab: four 100-ms contact/pulse conditions, fixed neutral surface gap 0.01 mm, no throttle actuator. Exact foot-pad contacts and slider motion were zero in every condition. The left-front foot moves away from the pad's positive-Y side; the extensor pulse changes its trajectory but does not touch this placement. Corrected an initial broad contact count that had included unrelated contacts. The report and two XML variants passed private-HF fresh-directory restore at revision a55ae956b8e0643d5e05a69981ed54336a631a4c. Geometry and muscle-to-neuron crosswalk remain unvalidated; see docs/MUSCLE_REFERENCE.md.

An explicitly exploratory negative-X pad, placed after examining the first trajectory, produced real foot-pad contacts and passive slider motion in MuJoCo. Contact-off slider motion was exactly zero. Contact-on no-pulse and extensor-pulse runs reached 0.0163085 and 0.00842636 mm respectively; the pulse reduced peak travel. The before-pulse contact traces matched, and all four runs had no MuJoCo warnings. Executed source, model XMLs, traces and report passed private-HF fresh-directory restore at revision 9aea14560ac8865dee3177dc41fd4341e20b5c21. This is causal muscle-to-lever mechanics in a trajectory-informed fixture, not a predeclared cockpit, MaleCNS motor mapping, trained controller or landing; see docs/MUSCLE_REFERENCE.md.

Separated initial passive leg relaxation from muscle actuation in the published FlyMimic model. After 20,000 low-activation steps, copied the identical fly state into eight 100-ms conditions crossing symmetric neutral-surface X pads, explicit contact and tibial-extensor pulse. Only negative-X pad + contact + pulse produced contact (236 exact pairs) and passive slider travel (peak 0.139131 mm); all seven controls stayed at zero. No direct slider actuator or MuJoCo warnings. Executed source, four XML variants, full traces/rest state and report passed private-HF fresh-directory restore at revision 5e2a9137cf66a31c344e34587cc55c9a1bf9cde8. This is a strong isolated mechanical link, but the axis followed earlier exploration, activation and load remain uncalibrated, and there is still no MaleCNS motor mapping, seated body or learned controller; see docs/MUSCLE_REFERENCE.md.

Re-read pinned MaleCNS motor annotations and the original Cheong et al. motor-target table in Molab against the FlyMimic tibia-extensor XML actuator. The two labelled MaleCNS cells 815344 and 815678 reference different curated groups (11657/MNfl41 and 11706/MNfl39); each group has both left and right source members. Predicted MANC body ID 10256 is absent from the target table and 22126 resolves to Tergotr. MN. A one-to-one or mirrored cell-to-actuator mapping is therefore unjustified. The disabled crosswalk report and both original data files passed private-HF fresh-directory restore at revision dcec7fca3973cef84be29da1709b5e8775ea9ed0. See docs/MOTOR_MAPPING_EVIDENCE.md.

Archived full-graph motor events were checked directly in Molab against their original HF manifest, protocol and SHA256 objects. In the 100-ms artificial direct-drive LIF diagnostic, MaleCNS tibia-extensor candidate 815344 emitted two spikes at ticks 190/641 with unclear signs excitatory and 190/761 with unclear signs inhibitory; candidate 815678 emitted none. The 12-ms timing shift shows model sensitivity to an unresolved transmitter assumption. The machine-readable audit and executable source passed fresh-directory HF restore at revision 3c85a259d5b6e4ebca23929a086ea695e5392f2f. This identifies a real neural event source for an explicitly diagnostic muscle replay, not validated motor physiology or a controller. See docs/MOTOR_MAPPING_EVIDENCE.md.

Replayed both archived event variants through the pinned FlyMimic tibia-extensor muscle and previously defined passive negative-X pad in Molab. The declared engineering filter (0.1 per spike, 20-ms decay) drove eight 100-ms conditions crossing motor output and foot-pad contact. In each variant, connected motor and contact yielded 62 exact contacts and 0.001548796-mm peak slide travel; first contact/motion occurred at tick 446 after the first spike at 190 and before the second. Motor-disconnected and contact-disconnected controls had zero slide motion. Independent trace analysis verified pre-spike equality and filter controls to <7.7e-17 error. Executed source, traces and report passed fresh-directory HF restore at revision e182a60a26e92e01da491e602f8f8a71d6e6bbd7. The motor-unit match and gain are assumptions; no closed sensory loop, seated cabin, physiological validation, learning or landing is established. See docs/MUSCLE_REFERENCE.md.

Pinned and read the original FlyMimic v1 paper in Molab: its force and velocity parameters are estimated/optimized, and its imitation policy outputs continuous per-muscle input, not a validated spike-to-activation rule for either MaleCNS cell. A predeclared 4-gain x 3-decay x 2-sign x 2-contact sensitivity grid completed 48 physical 100-ms runs. Only 5/12 filter settings per sign variant caused foot-pad contact and slide motion; all no-contact slides stayed zero. The arbitrary-grid fraction is not a biological probability. Central-case contact counts matched prior replay and numeric trace differences were at roundoff scale. Source, full recorded grid traces and report passed private-HF fresh-directory restore at revision 64ff8a0c159c607e6df0c6682a168dfcab6c81ae. This shows that physical contact is sensitive to an unmeasured neural-muscle interface; no fitted parameter has been promoted to biology. See docs/MUSCLE_REFERENCE.md.

The 3x100 landing-series assessor is now reachable as `assess-landing-series`.
It reevaluates all 300 supplied physics traces, rejects mixed environments,
missing/duplicate pairs and reused trace paths, and emits per-trace SHA-256
evidence. Seven local Rust tests pass, including a 300-file CLI integration
fixture. The fixture contains synthetic failures. It establishes neither KSP
provenance nor a trained fly; no actual landing series has run.

Full-MaleCNS mushroom-body boundary audit now verifies graph hashes and counts
the original KC, MBON and DAN populations and all nine directed class-pair
pathways. It identifies 61,210 KC-to-MBON anatomical rows without assigning
plasticity, a teaching signal or parameters. Report:
reports/malecns_mb_plasticity_boundary.json. The Huang aggregate reference
still has no justified per-synapse MaleCNS transfer.

The MB boundary report now also binds the raw source edge schema/hash and
original transmitter annotations. The edge table lacks synapse coordinates,
so compartment-specific KC-to-MBON plasticity cannot be inferred from pair
counts or instance labels. Two PPL203 DANs have unclear transmitter consensus.

The official MaleCNS 6.8-GB synapse-partner table was fully streamed in a
foreground CPU Molab notebook. Two downloaded filtered Parquet files contain
all 463,640 KC-to-MBON contacts. Independent local reconciliation matches all
61,210 source graph pairs exactly; 28 source neuropil labels are retained.
An independent full repeat used GCS generation `1780494942562468` for every
source read. Its 19,911,178-byte Parquet was transferred in five chunks,
reassembled to the reported SHA-256, and matches the first extraction row for
row in source order.
The coordinate data remain anatomy only. A name-matched Huang module audit
shows broad-lobe ROI labels cannot isolate α2 versus α3 or assign a local
dopamine learning signal. Reports: malecns_mb_synapse_reconciliation.json and
malecns_huang_module_anatomy.json. No MaleCNS plasticity enabled or biological
memory validation passed.

Handler 2019 γ4 source protocol and MaleCNS name-matched transfer boundary
checked in `reports/malecns_handler_gamma4_transfer.json`: 36,320 KC contacts
onto two MBON05 candidates, 50 PAM08(y4) and 14 PAM07(y4<y1y2) candidates.
The measured readout is KC-evoked MBON calcium before/after a single pairing;
the source does not publish per-contact weight trajectories and offers raw data
on request. Broad `gL` labels and absent KC receptor annotations prevent
assigning a local dopamine rule. Next anatomy query must locate candidate DAN
release sites and γ4 boundaries; this alone still cannot determine kinetics.

The pinned PAM spatial query is complete: 81,367 partner rows in broad `gL`,
with exact transferred SHA-256. MBON05 KC contacts are predominantly nearer
PAM08(y4) output sites than PAM01(y5) sites; MBON01(y5B′2a) reverses that
ordering, including equal-site-count and per-KC checks. MBON27(y5d) is mixed.
See `reports/malecns_pam_mb_spatial.json`. This supports a spatial candidate
for γ4 while leaving dopamine volume transmission, receptors and quantitative
plasticity unresolved. The main model remains unchanged.

Constructed and independently verified a flat KC→MBON contact/site/CSR view
from the pinned source: 463,640 contacts, 391,849 presynaptic coordinate keys,
61,210 original graph edges. 65,275 site keys serve multiple MBON partners
(137,062 contact rows). The verifier reconstructs source coordinates,
confidence, ROI and graph pairs/counts from the serialized SoA. This is a
necessary layout for testing shared presynaptic versus contact-specific
postsynaptic state; it does not assign efficacy or a plasticity mechanism.
See `reports/malecns_mb_contact_layout.json` and `docs/PLASTICITY_REFERENCE.md`.
Local public-source FlyMimic restoration and replay (2026-09-24): pinned XML plus 72 mesh assets were restored from public GitHub and verified per Git blob/SHA-256. MuJoCo 3.14.0 compiled the model locally; an artificial tibia-extensor pulse reproduced the prior 0.411480-rad knee response. A separate passive negative-X pad diagnostic from the relaxed body state produced 234 exact foot-pad contact samples and 0.162598-mm maximum slide only when both contact and the artificial muscle pulse were enabled; all three controls stayed at zero. This validates an isolated mechanical causal path, not a neural-muscle mapping, seated cockpit, closed-loop rocket control, learning or landing. See docs/MUSCLE_REFERENCE.md and reports/flymimic_passive_throttle_local.json.
Replayed those measured full-FlyMimic slider traces through the existing native radial rocket plant at 0.1-ms steps. The first nonzero throttle occurred one tick after first foot-pad contact; maximum throttle was 0.541795, and the largest velocity difference versus ballistic control was 0.035769 m/s over 100 ms. All three no-effect conditions yielded identical rocket traces; independent thrust/fuel recurrence checks passed. This remains a one-way prescribed-muscle diagnostic without neural mapping, rocket-to-body feedback, landing control or KSP execution. See reports/flymimic_rocket_replay_local.json.
Added an exploratory two-way mechanical loop using the same native rocket plant through a C ABI and MuJoCo 3.14.0 FlyMimic. Eight 100-ms cases crossed contact, prescribed pulse and thrust-derived effective cabin gravity. Only contact plus pulse moved the slider; closed/open trajectories agreed through first nonzero command, then differed by at most 1.574e-6 mm in slider and 2.660e-7 m/s in rocket velocity. This small feedback result is in a fixed-body, uniform-gravity, co-falling diagnostic frame initialized from a source-gravity relaxed pose; no validated cockpit, neural-muscle interface, learning or KSP landing. See reports/flymimic_rocket_feedback_local.json.
Replayed original local FP64 full-graph MaleCNS event arrays into the public-source FlyMimic tibia extensor using a declared hypothetical 0.1-per-spike, 20-ms filter. Eight conditions crossed the two unclear-transmitter-sign variants, motor connection and foot-pad contact. Only the two connected-contact conditions moved the slide: 64 exact contacts, first tick 446, peak 0.001446 mm; all six controls had zero slide. This uses artificial CNS voltage-jump stimulation and an unvalidated motor-unit assignment/gain, so it is a labelled causal diagnostic rather than biological motor validation or trained flight. See reports/flymimic_cns_event_contact_local.json.
Fed those measured eight slider traces into the native rocket plant. In both connected-contact variants, throttle first became nonzero on tick 447 after first foot-pad contact on tick 446; peak throttle was 0.004814 and maximum velocity difference from ballistic control was 0.000143 m/s over 100 ms. Six controls had identical rocket trajectories, with engine/fuel recurrences independently checked. This is a one-way local replay with artificial CNS stimulation and hypothetical muscle mapping; no live KSP run. Current machine had no running KSP process, standard Steam install or kRPC Python client. See reports/flymimic_cns_event_rocket_local.json.
Removed the event file from the CNS-to-FlyMimic execution path in a local diagnostic: the complete native FP64 MaleCNS graph advanced live for 1000 ticks alongside four physical bodies. All 5001 graph events matched the pinned prior event array exactly, and all four control/contact/slide traces matched the offline replay exactly. Only connected motor plus contact yielded 64 exact contacts and 0.001446-mm slide. This validates online numerical integration and local mechanics under artificial voltage-jump input, but there is no body-to-neuron sensory feedback and the motor-unit filter/mapping remains hypothetical. See reports/live_cns_flymimic_local.json.
Audited the first physical-to-CNS proprioceptive mapping prerequisite: among 23 left-root, ProLN-entering chordotonal MaleCNS candidates, one SNpp50 cell has a direct graph edge to motor candidate 815344, and 15 have two-edge paths; the three SNpp39 candidates each have 8/9/11 two-edge paths but no direct edge. Public VFB classifications show SNpp39 as hook in a MaleCNS ProLN cell and club in a MANC MetaLN cell, so a type-only subtype assignment across specimens/segments is unsafe. No encoder, joint binding or gain was enabled; see reports/lf_proprio_motor_paths.json and docs/PROPRIOCEPTIVE_INPUT.md.
Executed a first exploratory full-graph physical proprioceptive loop after freezing configs/lf_claw_closed_loop_probe.json: left-front knee position drove one anatomically eligible SNpp50 cell under positive/negative 200-mV/rad half-wave hypotheses, while the full FP64 MaleCNS and FlyMimic advanced live. Positive feedback changed sensor input at tick 192, added the sensor cell spike at 228, changed the motor candidate at 403 and the slide at 424; total graph events were 6742 versus 5001 blocked, and slide peak 0.040124 versus 0.001446 mm. Negative polarity produced no new event. An additional motor break with the same positive sensory sequence preserved every neural event but yielded zero contact/slide. This is a causal engineering loop with artificial central drive and unmeasured sensory/motor gains, not a biological reflex validation, trained pilot or KSP landing. See reports/lf_claw_closed_loop_local.json and reports/lf_claw_motor_break_replay.json.
Corrected that first loop's sensory-mask interpretation: the mask invokes zero refractory for Shiu Poisson targets, which yielded 333 SNpp50 spikes per 100 ms and overstated this candidate feedback effect. A second frozen-spec run kept all other inputs and mechanics identical but used the ordinary 22-tick refractory interval for SNpp50. The positive branch produced 33 sensory spikes (minimum gap 23 ticks), shifted the second motor spike from tick 641 to 615, and changed slide peak from 0.001446 to 0.002603 mm; first physical input, sensory spike, motor spike and slide differences occurred at ticks 192, 228, 615 and 819. A same-sensory-sequence motor break retained all neural events but gave zero contacts/slide. These are still uncalibrated engineering parameters, not measured MaleCNS receptor physiology. See reports/lf_claw_closed_loop_refractory_local.json and reports/lf_claw_motor_break_refractory_replay.json.
Initial-pose correction (2026-09-24): The earlier local FlyMimic muscle, pad, rocket, and SNpp50 loop diagnostics all used ordinary MuJoCo zero reset before passive relaxation. That starts the left-front tibia outside its declared range and settles near 0.4736 rad, whereas the published `default-pose` keyframe specifies 1.862 rad. Their numerical causal comparisons remain valid only in the non-keyframe fixture. New source-keyframe diagnostics show opposing extensor/flexor knee effects at pulse end (-0.473258/+0.790246 rad relative to control), retained after two seconds of passive settling from the keyframe (-0.265014/+0.721853 rad). This reverses an apparent same-direction finding near the zero-start lower boundary. No source-keyframe foot-pad, closed neural loop, biological response, or landing validation follows from this test. See reports/flymimic_keyframe_mechanics_local.json and docs/MUSCLE_REFERENCE.md.
Source-keyframe contact follow-up (2026-09-24): Derived pad positions from the foot mesh in the direct `default-pose` and after a 2-second passive settle from it. Across 16 posture/side/contact/pulse cases, the settled positive-X pad showed 92 exact contacts beginning at tick 220 and 0.227188-mm passive slide travel only with the extensor pulse and contact enabled; the three matched controls had no contacts or slide. In direct keyframe, positive-X contact began at tick 95 even without a pulse, so its slide is not evidence of pulse-caused first contact. This is a geometrically revised local diagnostic; the pad, pulse, motor map and posture as physiological stance remain unvalidated. See reports/flymimic_keyframe_contact_local.json.
Live full-CNS keyframe-derived motor contact (2026-09-24): Advanced all 167,216 nodes and 25,587,572 edge rows for 100 ms in FP64 CUDA while stepping four source-derived FlyMimic pad/motor control bodies. All 5,001 neural events exactly matched the preserved reference under identical artificial central input. Hypothetical motor spikes at ticks 190 and 641, the former preceding first contact and slide movement at tick 247. Connected motor plus contact produced 142 exact contact samples and 0.048848-mm peak slide travel; all three disconnected controls had zero contact and slide. This corrects initial geometry for the diagnostic but does not validate neuron-to-muscle identity, activation gain, biological sensory response, cockpit, learning, or KSP landing. See reports/live_cns_flymimic_keyframe_local.json.
Full-CNS keyframe-derived proprioceptive loop (2026-09-24): Reused the source-keyframe-derived positive-X pad and ordinary 22-tick SNpp50 refractory interval in four 100-ms full-network physical cases. Under the explicitly hypothetical 200-mV/rad knee encoder, positive polarity stayed inactive, while negative polarity first changed drive at tick 1, first added SNpp50 event at 86, changed candidate motor activity at 188 and slide at 245. It yielded 38 sensory spikes, 4,843 total graph events and 0.072597-mm peak slide, versus blocked-feedback 5,001 events and 0.048848 mm. A fixed-sensory-sequence motor break preserved exact full-neural events yet produced zero pad contacts/slide. These show numerical feedback and causal motor output in the fixture, not measured SNpp50 physiology, a natural reflex, or trained control. See reports/lf_claw_closed_loop_keyframe_local.json and reports/lf_claw_motor_break_keyframe_replay.json.
Claw calcium polarity evidence (2026-09-24): Audited source-pinned Mamiya 2018 R73D10 GCaMP6f X/Y/Z branch ramp recordings using per-row median high-angle minus low-angle decile responses. The 120 pixel-cluster rows split 59 positive / 61 negative, and 59/60 paired clusters in each fly/protocol/branch observation had opposite signs. This shows that both response polarities occur in these calcium clusters. It does not assign an individual MaleCNS SNpp50 cell, quantify spikes/membrane current, register its angle convention to FlyMimic, or calibrate 200 mV/rad. Runtime remains unchanged. See reports/mamiya_claw_angle_polarity.json.
Head-orientation visual path (2026-09-24): Added stateless native rotation of body-local optical rays into world panorama coordinates with right-handed orthonormality checks, exposed through Rust and the image-to-photoreceptor path. An independent 80-ray NumPy oracle matched native identity/yaw/pitch samples exactly. A fixed bright image with 180-degree head yaw switched a synthetic two-ray fixture's photon rates from [100000,0] to [0,100000] photons/s and changed receptor voltages; same- and fresh-process checkpoint continuations matched final state exactly. The pose matrix is recorded per frame. This supplies pose-aware visual input infrastructure, not a measured FlyMimic eye alignment, MaleCNS ray/neuron registration, biologically calibrated vision, or KSP imagery. See reports/retina_orientation.json and reports/visual_head_pose_verification.json.
FlyMimic-head visual pose follow-up (2026-09-24): Extracted head rotation matrices through MuJoCo from the source `default-pose` and an XML copy with prescribed 180-degree thorax yaw; transformed matrix exactly equaled world yaw times source matrix. Fed these recorded matrices, not hand-entered fixture rotations, into a fixed-image synthetic two-ray receptor run. Rates switched [100000,0] to [0,100000] photons/s and a fresh-process checkpoint resume matched the final full receptor state. The head is fixed to thorax and root yaw was prescribed, so this checks body/vision coordinates only; no dynamic flight, measured optics, MaleCNS neuron-ray map or KSP imagery. See reports/visual_body_pose_source.json and reports/visual_body_pose_verification.json.
Visual column/sensory reconciliation (2026-09-24): Independently joined the author's 4,392 optic-column assignments to the exact 6,098-cell MaleCNS visual sensory boundary. All 1,299 R7 and 1,329 R8 assigned cells match sensory IDs, graph indices and types; all 1,764 L1 cells are downstream, outside the sensory subset. The sensory population partitions completely into 3,377 R1-R6 without these column assignments, 2,628 column-assigned R7/R8, 86 unassigned R7/R8-like cells, and seven HBeyelet. No optical rays are assigned. This prevents L1 being driven as a receptor and identifies the exact unresolved input population; it does not create a cross-specimen ray map. See reports/visual_column_boundary_reconciliation.json.
Free-root body diagnostic (2026-09-24): Added only a MuJoCo freejoint to the published fixed-thorax FlyMimic XML and preserved every original joint coordinate in its `default-pose` keyframe, with unchanged actuator/tendon counts. In 100 ms at low activation, zero gravity had no contacts and whole-body COM drift at most 1.85e-6 mm; under published gravity the exact floor contact began at tick 142 (14.2 ms), without MuJoCo warnings. This shows that the pinned articulated body does not supply unsupported free flight; wing aerodynamics and a cabin remain to be built and verified. See reports/flymimic_free_root_local.json and docs/FREE_ROOT_BODY.md.
Free-root support check (2026-09-24): Extended the same source-gravity, low-activation variant to 2 s. The thorax up vector ended nearly opposite world up (dot -0.994710), and the head, thorax and both wings contacted the floor. A free body simply resting on a floor is therefore not a viable upright cabin operator in this diagnostic. A physically explicit seat/harness or active posture stabilization is required before reusing the fixed-root foot-pad result in a free body. No warnings occurred. See reports/flymimic_free_root_local.json.
Explicit harness/foot control diagnostic (2026-09-24): Added a named, finite-compliance thorax-to-world weld with the inverse published thorax pose to the free-root FlyMimic. At source gravity for 2 s, root translation remained under 0.000019 mm and thorax-up dot world-up was 0.99999968, with no floor contact. Re-derived foot-pad positions from this harnessed state because its joint coordinates differed from fixed-root relaxation by up to about 0.245 rad. Across eight side/contact/pulse cases, only positive-X contact plus the artificial full-strength extensor pulse produced 204 exact contacts from tick 221 and 0.124263-mm passive slide travel; three matched controls were zero, with equal pre-pulse knee traces and no slide before contact. The stiff engineering harness behaves nearly fixed and is not measured seat biomechanics, a neural muscle command, or KSP cabin control. See reports/flymimic_harness_local.json, reports/flymimic_harness_contact_local.json and docs/FREE_ROOT_BODY.md.
Moving-cabin harness diagnostic (2026-09-24): Reparented the explicit thorax harness and passive pad to a common MuJoCo mocap cabin frame. Across eight static/moving, contact and prescribed-muscle cases, the static slide trace exactly replayed the prior harnessed result. With a smooth prescribed 0.1-mm peak cabin displacement over 100 ms, body root motion relative to frame peaked at 0.005946 mm; only motor pulse plus contact moved the passive slider (227 exact contacts from tick 221, 0.109519-mm peak slide), whereas three matched moving-frame controls stayed at zero. This is body/cabin mechanics under a transparent imposed trajectory, not rocket-coupled acceleration, validated biology, or KSP. See reports/flymimic_moving_cabin_local.json.
Native rocket to moving-cabin diagnostic (2026-09-24): Extended the native rocket ABI with current-state and radial-gravity queries, then used an inertial MuJoCo frame translating at the rocket's initial -20 m/s to avoid a 38-mm artificial harness lag from directly imposing absolute cabin position. The initial 0.01-mm pad gap produced unwanted no-pulse contact and engine command at tick 186. A preserved 0/0.05/0.10/0.20-mm offset sweep showed that 0.05 and 0.10 mm suppress this control leak while retaining artificial extensor-pulse contact; 0.20 mm suppresses both. At the exploratory 0.05-mm offset, first pulse-driven contact/slide was tick 255, first throttle tick 256, peak slide 0.169170 mm; no-pulse and contact-off controls stayed zero. Actual rocket-motion feedback versus ballistic cabin-motion ablation first changed slide at tick 261 and rocket altitude at tick 330, by at most 5.86e-6 mm and 2.12e-8 m over 100 ms. This is a small uncalibrated mechanical loop, not biological or useful landing control; the clearance was selected after the sweep. See reports/native_cabin_gap_verification.json and docs/FREE_ROOT_BODY.md.
Correction (2026-09-24): The independent zero-gravity Galilean check of this `mocap` plus weld interface failed: 37.9615-mm relative root error and 0.247-rad joint error after 10 ms (`reports/mocap_galilean_check.json`). The preceding moving-cabin feedback numbers are numerical observations, not physically validated cabin feedback. A fixed cabin-local, co-falling alternative applies effective gravity `-thrust/m` directly. In its exploratory 0.10-mm pad-gap case, no-pulse and no-contact controls had zero slide; prescribed full-strength pulse plus contact gave first slide at tick 440, throttle at 441 and peak slide 0.024728 mm. At 0.05 mm, no-pulse contact still occurred; at 0.20 mm, pulse contact vanished. Feedback changed slide by at most 5.92e-8 mm. This does not calibrate fly physiology or demonstrate landing. See `reports/harness_effective_g_gap_100um_local.json` and `docs/FREE_ROOT_BODY.md`.
Native cabin-frame ABI contract (2026-09-24): `tools/check_rocket_cabin_frame.py` independently checked radial gravity, `-1000*thrust/(dry_mass+fuel)`, and 0.1-ms tick synchronization over 100 ticks each for zero, intermediate and full diagnostic slider inputs. All assertions passed; this validates ABI arithmetic, not MuJoCo contact mechanics or KSP. See `reports/rocket_cabin_frame_check.json`.
Candidate CNS event replay in the cabin-local model (2026-09-24): Recorded graph neuron 156979 events at ticks 190 and 641, hypothetically mapped at 0.1 actuator command per spike with 20-ms decay, produced first exact foot-pad contact/slide at tick 476 and throttle at tick 477 with a 0.005834-mm peak slide for the exploratory 0.10-mm pad gap. No-event and contact-disabled controls stayed at zero; rocket feedback changed slide by at most 2.70e-9 mm. This is only replay of uncertain-sign candidate events through an unvalidated motor-unit/muscle map and gain, not a sensory-neural loop or landing controller. See `reports/harness_effective_g_gap_100um_events_local.json`.
Unclear-sign sensitivity check (2026-09-24): Alternative inhibitory treatment shifts the second candidate spike from tick 641 to 761 and changes the hypothetical actuator command from tick 641 (maximum difference 0.1). Muscle activation differs from tick 641 (maximum 0.1929), force from tick 642 (maximum 57.87 in model units), and knee angle from tick 642 (maximum 0.007283 rad). Last exact foot-pad contact was tick 559, before this second spike; contact, slide, throttle and rocket-velocity arrays remain identical through 1000 ticks. Thus the event changes limb mechanics but has no cockpit effect in this fixture and window. The shared output does not settle transmitter sign, motor correspondence or gain. See `reports/harness_effective_g_gap_100um_events_unclear_inhibitory_local.json` and `docs/MOTOR_MAPPING_EVIDENCE.md`.
Correction to the preceding tick comparison: its activation and force arrays were sampled at different phases of the MuJoCo step. The one-tick separation cannot be interpreted as physiological muscle latency; the phase-corrected v2 reports supersede timing claims from this historical line.
Candidate-event pad-clearance sweep (2026-09-24): At offsets 50 and 75 µm the no-event control itself contacts and moves the slider; at 100 µm events move the slider without no-event motion; at 125, 150, 175 and 200 µm events do not reach the pad. Only one sampled offset satisfies both diagnostic conditions, and it was chosen after inspecting the fixture. This fragility precludes a claim of calibrated physiological contact or reliable cockpit control. All seven traces and report hashes are checked by `tools/summarize_cabin_event_gap.py`; see `reports/cabin_event_gap_sweep.json`.
Initial-gravity control (2026-09-24): With the same author keyframe, 2-s relaxation under Earth gravity gives left-front knee 0.806424 rad, while relaxation at zero gravity gives 1.126326 rad. The zero-gravity relaxed body does not touch the Earth-placed 100-µm pad under candidate events. Repositioning the pad from the zero-gravity relaxed foot surface by the same bbox rule restores event contact at tick 419, throttle at 420 and 0.020761-mm peak slide, with zero no-event slide. These two controls establish pose and pad-placement dependence; neither pad is a measured cockpit fixture. See `reports/harness_effective_g_gap_100um_events_zero_g_relax_local.json` and `reports/harness_effective_g_gap_100um_events_zero_g_relax_relaxed_pad_local.json`.
Live full-CNS/body/rocket cabin loop (2026-09-24): `tools/probe_live_cabin_claw.py` ran the complete native FP64 graph, harnessed body and radial rocket online at 0.1 ms for 100 ms from zero-gravity relaxation. Under the unvalidated negative-position SNpp50 encoder, 35 sensory spikes changed total graph events from 5,001 to 4,754 and moved candidate motor spike tick 641 to 612. Knee differed from tick 613, after the last foot-pad contact at tick 510. Contact, slide, throttle and rocket velocity were identical to blocked sensory input; the motor-off and contact-off controls had zero slide. The sensor drive peaked at 114.42 mV; central voltage jumps, encoder gain/sign and motor mapping remain artificial. This is a live numerical loop with negative cockpit feedback, not biological behavior or landing. See `reports/live_cabin_claw_local.json` and `docs/FREE_ROOT_BODY.md`.
Central-drive ablation (2026-09-24): A matched four-case live run removed only the ten artificial source-neuron voltage jumps. All four 100-ms cases then had zero full-graph events, exact pad contacts, slide and throttle. Passive knee drift supplied at most 0.005994 mV to the negative-position encoder, versus 35 SNpp50 spikes under periodic jumps. `tools/check_live_cabin_central_necessity.py` checks both reports and all event/trace hashes; see `reports/live_cabin_central_necessity.json`. Thus this fixture's contact depends on artificial central excitation. This does not imply natural MaleCNS silence or validate the biological encoder.
Same-connectome visual source lead (2026-09-24): Hoeller et al., Cell 2026, DOI 10.1016/j.cell.2026.08.014 and the author `reiserlab/visualpathways` repository identify predicted anatomical receptive fields and a `ME(R)-columns-r-theta` retinotopy layer in MaleCNS. This may provide a stronger basis for column/angular registration than transferring the separate eye-map specimen, but no per-column angular table has been acquired or matched to our pinned 1,772 columns. Predicted downstream receptive fields are not measured photoreceptor optical axes. Image-to-CNS assignments remain disabled; see `docs/VISION_MAPPING.md`.


## MoLab KC-to-MBON recovery and gamma1 candidate strata (2026-10-04)

The generation-pinned complete synapse-partner source was recovered directly in
MoLab as 13 immediately archived immutable ranges. Whole-source size
6,777,179,098 bytes and published MD5 58efcf712f8c4d4de5f2ad51e97def76
match; the verified HF composition receipt is
06d9c0131f62f6555529ae045b025f959bce8e3d / manifest
67bba473f9e8289ed0fdb866692ac5242441efe66a61518d41c4906d0a113318.

A fresh full pass over 311,833,243 partner rows in all 4,759 batches recovered
463,640 KC-to-MBON contacts. Every one of the 61,210 pairs agrees with the
pinned candidate incoming CSR; mismatches: zero. Five completed contact shards
were individually archived before continuing. Final report/strata receipt:
633002a94ba6f474f65a482a69549623021ac7b3 / manifest
f7b6479c91af427831e9bc620accb592c9bc20dc04774cb01a920c751e50e155.
See reports/yamada_gamma1_contact_strata_molab.json.

MBON11 annotation candidates 10704 and 11402 receive 41,460 retained KC
contacts from multiple gamma and alpha/beta annotation subtypes. Preserve these
strata for the independent Yamada gamma1 physiology controls; an aggregate
MBON11 gain cannot by itself establish subtype-specific physiology. Annotation
labels and broad lobar ROIs do not establish each contact's gamma1 compartment,
receptor action or plasticity. No learning was enabled. This closes the missing
remote KC-to-MBON coordinate input, not whole-CNS morphology coverage, biological
identity transfer, calibrated local plasticity, body control or KSP acceptance.
All original contract gates remain open pending their own evidence.


## Native Huang memory-reference replay in MoLab (2026-10-04)

The unchanged native C++ FP64 translation at project commit
28c8adb140fb33327fe3754f02ca422b5f9350c1 was built and executed entirely in
foreground MoLab. Thirty original author files were acquired and verified
against Git blobs at 5d7c08a9a88f923169a0c3008aca68af421e9a7f; source,
inputs, build inputs, library, prediction arrays and logs were archived before
dependent stages with verified immutable HF receipts.

All 108 Figure 5d protocols, 18 panels and 1,944 saved author numeric values
agree within maximum absolute error 7.105427357601002e-15 against the frozen
1e-8 threshold. No parameters were refitted. The comparison uses the author's
saved FIG arrays, not a new MATLAB run. Report:
reports/huang_native_figure5d_molab.json. Final HF revision:
9fb1c16c4ce216d541db307d211fcb4f9ac766df, manifest
ddfebe562f3dee29d1fee3fda6595b03341f2ab192724efa26eb18d2611bdaed.

This verifies original aggregate-model numerical reproduction only. It does
not validate independent animal observations, individual MaleCNS synaptic
parameters, receptor-dependent local plasticity or learning. Gate B remains
open for its biological and transfer requirements; no contact learning was
enabled and the full accepted contract remains unchanged.


## Huang physiological workbook scope audit (2026-10-05)

Foreground MoLab inspection found two aggregate mean/SEM sheets, six population
pairs and all six sessions including 24hr; no individual animal recordings.
The author fit includes the 24hr data, so supplied-parameter residuals are
calibration, not held-out physiological validation. Exact author six-weight
selection is columns 1:6 for ACV/ETA and [7:9,4:6] for OCT/BEN. The native ABI
already accepts each selected vector, while both current harnesses hardcode
two imaging sessions and require generalization for this six-session protocol.
See docs/HUANG_PHYSIOLOGICAL_CALIBRATION_AUDIT.md. Verified completed HF audit:
f11f1dbdecce9cd817514225cfe7ad58503c16d7 / manifest
2764ea9b2487c7b7b3adccacb78cec389bee2557709541ce2e0096b7d55220ad.
No new physiological simulation, parameter refit or contact learning was
performed. All full-project acceptance gates remain open.


## Full original Huang calibration protocol in MoLab (2026-10-05)

The reference/native harnesses now preserve fitted nine-weight source parameters,
select the exact six weights for each author odor pair, and support six imaging
sessions plus all-event activity output. All four model/odor combinations agree
across all 51 events and six imaging sessions, with maximum absolute error
9.769962616701378e-15 below the fixed 1e-8 threshold. The unchanged native
library remains pinned; the updated-harness Figure5d regression also retains
its original 1,944-value result. Numerical comparison is against the Python
translation and saved Figure5d arrays, not a fresh MATLAB execution.

The workbook is sparse: included calibration cells are 36/24 for the two-module
ACV/ETA and OCT/BEN cases, 52/34 for the three-module cases. Late 3hr/24hr
sessions supply two observed cells each per odor pair. Missing cells remain
missing. Supplied parameters were not refitted; those 24hr observations already
participated in the author fit. No independent animal holdout or biological
transfer follows from the residuals. All four completed conditions were
immediately archived before advancing. Final verified HF revision:
f7714e1ae6ef05c448534a28e231e670334312d7 / manifest
c54c5c203f139250acb716b3a06d87947804140886ced5ef74cb8962ff2961a7.
Report: reports/huang_six_session_calibration_molab.json. The initial two-session
harness coverage gap is closed; independent physiological/local plasticity,
whole-CNS geometry, embodied control and KSP acceptance remain open. Contact
learning remains disabled. No local computation or result/data download.


## Explicit gamma1 atlas route and complete candidate sampling (2026-10-05)

Official subcompartment atlas v1/v2/v3 and neuPrint debug metadata explicitly
name g1–g5 in both hemispheres. The earlier negative fullbrain v4/v5 result
was scoped to those label lists. Pin v3 IDs 190(L)/195(R), 256-nm grid and zero
offset; the official state attaches this layer in the 8-nm MaleCNS space
without a separate transform. All coordinate/contact processing ran in MoLab.
See docs/YAMADA_GAMMA1_PLASTICITY_GATE.md for source evidence and remaining gates.

All five original contact shards were restored from verified HF receipts.
The complete 41460 MBON11 candidate contacts, both pre/post coordinates and
27-point neighborhoods required 157 chunks. Acquisition pinned 147 available
chunks and recorded ten metadata HTTP404 as unknown, not zero. Each completed
input segment was immediately HF-verified. Final input closure:
fd5ef6b95826bbe33d7dea0e719230a515796049 / manifest
11c50bc6df1322ba054fa1553d6e38183fa1b7931fb4dcbe86a2b58832d3c484.

Full provisional classification reconciles exactly: 23559 robust expected-g1;
1233 center-g1 boundary-sensitive; 1304 near-g1 boundary-sensitive; 11627 outside;
3737 unknown-neighborhood. Independent decoder agreement covers 9408 points.
No contacts were discarded. Final completed classification receipt:
39c79aac825b2e1e0a22677b2d4b9eaff79cd8f0 / manifest
692bde3910691681fdca1afffef4bc7a46ffbee594af501c0c5144a335cc2fda.
See docs/GAMMA_CONTACT_PROVISIONAL_CLASSIFICATION.md and linked MoLab tools.

This closes full candidate volume sampling, not anatomical or biological admission.
Bilateral landmark/territory checks, gamma1-pedc semantics, atlas-version and
boundary sensitivity, subtype/receptor physiology and local plasticity remain
open. Learning remains disabled. Whole-CNS geometry, body/vision, three training
seeds, held-out KSP evaluation and recordings remain required by the original
contract; all original acceptance gates remain open.


## Gamma1 candidate KC subtype join and source-ROI crosscheck (2026-10-05)

A full foreground MoLab body-ID join preserves all 41,460 provisional classified
contacts, original fields and row order, with zero missing presynaptic IDs/types.
Pinned KC annotations yield gamma 27,820 contacts (22,981 robust g1), alpha/beta
13,150 (355 robust), alpha-prime/beta-prime 490 (223 robust). Thus 578 robust
g1 contacts carry non-gamma annotations. Preserve all subtypes and separate
physiology controls; an atlas g1 filter does not isolate gamma-KC physiology.
Joined table/strata/report/log HF: b0038a27253d4ebadb32c2ea2d75785085264a91,
manifest 877edae6b332a5e83a8635143cd198f2440389829ef872d7929d6f26a38b3ce7.
Final family summary HF: ee6efa05066f3b3dcb4be6244ff9b19c21080273,
manifest 70921cd8b0f7b2d836fe8c6c0f8eb673ff7870bc4c1c451818e35a51a46677cd.
See docs/GAMMA_KC_SUBTYPE_STRATIFICATION.md and linked durable MoLab tools.

The prior scalar reclassification agrees for all rows. Source primary_post vs
atlas center has zero lateral mismatches among 29,122 comparable post endpoints.
All 9,189 PED-labeled post contacts have background/unknown atlas labels.
HF crosscheck f0f4c7b0b6f3e002dac2e8487d26da685f18fd3d, manifest
69f1e13a91774e30e81b6b3f25747fffacf40b0c080ea86ba735737093fb45df.
See docs/GAMMA_SOURCE_ROI_CROSSCHECK.md. This is metadata consistency, not
independent anatomical registration.

Primary anatomy describes gamma1pedc innervation across gamma1 and the distal
pedunculus core; whole PED is not a pedc mask. Independent landmarks/DAN
territory, explicit pedc geometry, atlas-version sensitivity and subtype/receptor
physiology remain open. Learning remains disabled. All original full-project
gates and success requirements remain open. All computation/data stayed in MoLab.


## Full candidate atlas v2/v3 sensitivity (2026-10-05)

Complete generation-pinned v2 inputs (157 planned objects;147 available;10 unknown)
were archived in groups before dependent work. Fresh v2 decoding independently
agreed in 9408 format-reader checks. All original contact columns equal the v3
input row for row. Every center and every 27-neighbor pre/post label agrees for
all 41460 contacts, including unknown markers; changed labels/statuses: zero.
All23559 robust expected-g1 contacts are robust in both versions. This closes
v2-to-v3 version sensitivity for this frozen contact/neighborhood sample only,
not whole-volume equality or independent anatomy admission. V1 remains untested.

Verified input closure: c78cc667e5d43c9e1c62239ee8959501edca6851, manifest
d187e5a57c02b5da5a2a53ef888472fa3dd62883ca856d056870a3129c233c0b.
Verified comparison: 36284091f29ac8003b2033e1cda3a14f198b5df0, manifest
d0c8b5441c9c1190c1005f1715b1e14dc93b0f1debcec2a6dd944dceb39d79d9.
See docs/GAMMA_ATLAS_V2_V3_COMPARISON.md and its foreground MoLab tools.
Independent landmark/DAN territory and pedc checks plus physiological transfer
remain open; learning remains disabled. Do not repeat unchanged v2/v3 sampling.
All original full-project goals/gates stay open; no local computation/data download.


## Native no-learning paired-pulse transmission screen (2026-10-05)

The unchanged conductance CUDA runtime at d06ce5a7a68b7a67828b57b15d9d989a3dd287bc
was built and executed on current MoLab Blackwell after pinned CCCL restoration.
Five two-neuron artificial-event conditions ran, each archived before the next.
Native exponential conductance agrees with an independent closed form to maximum
2.1510571102112408e-16 under the frozen1e-10 threshold. Source spikes and 2-tick
delays agree; zero-input control has zero events/conductance. Tail-subtracted
PPR=1.0000000000000004 is the additive-kernel software identity, not physiology.

Equal scalar gains labelled presynaptic/postsynaptic produce identical outputs.
Those labels do not implement actual calcium or receptor interventions. The
static scalar representation cannot encode the published A1/PPR dissociation;
separate release dynamics and justified observation/efficacy remain needed.
Readout is offline current per leak conductance, not absolute EPSC or an actual
voltage-clamp experiment. Full MaleCNS/three-minute optical protocol not run.

Verified final report with all condition receipts: HF dc86507032b0187ec0260d89b4035288c33b5849,
manifest526fc1bb4084534a901d322c9961a30b25c0af6d71e53d4c8cf967be8095b2fb.
See docs/NATIVE_PAIRED_PULSE_DIAGNOSTIC.md. Complete CUDA dependency closure and
sanitizer admission are not established. Learning remains disabled; independent
pedc/DAN anatomy, subtype/receptor physiology and all original project gates open.


### 2026-10-05: candidate skeletons and bilateral node geometry

MBON11 10704/11402 and PPL101 11327/11900 plus PPL102 11618/13428 acquired as generation-pinned GCS SWCs, structural checks passed and each immutable input/audit archived before advancing. MBON final HF 6b93ffad58fa19aa69a7986f02b2ffe3a6500512; DAN final HF 0a43cc898d3df9c1e2ed8fd378f0dca5994e284c. All skeletons coarse, not complete morphology.

Official 8nm coordinate convention archived before all-41460-row nearest-node diagnostic. Bilateral result HF 33db5a4375e025fad1440a2faad05a32bd594e4d, manifest 1bca7b32d497849b9a01106ea64c9070de47654f436649ea6beffa62d9ac2477. 170 exhaustive node-scan crosschecks passed. PPL102 proximity to robust gamma1 contacts follows opposite annotation suffix; both PPL101 skeletons are near both MBON populations. L/R suffix cannot replace territory mapping. See docs/GAMMA_BILATERAL_SKELETON_GEOMETRY.md. No surface/segment/release-site localization, contact-mask or plasticity admission; no learning enabled. Next: pinned DAN pre-synaptic coordinates and independently verified coverage/territory.


### 2026-10-05: DAN synapse input schema pinned

MoLab preflight confirmed no running cell and private HF access. Synapse CSV listing has continuation after first 1000 entries, so no complete inventory claim. Flat-connectome list pins full syn-points generation 1780494991007477 (13061489098 bytes). Small non-target CSV plus ingestion arguments archived before schema inspection; fields include bodyId, pre/post, compartment, location and transmitter probabilities. Schema report HF b75d42605143f87d6937a0a0f551910a9c4ba2ae, manifest 4efab0cadef7e4e18033612a5720871ed7182c900ec16d34961370ace8be0e6a. See docs/DAN_SYNAPSE_INPUT_SCHEMA.md. Next: complete target DAN presynapse selection with immutable source closure, not arbitrary CSV subset. No anatomy/plasticity/learning admission.


### 2026-10-05: complete syn-points source and four-DAN selection

Full 13061489098-byte source, generation 1780494991007477, size+CRC32C verified in MoLab and pinned to HF a9c46d71aa5c7e8b05bffa2f1160fc075958ea81 before selection. All 357489383 rows / 5455 batches scanned. Four PPL101/PPL102 bodies yield 67575 points including 8362 PreSyn (2604,2433,1689,1636 by bodies 11327,11900,11618,13428); zero duplicate kind+xyz. All original columns and both kinds retained. Selection HF a9d36c843814ce8a3f497a197df053d64d900c6d; manifest c3f39e692a67acca13bbbaec942f1d51b8654f5c2402db0b0bc0ef930421896e. See docs/DAN_COMPLETE_SYNPOINT_SELECTION.md. Next: actual presynapse atlas territory and contact proximity; no physiological release, contact-mask, plasticity or learning admission.


### 2026-10-05: actual annotated DAN presynapse geometry

All 41460 contacts compared at both endpoints against all 8362 annotated PreSyn points of four DAN candidates; 136 exhaustive nearest-point crosschecks passed in MoLab. HF b0506b71173fbddfac3e407e435624c7c1b5ebe0, manifest 28163c60953d9da139bdc91a66c98064efb5ecfc4acf0193b795ba6e9b746bd7. Source ROI supports bilateral PPL101 gamma1 (599/873 and 710/702 L/R) and contralateral PPL102 gamma1 (147 R for body11618; 150 L for13428). Material source compartment asymmetry: gamma1 PPL102_L PreSyn are axon; PPL102_R PreSyn are dendrite. Preserved without relabeling/filtering. See docs/DAN_PRESYNAPSE_CONTACT_GEOMETRY.md. Whole PED is not pedc. No partner/release/diffusion/mask/plasticity admission. Next: independent DAN atlas sampling and source compartment semantics.


### 2026-10-05: complete DAN compartment contingency

All 67575 points audited; counts conserve all rows. Gamma1 body13428 has both150 PreSyn and1544 PostSyn labeled dendrite, whereas11618 has147 PreSyn and1226 PostSyn labeled axon. PreSyn minimum confidence0.701/0.75, so asymmetry is not solely near-threshold0.5 detections. No generator semantics established; no biological release or misannotation conclusion. HF f9d31be8c5870407fa5d09818c2c895d45138ded, manifest caeafe6cf1512898288a7e77172e85deac079b3585ff3e5f75edae85ae937463. See docs/DAN_COMPARTMENT_AUDIT.md. Preserve kind separately from compartment and proceed to independent DAN atlas coverage; no plasticity/learning admission.


### 2026-10-05: DAN atlas input closure completed

All8362 PreSyn /225774 queries need277 keys. New169 completed (99 available70 metadata404),108 reused (99 available9 missing). Combined198 available79 unknown; no sparse-zero assumption. Seven new immutable segments remotely verified. Final HF6edf60cdd02c5f0ae4cdd463b6c8c4b94b708767 manifestd315aeb1c2bd2f6e12206ace5233c7298ff320c44d4be3d1ee621f0529b9884a. Foreground BCpL terminal; no restart needed. See docs/DAN_ATLAS_ACQUISITION.md. Next pinned decode and full source/volume classification; all biological gates remain open.


### 2026-10-05: all four-DAN PreSyn atlas classification

All8362 PreSyn sampled at centers+27neighbors in MoLab DKWV.12672 independent decoder checks passed.3040 robust gamma1 (1413L1627R),249boundary,4288outside,785unknown. All3181 source-g1 center labels comparable; zero mismatches. Shared ROI/atlas provenance means cross-format consistency, not independent biological validation. HF935a216bab16efbc125469855a6e0f53535e8aa6 manifest27d8903b333b95598c12de41a31020ebcace3eefa16edbd955ae4cf911afc52b. See docs/DAN_ATLAS_CLASSIFICATION.md. No pedc/receptor/release/mask/plasticity admission. Next evidence-defined pedc boundary and physiological calibration; wholePED forbidden as surrogate.


### 2026-10-05: primary pedc definition pinned

Aso2014e04577 XML pinned before extraction HF1b3a6bd71b528dadb92eacd2e9f8e7975481d0c8; extraction49e47c32e378b9e70b077c0d48018a59e24dc71e. pedc is distal pedunculus core intersecting alpha/beta KCs. Preserve alpha/beta anatomical contacts; gamma-only physiology does not admit alpha/beta plasticity. WholePED or unvalidated DAN-radius surrogate cannot define pedc. See docs/PEDC_ANATOMICAL_BOUNDARY.md. XML page fields are paragraph indices. Open: registered/fine pedc boundary plus relevant class physiology; no training.


### 2026-10-05: exact four-DAN outgoing partners

Full syn-partners6.78GB pinned before selection HF70734f7acf44864905e3ec564cb6896b511d635b. All311833243rows4759batches scanned;37219outgoing DAN contacts preserved. Exact DAN→MBON11 links corroborate bilateralPPL101 and contralateralPPL102 at source threshold. ResultHFd38176c717e38bd7c7a9964134588221172bc062 manifeste5dd119b12f4163f091740af40b7904b469fbcf9ab4f90f90f796890b7201296. See docs/DAN_PARTNER_SELECTION.md. Next exact KC target subtype join; no physiological release,pedc,plasticity or training admission.


### 2026-10-05: DAN target subtype join

All37219contacts preserved;12072to3080knownKC targets.13115contacts12112targets absent from selected167216annotations retainedunknown. PPL101 directPED KC contacts includeKCab-c/m/p/s bilaterally;PPL102noPED KC contacts in selected-source join. HF0dd4290d6fdbed37f901f06ba8fcd009b979dc89 manifestdc3100f1460420b9c811f46bb1728a8c046640f3eb539440ecbfb40bc7502747. See docs/DAN_TARGET_ANNOTATIONS.md. Nextfullannotation reconciliation and justifiedpedc geometry; no plasticity/training.


### 2026-10-05: full released annotation reconciliation

Generation1780494878811468 fullbodyannotations211577records pinned before join.22targets58contacts newly matched;13057contacts12090targets still absent from releasedannotations, preservedunknown. KC evidence unchanged12072contacts3080targets. HFb100773edef5308434daa1660795eab651caebb3 manifestca23dc618aac9608ad979c8deff472ad5bcb4a9a585161200495297a1ad30773. See docs/DAN_FULL_ANNOTATION_RECONCILIATION.md. Nextsegmentstatistics and exactlocalPED coinnervation; no biological/training admission.


### 2026-10-05: same-KC local DAN/MBON11 overlap

12040of12072DAN→KC contacts matched sameKC with output in41460KC→MBON11table;32unmatched retained.3059exhaustive checks passed. PED KCab c/m/s medians ~0.6–1.6um, KCab-p andtails muchfarther; no arbitraryradius admission. HFb4f568e0769781a48e5c37e654ca3dfcaa84a172 manifestdce3f44aba0f174209e87388065075c6b48ef198d535bf31410afa97d598d271. See docs/DAN_KC_MBON_LOCAL_OVERLAP.md. Exactsharedcell plusEuclideanproximity is not sharedbouton/receptor/diffusion/pedc/plasticity; nextfineanatomy/physiology, no training.


### 2026-10-05: Yamada full protocol extraction

The 27-page primary PDF was pinned before MoLab extraction with archived pypdf 6.1.1. Completed pages/report HF 5b7ca66fd588c37a322a54d9f32c4a75315b8d4f, manifest aa9c55b7f3460324b13db9fb19cca36fe2540b5d44da96e5732e3a2c0ff43c35. Exact measurement uses a single reference plus four 400-ms pairs per minute, reference-waveform subtraction, and at least three baseline minutes. Existing single-pair diagnostic does not reproduce that operator. Primary Figure 8 also establishes transient alpha/beta KC depression/PPR increase, distinct from persistent gamma effects. Original preparation-level data are supplied on request; none acquired. See docs/YAMADA_PROTOCOL_DATA_BOUNDARY.md. Next exact observation schedule and separate release/efficacy implementation; no quantitative physiology/plasticity admission or training. All original gates remain open.


### 2026-10-05: native three-minute observation operator

Unchanged two-neuron CUDA conductance runtime executed all 180000 ticks and 27 exact source events in foreground MoLab. Three sets of one reference plus four 400-ms pairs were observed with separately recorded reference-waveform subtraction. Independent exponential superposition agrees within 1e-10; all three PPR values are 1.0. This is the static additive-kernel identity, not physiology. Completed HF 13a8665fd5c1ef3c5f217da6c9907370240e7cdd, manifest 003af2494585a145eebfca5f8608a475e3a204675922d5d2924f0b00156dd4c0. See docs/YAMADA_MINUTE_OPERATOR.md. Optical recruitment, actual voltage clamp, release/efficacy dynamics and quantitative calibration remain open. Next separate release-state implementation; learning disabled and full original contract unchanged.


### 2026-10-05: native per-edge release candidate

Optional CUDA depletion/recovery state and separate postsynaptic efficacy added at 1af3f44e70827e65904511b43bbc5653a63eb35d. Five foreground MoLab conditions agree with independent formulas, max error 1.942890293094024e-16 under 1e-10. Both interventions halve A1; U reduction raises PPR from 0.66484 to 0.83242, efficacy reduction preserves PPR. Diagnostic parameters are uncalibrated and these directions are model properties, not physiological validation. Each condition immediately archived. Final HF f0d6861e46ba83e3fa77991f237b49e3e5901c8b, manifest 9d0133ac360bb308d1cdd35e72baf0db7ef74609e48735aee2d0db02185c5779. See docs/NATIVE_RELEASE_CANDIDATE.md. Next state/reset/chunk and exact observation checks, sanitizers, measured graph scaling and biological calibration. Full-CNS release not enabled, no long-term learning; original contract unchanged.


### 2026-10-05: release state and minute observation verified

Restored immutable native release build in foreground MoLab. Mixed excitatory/inhibitory three-neuron fixture matches independent event formulas to 2.255140518769849e-16. Reset and six-chunk continuation are bit-exact; eight invalid configurations reject without mutation; late configuration rejects while preserving continuation. Three separate 180000-tick minute protocols preserve release versus efficacy PPR dissociation under independent reference-subtraction checks. Each condition immediately HF verified; final 3c2373646e6be4bcf833a9c31e4269792b3b483c, manifest 9d5fde05237ae01abe22f9bd76700504e9c0b6d07ccc37b8d94bfe8709bccb9b. See docs/NATIVE_RELEASE_STATE_VERIFICATION.md. These are software checks with uncalibrated parameters; no physiological admission. Next sanitizers, complete dependency closure, persistent release checkpoint and full-graph measurement before transfer. Learning disabled; original objective and all whole-project gates remain open.


### 2026-10-05: sanitizer instrumentation unavailable on live GPU

Official pinned sanitizer components 13.0.85 and 13.2.23 both terminate memcheck with Device not supported before model kernels, followed by initial cudaMalloc error. Both terminal logs/results immediately HF verified; no sanitizer pass, kernel defect or instrumentation coverage claimed. Newer failure HF c41fdc165faac4694c141ee0f9902edd73cca51c, manifest f2117114b89f794e5ba22609cf64ca13fad44e582ff5d8c26af49981b73bbe06. Same immutable build subsequently passes uninstrumented state control; GPU reports Blackwell, driver595.71.05, virtualization None. Complete control HF a2b46fc45bd7606f9afbe5578b775a3ff3eda76d, manifest 2779f8832f5ba2fe32e9198687227ad3f3005d77487146d9d6f1df421735cc29. See docs/NATIVE_RELEASE_SANITIZER_LIMITATION.md. Instrumentation needs compatible MoLab configuration; no identical retries or local fallback. Next independent persistent-state/checkpoint work. Release full-graph admission and learning remain disabled; full original goal remains active.


### 2026-10-05: native release-state checkpoint implemented

Versioned state ABI at a041949647eb66702b44e5c9c8cc9333f47d78d9 binds exact graph/configuration and includes neural state, refractory deadlines, delay ring and release resources. Five foreground MoLab conditions save at tick412 and restore into separate handles; snapshots and suffix arrays are bit-exact, including pending arrival413. Payload corruption and changed weight reject without mutation; truncated input rejects. Every checkpoint/result immediately HF verified; final 54a29b07b53ff153bd80925891640191c01f92df, manifest 6e30a0875bd1618717d645c6e60f99c098d4addc41160318448dc80bd9c2bc08. See docs/NATIVE_RELEASE_CHECKPOINT.md. Broader identity/malformed-state/fresh-process and full-graph checks remain; FNV is corruption detection, external SHA256 receipts remain authoritative. Sanitizer unavailable; no physiological admission or learning. Original full goal unchanged.


### 2026-10-05: immutable HF checkpoint continuation in new processes

All five native release checkpoints restored from verified HF objects into separate fresh processes, using capacity127 instead of1024. Snapshot roundtrip and 612 suffix ticks are bit-exact across voltages/conductances/spikes, retaining pending arrival413. Each restored result immediately archived; final HF 5af8a7251ddec89079bedf8caa56dea5f0ab3f3b, manifest d295f0411225d6f9922dee01860a4b8a3927b8526e7d897c860dfc2bec1aa73e. See docs/NATIVE_CHECKPOINT_HF_RESTORATION.md. This is same-session two-neuron recovery, not full-CNS/new-sandbox or training recovery. Next complete generation-pinned source geometry acquisition and physiological calibration; sanitizer remains unavailable and learning disabled. Full original objective unchanged.


### 2026-10-05: full SWC inventory input gap revalidated

The historical inventory report records 167216 listed graph SWCs and 9034068018 bytes, but compressed inventory data/derived/malecns_v1_swc_bucket_inventory.csv.gz is absent from current pinned Git commit (HTTP404) and the selected immutable HF closure 66705179b8843c182534e9be8a0adf7affa7cb36 / manifest82d3d7ae1569326ce420cb7bf31754ad4a498086c25470a3ba11f6e64eba0405. Both foreground planning attempts terminated before any SWC download. Sources pinned to HF ebbec04663fcb57360c5a173ac2ddc32ffeb97bb and15afdc13749d5620dc234e61feaedd04566c9fe8. No complete acquisition plan or current availability claim established. Next regenerate and immediately archive official GCS metadata pages in MoLab, reconcile exact graph IDs and pin full shard plan before source acquisition. Do not read/copy historical local binary inventory or run local helpers. Whole-population geometry remains open; original objective unchanged.


### 2026-10-05: full SWC input closure regenerated and acquisition started

All212 official GCS metadata pages archived in14verified segments. Exact167216 graph IDs reconcile with211573 listed SWCs: no missing IDs, source9034068018bytes. Complete inventory/164-shard plan HF965d416f6ed49f2b856dca6b36d5e51a772e6c6d, manifest1ea8b4678a0ee3b48104f9076e6d6ff6f7e160ccd51808e8f2bf930e748d1ea9. The missing historical compressed input gap is closed by newly pinned current metadata, not copied local binaries.

First source shard0:1024files generation/size/MD5 verified with zero errors; immutable tar+per-file SHA ledger pinned before audit HF811a855b377f7951c75a48e5f9f722cf86d2f6c6. Audit11461411nodes passes defined syntax/topology checks,163multi-root files retained. AuditHF2d133b13bdeadccca2d74b6e58fab6006617c815, manifest0847094f9e7472dbc6ea200aefc57d2fb6381f9be1a5f62b57acbf257f431f95. Coverage1024/167216 in this remote family; do not add historical local coverage without verified union. See docs/COMPLETE_SWC_INVENTORY_AND_ACQUISITION.md. Statvfs near2^63 output is virtual: disk_admitted field is not a proven quota/reserve. Continue bounded staging/publication for remaining163shards; full morphology quality and all biological/embodied/KSP gates remain open. Learning disabled; original full goal unchanged.


### 2026-10-05: SWC source coverage through shard4

Four additional planned shards1–4 completed in foreground MoLab, each source/archive/audit remotely verified before next shard. Independent HF-metadata union verifies exact planned IDs and generations with zero duplicate bodies. Remote family total5120/167216 SWCs (3.0619079513922114%),1191321673source bytes,34916649nodes; all defined structural checks pass,676multi-root files retained. Final union HF7302eb033dac6e3c38037df8654ea0f04cdb699c, manifestd9a2b99f003584177cae941bab5a87a67cab3df39e5d96711658850816972c06. Last shard4audit HF64e61036b20d57c8ea3ad02c563671aa22578d9f, manifest1e454df4ffe47ee9e3e9fc42042adefdd4474593797ac3621efff2aee72cb08e. See docs/SWC_ACQUISITION_SHARDS_0000_0004.md. Next shard5;159remaining. No historical-local coverage addition, morphology-quality admission or learning; all original gates and full goal unchanged.


### 2026-10-05: SWC source coverage through shard8, interrupted shard recovered

Shards5–8 completed with immediate immutable HF publication and structural audits. Initial cell sWoq was authoritatively interrupted during shard7 after completing5/6; remote inspection confirmed no active cell/process and1024 saved files. Recovery reverified original HF source closure and all saved files without redownloading, then completed7/8 in foreground cellTdtX. Unknown interruption cause; SSE timeout alone was never used as restart authority.

MoLab immutable-metadata union in KKug verifies9216distinct SWCs/167216, coverage_fraction0.055114343125059806,1684627745source bytes,49559286nodes,1116multi-root files. Exact planned ID/generation reconciliation passes; zero duplicate bodies; all defined structural checks pass. FinalHFf1485e55b21242a5b8a958700b08368a77e65c41 manifest9a134487210cc14341e5819048522100e26a599b0a48aaa83cea6bd3a3564c95. Last8auditHF29fd7506bdeba6d86f6d42af86e672f74c361f15 manifest4d8f2254e3da25d0ed5323b43f6d47ef9ca3c38339e4a656b71e1a56f7fb6589. See docs/SWC_ACQUISITION_SHARDS_0000_0008.md. Next shard9;155remain. Virtual quota/reserve unproven, continue bounded staging. No morphology/biology admission, historical-local count addition or training. Full original objective and all gates remain open.


### 2026-10-05: SWC source coverage through shard12

Foreground MoLab BCGJ completed shards9–12 with immediate verified source/archive/audit publication before each successor. Union owOM re-read immutable HF manifests and reconciled exact planned body IDs/generations and predecessor chain:13312distinct SWCs/167216, coverage_fraction0.07960960673619749,2111128669source bytes,62192716nodes,1490multi-root files,zero duplicate bodies. All defined structural checks pass. FinalHF644caa6eac838df13d0b9ed8f4220ffce222a6aa manifest760800d310259bb28e389fbf407d81dee2ee5bf637a73bf9fe4d1cb9a19718ee. Last12auditHFf3ba0487c111879ce9db7531dc41c80a3c804a8b manifestfaa3fce433b94649647e2159de4086fe41d2659d10e5e3a2a81aa40a3423904b. See docs/SWC_ACQUISITION_SHARDS_0000_0012.md. Next13;151remain. Bounded staging only, virtual quota/reserve unproven. No historical-local count addition, full morphology or biological admission, or learning. Original full goal and all gates unchanged.


### 2026-10-05: SWC source coverage through shard16

Foreground MoLab DNjl completed13–16 with immediate verified source/archive/audit publication. Immutable HF union KEGg reconciles planned IDs/generations and predecessor chain:17408distinct SWCs/167216,coverage_fraction0.10410487034733518,2444062269source bytes,72121154nodes,1808multi-root files. Zero duplicate bodies; all defined structural checks pass. FinalHFc18a24011c40d461fbe5d87e1a9fdd05c93f3451 manifest3839be8156d6ac4f41843e3cc90fcb68a1e43d4d7cbe5f113fc57fd3f4ac7a60. Last16auditHFb8bd74d882911c44248b94bad6fae20b79ff0361 manifesta6b67907e6e248dba42c9993880559cc90dca220dafdf536763db5f2224733b5. See docs/SWC_ACQUISITION_SHARDS_0000_0016.md. Next17;147remain. Virtual quota/reserve unproven; staging bounded. No historical-local count addition, morphology/physiology/plasticity admission or learning. All original gates and full goal remain open.


### 2026-10-05: SWC source coverage through shard20

Foreground nPVH completed17–20; SSE failed during18 but browser confirmed continuing work, then code-mode confirmed idle/no errors and final verified receipts. No duplicate/restart. MoLab immutable-HF union duGF verifies21504distinct SWCs/167216,coverage_fraction0.12860013395847286,2739376998source bytes,80940983nodes,2125multi-root files. Exact planned IDs/generations reconcile; zero duplicate bodies; all defined structural checks pass. FinalHF2df4f7874ec15a3d45a65ffa494677198ff55a85 manifestbbc7896e305abec7c3b32cf3b702391933767495c1e7d1c6a66d5d9f4605954c. Last20auditHF9e851c86a5d781d8449b9fd333dfdbb63649ed1e manifestd87c952422c685120abdc39793530ad17cb24ec0e3844854a0d1eadf323ec235. See docs/SWC_ACQUISITION_SHARDS_0000_0020.md. Next21;143remain. Bounded staging, virtual quota/reserve unproven, no historical-local count addition, morphology/biological admission or learning. All original gates and full goal remain open.


### 2026-10-05: SWC source coverage through shard24

Foreground Jgqb completed21–24 with immediate verified source/archive/audit publication before successors. MoLab union pxrI reconciles exact planned IDs/generations and predecessor chain:25600distinct SWCs/167216,coverage_fraction0.15309539756961058,2992689364source bytes,88535217nodes,2452multi-root files. Zero duplicate bodies; all defined structural checks pass. FinalHFe1f0cd5a155759e7ec67e765589175e69b8208a7 manifestaa31a3e975f7b90017e5dd310508b587984a0b1251d97f075ef67b22e738d08c. Last24auditHFaf4e871ed326e43dc4086ca7f435ee64aab958f8 manifestf9af22a1c5c23fc008881820f887dd1d15fefceeb5ccdc2e712ecadbf167e9ca. See docs/SWC_ACQUISITION_SHARDS_0000_0024.md. Next25;139remain. Bounded staging; virtual quota/reserve unproven. No historical-local count addition, morphology/physiology/plasticity admission or learning. All original gates and full objective remain open.


### 2026-10-05: SWC source coverage through shard28

Foreground viWy completed25–28; every immutable source/archive/audit verified before its successor. Slower27/28downloads finished without errors/restart. MoLab immutable-HF union yLfX reconciles exact planned IDs/generations and predecessor chain:29696distinct SWCs/167216,coverage_fraction0.17759066118074826,3230286213source bytes,95663282nodes,2728multi-root files. Zero duplicate bodies; all defined structural checks pass. FinalHFfdd70643119ea7c95f682827abaecad174fe15e9 manifest587d126531ee71b33706423ed8d9fb01f3e7263c8bc4de19af0720e620eee79e. Last28auditHFdfe1155b68505080dd865a1658d298acaad9f5f1 manifest1bea210eb40240c103cb01a79fed970f6f64171874d1fd48bf7bd01eec7e2453. See docs/SWC_ACQUISITION_SHARDS_0000_0028.md. Next29;135remain. Bounded staging; virtual quota/reserve unproven. No historical-local count addition, morphology/biological admission or learning. All original gates and full objective remain open.


### 2026-10-05: SWC source coverage through shard32

Foreground fIhB completed29–32 with immediate verified source/archive/audit publication before successors. MoLab immutable-HF union cjqf reconciles exact planned IDs/generations and predecessor chain:33792distinct SWCs/167216,coverage_fraction0.20208592479188595,3445646786source bytes,102147115nodes,2992multi-root files. Zero duplicate bodies; all defined structural checks pass. FinalHFcf980afc1c60cddaa8d5f78408e03c428bdf3893 manifestf02891960f32305ce8425ed5a2e1fe9c549ea3fc3368f57176381b12e17e03e9. Last32auditHF63f2c0d32a2cff3fd325793628711faf66059255 manifesta4234c96cebc01f4e0015016772c64ab549f9918136f541e10dde8a33402ef2c. See docs/SWC_ACQUISITION_SHARDS_0000_0032.md. Next33;131remain. Bounded staging; virtual quota/reserve unproven. No historical-local count addition, morphology/biological admission or learning. All original gates and full objective remain open.


### 2026-10-05 — remote SWC union through shard 36

Shards 33–36 completed in MoLab, each source closure pinned before acquisition and each completed acquisition/audit remotely verified on private HF before advancement. Immutable union report HF commit `389a7feb7cefc4dd89b441fe3689e49735273c36`, manifest `09f3e3df85efefb6f980c6be84ac888aece6bb0d49062866adc71e684224d36b`: 37,888 distinct SWCs / 167,216 (22.658118840302363%), 3,640,610,201 source bytes, 108,036,545 nodes; zero duplicate body IDs; all defined structural checks pass; 3,239 multi-root files retained. Exact planned ID/generation reconciliation verified remotely. Next shard 37, remaining 127. See docs/SWC_ACQUISITION_SHARDS_0000_0036.md for immutable identities and limits.

Full WORK_PLAN goal remains active. This partial structural audit does not admit anatomical geometry or biological fidelity. Plasticity/training remain disabled; physiology, body/cockpit, runtime acceptance, three independent training/evaluation series and reproducible recordings remain open.


### 2026-10-05 — remote SWC union through shard 40

Shards 37–40 completed in visible foreground MoLab; every immutable source/acquisition/audit stage was verified on private HF before dependent advancement. Union HF commit `3c5273dd7d562d637e5ec3e8ffbe9d28bf51aed5`, manifest `9021c007ba7f3e6c900f71fda1f474bf3c38a0f897637efa9cd740233b03af36`: 41,984 distinct SWCs / 167,216 (25.107645201416134%), 3,829,650,020 source bytes, 113,754,104 nodes. Exact planned ID/generation reconciliation passes, duplicate body IDs zero, all defined structural checks pass; 3,520 multi-root files retained. Next shard 41; remaining 123. See docs/SWC_ACQUISITION_SHARDS_0000_0040.md for immutable receipts and scope.

Full project goal remains active. This partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; all broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 44

Shards 41–44 completed in visible foreground MoLab; every immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `91ad2e66e594419e96bea875e9b09a3e2536ab09`, manifest `92a195f7bd7c84bcfa265fdebadef8a0c04cebecefb30acae6998330a1b1fd60`: 46,080 distinct SWCs / 167,216 (27.557171562529903%), 4,006,052,611 source bytes, 119,099,876 nodes; exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 3,807 multi-root files retained. Next shard 45; remaining 119. See docs/SWC_ACQUISITION_SHARDS_0000_0044.md for immutable receipts and limitations.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 48

Shards 45–48 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `ac036294e19293bfc1637691af6482b191c07f32`, manifest `9662610216ba2a560ffe27b90f3cf8285ddca6bf3e2368d567af5de4ab4f5978`: 50,176 distinct SWCs / 167,216 (30.00669792364367%), 4,177,316,509 source bytes, 124,291,219 nodes; exact planned ID/generation reconciliation passes, zero duplicate body IDs, all defined structural checks pass; 4,074 multi-root files retained. Next shard 49; remaining 115. See docs/SWC_ACQUISITION_SHARDS_0000_0048.md for immutable receipts and scope.

Full project goal remains active. This partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 52

Shards 49–52 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `62ee7d2cea8035f56c7be532608293717b0dcfba`, manifest `9880bb348e2e886fb5ed1233c75559d7fe590b9143304e26ccd2e8b0cf088b73`: 54,272 distinct SWCs / 167,216 (32.45622428475744%), 4,340,765,589 source bytes, 129,254,203 nodes. Exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 4,381 multi-root files retained. Next shard 53; remaining 111. See docs/SWC_ACQUISITION_SHARDS_0000_0052.md for receipts and limits.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 56

Shards 53–56 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `49b06a11403d15657293dfa109285786f67ee261`, manifest `965817478d341caf564b70f0b291a36ebc5e285da7d9b98a1648b6903b1a7300`: 58,368 distinct SWCs / 167,216 (34.90575064587121%), 4,493,048,506 source bytes, 133,879,518 nodes; exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 4,682 multi-root files retained. Next shard 57; remaining 107. See docs/SWC_ACQUISITION_SHARDS_0000_0056.md for receipts and limitations.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 60

Shards 57–60 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `9422dd0116d9d76d00ea0cb7dde51e4158cb50e9`, manifest `5f646b71e93d26da0c22831d1522a247e75df7b5d059f20012bb09a29191c08c`: 62,464 distinct SWCs / 167,216 (37.355277006984977%), 4,636,427,045 source bytes, 138,242,321 nodes; exact planned ID/generation reconciliation passes, zero duplicate body IDs, all defined structural checks pass; 4,940 multi-root files retained. Next shard 61; remaining 103. See docs/SWC_ACQUISITION_SHARDS_0000_0060.md for receipts and scope.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 64

Shards 61–64 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `fa31d788e4d27ad7833dd0334341169f0a11dbf4`, manifest `42bd9f91890527cf5498a751277102ab63506299ee81ce6ab3f9eda580ffe7d4`: 66,560 distinct SWCs / 167,216 (39.804803368098746%), 4,775,391,612 source bytes, 142,469,471 nodes; exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 5,232 multi-root files retained. Next shard 65; remaining 99. See docs/SWC_ACQUISITION_SHARDS_0000_0064.md for receipts and limits.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 68

Shards 65–68 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `6fa76cda228c95ce15c98167962127fd3d3258c4`, manifest `8ae679dc755e9edbc1758a8a3cfea7d8f4b75ff0ddc90ad439393ea809e4c474`: 70,656 distinct SWCs / 167,216 (42.254329729212514%), 4,904,220,586 source bytes, 146,390,197 nodes; exact planned ID/generation reconciliation passes, zero duplicate body IDs, all defined structural checks pass; 5,480 multi-root files retained. Next shard 69; remaining 95. See docs/SWC_ACQUISITION_SHARDS_0000_0068.md for receipts and limitations.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 72

Shards 69–72 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `dcc672830f88d09b0425bbc02ba8ea25855d6b0d`, manifest `2586de03bf2d293ab5956941d0da08489ee5ad90a1c7a985d04ba5e39ea1e629`: 74,752 distinct SWCs / 167,216 (44.70385609032628%), 5,022,320,705 source bytes, 149,991,397 nodes; exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 5,737 multi-root files retained. Next shard 73; remaining 91. See docs/SWC_ACQUISITION_SHARDS_0000_0072.md for receipts and limitations.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 76

Shards 73–76 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `b21b0e36f0d238c5a5bceb296375a08e0c165134`, manifest `5c6de091b75ecabac6f4f59f8e460dcdb10a21502ea77cc2bbc2ad6d244dd70c`: 78,848 distinct SWCs / 167,216 (47.15338245144005%), 5,138,679,634 source bytes, 153,539,682 nodes; exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 5,958 multi-root files retained. Next shard 77; remaining 87. See docs/SWC_ACQUISITION_SHARDS_0000_0076.md for receipts and limits.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 80

Shards 77–80 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `54f2aa53690bc355b8b9d45b90ea9728a2b770b7`, manifest `643039087f760cbe63d92c96c7cf8607ebb6d76174737665d090ee0e0c921c29`: 82,944 distinct SWCs / 167,216 (49.602908812553825%), 5,254,284,262 source bytes, 157,059,349 nodes; exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 6,204 multi-root files retained. Next shard 81; remaining 83. See docs/SWC_ACQUISITION_SHARDS_0000_0080.md for receipts and limits.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 84

Shards 81–84 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `82353dd4a09291394548503ac9f16dc2d8a41c74`, manifest `cc696d4992e5987264df36c424ca02b4077d41e905585e17aebc7fa1f86fe1e3`: 87,040 distinct SWCs / 167,216 (52.05243517366759%), 5,360,345,779 source bytes, 160,295,816 nodes; exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 6,438 multi-root files retained. Next shard 85; remaining 79. See docs/SWC_ACQUISITION_SHARDS_0000_0084.md for receipts and limits.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — remote SWC union through shard 88

Shards 85–88 completed in visible foreground MoLab; each immutable source/acquisition/audit was published and remotely verified before dependent advancement. Union HF commit `058d7976f832470cbbf3cd4c1fa7baacaec2f3e8`, manifest `8979cd07d81c25f27ba00ec0fcf0f3e0cb750b421590f381a01a0969d9880fdc`: 91,136 distinct SWCs / 167,216 (54.50196153478136%), 5,463,678,668 source bytes, 163,442,722 nodes; exact planned ID/generation reconciliation passes; zero duplicate body IDs; all defined structural checks pass; 6,675 multi-root files retained. Next shard 89; remaining 75. See docs/SWC_ACQUISITION_SHARDS_0000_0088.md for receipts and limits.

Full project goal remains active. Partial structural evidence does not admit anatomical geometry or biological fidelity. Plasticity and training remain disabled; broader physiology/body/runtime/training/evaluation/recording gates remain open.


### 2026-10-05 — SWC acquisition through shard 0092

Verified MoLab/HF union: 95,232 / 167,216 distinct SWCs (56.95148789589513%), 5,565,581,038 source bytes, 166,545,526 nodes, 6,949 multi-root files retained, zero duplicate bodies; exact planned identity/generation reconciliation and defined structural checks pass. Report commit b8f348acbf41186a6554b3618514cd6397181551, manifest 96f2b9c3456dcd6e7584db78af4ea1484587fee9c7e42be74b86a58f232d911c. Source closure commit 2ccd52774617af782a226a512c6b14fe856396b9, manifest b6da56027fcc9af4cca828ff7941bcae5cb1d495ae7490c105507335a594d437. Details: docs/SWC_ACQUISITION_SHARDS_0000_0092.md. Next shard 0093; 71 remain. Syntax/topology does not establish biological fidelity; geometry admission false, plasticity and training disabled. Actual sandbox quota remains unknown; virtual statvfs is not reserve proof. Full original objective and all broader gates remain open.


### 2026-10-05 — SWC acquisition through shard 0096

Verified MoLab/HF union: 99,328 / 167,216 distinct SWCs (coverage_fraction 0.594010142570089), 5,662,571,611 verified source bytes, 169,502,827 nodes, 7,223 multi-root files retained, zero duplicate body IDs. Exact planned identity/generation reconciliation and all defined structural checks pass. Union report commit fc5170390f09bcd39747c88f8e59f9a4e57941a9, manifest 32c210fd2b026c86755d68778dbd33317fa5595af00838bd6371535aa1d461ad; source closure commit 5ca98c354de6e2c49123dcd17956568bebc03e56, manifest 7848e0b9f44148306017348adca377efa0ea9fd364a42c3fd3ae17c0e1e53515. Details: docs/SWC_ACQUISITION_SHARDS_0000_0096.md. Next shard 0097; 67 remain. Geometry admission false; plasticity/training disabled. Source-byte and topology checks do not establish biological fidelity. Actual sandbox quota remains unknown; virtual statvfs is not reserve proof. Full original goal and broader gates remain open.
