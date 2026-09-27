# Current biological gate (2026-09-24)

KSP, landing training, cockpit geometry, and rocket diagnostics are deferred. The active path is measured sensory input to neural response, then verified motor identity and movement, then local plasticity with a measured behavioral effect. The eventual Mun goal is unchanged.

## Evidence boundary

The full-CNS 20 ms gray/light/dark visual runs give model L1/L2 responses (see `VISUAL_CAUSALITY.md`), but their absolute photon rate, synaptic gains, membrane parameters and observation model are not calibrated against a recording. Existing leg/contact motion was elicited by artificial central voltage jumps through an unconfirmed individual motor-neuron-to-muscle link; it is an engineering chain check, not a biological sensorimotor reaction. The gamma4 KC-to-MBON contact ROI has no verified compartment-specific synapse assignment or receptor mechanism, so learning remains disabled.

Pang et al. measured L1/L2 biphasic responses to 20 ms flashes and recorded the stimulus settings and voltage-indicator traces (DOI 10.1016/j.cub.2024.11.064; Dryad DOI 10.5061/dryad.ngf1vhj4c). Their flies were female; this is a transfer limitation for the male connectome. The dataset API exposes version 335185 and file metadata, but individual downloads returned HTTP 401/403 in this environment on 2026-09-24. The Dryad per-recording traces were not acquired. The public Dryad page lists L1L2_Metadata.xlsx (195.43 KB), but the browser download did not complete and the page exposes no XLSX preview. The pinned author notebooks refer to highLum/lowLum MAT files without filter, PWM, photon-rate, or recording-ID metadata. Thus neither the workbook contents nor a numeric luminance assignment can be inferred from those labels. Four processed author-repository mean curves were acquired separately below; no fit or agreement is claimed.

As an accessible primary reference, `data/reference/juusola_r16_elife26117/elife-26117-fig1-data1-v2.xlsx` is a byte-pinned source table from eLife 26117 Figure 1 source data 1. `reports/juusola_r16_reference_audit.json` checks five sheets, each with 2,000 one-ms samples, 20 runs, a mean and SD. Those data are burst stimuli at 20-500 Hz in darkness; they do not match our 20 ms single-flash experiment. Do not score current model traces against this table.

The pinned Pang stimulus repository supplies three 20-ms flash configurations
on a 0.5 relative-gray background: A uses dark/light 0/1, B uses
0.25/0.75, and C uses 0.375/0.625. `reports/pang_20ms_stimulus_family.json`
pins the configuration bytes and MATLAB class. Since recording-specific
`stimcode` remains unavailable, no processed highLum/lowLum curve can be
assigned to A, B or C from its filename alone.

## Next discriminating experiment

Acquire the Pang L1/L2 processed traces and recording-specific stimulus/photodiode metadata through an accessible author mirror or archive. Freeze the published light waveform and analysis windows before a new model run. Match stimulus delivery and indicator/voltage observation transforms explicitly, then compare light and dark first-phase sign, peak latency, second-phase area and genotype manipulation. Treat female-to-male transfer and any uncalibrated photon scale as explicit uncertainties. A failure should direct a source-backed receptor or circuit correction, not a fitted hidden motor drive.

Separately, pursue a verified individual MaleCNS-to-MANC motor identity and muscle target with measured neural response to a natural sensory input before enabling body movement as biological evidence. Keep local plasticity disabled until synapse compartment and receptor-sign assignments support a testable local rule.

## Male tibia-extensor response target

### Independent interneuron physiology source audit (2026-09-24)

[Agrawal et al. (2020)](https://elifesciences.org/articles/60299) measured leg-proprioceptive responses in the 13Bα, 9Aα and 10Bα interneuron classes. Their [Dryad dataset](https://datadryad.org/dataset/doi:10.5061/dryad.k3j9kd55t) is version 3 (API version 94574) and lists `Imaging_data.zip` (804,623 bytes; SHA-256 `c7b3787fdf3be70f0eccf3a7687b37f64161883074c17b0909cbac4ac69e1788`), `Behavior_data.zip` (8,951,863 bytes), and `Ephys_data.zip` (7,496,404,627 bytes). An unauthenticated API file-download request for the small imaging ZIP returned HTTP 401 here. No recording bytes were acquired, and the 7.5-GB ephys archive was not downloaded. The authors' [analysis and stimulus-code repository](https://github.com/sagrawal/InterneuronAnalysis) is accessible; its `master` tree was `b3c43530d1915c4059cc2046494cf3db1311dbdd` at audit time.

The publisher's [PDF](https://cdn.elifesciences.org/articles/60299/elife-60299-v2.pdf) is available and byte-pinned locally under `data/reference/agrawal2020/elife-60299-v2.pdf`. `tools/extract_agrawal_13b_figure2g.py` extracts the two colored mean vector paths from Figure 2G, with 11 angle/normalized-response points each and separately declared approximate axis anchors (`data/reference/agrawal2020/figure2g_digitized.csv`, `reports/agrawal_13b_figure2g.json`). The figure describes ramp-and-hold measurements: steady-state response from the middle second of each 3-s step; individual traces were normalized to the same maximum before averaging. These published *figure means* give an accessible orientation/hysteresis target even though raw Dryad recordings remain unavailable. Axis reading contributes about ±2.5° and ±0.015 normalized-response uncertainty. These are not absolute membrane voltages, individual-cell traces, a graded-release calibration, or a basis for assigning a MaleCNS body ID.

`tools/audit_agrawal_13b_hysteresis_gate.py` compares the digitized means at shared angles without fitting the model. Extension-minus-flexion normalized-response gaps are approximately 0.131 at 90°, 0.157 at 120°, and 0.206 at 150° (`reports/agrawal_13b_hysteresis_gate.json`). Perturbing all four PDF axis anchors by ±1.5 PDF points gives respective gap ranges 0.122–0.142, 0.152–0.162, and 0.200–0.212 when the two curves share one calibration; independently perturbing the two curves gives 0.072–0.192, 0.076–0.238, and 0.141–0.271. This is a numerical axis-reading sensitivity check, not an animal-level confidence interval. The current SNpp50 diagnostic encoder is an instantaneous formula of angle and contains no explicit approach-history state. The script establishes that property from the formula, but does **not** execute opposite-history trajectories through the encoder and complete recurrent CNS at a matched angle. Recurrent state may retain history, and the biological location of any history mechanism is unresolved. A credible reproduction requires paired stimulus/response data, individual 13Bα identity and observation mapping, and matched-angle opposite-history runtime comparisons before attributing a failure to peripheral mechanics or central circuitry.

A separate matched-angle **full-graph runtime diagnostic** now tests two histories (`tools/probe_agrawal_matched_angle_full_graph.py`, `reports/agrawal_matched_angle_full_graph.json`). The unchanged unmeasured positive-half-wave encoder drives one SNpp50-named candidate for 100 ms at +10° or -10° relative angle, followed by the same 0° angle and zero sensory drive for 300 ms. The +10° run produced 51 graph events (44 in the input cell); the -10° run produced none. At the matched angle, the maximum full-graph voltage difference fell from 19.069 mV at the first hold step to 0.221 mV at 100 ms and 0.0000100 mV at 300 ms. Seven of 13 screened IN13B candidates had a nonzero voltage difference at the first hold step; none fired during either run. Thus this actual recurrent model temporarily retains history despite identical instantaneous input, and its observed difference decays over this 300-ms hold. The 100-ms history/300-ms hold, one artificial spiking input, uniform LIF cells, and unresolved candidate identity do **not** reproduce the paper's 3-s ramp-and-hold 13Bα graded responses. The older figure audit records no runtime experiment *within that script*; this separate report supplies the runtime check without changing the biological conclusion.

These measurements are a promising *independent* response target, but no individual MaleCNS body IDs have yet been justified as the recorded 13Bα/9Aα/10Bα cells. The released stimuli and recordings must be paired, their sex/preparation checked, and a cell-type crosswalk established before any model-versus-recording score. A model response under the present unmeasured angle encoder cannot be called a reproduction of these observations.

`tools/audit_agrawal_lineage_candidates.py` pins the local MaleCNS nodes file and counts type prefixes without treating them as identities: 439 `IN13B` rows across 97 types, 535 `IN09A` rows across 92 types, and 254 `IN10B` rows across 33 types (`reports/agrawal_lineage_candidates.json`). This many-to-many lineage ambiguity rules out assigning the published traces to a convenient individual body ID by name alone. The audit approves zero individual mappings.

The published whole-cell physiology also exposes a **model-class mismatch**. The recorded 13Bα neurons had no detectable action potentials and encoded tibia position through tonic graded membrane potential; 10Bα current injection did not evoke identifiable action potentials in the reported recordings, though occasional spike-like events occurred. Recorded 9Aα neurons did fire and were heterogeneous across cells. The existing full-CNS runs use binary threshold events only. It would be incorrect to interpret their 13Bα-like output as the measured graded response, or to conclude that all 10Bα cells are biologically nonspiking.

The same [Agrawal et al. paper](https://elifesciences.org/articles/60299) reports that depolarizing a recorded 13Bα cell reduced its membrane-potential changes during both tibia extension and flexion (Figure 2 supplement 1E/F). The authors interpret this as evidence for changing excitatory driving force: picrotoxin did not affect the 13Bα response, whereas TTX abolished it; nicotinic and muscarinic antagonists had only subtle effects. They leave gap-junction coupling versus incomplete cholinergic blockade unresolved. `tools/check_agrawal_voltage_driving_force_gate.py` tests a narrower numerical question on the current native mixed ABI (`reports/agrawal_voltage_driving_force_gate.json`). A graded source is held at -50 mV and an isolated receiver at either -65 or -55 mV, with spike thresholds disabled and synaptic input compared to a weight-zero control. At 100 ms the evoked receiver shifts are 0.4949744913447063 and 0.49497449134478444 mV: equal within 8e-14 mV, whereas the published depolarization intervention decreased response amplitude. The present *current-based, voltage-independent* synaptic term cannot represent that driving-force dependence in this subthreshold setting. Full-network nonlinearities or other mechanisms are not ruled out. A biologically grounded 13Bα path needs a source-supported conductance/electrical-coupling hypothesis and an independent intervention check; the pharmacology does not by itself prove electrical coupling or set its strength.

The publisher's separate [Figure 2 supplement 1 image](https://iiif.elifesciences.org/lax/60299%2Felife-60299-fig2-figsupp1-v2.tif/full/full/0/default.jpg) is pinned under `data/reference/agrawal2020/fig2_supp1.jpg` (SHA-256 `73de398fb86593e1e3775b1bfaf5a460af634d66d193ee6c61cb71884b411845`). Panel E plots paired response amplitudes against resting voltage. We built an *isolated native C++ conductance hypothesis* (`native/agrawal_conductance_candidate.cpp`) with an explicit conditional `E_rev=0 mV`, `gmax=0.02`, and 0.5 release. At 100 ms, baseline -65 versus -55 mV yields evoked shifts 0.64349 versus 0.54453 mV: the qualitative direction in the source panel, and a depolarized/hyperpolarized ratio of 0.84621 stable across dt=0.2/0.1/0.05 ms. An independent Python recurrence checks the compiled outputs (`tools/check_agrawal_conductance_candidate.py`, `reports/agrawal_conductance_candidate.json`). Neither the reversal, conductance, release law, nor cell identity is measured here. This is a model-class capability demonstration, **not** a fit to Panel E, proof of a chemical synapse, or an enabled full-CNS phenotype. Quantitative paired intervention data and a cell/edge crosswalk are needed before selecting or transferring this mechanism.

An exploratory reading of two particularly long individual lines in Panel E now constrains that simple interpretation (`tools/audit_agrawal_voltage_panel_lines.py`, `reports/agrawal_voltage_panel_lines.json`). OpenCV line detection on the pinned colored pixels identifies red extension endpoints (130,1702)→(419,1837) and blue flexion endpoints (162,1777)→(300,1901). With explicitly declared image-axis anchors, straight-line extrapolation of response `k*(E-V)` gives zero-response intercepts +32.37 and -25.59 mV. Under 20,000 deterministic ±3-pixel perturbations of endpoints and anchors, the sampled ranges remain disjoint (+26.0…+39.5 versus -28.5…-22.1 mV). Three Hough detector settings retain a positive red and negative blue intercept, although the blue settings can select different overlapping line segments. These are **not measured reversal potentials** or confidence intervals. Only two illustrative lines were read, and changes in presynaptic input, intrinsic response, electrical coupling, or cell-specific conditions could also affect their slopes. The exercise rejects treating the earlier arbitrary shared `E_rev=0` demonstration as a quantitative fit to these two lines; it does not reject a conductance component in the biological cells. Raw paired voltage/current records and a mechanistic model of the intervention are the next gate.

The native FP64/FP32 CUDA libraries now expose a separate `create_mixed` ABI with a caller-supplied cell mask and voltage span. For masked cells, the **uncalibrated diagnostic** release is `r=clip((V-rest)/span, 0, 1)`; those cells do not reset or emit spike events. A graded edge contributes `w*r*(1-exp(-dt/tau_synapse))` to synaptic state each step: `w` is its steady synaptic-state contribution at unit release. An unmasked spiking edge retains the previous event-impulse weight semantics. `tools/check_cuda_mixed_output.py` checks a two-cell path: a subthreshold 10-mV voltage jump yields postsynaptic synaptic state 0.09802150100329941 at tick 2 through the graded path, while the old spike-only path is silent. It also checks exact mixed checkpoint replay and rejection of a mixed checkpoint by the old handle (`reports/cuda_mixed_output.json`). Mixed checkpoints now use version 3 and a numerical-semantics identity tag; synthetic version-1/2 headers are rejected without changing the destination state, while legacy spiking checkpoints retain version 1. Both DLLs compile locally. A separate constant-voltage two-cell test checks three step sizes at equal physical times (`tools/check_cuda_mixed_dt_convergence.py`, `reports/cuda_mixed_dt_convergence.json`): the 20-ms synaptic-state spread across dt=0.2/0.1/0.05 ms is 0.000344, and the 100-ms spread is below 4e-11. Receiver-voltage error toward an idealized continuous 1-ms-delayed forcing reference at 20 ms falls from 0.01095 to 0.00276 mV as dt decreases from 0.2 to 0.05 ms. This tests a controlled two-cell numerical limit, not an exact solution for arbitrary networks or a measured biological conductance. No MaleCNS cell has been assigned the new mask; no source supports the linear release law or its voltage span for 13Bα. Next biological gate: establish individual-cell identities and source-supported graded release/observation equations, then score voltage trajectories against paired published input-response recordings. The present full-CNS runs remain diagnostic, not a physiologically complete CNS.

The rebuilt FP64 DLL also passes a full-graph legacy regression (`tools/check_cuda_legacy_full_graph_rebuild.py`, `reports/cuda_legacy_full_graph_rebuild.json`). Both archived tick-500 checkpoints load with unchanged model identity. Ticks 500–999 reproduce all archived suffix events exactly (3,756 and 1,852 events in the two transmitter-sign variants) and both final voltage/synapse arrays bit for bit. This establishes backward compatibility for those two diagnostic conditions, not biological fidelity.

A separate four-tick **full-graph mixed numerical test** now exercises the new path without assigning a phenotype (`tools/check_cuda_mixed_full_graph.py`, `reports/cuda_mixed_full_graph.json`). The test temporarily masks one anatomically screened body ID 800115 and adds an artificial, subthreshold +5 mV jump. At tick 2, the complete postsynaptic synaptic-state vector agrees with the analytical CSR-weighted release vector; all 583 direct targets receive nonzero input. The legacy spike-only handle has no spikes or propagated input under the same drive, and a mixed checkpoint resumes with bit-exact suffix outputs. The 20-mV release span and selected cell are strictly software-test parameters, not physiology or an approved 13Bα identity.

`tools/audit_agrawal_13b_connectivity.py` now screens the exact incoming CSR for all 147 T1 `IN13B` rows without enabling any graded mask. Thirty-one receive at least one direct edge from a front-leg chordotonal annotation. Thirteen receive 17 direct edge rows / 40 source synapses from `SNpp50/51`-named front-leg objects (`reports/agrawal_13b_connectivity.json`). All thirteen have `somaSide=R`; these `SNpp50/51` sources have `rootSide=L`. The source paper positions 13Bα near extension-tuned claw input but does not establish that every MaleCNS `SNpp50/51` is that class, nor that a cross-midline soma-side relationship matches the recorded morphology. Synapse rank and lineage name do not resolve this lateralization or individual identity. No candidate was selected for the mixed runtime.

The complete front-leg chordotonal side matrix for these T1 `IN13B` rows is 49 direct edge rows from left-root `ProLN` cells into right-soma candidates and 4 from right-root `ProLN` cells into left-soma candidates; no `ProCN` edge appears in this direct subset. This is asymmetric even though both sides have annotated sensory candidates, and it cannot by itself establish a biological left/right rule. Thirteen version-pinned public MaleCNS SWCs (`data/reference/malecns_v1_agrawal_13b_candidates/source_manifest.json`) were compared with four already pinned presynaptic SWCs. All 17 linked candidate/source pairs have nearest coarse skeleton nodes within 0.887 µm, confirming geometric proximity compatible with the graph contacts (`reports/agrawal_13b_skeleton_proximity.json`). Coarse-node proximity does not localize synapses, assign the experimental 13Bα subtype, or resolve the side asymmetry.

[Akitake et al. (2015)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4535187/)
measured extensor-muscle EMG in 3–5-day-old male Drosophila after a 1-hour
recovery from cold anesthesia. A speaker-driven wire loop moved the tibia
sinusoidally at 2 Hz through approximately 20°; ten movements formed a set,
with one minute between sets. In wild type, the reported slow-extensor-related
signal was 107.2 ± 11.5 detected events per movement cycle (mean ± SEM), with
the extensor silent without flexion. TRPγ mutant groups showed reduced counts
(64.8 ± 8.6, 64.4 ± 7.5, and 45.8 ± 8.3, depending on genotype); genetic
restoration returned counts near wild type. These are published muscle EMG
observations, not intracellular spikes from MaleCNS body 815344. The paper
does not assign the response to individual SNpp50 body 912317 or identify
its synaptic receptor.

This gives a prospective, sex-matched **behavioral physiology gate**: a
source-specified passive tibia-flexion protocol should drive extensor-muscle
activity in the intact native CNS/body chain, with an independently justified
observation mapping from motor units to EMG events. A no-motion control and
sensor-path perturbation should distinguish the evoked response from background
or imposed central drive. The published TRPγ perturbation is informative but
cannot be represented by deleting one SNpp50→motor edge: TRPγ acts in both
chordotonal sensory neurons and scolopale support cells. Absolute EMG counts
cannot be scored against a single simulated motor neuron or a 100-ms
artificial-voltage-jump diagnostic. Sensory transduction, motor-unit crosswalk,
force transfer, and observation mapping must be justified before a match claim.

The [MaleCNS annotation paper](https://elifesciences.org/reviewed-preprints/97766)
predicts direct and serial activation of tibia extensor MNs by SNpp50.
The later [grooming-circuit study](https://elifesciences.org/articles/106446)
also describes flexion-sensing proprioceptors targeting extensor MNs and
flexor-inhibiting premotor cells. These connectomic predictions support the
choice of pathway for testing, but neither provides a measured response for
the individual 912317→815344 contact.

### Prescribed movement full-CNS diagnostic (2026-09-24)

`configs/lf_tibia_passive_movement_probe.json` freezes one 500-ms cycle of a
2-Hz, 20° peak-to-peak sinusoidal tibia-angle hypothesis. This interprets the
paper's approximate movement range; its exact phase and sign relative to the
MaleCNS SNpp50 response and exact FlyMimic angle scale were unregistered.
Subsequent author-angle and body-geometry audits established only the
qualitative movement convention: high Mamiya degrees and low FlyMimic q
both mean extension (`reports/mamiya_claw_angle_direction.json` and
`reports/flymimic_lf_knee_angle_direction.json`). Neither audit identifies
which sign excites body 912317. The full native FP64 graph received
no artificial central voltage jumps. Only SNpp50 body 912317 received the
existing, **unmeasured** 200-mV/rad half-wave encoder. Both possible angle
polarities and a sensor-off control were run for 5,000 0.1-ms ticks.

The sensor-off control yielded zero events. Each driven polarity yielded 107
SNpp50 spikes and 17 further spikes in two intrinsic neurons (IN13A002_L:
15; IN13A009_L: 2); motor candidate 815344 never spiked. The two driven
responses are time-shifted by a half-cycle. Of 106 SNpp50 interspike gaps,
95 are the minimum observed 23 ticks (89.6%), so this encoder drives the
model cell close to its refractory-limited rate; it is not a mild stimulus
whose gain can safely be increased to force motor spikes. An exact neural
replay of the
positive-angle case recorded candidate motor voltage from −52.0 to
−49.0043 mV, below the model's −45-mV spike threshold by at least 4.0043 mV.
Source and output hashes are in `reports/lf_tibia_passive_movement.json` and
`reports/lf_tibia_motor_voltage.json`; the latter replay reproduced every
archived event exactly. This is a **negative model result** under a stated
unmeasured encoder, not proof that a biological fly lacks a reflex. It also
cannot be compared numerically to the published EMG count without a validated
motor-unit and observation mapping. Raising sensory gain solely to recover
motor firing would fit the desired outcome rather than calibrate physiology.

`tools/audit_lf_tibia_motor_input.py` resolves the active cells against the
original incoming CSR and the actual runtime weights. SNpp50 body 912317 is
the **only** cell that both fired and has a direct retained edge to motor
candidate 815344: five contacts with the diagnostic +1.375-mV edge weight.
The other active cells, GABA-predicted IN13A002 body 800270 and IN13A009 body
800931, have no direct edge to that motor candidate. Their 15 and 2 spikes
therefore cannot directly explain its subthreshold voltage in this 500-ms
run. The result is pinned in `reports/lf_tibia_motor_input_audit.json`.
It does not establish a biological synaptic amplitude, a complete motor pool
response, or the effect of ongoing physiological background activity.

The diagnostic's common −52-mV rest, −45-mV threshold and 20-ms membrane
constant are global engineering settings. They have not been measured for
MaleCNS 815344. The pinned graph itself gives 10,207 incoming annotated
contacts to this candidate versus 3,740 to the other labelled left/right
Ti-extensor candidate 815678; these cells are not an approved fast/slow pair
or a verified one-to-one MANC crosswalk. Independent [FANC anatomical work](https://pmc.ncbi.nlm.nih.gov/articles/PMC11348827/)
reports distinct fast and slow front-leg extensor neurons with 14,904 and
7,090 input synapses in a different specimen. Those numbers must not be
substituted for this MaleCNS pair, but they reinforce that one global LIF
parameter set cannot be assumed to represent extensor motor-unit diversity.
The available [adult Drosophila whole-cell motor physiology](https://pmc.ncbi.nlm.nih.gov/articles/PMC7347388/)
characterizes tibia **flexor** units; it is not a threshold calibration for
this extensor candidate. The next motor validation needs a source-backed
individual motor-unit identity and intrinsic response, as well as a calibrated
FeCO input. The negative spike result is therefore a model finding under
current parameters, not a falsification of the anatomical SNpp50→extensor
prediction.

The MANC ID ambiguity is concrete in the pinned source annotation. `tools/audit_motor_manc_crosswalk.py`
verifies the generation-pinned raw Feather and retained graph nodes: MaleCNS
815344 (`Ti extensor MN_L`, `vnc_motor`) and 800163 (`IN19A002_L`,
`vnc_intrinsic`) both carry `mancBodyid=10256`, while right candidate 815678
carries 22126. In the raw annotation, 438 MANC IDs are assigned to two
MaleCNS rows each; 412 such IDs survive the graph selection. See
`reports/malecns_motor_manc_crosswalk.json`. The duplicate does not prove
which annotation is wrong or establish a muscle target. Do not use MANC
10256 as a unique identity bridge for 815344 without independent morphology
and target evidence.

The version-matched published [MANC v1.0 export](https://storage.googleapis.com/flyem-manc-exports/v1.0/manc-v1.0-neuron-properties.feather?generation=1685939278333965)
is pinned in `data/reference/manc_v1_motor_crosswalk/source_manifest.json`.
Its body 10256 is `IN19A001_T1_L`, class `intrinsic neuron`, with no exit nerve;
body 22126 is `Tergotr. MN`, class `motor neuron`, target `Tergotr.` and exit
nerve `VProN_R`. The audit verifies both against the pinned MANC v1.0 file.
These IDs do not match the MaleCNS `Ti extensor MN` assignments on either
side. The `IN19A001` versus MaleCNS `IN19A002` subtype difference also
prevents claiming an exact match to 800163. This invalidates both specific
numeric MANC crosswalks as evidence for the extensor muscle, without
identifying the correct MANC counterparts. MaleCNS motor annotations and
its retained graph are unchanged pending an independent morphology match.

There are 12 `Ti extensor MN` rows in each pinned annotation. Eight MaleCNS
`mancBodyid` values name a MANC v1.0 neuron of the same type; two are missing,
and the two disputed IDs name neurons of other types. Of the four MANC
extensor IDs not present in MaleCNS extensor `mancBodyid`, 11657 is a left T1
`Ti extensor MN` and 11706 a right T1 `Ti extensor MN`. They also equal the
`mancGroup` values on MaleCNS 815344 and 815678, respectively. The report
records **815344→11657 and 815678→11706 as candidates only**. A group value
and matching side/type are insufficient for a one-to-one identity; obtain an
independent aligned-skeleton comparison and muscle-target evidence before
replacing either source field or connecting a motor spike to FlyMimic muscle.

Four generation-pinned MaleCNS v1.0 SWCs for the disputed T1 pair and their
same-type T1 alternatives are in `data/reference/malecns_v1_ti_extensor_skeletons/`.
`tools/audit_ti_extensor_skeleton_integrity.py` checks hashes, parent links,
cycles and physical lengths (`reports/malecns_ti_extensor_skeleton_integrity.json`).
The 815344 SWC has three components (8,889, 59, 27 nodes); 800636 has two
(4,112, 12). Largest components cover 99.04% and 99.71% of nodes,
respectively. A morphology match should predeclare whether it uses the
largest component or all components. These MaleCNS skeletons are in native
MaleCNS 8-nm-voxel coordinates; no MANC skeleton or registered cross-volume
comparison has yet been validated.

The four corresponding MANC v1.0 candidate/alternative SWCs are now pinned
through Virtual Fly Brain alongside four official MaleCNS template SWCs in
`data/reference/ti_extensor_template_crosswalk/source_manifest.json`.
`tools/audit_ti_extensor_template_spaces.py` verifies all eight hashes and
bounding boxes (`reports/ti_extensor_template_space_boundary.json`). VFB's
MANC skeletons are in `JRC2018UnisexVNC`, whereas the MaleCNS transformed
SWCs are in `JRC2018U`. These are distinct coordinate frames despite the
similar names; their raw coordinates cannot be compared as distances.
The next morphology check requires a published transformation between these
templates, validated axis orientation and units, and positive/negative
same-type control pairs before a candidate identity is accepted.

The passive-movement diagnostic drove **one** retained SNpp50, whereas a
physical tibia movement stimulates a heterogeneous FeCO population. The
original pinned MaleCNS annotation contains only 23 chordotonal cells
entering the left prothoracic leg nerve, including one SNpp50 and three
SNpp51; the right side has 13. The broader source class
`mechanosensory_proprioceptive` contains 45 left-front cells, including seven
`SNppxx` and ten with no type, whose FeCO subtype cannot be assigned from
these labels. By comparison the same source has 80/83 chordotonal cells for
the left/right mesothoracic leg nerves and 93/100 for the metathoracic nerves.
`tools/audit_lf_proprio_motor_paths.py` checks that all 23 left-front source
IDs were retained in our graph, so this imbalance is in the published source
annotation, not introduced by the local graph filter. The [MaleCNS authors](https://elifesciences.org/reviewed-preprints/97766)
explicitly warn that leg proprioceptive cells suffered degradation and poor
segmentation, with strong variation between hemineuromeres. Independent
[FeCO microscopy](https://pmc.ncbi.nlm.nih.gov/articles/PMC6481666/)
describes roughly 135 cells per leg, including multiple functional classes;
specimen and assay differences prevent a missing-cell count by subtraction.
The 107-spike, no-motor response must therefore be described as a
**single-retained-cell challenge** of this incomplete sensory boundary. It
does not test the published fly's full mechanically recruited population.

The source `mancBodyid` field also fails a direct release-matched identity
check for this group. `tools/audit_malecns_lf_sensory_manc_v1_crosswalk.py`
compares all 23 left-ProLN chordotonal MaleCNS cells with the pinned MANC
v1.0 neuron-property table. Twelve have a numeric MANC ID; all twelve
resolve, but **none has the same type label**. Six targets are sensory and
six are non-sensory. In particular, the tested MaleCNS SNpp50 912317 maps
numerically to MANC 42121, which is `IN14A005`, an intrinsic neuron.
`reports/malecns_lf_sensory_manc_v1_crosswalk.json` pins source hashes and
every row. This does not prove that the MaleCNS cell annotation itself is
wrong; it shows that its numeric cross-release field cannot identify the
same sensory cell without independent evidence. Do not use MANC 42121 to
transfer an SNpp50 tuning curve or receptor identity to MaleCNS 912317.

MANC v1.0 has no neuron with exact `type=SNpp50` in its pinned neuron-property
table. The public Lee-lab **MANC v1.2.1** metadata instead lists three
left-front `SNpp50` cells (96728, 100531, 163745). Their native SWCs are
generation- and SHA-pinned in
`data/reference/manc_121_lf_snpp50_native_swcs/source_manifest.json`.
`tools/screen_malecns_23_chordotonal_manc_121_snpp50.py` transformed all 23
MaleCNS v1.0 left-ProLN chordotonal SWCs through the published
`JRCFIB2022Mraw → MANC` registration chain and compared their centerlines
to those three SWCs. MaleCNS 912317 ranks 4th for MANC 96728 and 3rd for
both 100531 and 163745 by mean bidirectional median nearest-node distance.
The latter two distances are 4.833 and 5.208 µm, while the top MaleCNS
cell for each is 817680 at 4.022 and 3.785 µm. Full rankings and source
hashes are in `reports/malecns_23_chordotonal_manc_121_snpp50_screen.json`.
This is a cross-release morphology screen, not a receptor or individual
identity assignment. Nearest-node distance is affected by SWC sampling
density, and this chain crosses several nonlinear registrations; neither
effect has been calibrated here. No MANC candidate is promoted into the
physiological input model.

The SWC-node density concern was tested without choosing a favorable
sampling scale. `tools/screen_malecns_23_chordotonal_manc_121_resampled.py`
repeated the complete 23-by-3 screen after sampling every parent-linked
branch at predeclared maximum spacings of 1, 2 and 4 µm. A synthetic
straight-segment check gives the same sample positions whether that segment
is stored as two or eleven nodes. All 23 source SWCs had zero missing-parent
links. MaleCNS 912317 stayed **4th, 3rd, 3rd** for MANC 96728, 100531 and
163745 at each of the three spacings. At 1 µm, the respective distances
are 10.14, 4.88 and 5.24 µm. Full source hashes, segment counts, cable
lengths and ranks are in
`reports/malecns_23_chordotonal_manc_121_resampled_screen.json`.
This shows that this *negative specificity result* is stable to the tested
SWC node densities. It does not quantify registration error, missing
peripheral branches or biological identity, and cannot license transfer of
an MANC physiological curve to 912317.

### Four direct sensory partners: circuit-capability diagnostic

`tools/probe_lf_four_direct_proprio_inputs.py` reused the pinned 500-ms
positive-angle trajectory and native FP64 full graph, and applied the same
unmeasured 200-mV/rad half-wave drive **synchronously** to SNpp50 912317,
SNppxx 817697 and 821306, and untyped 908487. No central voltage jump was
applied. Each cell fired 107 times; the graph produced 627 total events and
candidate Ti-extensor motor 815344 fired 22 times, first at tick 115. The
previous one-cell positive-angle case had 124 total events and zero motor
spikes. The full event stream, motor voltage and synaptic input are pinned by
hashes in `reports/lf_four_direct_proprio_inputs.json` and stored under
`data/derived/lf_four_direct_proprio_inputs_v1/`.

This establishes that the **current model circuit can fire this motor** under
one strong, artificial joint-input hypothesis. It does not establish that
these cells share SNpp50 angle tuning, are coactivated by the same movement,
or produce the published extensor EMG. Their source labels and individual
MANC matches do not supply those properties: 817697, 821306 and 908487 have
no `mancBodyid` in the pinned v1.0 annotation. The 22 simulated spikes must
not be compared directly with 107.2 ± 11.5 muscle EMG events/cycle. Next
resolve distinct sensory tuning and motor-unit identity experimentally or
through an explicitly validated cross-specimen mapping; retain the one-cell
negative result and the four-cell sensitivity as separate diagnostics.

`tools/probe_lf_four_proprio_body_loop.py` extended that sensitivity test to
the actual FlyMimic mechanics without a central voltage jump. All three
cases began from the same published default keyframe, 20,000 passive steps,
and an explicit +10° left tibia perturbation. The simulated knee then moved
freely for 500 ms. With sensory input blocked, the CNS had zero events and
there was no foot-pad contact or passive-throttle movement. With the same
four-cell hypothetical angle encoder and motor output connected, the first
sensory spikes occurred at tick 1, motor 815344 fired at ticks 92, 207 and
328, and the first exact LFTarsus5-to-pad contact and first slider divergence
occurred at tick 316. Contact occupied 267 ticks and the maximum slider
travel was 0.102080 mm. With motor output disconnected, sensory and neural
events were identical through the first motor spike at tick 92, the motor
candidate continued to spike, but there was no exact foot-pad contact and
the slider stayed at zero. Later neural streams diverged because physical
feedback differed. Hashes and complete event/physical traces are in
`reports/lf_four_proprio_body_loop.json` and
`data/derived/lf_four_proprio_body_loop_v1/`. The trace and all three event
hashes were checked after execution. A v2 rerun with the same numerical
outputs is in `reports/lf_four_proprio_body_loop_v2.json` and
`data/derived/lf_four_proprio_body_loop_v2/`. Its trace and all three event
SHA-256 values match v1 exactly. V2 also pins the executed script, imported
Python sources, loaded CNS DLL, source/modified FlyMimic XML, NumPy and
MuJoCo versions; it asserts the 0.1-ms physical step. For trace index `t`,
sensory drive reads knee position at `t*dt`, motor command applies during
that step, MuJoCo contact geometry is from its forward phase at step start,
and saved knee/slider `qpos` is after integration at `(t+1)*dt`. Thus a
one-index contact/slider difference is an array comparison, not a measured
physiological latency.

`tools/audit_lf_body_loop_stimulus.py` now checks the actual V2 knee traces
against the [Akitake et al.](https://www.nature.com/articles/ncomms8288)
reflex protocol. In the sensory-blocked body control, the saved knee angle
decreases on all 4,999 step intervals, traverses only **6.223°** in 500 ms,
and stays **3.776°–9.999° above** its relaxed angle throughout. The
motor-disconnected case has a byte-identical knee trace. Thus this
initial-displacement/free-relaxation stimulus is not the published 2-Hz,
approximately 20° sinusoidal tibia movement. Under the existing half-wave
angle encoder, its passive sensory drive would remain active for the whole
window. The fully motor-connected case instead traverses 30.655° because
the hypothetical motor output changes the mechanics. Source trace and
report hashes, all three trajectories and exact calculations are in
`reports/lf_four_proprio_body_stimulus_audit.json`. The observed closed-loop
contact is a capability test and cannot be scored against published EMG
events per 2-Hz cycle.

`tools/build_flymimic_prescribed_tibia_cycle.py` constructs one 500-ms,
2-Hz, 20° peak-to-peak tibia cycle in the pinned FlyMimic source body.
The center is the body's passively settled default pose (133.832° 3D
interior angle), an explicit geometric choice rather than an experimental
start angle. The inverse joint calibration holds every other joint at its
settled position and realizes the sinusoidal angle with at most 0.000010°
error over 5,001 samples. The trace and source hash are in
`data/derived/flymimic_prescribed_tibia_cycle_v1/kinematics.npz` and
`reports/flymimic_prescribed_tibia_cycle.json`. This is an externally
prescribed kinematic boundary; the cycle does not run MuJoCo dynamics,
identify the biological proprioceptor transfer function, or produce a
neural or muscle response. Those mappings must be validated before scoring
the CNS against the published reflex experiment.

`tools/audit_tibia_geometry_neural_stimulus.py` aligns the first 5,000 body
samples to the earlier full-CNS prescribed-angle diagnostic at the same
timestamps. After subtracting the body's initial interior angle, the maximum
angle discrepancy is 0.0000053°; under that diagnostic's 200-mV/rad
half-wave encoder, the maximum drive discrepancy is 0.0000185 mV. One
positive-polarity active-tick count differs at a near-zero crossing because
the audit counts values strictly greater than zero. The hashes and full
comparison are in `reports/tibia_geometry_neural_stimulus_audit.json`.
This establishes that the previous neural input had a FlyMimic-realizable
joint-angle waveform, but does not validate the sensory gain, polarity,
individual cell identity, or physiological response.

`tools/audit_mamiya_local_tibia_window.py` checks the pinned Mamiya 2018
R73D10 GCaMP cluster data over the body's chosen 123.832°–143.832° interval.
Only 32 of 120 cluster/protocol rows contain at least three finite samples
in each 10° half-window. Their median fluorescence contrasts are mixed in
some branch/protocol combinations, and these ramp-and-hold traces confound
angle with time and movement direction. The source video angle has not been
registered to the FlyMimic body-origin angle. The per-row counts, contrasts,
and source hashes are in `reports/mamiya_local_tibia_window.json`. This
limited overlap cannot supply a cell-specific SNpp50 voltage gain, tonic
baseline, or activation polarity; keep the 200-mV/rad half-wave rule labeled
as a diagnostic hypothesis.

`tools/audit_lf_mechanical_observables.py` exactly replayed all three saved
muscle-control traces in the same FlyMimic model, with zero maximum knee
trajectory difference and zero final slider difference.

`tools/check_synced_cns_body_checkpoint.py` now saves the native FP64
MaleCNS state, MuJoCo integration state, scheduler tick and hypothetical
motor-filter activation together during the four-cell feedback diagnostic.
At tick 250, a fresh brain handle and fresh body reproduce every neural
event and all eight recorded signals through tick 500 exactly. The entire
first 500 ticks also match the prior archived uninterrupted run. A separate
`--resume-only` process loads the saved files and again reproduces the
continuation exactly. The 29,430,080-byte brain snapshot, 542-double body
state and SHA-256 manifests are under
`data/derived/synced_cns_body_checkpoint_v1` and in
`reports/synced_cns_body_checkpoint.json` and
`reports/synced_cns_body_resume.json`. This establishes same-build,
same-machine cross-process continuity for this diagnostic. The checkpoint
does not include optics, rocket, training, video recorder or a validated
sensor/motor interface; it is not a full experiment resume format.

The mechanical audit sampled joint angle and velocity, generalized
actuator/constraint forces, extensor force
and tendon length, and the exact foot-pad contact force after each 0.1-ms
step. The source and modified FlyMimic XML both have zero declared MuJoCo
sensors. In the connected case, the exact geometry pair appeared on 267
ticks, but normal contact force was positive on only 199 of those ticks;
first nonzero force was at tick 316. The blocked and motor-disconnected
controls had zero exact contact force. The connected model knee reached
−12.90 rad/s and its extensor-actuator force reached −60.01 in the model's
force convention, compared with a roughly −0.03 baseline; these are
uncalibrated mechanical outputs, not measured fly physiology. Full channels,
hashes and replay checks are in `reports/lf_mechanical_observables.json` and
`data/derived/lf_mechanical_observables_v1/`.

Joint generalized force is not cuticular strain, and this rigid-body model
has no hair deflection variable. The available mechanics therefore cannot
be assigned as biological campaniform or hair-plate input without a
receptor-specific geometry and transduction model. Count geometric contact
and load-bearing contact separately in subsequent evaluations.

This is a causal **implementation** check for the stipulated four-cell
encoding and motor-to-muscle map, not a biological reaction. The shared
200-mV/rad gain and phase, the 0.1 per-spike motor activation, and the
815344-to-LFTibia_extensor_93932 mapping lack individual physiological
validation. The connected case produced only 3 motor spikes while the
disconnected case produced 43 because muscle motion changed the sensed angle;
the resulting feedback difference cannot be treated as an independent
motor-neuron physiology comparison. The observed 0.102-mm slider motion is
also far from a validated cockpit control action.

`tools/probe_lf_untyped_three_only.py` repeated the prescribed 500-ms
open-loop tibia-angle diagnostic with the same graph, waveform, gain, and
initial neural state, but withheld the external drive to typed SNpp50 912317.
The cell and all its connections remained in the full graph; it emitted no
spikes in this particular rerun. This is input-drive withdrawal, not a
cellular deletion or silencing experiment.
The remaining SNppxx 817697/821306 and untyped 908487 each fired 107 times
and produced 21 spikes in motor candidate 815344, first at tick 120. The
four-cell case produced 22 motor spikes, first at tick 115; SNpp50 alone
produced zero. The 21-versus-22 comparison is descriptive, not an additive
decomposition of a nonlinear recurrent circuit. Events, motor voltage and
hashes are in `reports/lf_untyped_three_only.json`. The v2 rerun in
`reports/lf_untyped_three_drive_withheld_v2.json` pins the executed code and
CNS DLL hashes and reproduced the v1 event and voltage hashes exactly. The
result narrows the
immediate biological dependency: the apparent four-cell motor response
largely persists without externally driving the only typed SNpp50, so it cannot be attributed
to a validated SNpp50 sensory reflex. Resolving individual sensory identity
and tuning of those three cells takes priority over further tuning the
shared artificial encoder or motor gain.

The [published MANC sensory taxonomy](https://elifesciences.org/reviewed-preprints/97766)
explains why this is a modality gate, not merely a missing gain: `SNppxx`
is an unresolved proprioceptive label, and the authors could not distinguish
some hair-plate-like from campaniform-like leg afferents in that population.
Those receptors need different physical inputs from a FeCO angle encoder.
MaleCNS 817697/821306 have this unresolved type; 908487 has no type.
The next accepted sensory-to-movement test must identify each receptor
modality and its measured physical input before activating it. The current
four-cell result is retained solely as a circuit and body sensitivity test.

Within the broader 45-cell left-front proprioceptive class, three additional
cells have direct retained edges to motor candidate 815344: `SNppxx` bodies
817697 and 821306 have 28 and 12 contacts, while untyped body 908487 has
18. The tested SNpp50 body 912317 has five. All four have **predicted**
acetylcholine, without ground-truth transmitter entries in the source table.
The three additional cells cannot be assigned claw direction, angle tuning,
or FeCO subtype from these annotations. Their stronger anatomical contacts
show why the one-cell test cannot stand for the full sensory pathway; driving
them with the SNpp50 encoder would be an unsupported substitution.
`tools/probe_lf_untyped_single_drive.py` further isolates this artificial
input sensitivity in the full retained graph. With the same 500-ms 2-Hz
prescribed movement and saturating 200-mV/rad half-wave drive applied to
**one** unresolved afferent at a time, 817697, 821306, and 908487 each
spiked 107 times; motor candidate 815344 spiked respectively 13, 3, and
1 times. Typed SNpp50 912317 spiked zero times in all three trials.
`reports/lf_untyped_single_drive_v1.json` pins the executable sources,
graph, DLL, input and event traces. The three-cell trial had 21 motor
spikes, so the single-cell results are not treated as additive. The
largest single-cell sensitivity is to 817697, making its peripheral
identity and natural tuning the first target for source-backed validation.
These tests still use an unmeasured, nearly refractory-limited drive and
provide no biological reflex evidence.
The [FANC hair-plate reconstruction](https://www.nature.com/articles/s41467-026-69333-z)
reports that TrHP5/6/7 axons can also enter through ProLN; hence 817697's
ProLN entry does not distinguish FeCO from all hair plates. The authors
explicitly did not identify specific MANC hair-plate axons because of
reconstruction limits. This prevents reusing a claw angle encoder just
because 817697 has a strong direct motor contact.
`tools/audit_lf_sensory_morphology_vs_motor.py` quantifies why neither
geometry nor output target alone settles this identity. In the source
MaleCNS frame, 817697 and 821306 have 2.60-µm mean bidirectional nearest
SWC-node distance and a 0.795 cosine between their 33-cell tibial motor
contact vectors. Conversely, 817697 and the untyped 908487 have very
similar motor vectors (cosine 0.995) despite a 29.00-µm skeleton distance.
821306 and typed SNpp50 912317 have motor cosine 0.975 but 14.99-µm
skeleton distance. `reports/lf_sensory_morphology_vs_motor.json` pins the
SWCs, graph arrays and all pairwise measures. Shared nerve trunk,
incomplete skeletons and convergent motor targets remain confounds; these
numbers do not classify 817697 as FeCO or any particular hair plate.
The comparison has now been widened to **all 45** left-front ProLN
proprioceptive skeletons, each downloaded from the v1.0 author bucket with
its object generation and SHA-256 pinned in
`data/reference/malecns_v1_lf_proprio_45_skeletons/source_manifest.json`.
`tools/audit_lf_45_skeleton_neighbors.py` confirms 817697 and 821306 are
each other's nearest sampled centerlines at 2.60 µm; the next nearest to
817697 is typed SNpp50 912317 at 11.49 µm, and the next nearest to
821306 is untyped 821547 at 12.96 µm. The 817697/821306 pair ranks sixth
closest among all 990 possible pairs. `reports/lf_45_skeleton_neighbors.json`
contains all distances and node-coverage checks. This prioritizes joint
review of the pair but does not establish receptor modality: nearest-node
distance is sensitive to shared nerve trunk and incomplete reconstruction.
To test the shared-trunk explanation, `tools/audit_lf_45_distal_skeleton_neighbors.py`
retains only each cell's last quartile of sampled nodes ranked by path
distance from its SWC root, then repeats all 990 pairwise comparisons.
817697 and 821306 remain mutual nearest neighbors at 5.10 µm; their
next neighbors are 11.12 and 14.67 µm away. Their distances to typed
SNpp50 912317 increase to 38.88 and 45.36 µm. The source-pinned
`reports/lf_45_distal_skeleton_neighbors.json` makes this test auditable.
The root-distance quartile is an algorithmic proxy for terminal material,
not a histologically registered arbor compartment, so receptor identity
remains unresolved.
An independent [NeuronBridge public API](https://link.springer.com/article/10.1186/s12859-024-05732-7)
check used its immutable `v3_10_0` paths to acquire color-depth matches for
817697, 821306 and typed SNpp50 912317. The indexed EM images are explicitly
`male-cns:v0.9` VNC projections. Among the first 50 **distinct** LM line
names, 817697 and 821306 share 30 (Jaccard 0.429), compared with 24 for
817697/912317 and 19 for 821306/912317. Raw API JSON, URLs, SHA-256 values
and rankings are pinned in `reports/neuronbridge_lf_sensory_matches.json`
by `tools/audit_neuronbridge_lf_sensory_matches.py`. This adds a cross-modal
morphology search observation, but the broad driver-line images can label
multiple VNC cells and show no individual peripheral receptor. The v0.9
images are also not the v1.0 source skeletons used above. No receptor label
or drive was promoted from these matches.
Additional cells or cross-specimen wiring must not be invented to make the
reflex appear; a source-backed reconstruction or an explicitly separate
population-level sensory model would need its own provenance and validation.

Prior KSP experiments and the project-local kRPC installation are retained as historical engineering results, not biological evidence. The known artifact-overwrite and time-axis issues in earlier reports remain required reliability fixes before reusing those results.

## Ti extensor motor morphology (2026-09-24)

The Ti extensor motor crosswalk now has an **executed** published coordinate route. `navis-flybrains` registers `JRCFIB2022Mraw → JRCFIB2022M → BANC → BANCum → JRCVNC2018F → JRCVNC2018U`: a voxel-to-nm scale, the published MaleCNS/BANC landmark TPS, a nm-to-µm scale, BANC/VNC Elastix, and Janelia H5. We pinned transform inputs and Elastix 5.3.1 in `data/reference/ti_extensor_transform_inputs/source_manifest.json`; `tools/register_ti_extensor_v1_to_vnc.py` verified their hashes and transformed all 12 pinned Ti extensor MaleCNS v1.0 SWCs, preserving point order but not claiming transformed SWC radii. `reports/ti_extensor_v1_vnc_registration.json` records output hashes and bounds. VFB labels its `JRC2018UnisexVNC` imagery as aligned to `JRCVNC2018U`. `tools/audit_ti_extensor_v1_vnc_overlap.py` independently compared the transformed v1.0 points with VFB v0.9 copies of the same two cells: both directions have median nearest-point distance below 1 µm (report `reports/ti_extensor_v1_vnc_overlap.json`), a sanity check of gross orientation and units, not a release-matched anatomical landmark validation. The same report gives two-by-two, same-side MANC comparisons. Rankings are ambiguous under directional and tail metrics, and the VFB MANC SWC release is not confirmed as v1.0. The transformed points therefore do not establish identities for 815344/815678 or muscle assignments; their contradictory `mancBodyid` annotations remain rejected.

VFB also serves 815344 and 815678 SWCs directly in `JRC2018UnisexVNC`, but their VFB pages attribute them to **MaleCNS v0.9**, whereas the native graph uses MaleCNS v1.0. A further source check found that the VFB `Takemura2023` MANC dataset page states **v1.2.1**; the specific VFB MANC SWC exports have no individually confirmed v1.0 release provenance. The v1.0 MANC neuron-properties table used for type checks is a separate official source and must not be treated as provenance for those VFB skeletons. The SWCs and hashes are pinned in `data/reference/ti_extensor_template_crosswalk/source_manifest.json`. `tools/audit_ti_extensor_v09_same_template.py` compares each MaleCNS v0.9 cell to two same-side VFB MANC Ti-extensor candidates in the common template (`reports/ti_extensor_v09_same_template.json`). Nearest-neighbor rankings change with direction and distribution tail; neither proposed ID obtains a unique win. The VFB and v1.0 MaleCNS SWCs have equal node counts but different parent sequences, including three v1.0 roots versus one VFB root for 815344. This cross-version result is descriptive only and does not replace a release-matched v1.0 morphology test.

An additional tangent-aware comparison uses `navis.nblast` on the same registered v1 point arrays and VFB MANC skeletons (`tools/audit_ti_extensor_v1_nblast.py`, `reports/ti_extensor_v1_nblast.json`). Both proposed replacement pairs rank first in their same-side 2×2 matrices for dotprops neighborhoods `k=10,20,40`; at `k=20`, 815344 scores 0.614 against 11657 versus 0.579 against 12704, and 815678 scores 0.603 against 11706 versus 0.588 against 13115. Existing correctly typed partners 800636→12704 and 804257→13115 also rank first. Cross-release same-cell MaleCNS v1/v0.9 positive controls score 0.883 and 0.905. The right replacement margin is small, scores use navis's default FCWB-trained matrix rather than a VNC-specific calibration, local tangents come from k-nearest point clouds, and the MANC VFB skeleton release is not individually verified. This strengthens candidate prioritization but does **not** authorize changing motor-output mappings or claiming muscle innervation.

The full type-level screen now covers **all 12 MaleCNS v1.0 Ti extensor MNs** and all 12 corresponding MANC IDs in the official v1.0 properties table. The 12 MANC SWCs are pinned VFB exports; VFB's dataset page states v1.2.1, so their individual v1.0 provenance remains unverified. `tools/audit_ti_extensor_full_nblast.py` groups cells by T1/T2/T3 and side, then scores each 2×2 group at `k=10,20,40` (`reports/ti_extensor_full_nblast.json`). Every MaleCNS cell has the same top-ranked MANC candidate at all three k values. Eight agree with the published `mancBodyid`; four are missing or contradict official MANC v1.0 type annotations: 815344→11657, 815678→11706, 800911→10737, and 928579→10461 are **candidate** repairs. At `k=20`, margins over the second within-group candidate are 0.0344, 0.0151, 0.0047, and 0.0514, respectively. The 800911 result is especially weak. This is morphological prioritization with a brain-trained score matrix and a cross-release reference, not a validated neuron-to-muscle map. Keep the native source annotation intact and motor coupling disabled for these inferred replacements until independent anatomy and functional checks agree.

## Newly recovered author curves (2026-09-24)

Four processed 120-Hz L1/L2 mean-response curves at author-labelled high/low luminance and two pinned author notebooks are in `data/reference/pang_l1l2_author_curves/`. `tools/audit_pang_author_curves.py` checks every source hash and notebook row usage, 63 time points per MAT file, and the two phase areas over the paper's 250-ms window, using the paper's raw ΔF/F = 0 phase boundary but the notebook's nominal sampled onset rather than a separately estimated response onset. `reports/pang_author_curve_audit.json` has the output. An earlier sign-only interpretation was wrong: in the author notebook row 0 is plotted red and row 1 blue after negating raw fluorescence; the paper's red/dark and blue/light convention identifies raw row 0 as dark and row 1 as light. The MAT files themselves do not carry those labels. Exact recording cohorts and per-fly uncertainty are still unavailable.

The light (raw-positive) rows peak 8.33 ms after the notebook's placed input index at high luminance; low-luminance L1 peaks at 8.33 ms and L2 at 16.67 ms. **These are index offsets, not measured physiological latencies.** At the nominal input index, the light signal already reaches 46.0% and 37.4% of its first peak for high-luminance L1 and L2, respectively (25.6% and 14.6% at low luminance). The notebook's input placement therefore cannot anchor physical flash onset in the processed MAT traces. The four control MAT files contain only `meanResp` and `t`; they contain no photodiode trace, physical flash-onset timestamp, or frame-to-projector alignment (`reports/pang_author_curve_audit.json` verifies the field sets). The earlier full-CNS light response peaked at 36 ms in a separately driven and sampled experiment (see `VISUAL_CAUSALITY.md`); direct latency comparison is invalid until the experimental stimulus timestamps are recovered: the curves are processed ΔF/F, not millivolts; per-recording optical intensity and the indicator transform are unavailable; and the notebook's three 120-Hz stimulus samples approximate the 20-ms projected flash. At high luminance the light second/first absolute area ratio with the published raw-zero boundary is 0.045 for L1 versus 0.478 for L2, a concrete type-specific target. Do not score the current model's peak-amplitude ratios as though they were these integrated area ratios. Resolve source cohort, optical calibration, and matched model readout before validation.

ASAP2f observation check (primary source: Yang et al., *Cell* 2016, DOI 10.1016/j.cell.2016.05.031, https://pmc.ncbi.nlm.nih.gov/articles/PMC5606228/): depolarization decreases fluorescence and hyperpolarization increases it. Thus raw ΔF/F and membrane-voltage deflection have opposite initial signs; if an author plot uses −ΔF/F, invert this mapping. Yang et al. observed similar ASAP1/ASAP2f response kinetics in L2 under 300-ms flashes, and found that a 25-ms flash response measured optically in Mi1 had onset and peak times indistinguishable from a previously measured Mi1 electrophysiological linear filter. Their approximately 2.5-ms on/off constants refer in the text to ASAP1, so **do not assign those constants directly to ASAP2f**. The Mi1 timing comparison is evidence that ASAP2f can preserve fast visual timing under those conditions, but does not calibrate the Pang L1/L2 amplitude, the recording-specific F(V), sensor background, or a 20-ms-flash observation kernel. An indicator/filter correction cannot repair the missing physical time alignment in the MAT files. For biphasic responses, any claim about peak shift also requires applying a measured observation kernel to a matched voltage trace. The 8.33-ms notebook offset and 36-ms model peak must not be compared as biological latencies. The next matched run must record L1/L2 membrane voltage, specify raw or sign-inverted ΔF/F, reproduce stimulus timing and 120-Hz analysis, and score sign/latency before any amplitude fit.

## Two-level L1/L2 physiological discriminator

With the published raw ΔF/F = 0 phase boundary, all four light means cross into an opposite phase by 250 ms. At highLum, the second/first absolute area ratio is 0.045 for L1 and 0.478 for L2; at lowLum it is 0.038 for L1 and 0.513 for L2. My earlier mean-baseline ratios (0.154/0.457 at highLum and 0.743 for lowLum L2) were not the paper's metric and must not be used. For lowLum L1, the presence of a second phase changes under alternative baselines drawn from the two available pre-flash samples; its tiny raw-zero area ratio is therefore fragile. L2 at both levels and L1 at highLum retain a crossing under all those baseline choices, though their area ratios remain baseline-dependent. `reports/pang_author_curve_audit.json` records the raw-zero result and baseline sensitivity. These are processed means without per-fly confidence intervals. Exact `lowLum`/`highLum` photon absorption rates, cohort membership and indicator transformation remain unverified. A prospective full-CNS test should hold graph, source, seed and non-stimulus parameters fixed, run matched gray/light/dark conditions at independently calibrated luminances, and compare first-peak timing plus phase area separately for L1 and L2. The existing single-level 36-ms model summary cannot test this signature.

## Conditional optical scale check

Pang et al. report approximately 78 mW·sr⁻¹·m⁻² at 482 nm for their projected stimulus. Published Drosophila facet diameters are 16–17 µm, and a separate measurement of nearly dark-adapted female R1–R6 angular acceptance has FWHM 8.23°. `tools/estimate_pang_photon_ceiling.py` combines these with a Gaussian angular response and full geometric facet pupil. With 100% throughput, the conditional central-facet optical opportunity is 0.89–1.00 million weighted incident photons/s (`reports/pang_ideal_photon_ceiling.json`). The existing 100,000 photons/s model maximum is 10–11% of that ideal number. This is **not** an absorbed-photon calibration: the paper's per-recording PWM/filter settings, spectral convention, effective pupil fraction, transmission, rhabdomere absorption, adaptation and male/female transfer are unresolved. It cannot justify retaining or tuning the model's 100,000 photons/s. It does show that the published radiance must be used when reconstructing the next stimulus, rather than choosing a photon rate solely from a model fit.

## Octopaminergic state reference

The same pinned author repository contains four CDM (chlordimeform) curves. CDM is an octopamine-receptor agonist in Pang et al.; it is not a synaptic-feedback deletion. `tools/audit_pang_cdm_modulation.py` checks all source hashes, confirms that each CDM `meanResp` equals the average of its available individual cell traces, and writes `reports/pang_cdm_modulation_audit.json`. Under the raw-zero, nominal-onset metric, the L2 light opposite-phase absolute area after CDM is 0.200 of control at highLum and 0.436 at lowLum; the L2 dark opposite-phase area is 2.260 and 1.483 times control, respectively. These are descriptive comparisons of author processed means, not paired treatment effects or fly-level significance: control individual traces and fly identities are missing here, and exact optical settings are unresolved. Do not reproduce this pattern by arbitrarily scaling feedback. A biological model of this modulation needs octopamine receptor localization, sign, and source-backed cell-level mechanism before enabling it.
