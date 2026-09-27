# Proprioceptive input: anatomical inventory before functional binding

## Actual MaleCNS incident connections

`tools/build_proprioceptive_boundary.py` builds a lossless incident-edge index
for the complete 1,454-object annotated population in the accepted MaleCNS graph.
It verifies source hashes and independently checks the union of incoming CSR
rows and outgoing edges. Original edge indices, source-row IDs, neuron IDs and
contact counts remain intact. Weak edges and internal sensory connections are
retained, with internal edges included once in the union.

The view contains 209,361 edge rows and 1,183,473 synaptic contacts:

| Direction | Edge rows | Contacts |
|---|---:|---:|
| Proprioceptor to other | 168,599 | 975,377 |
| Other to proprioceptor | 30,176 | 179,807 |
| Proprioceptor to proprioceptor | 10,586 | 28,289 |

Every selected neuron has incoming connections in this dataset. The largest
nonselected source type by contact count is IN06B017 (19,534 contacts across
1,501 rows). This establishes anatomical feedback, not its sign, physiological
strength or functional effect. Sensory transduction must preserve these paths
rather than impose a network-independent firing sequence.

The exported cells match the earlier candidate registry exactly and remain
runtime-disabled. Data: `data/derived/malecns_proprioceptive_boundary_v1`.
Report: `reports/proprioceptive_boundary.json`. No dynamics or new signs were
assigned and the authoritative full CNS graph remains unchanged.

`tools/audit_proprioceptive_candidates.py` verifies the source node-table hash
and exports all 1,454 objects annotated `mechanosensory_proprioceptive`.
Original node fields, IDs and graph indices are preserved exactly. The derived
view does not remove any other neuron or edge from the full graph.

425 objects carry the chordotonal-organ subclass. Of these, 392 enter leg nerves:

| Entry nerve | Left root | Right root |
|---|---:|---:|
| ProLN | 23 | 13 |
| MesoLN | 80 | 83 |
| MetaLN | 93 | 100 |

The other 33 enter ProCN (25 left, 8 right). This is annotation coverage, not
proof of biological population completeness. The broad inventory additionally
retains campaniform sensilla, hair plates, haltere and other proprioceptors.
Leg nerve labels identify candidate segment context only. They do not uniquely
specify femoral receptor identity, knee joint, flexion/extension tuning, gain,
adaptation or spike rate. Root side is retained independently of soma side.

All encoder, joint and gain fields remain unassigned and runtime-disabled in
`data/derived/proprioceptive_candidates_v1`. Report:
`reports/proprioceptive_candidates.json`. In particular, the limited front-leg
chordotonal annotation counts must be resolved rather than padded with invented
neurons or silently treated as complete sensory coverage.

## Relevant primary reference

[Lee et al., 2025](https://www.nature.com/articles/s41467-025-59302-3) provides
FeCO connectivity analysis in FANC/FlyWire, with annotated matrices and analysis
code at https://github.com/sagrawal/Lee_2024. This is a separate specimen/dataset,
not an automatic MaleCNS functional mapping. Distinct position, directional
movement and vibration-sensitive populations must be reconciled with the
MaleCNS type annotations and physiological experiments before sensor injection.
The public data have now been acquired at commit
`4328b1d5549749f1014c4d73cccc0c5241d98ae4` with per-file SHA-256 in
`reports/feco_reference_sources.json`. No author code or CAVE query was executed.

`tools/audit_feco_reference.py` validates 99 distinct annotated FANC roots and
joins all 18,502 published output synapse records and 2,315 input records without
unmatched sensory endpoints or duplicate synapse IDs. Aggregation yields 2,117
outgoing and 304 incoming neuron pairs. Scores remain confidence-like source
fields, not synaptic weights; pair counts count rows. No additional threshold
is applied. Sixteen of the 99 annotated roots have no input records in this
published subset, which does not establish biological absence of input.

The annotations preserve claw extension/flexion, hook extension/flexion, club,
ascending club and `maybeclub` uncertainty. Derived pair tables are in
`data/derived/fanc_feco_reference_v1`; report `reports/feco_reference_audit.json`.
These reference sensory neurons receive central input, so a future encoder must
not silently replace their network state with a fixed firing command. A verified
crosswalk to MaleCNS and fitted physiological transduction remain absent.

## Measured sensory responses: Mamiya 2018

The [author data archive](https://faculty.washington.edu/tuthill/docs/Mamiya2018Data.zip)
for [Mamiya et al. 2018](https://doi.org/10.1016/j.neuron.2018.09.009)
is pinned in `reports/mamiya2018_source.json`. Archive SHA-256 is
`31565245097ca8a9f572555aa32e7f20052ac2a1cd9dcc45ce1803c7858973d2`.
`tools/import_mamiya2018.py` preserves all 144 numeric arrays from 12 MATLAB
files in immutable NPZ files under `data/derived/mamiya2018_recordings_v1`.
Independent source comparison (`tools/check_mamiya2018.py`) passes: 36 protocol
tables, 771 response rows, 249,069 paired finite calcium/angle samples, 255 missing
angle samples, no missing calcium samples or infinities. These are repeated
measurements, not 771 distinct cells or animals. No missing value was imputed.

The author description specifies 8.01 imaging frames/s. Rows are pixel clusters
grouped by response similarity, with fly and cluster identifiers; columns are
frames. Both ramp-and-hold directions and swing are retained. Cross-file animal
identity is unverified, so splitting rows randomly would not establish an
independent-animal validation set. Functional labels are not inferred from file
names alone. The measured calcium signal is not a spike train.

Before runtime use, establish the paper's genotype/branch-to-population mapping,
resolve animal identity across files, register the measured tibia angle to the
FlyMimic joint coordinate, and specify a calcium observation model separately from neural
transduction. Predeclare calibration/held-out animals and stimulus protocols
before fitting. Dynamics unidentifiable at this imaging rate must remain explicit
uncertainties. MaleCNS cell correspondence remains a separate prerequisite.
No physiological fit, neural gain, or enabled sensory injection is claimed.

Figure 4 now verifies driver-level assignments: R73D10 to claw, R64C04 to
club, R21D12 to hook. Per-region animal counts match all three exported
protocols. This does not assign cluster numbers to functional subtypes.
`tools/prepare_feco_calibration.py` freezes 244 ramp-and-hold rows for exploratory
calibration and 122 swing rows for protocol transfer assessment; 405 broad-driver
rows remain unassigned. All 771 source rows occur exactly once, with file hashes
and row bounds checked. No responses were used to choose the partition.

This partition is explicitly not an independent-animal test: the original
preprocessing clustered response traces, and animal identity across regions is
unresolved. Report: `reports/feco_protocol_partition.json`. No fit has run.

## First motion-response pilot: rejected transfer hypothesis

`tools/fit_feco_motion_pilot.py` now fits a deliberately limited calcium predictor
for five club/hook regions. Nonnegative flexion/extension velocity gains and a
free intercept share one first-order filter; tau is selected from a declared
0.125--2 s grid using only ramp-and-hold squared error. Complete rows with any
missing angle/response are excluded, with exact indices logged. This can bias
the sample. Initial filter state is assumed zero. This is an engineering
observation hypothesis, not an identified sensory neuron or spiking model.

All five regions select tau=0.5 s, but fail the frozen swing assessment. Test MSE
is 1.45--12.63 times the calibration-mean constant baseline error. Thus the
declared requirement of improvement in every region fails. Independent SciPy
`lfilter` reconstruction reproduces all held-out predictions and MSEs. Reports:
`reports/feco_motion_pilot.json`, `reports/feco_motion_pilot_validation.json`.
The negative result rejects this linear velocity/filter predictor as a general
transfer model; it does not isolate whether saturation, stimulus sampling,
calcium dynamics, initial conditions, or population averaging cause the failure.
Do not enable these gains in MaleCNS or tune repeatedly on this now-observed
assessment set while still calling it untouched validation.

Post-failure diagnosis (`tools/diagnose_feco_transfer.py`) performs no refit.
Across these five regions, median row-peak speed estimated from frame-averaged
angles is 119--126 degrees/s in ramp protocols and 360--365 in swing. Predicted
swing median peaks exceed observed median peaks by 1.95--4.62 times. These are
descriptive diagnostics on the now-observed assessment data, not new validation.

The paper's Methods specifies nominal 18-degree ramps at 240 degrees/s. The
constant-speed traverse would last 75 ms, shorter than the 125-ms imaging
interval (acceleration and actual limb mechanics change exact duration).
Original tracking was faster than imaging, but this export averages angle per
imaging frame. Differentiating this export does not recover instantaneous peak
velocity. Therefore the fitted gains cannot be transferred directly to a
high-rate MuJoCo joint velocity. Sampling and observation dynamics must be
modeled explicitly; this evidence does not uniquely prove neural saturation.
Report: `reports/feco_transfer_diagnosis.json`.

## Independent speed-response evidence

The author supplement is now locally pinned at
`data/reference/mamiya2018/supplement.pdf`, with checksum in
`reports/mamiya2018_supplement_source.json`. Figure S5B (PDF page 6) compares
maximum calcium-response slope with mean tibia speed during that imaging interval.
Four motor commands are 180, 360, 720 and 1440 degrees/s. Club tip includes 14
flies per speed and direction; hook Y includes 9 per speed for flexion.
The displayed clouds do not support a simple proportional increase. This is a
qualitative inspection, not a digitized regression or a spike-rate measurement.
Speed-sweep numeric arrays are absent from the acquired archive's three protocol
families. Neither a saturating law nor its parameters are identified by this
figure alone. Structured evidence: `reports/feco_speed_evidence.json`.

Native observation arithmetic is now available in native/calcium_observation.h: exact state and time integral for a held-drive first-order filter. Exposure boundaries must be split explicitly by the caller; frame mean is total integral divided by exposure duration. Stable small-step arithmetic, a 75-ms pulse within one frame, subdivision equivalence and invalid input rejection pass independent Decimal/quadrature checks (reports/calcium_observation.json). This is an observation hypothesis, not fitted GCaMP kinetics or a reconstruction of missing high-rate angles. Frame scheduling and data fitting remain unimplemented.

## Left-front sensory-to-motor anatomical gate (2026-09-24)

`tools/audit_lf_proprio_motor_paths.py` checks the original full MaleCNS CSR
graph and all 23 left-root, ProLN-entering chordotonal candidates against
motor body 815344 (graph index 156979). One cell, SNpp50 body 912317, has
one direct retained edge row containing five annotated contacts to this motor
candidate. Fifteen of 23 have
at least one two-edge path. The three SNpp39 candidates have 8, 9 and 11
two-edge path rows but no direct row. Exact IDs and source hashes are in
`reports/lf_proprio_motor_paths.json`. This establishes a structural route
that a future sensory experiment could interrogate; path counts do not
determine response sign, delay, gain or reflex function.

This 23-cell selection is **not** the whole source-annotated left-front
proprioceptive class. The pinned raw annotation has 45 such cells, all
retained in the graph; seven are `SNppxx` and ten have no type. Among those
45, `SNppxx` bodies 817697 and 821306 and untyped body 908487 also connect
directly to motor 815344, with 28, 12 and 18 contacts. SNpp50 body 912317
has five. All four have predicted acetylcholine, but no measured transmitter
entry or source-backed per-cell angle tuning. The extra cells cannot be
treated as SNpp50 copies. Their omission from the one-cell movement probe
limits its negative result to that tested path, not the complete FeCO reflex.
An independent [CxHP8 physiology/connectomics study](https://www.nature.com/articles/s41467-026-69333-z)
reports that this coxa hair-plate class enters the VNC through VProN, and
that individual MANC hair-plate axons could not be identified reliably.
`tools/audit_lf_cxhp8_nerve_boundary.py` checks both the pinned raw MaleCNS
annotation and retained graph nodes: all three uncertain direct extensor
inputs (817697, 821306, 908487), and typed 912317, carry `entryNerve=ProLN`
and `rootSide=L` (`reports/lf_cxhp8_nerve_boundary.json`). Consequently the
CxHP8 tuning and coxa-limit circuit cannot be assigned to these ProLN cells.
This nerve comparison does not exclude other hair-plate identities or resolve
the unknown cells' receptor modality.

[Mamiya et al. (2023)](https://doi.org/10.1016/j.neuron.2023.07.009)
measured the peripheral mechanics of FeCO: tibia flexion moves the arculum
and claw cap cells distally, increasing claw-dendrite tension; extension
reduces it, but tendon-cut experiments indicate tension remains even at full
extension. Their model includes medial and lateral FeCO tendons, fibrils,
dendrites, and surrounding elastic tissue. The published FlyMimic source XML
has the femur-tibia joint and 15 named muscle tendons, but no `<sensor>`
elements or named FeCO, arculum, or chordotonal structures. This is checked
against the source XML hash in `tools/audit_flymimic_feco_structure.py` and
`reports/flymimic_feco_structure.json`. The existing rectified angle-to-voltage
drive therefore has neither a measured tendon-strain input nor source-backed
single-cell tuning. Even its zero half-cycle cannot be interpreted as zero
claw tension. Reconstruct and check peripheral mechanics before treating a
joint trace as a biologically calibrated FeCO stimulus; identifying which
branch of that signal reaches MaleCNS SNpp50 remains a separate gate.

The [author-hosted Mamiya paper PDF](https://faculty.washington.edu/tuthill/docs/mamiya_2023.pdf)
is SHA-pinned under `data/reference/mamiya2023/mamiya_2023.pdf`. Figure 3G
contains its colored mean arculum-centroid trajectory as 64 vector segments
and a separate 10-µm vector scale bar. `tools/extract_mamiya_arculum_trajectory.py`
extracts these rather than tracing a resized screenshot. The plotted mean
moves 31.62 µm horizontally and 1.48 µm vertically between its flexed and
extended endpoints, a 31.65-µm endpoint displacement; all 65 relative plot
coordinates and segment colors are in `reports/mamiya_arculum_centroid_fig3g.json`.
The PDF also contains six continuous grey fly-level vector paths.
`tools/extract_mamiya_arculum_individual_paths.py` saves their plotted
coordinates separately in `reports/mamiya_arculum_individual_fig3g.json`.
Their endpoint displacement magnitudes range from 23.30 to 40.05 µm,
with a median of 32.74 µm. These are still figure-derived trajectories,
not the raw fly-level measurements; the grey paths carry no separate
angle or time labels. The mean-path script also matches each segment's
vector RGB to the PDF colorbar and anchors its linear scale at the printed
160°, 90°, and 20° labels. The mean path spans approximately 24.4° to
151.3° under this figure-resolution reading; tick-fit residual is below
0.5° and maximum RGB mismatch is 0.0056 on a 0–1 scale. These are estimated
angles from the rendered figure, not original per-frame tibia measurements.
These 2D centroid coordinates are a measured geometry
target for a future arculum model, not medial-tendon strain or an SNpp50
encoder. Registering this female experimental geometry to FlyMimic and
checking the model's measured arculum motion are still required.
`tools/derive_flymimic_arculum_observation.py` interpolates this published
mean 2D path by estimated tibia angle onto the current 20° FlyMimic joint
cycle (`data/derived/flymimic_arculum_observation_v1/observation.npz`,
`reports/flymimic_arculum_observation.json`). Across the cycle's
123.832–143.832° range, the plotted centroid coordinates cover
x=26.446–31.201 µm and y=-1.136–1.239 µm. This is a cross-specimen,
angle-indexed observation trace only: it does not attach a 3D arculum to
the fly, compute tendon strain or force, establish hysteresis, or supply
neural input.
`tools/audit_lf_proprio_motor_pool_outputs.py` records all 45 cells' direct
contacts to the four front Ti-extensor, ten Ti-flexor, and 19 accessory
Ti-flexor motor candidates in
`reports/lf_proprio_motor_pool_outputs.json`. The two `SNppxx` cells 817697
and 821306 and untyped 908487 have 33, 25, and 20 contacts across the
extensor group and none to Ti-flexor, like typed SNpp50 912317 (nine to
extensor, none to flexor). The three typed SNpp51 cells have 25, 14, and 26
contacts to Ti-flexor and none to Ti-extensor. This is a reproducible
connectivity pattern that prioritizes 817697, 821306, and 908487 for
morphological and functional review. It is **not** an SNpp50 identity
assignment: similar motor targets do not prove FeCO receptor class, preferred
joint angle, or response polarity.

Seven v1.0 MaleCNS SWC skeletons were independently acquired from the
authors' public GCS release, with exact object generations and SHA256 values
in `data/reference/malecns_v1_lf_proprio_skeletons/source_manifest.json`.
The shared-coordinate projections are in
`previews/lf_proprio_skeletons_v1.png`, generated by
`tools/plot_lf_proprio_skeletons.py`; node counts and extents are in
`reports/lf_proprio_skeleton_geometry.json`. The two `SNppxx` skeletons
817697 and 821306 reach Z maxima 74,304 and 73,152 source units, whereas
typed SNpp50 912317 reaches 78,592. Untyped 908487 reaches 81,984 and has
a visibly different long branch. These are geometry observations only.
Reconstruction completeness, registration quality, and source annotation
remain unresolved; the projections do not justify relabeling any cell or
activating its angle encoder. The published [MaleCNS release bucket](https://github.com/flyconnectome/2025malecns/blob/main/README_RELEASE_BUCKET.md)
describes the corresponding skeleton products and EM coordinate space.

The [MANC sensory-annotation study](https://elifesciences.org/reviewed-preprints/97766)
uses `SNppxx` for proprioceptive axons whose specific type could not be
assigned. Its authors explicitly leave hair-plate-like and campaniform-like
leg afferents among that unresolved population. They describe FeCO, hair
plates, and campaniform sensilla as different receptor classes: FeCO reports
joint position/movement, hair plates are deflected at joint cuticle, and
campaniform sensilla detect cuticular strain/load. This taxonomy informs the
interpretation of inherited type labels; it does **not** assign one of those
modalities to MaleCNS 817697 or 821306. Body 908487 has no type at all.
Consequently, common angle drive to 817697/821306/908487 in the four-cell
probes is an explicitly artificial circuit-sensitivity intervention. Their
stronger motor contacts and observed effect cannot upgrade that encoder to
a FeCO transduction model. The acceptance gate is individual receptor
modality and tuning, followed by the matching measured physical variable;
until then these cells stay unassigned in biological sensorimotor runs.

The pinned FlyMimic XML has no declared MuJoCo sensors. The exploratory
body loop can read knee angle/velocity, muscle and generalized joint forces,
tendon length, and exact contact forces from solver state. An exact replay
of the four-cell diagnostic stores these synchronized channels in
`reports/lf_mechanical_observables.json`. Neither generalized joint force
nor pad contact force is a measurement of local cuticular strain; the rigid
model also has no hair-plate deflection state. These mechanical channels
cannot by themselves resolve the `SNppxx` receptor type or calibrate its
afferent response.

`tools/audit_lf_proprio_annotation_history.py` compares the same seven body
IDs and eight identity-related fields against the published v0.9 annotation
table. `reports/lf_proprio_annotation_history.json` pins both table hashes
and records zero changes between v0.9 and v1.0 for these cells. The
[official release page](https://male-cns.janelia.org/release/) lists v1.0 as
the latest release; the public bucket has no v1.1 prefix as of the audit.
Historical agreement does not supply the missing sensory tuning evidence.

The pinned MaleCNS neurotransmitter table predicts acetylcholine for the one
direct presynaptic cell **within the 23 typed chordotonal candidates**,
SNpp50 body 912317, with reported confidence
0.95125; its ground-truth field is empty. The path audit now binds that exact
table by SHA256 and records this prediction. It does not identify the
postsynaptic receptor on motor candidate 815344 or its current sign, so the
prediction does not authorize an excitatory synapse assignment or a measured
reflex. An individual receptor annotation or physiological perturbation is
still needed to determine the effective sign.

The existing full-graph FP64 diagnostic **does** assign this edge a positive
weight: its global acetylcholine rule is +1 and it uses 0.275 mV per annotated
contact, giving +1.375 mV for these five contacts. The path audit derives this
from the archived diagnostic spec, pins that report's SHA256, and checks the
actual +1.375-mV edge in `build/brain_body_graph.bin`. This is an
explicit computational hypothesis shared by the closed-loop probes, not a
measured receptor-mediated postsynaptic potential. The previous body motion
therefore cannot resolve this sign ambiguity.

The [MaleCNS annotation paper](https://elifesciences.org/reviewed-preprints/97766)
predicts that SNpp50 activates tibia extensor motor neurons directly and
through cholinergic serial neurons. Thus the positive diagnostic sign agrees
with the authors' circuit-level prediction, but the paper presents it as an
inference from anatomy and transmitter class. It does not measure the receptor,
postsynaptic potential, or gain for the individual 912317→815344 contact. The
local audit establishes that this particular retained graph pair has five
contacts; it cannot convert the type-level prediction into a measured
individual synaptic response.

A frozen full-CNS edge-sign replay in
`tools/probe_lf_claw_direct_edge_sign.py` used the archived 1,000-tick
keyframe negative-position sensor-drive trace. With the original +1.375-mV
edge, all 4,843 neural events matched the archived closed-loop run exactly;
SNpp50 fired 38 times and candidate motor 815344 fired at ticks 188, 296,
and 710. Silencing only this edge kept 4,843 total events but shifted those
motor events to 190, 302, and 726. Reversing only the edge produced 4,842
total events and motor events at 193 and 734. Both interventions first changed
the event sequence at tick 188; the sensory cell's 38 spikes were unchanged.
The source trace, original graph, source event file, and all three new event
arrays are hash-bound in `reports/lf_claw_direct_edge_sign.json`. The sensor
drive was replayed open-loop without recomputing body mechanics, and the
central voltage jumps, sensory gain, and motor mapping remain unmeasured.
This establishes sensitivity of the numerical full-CNS diagnostic to one
assumed contact sign, not an experimentally determined postsynaptic sign or
biological reflex.

Do not assign a uniform FeCO subtype solely from `SNpp39`: Virtual Fly Brain
labels a [MaleCNS SNpp39 ProLN cell](https://www.virtualflybrain.org/term/none-malecns903843-vfb_jrmc171p/)
as a femoral chordotonal **hook** neuron, while a
[MANC SNpp39 MetaLN cell](https://www.virtualflybrain.org/term/snpp39_metaln_r-manc44595-vfb_jrcv0yer/)
is labelled **club**. These are different specimens and leg segments, and
the public pages do not establish an individual crosswalk for the local
FlyMimic front-leg joint. The existing MaleCNS candidate table has no
functional encoder, joint binding or gain. A closed-loop injection would
therefore still be an engineering hypothesis, not biologically validated
proprioception.

## Exploratory closed left-front claw loop and refractory correction (2026-09-24)

The [MaleCNS annotation study](https://elifesciences.org/reviewed-preprints/97766)
identifies SNpp50 as a claw type and predicts activation of tibia extensor
motor neurons directly and through cholinergic serial neurons. This is a
connectomic prediction, not an individual cell's measured angle tuning or
spike transfer function. The local source graph independently contains one
five-contact edge from left-front SNpp50 body 912317 to tibia-extensor
candidate 815344. Claw physiology in [Mamiya et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6481666/)
supports sensing tibia position, but it does not identify the preferred angle
or membrane-current gain of this MaleCNS cell.

Before execution, `configs/lf_claw_closed_loop_probe.json` fixed four cases,
1000 steps, a positive and negative half-wave position encoder at
200 mV/rad, and the existing hypothetical motor-to-muscle filter. Both the
full FP64 MaleCNS CUDA graph and the published FlyMimic mechanical model
advanced online at 0.1 ms. The same artificial central voltage jumps were
applied in every case. No altitude, rocket velocity or other privileged
flight telemetry entered the graph.

The first run erroneously marked SNpp50 as `sensory=1` in the native Shiu-style
API. That bit gives **zero refractory interval** to its Poisson-input targets;
it does not mean a MaleCNS cell has validated sensory physiology. In this
first run SNpp50 fired 333 times in 100 ms, with a minimum two-tick
interspike interval. Preserve the result below as a diagnostic of this
zero-refractory model variant, not evidence for a plausible claw firing rate.

The positive-position branch first differed from blocked feedback in its
physical knee-derived input at tick 192. Its first extra full-graph spike
was the selected sensory cell at tick 228; first motor-candidate spike
difference was tick 403; the passive slide first differed at tick 424.
It produced 6742 total neural events versus 5001 blocked, 8 versus 2
motor-candidate spikes, 217 versus 64 exact foot-pad contacts, and
0.040124 versus 0.001446 mm peak slide. The negative-polarity branch
delivered at most 0.000117 mV under this physical trajectory and caused
no new neural event. The positive branch reached 25.356 mV sensor input;
this is not a measured physiological amplitude. Full event and physical
traces are hash-bound in `reports/lf_claw_closed_loop_local.json`.

The free-loop motor-disconnected case did not move the joint enough to drive
the chosen positive sensor. A separate, explicitly post-result motor-path
intervention therefore replayed the exact positive-branch sensory input
while disconnecting the muscle output. All full-graph events and motor spikes
matched the positive branch, but exact pad contacts and slide motion were
both zero (`reports/lf_claw_motor_break_replay.json`). This supports the
sequence physical position -> assumed encoder -> native CNS -> assumed motor
filter -> muscle/contact in this engineering fixture. It does not establish
individual claw tuning, physiological gain, biological reflex accuracy,
learning, visual control, a seated cockpit or KSP competence. Python
orchestrates the two native solvers; a unified native runtime is still open.

The corrected `configs/lf_claw_closed_loop_refractory_probe.json` kept the
same physical scene, drive coefficient, polarity pair, central stimulus,
motor filter and four interventions. Only SNpp50's sensory mask bit was
cleared, giving it the ordinary 22-tick (2.2-ms) refractory interval;
external current injection still works. The positive branch then had 33
SNpp50 spikes, with a minimum 23-tick gap. It first differed in input at
tick 192, in its own spike at 228, in the motor-candidate spike at 615,
and in slide motion at 819. Peak slide was 0.002603 mm versus 0.001446 mm
with feedback blocked. Total graph events were 4751 versus 5001 blocked;
the motor candidate spiked twice in each branch but its second spike shifted
from tick 641 to 615. The positive sensor input peaked at 7.272 mV. The
negative branch still produced no additional event. The source-fixed
sensory replay with motor output disconnected preserved every neural event
of the corrected positive branch and yielded zero pad contacts and slide
motion. Reports: `reports/lf_claw_closed_loop_refractory_local.json` and
`reports/lf_claw_motor_break_refractory_replay.json`.

The correction sharply reduces the apparent feedback effect; it does not
calibrate this particular receptor's refractory period, preferred angle,
gain, or motor-unit identity. The native model's 2.2-ms value comes from
the Shiu numerical reference, not a measurement of this MaleCNS SNpp50.
**Pose limit of the exploratory physical loop:** The FlyMimic leg in the
closed-loop and motor-break reports below was initialized with ordinary MuJoCo
zero reset followed by passive relaxation. The published XML has a
`default-pose` keyframe with left-front tibia pitch 1.862 rad; zero reset
settled near 0.4736 rad. Thus the reported sensory/central/contact causality
is specific to the exploratory non-keyframe fixture. The angle polarity,
threshold, gain, and motor action have not been validated from the source
keyframe. See `reports/flymimic_keyframe_mechanics_local.json`.

A new source-keyframe-derived loop starts from the published `default-pose`,
then applies 20,000 low-activation passive steps and uses a positive-X pad
derived from that foot mesh. It keeps the 22-tick SNpp50 refractory interval
and tests both unmeasured knee-position polarities against blocked feedback.
The positive-polarity input stayed zero and all 5,001 full-graph events matched
blocked feedback. The negative-polarity hypothesis first changed sensory
drive at tick 1, produced an SNpp50 spike at tick 86, changed the motor
candidate at tick 188, and changed slide travel at tick 245. It produced 38
SNpp50 spikes and 4,843 graph events in 100 ms; peak slide travel was
0.072597 mm versus 0.048848 mm with feedback blocked. These are outcomes of
the declared artificial 200-mV/rad encoder, not evidence that this cell has
that sign or gain in the animal. A motor-disconnected live run changed its
later sensory stream because body motion changed. Replaying the *identical*
negative sensory sequence with motor output disconnected preserved all neural
events and motor spike times exactly while giving zero foot-pad contacts and
slide travel. See `reports/lf_claw_closed_loop_keyframe_local.json` and
`reports/lf_claw_motor_break_keyframe_replay.json`.

`tools/audit_mamiya_claw_angle_polarity.py` describes the imported author
R73D10 GCaMP6f claw recordings without fitting a neural encoder. For each
pixel-cluster row in the X/Y/Z branches and both ramp-and-hold directions, it
subtracts median calcium response in the lowest 10% of measured-angle frames
from the median in the highest 10%. Across 120 rows, 59 contrasts are
positive and 61 negative; 59 of 60 fly/protocol/branch pairs have opposite
cluster signs. The report pins every source file and row contrast:
`reports/mamiya_claw_angle_polarity.json`. This supports retaining both
sensory-polarity hypotheses in exploratory tests. It does **not** identify
which cluster, if either, corresponds to MaleCNS SNpp50; cluster labels are
derived from response similarity within a trial, and calcium response is not
a measured membrane-voltage gain. No parameter in the full-CNS runtime was
changed by this audit.

`tools/audit_mamiya_claw_approach_order.py` now screens the same source-pinned
R73D10 ramp-and-hold tables for within-trial response differences at the same
measured angle after opposite movement directions. It uses the middle eight
frames of each qualifying plateau (at least 12 contiguous frames within ±3°),
normalizing each contrast by that row's 5th-to-95th-percentile calcium range.
The exploratory 154° bin yields median extension-minus-flexion contrasts of
0.228 in FlexFirst and 0.030 in ExtFirst (24 accepted pixel-cluster rows per
protocol); at 97° they are −0.004 and 0.007 (16 rows per protocol). Every
selected frame and source hash is in `reports/mamiya_claw_approach_order.json`.
The protocol-order dependence prevents interpreting these contrasts as a
unique tendon hysteresis law. GCaMP kinetics, adaptation and experimental
history are entangled; matching fly/cluster labels across protocols do not
prove the same physical pixel cluster. This analysis was chosen after
exploratory inspection of the recordings and is not an untouched validation
set. No peripheral memory state or MaleCNS sensor current is calibrated.

`tools/audit_mamiya_angle_direction.py` resolves the **author recording's**
angle convention from the archive README and all 120 R73D10 ramp-and-hold
rows. FlexFirst begins extended and its initial three-frame angle lies at
99.912–99.9996% of each row's measured range; ExtFirst begins flexed and
starts at 0.0005–0.1872%. Thus high recorded degrees mean extension and low
degrees mean flexion. `reports/mamiya_claw_angle_direction.json` pins the
source and per-region bounds. The 59 positive high-minus-low claw calcium
contrasts describe extension-associated pixel-cluster responses; the 61
negative contrasts describe flexion-associated ones, subject to calcium
response dynamics. This does not map a cluster to SNpp50 or SNpp51. The
[MANC annotation authors](https://elifesciences.org/reviewed-preprints/97766)
explicitly describe SNpp50 and SNpp51 as two claw types not yet reported
as separate types in the light-level literature, while predicting opposing
motor effects. Their anatomical motor prediction is not a measured
SNpp50-versus-SNpp51 angle preference. Both per-cell tuning hypotheses
remain open in the native MaleCNS model.

`tools/audit_flymimic_knee_angle_direction.py` independently computes the
3D interior angle at the left knee from the trochanter, tibia and first
tarsus body origins in the pinned FlyMimic XML. Across 201 evenly spaced
joint coordinates over its allowed range, every increase in
`joint_LFTibia_pitch` reduces this geometric angle: 152.78° at q=0.4789 rad
to 44.07° at q=2.502 rad. Thus increasing FlyMimic q is flexion and
decreasing q is extension. Combined with the author data above, the
**qualitative** sign between the two angle conventions is opposite.
`reports/flymimic_lf_knee_angle_direction.json` pins the XML and calculation.
Exact degree-to-radian calibration, joint-axis registration, specimen
geometry transfer and individual SNpp50/SNpp51 tuning remain unresolved.

### Static FeCO structure geometry

`tools/audit_mamiya_xray_geometry.py` now pins four Virtual Fly Brain SWC
exports from the [Mamiya X-ray reconstruction](https://www.virtualflybrain.org/term/biomechanical-origins-of-proprioceptive-maps-in-the-drosophila-leg-mamiya2022/):
arculum midline and outline, plus medial and lateral FeCO tendons. Each
header specifies micrometer coordinates. `reports/mamiya_xray_geometry.json`
records source URLs, hashes, node counts, bounding boxes, and sampled-node
proximity in the common VFB frame. The nearest sampled medial/lateral tendon
nodes are respectively 0.735/0.439 µm from arculum *outline* nodes. These
are discrete skeleton distances, not measured surface gaps or identified
mechanical attachment sites. The long tendon traces extend far beyond the
arculum, consistent with a separate structure representation.

This provides a source-anchored static geometry constraint for a future FeCO
mechanism. It does not determine deformation with knee angle, tension or
strain at cap cells, the joint pivot, specimen-to-FlyMimic registration, or
the input transform for any MaleCNS sensory neuron. No sensory current or
plasticity rule is inferred from these coordinates.

The same source PDF, STAR Methods e6–e7, gives the **author FE model's** four
equilibrium tendon lengths (joint 72, femoral 225, medial 268, lateral 283 µm),
areas (295.3, 295.3, 50.9, 57.2 µm²), assumed resilin modulus 1.8 MPa,
arculum modulus 3.6 MPa, density 1200 kg/m³, and Poisson ratio 0.3. The
authors halved the medial spring's effective stiffness to represent soft
proximal coupling. These are specified FE assumptions, not independent
measurements of material constants for this MaleCNS specimen.

Our SWC medial/lateral **total edge lengths** are 569.38/443.36 µm, and
their largest individual gaps are 114.31/78.55 µm. The FE equilibrium lengths
268/283 µm therefore cannot simply be substituted for the total sampled
SWC paths. Different modeled endpoints, branches, sparse skeleton sampling,
and specimen representations need to be resolved before transferring these
values into the fly body. `reports/mamiya_xray_geometry.json` records both
source-pinned sets explicitly.

Topology resolves one ambiguity: the medial SWC has one root, one branch
node, and **two** root-to-tip paths of 329.92 and 462.95 µm; its 569.38 µm
total counts their shared segment only once and does not describe any one
complete route. The lateral SWC has one root-to-tip path of 443.36 µm.
All three root-to-tip distances exceed the corresponding FE equilibrium
lengths; the report retains root/tip coordinates so attachment endpoint
selection can be audited rather than inferred from a single length.
The medial root-to-branch path is 223.49 µm, closer to the authors' 250-µm
idealized medial cable than either full root-to-tip path. This is a candidate
geometric correspondence only: the SWC branch has not been verified as the
fibril attachment endpoint of that 2D model.

`tools/audit_mamiya_xray_surfaces.py` also pins the source VFB OBJ meshes for
the arculum and both tendons. They are watertight triangle meshes, with the
SWC nodes inside each mesh's coordinate bounds. Their closest sampled **vertex**
pairs are 0.444 µm (medial–arculum) and 0.288 µm (lateral–arculum), as recorded
in `reports/mamiya_xray_surfaces.json`. A vertex pair is an upper bound for
the true surface separation; it neither proves contact nor identifies a
load-bearing attachment. Surface intersections, local normals, and attachment
patches need a separate geometrical and histological check before the meshes
can define force transmission in the body model.
