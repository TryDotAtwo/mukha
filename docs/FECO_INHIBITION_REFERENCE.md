# Dallmann 2025 reference acquisition

Pinned repository: https://github.com/chrisjdallmann/feco-inhibition at
`e1233f4a987c532c9f1ab42273af21a0a6a50393`.
31 source files (1,981,746 bytes) acquired and verified against local SHA-256
manifest `reports/feco_inhibition_sources.json`; MIT license retained. No author
code executed and no connectome credentials used.

The inspected MATLAB calcium predictor uses binary thresholded motion for
hook/club and a normalized difference-of-exponentials observation kernel.
This provides an author-defined next replication target, not a verified
spiking transducer or direct MaleCNS mapping. See exact code-level caveats in
`reports/feco_inhibition_model_audit.json`. Preserve original discretization for
replication before comparing with our continuous exposure integrator.

Dataset DOI: https://doi.org/10.5061/dryad.gqnk98t16, version 393607.
Dryad metadata retrieved. The first files-list page is explicitly incomplete
(has a next-page link); do not treat it as the whole dataset. Three small
Mamiya calibration Parquets are listed, but API download returned 401 and web
public-download links returned 403. None has been acquired. This blocks that
specific data replication route, not local numerical reproduction from inspected
source or other project work. No authentication was bypassed.

The model's finite-trace kernel normalization and inclusive time grid need exact
replication; causal online execution is a separate change. Claw angle offsets
and one example legend disagree across source files and remain unresolved.
No full presynaptic-inhibition experiment has yet been reproduced.

Native offline motion branches are implemented in native/dallmann_observation.h. tools/check_dallmann_observation.py independently checks activation, normalized kernel and convolution against NumPy. This checks a source-equation port only; MATLAB execution and data-level replication remain absent. Claw, 9A and web branches are not included. The direct convolution is a small-reference implementation, not a GPU hot path.

Retrospective comparison on existing Mamiya MAT-derived recordings now runs through native/dallmann_observation_cli.cpp. Fixed author hook/club thresholds and kernel, with only regional scale/intercept fitted on ramp protocols, reduce swing MSE versus the calibration-mean baseline by 37.9--68.7% across five regions. Every native trace is independently compared with NumPy convolution. This previously observed assessment set is not fresh validation, and the unavailable author Parquet preprocessing/fit is not reproduced. No firing rates or MaleCNS parameters are established. See reports/feco_threshold_pilot.json; exact exclusions match the failed linear pilot.

Exact crosswalk audit: tools/audit_inhibition_crosswalk.py queries eight author MANC IDs against MaleCNS mancBodyid annotations, preserving every match and matchingNotes. IDs 13157 and 10107 are nonunique. Author notebook hook selector SNpp38 matches six MaleCNS campaniform-sensilla objects entering ADMN, not the intended FeCO chordotonal population. Do not transfer that selector across dataset versions. All mappings remain unapproved; report reports/inhibition_crosswalk_candidates.json. The source network itself uses additive signed LIF synapses, not an explicit calibrated presynaptic release mechanism.

Anatomical follow-up retains every outgoing edge for all ten annotation candidates, including ambiguous alternatives, in data/derived/inhibition_candidate_paths_v1/edges.feather. Exact CSR endpoints, counts and original row IDs are checked; no weak-edge threshold. All six IN09A012 candidates project to SNpp39 and SNpp41 sensory populations. This supports examining those paths but does not identify their physiological sign or resolve the cross-release hook naming conflict. reports/inhibition_candidate_paths.json contains descending-to-candidate edges and every sensory target-type total; runtime remains disabled.

Source neurotransmitter audit now preserves all ten candidate rows and 15 inter-candidate connections (reports/inhibition_chemistry.json). Six IN09A012 candidates have GABA consensus and a GABA value in the source ground_truth column; this audit does not establish specimen-specific experimental provenance. DNg100 is acetylcholine consensus. DNg74_a is GABA consensus, while the untyped alternative sharing MANC10107 is acetylcholine consensus: the identity ambiguity has a material chemical consequence. Prediction confidence values remain source scores, not calibrated probabilities. No postsynaptic receptor mechanism, reversal potential or functional sign is assigned.

All six predictor branches now have a C++ source-equation port and independent NumPy checks (54 output samples; five invalid calls). The claw predictor retains its published 80-degree offset without silently reconciling the fit script's 90-degree offset. Its polynomial may be negative and is not rectified. The 9A branch requires an explicit external behavioral mask: this is analysis-only and must not become an oracle input in the embodied agent. Web preserves direct input-to-calcium convolution. Absolute/relative numerical tolerances account for its angle-sized outputs. Public Dryad file requests also returned 403 in requests; no calibration files acquired.

Author network execution is now checked on a two-cell synthetic graph with Brian2 2.9.0 NumPy backend (tools/probe_dallmann_network.py). Only inspected default_params/create_model AST nodes are executed. Unmodified reset including w=0 runs and emits a spike at 1.7 ms; removing w solely for comparison leaves all recorded voltage/conductance trajectories and spikes identical. The undeclared-looking reset name is therefore not a demonstrated compatibility defect in this backend. No source patch applied. Brian's optional CPU-feature helper reports missing cpuinfo; NumPy simulation nevertheless completes. This is a 20-ms compatibility fixture, not biological MANC replication or native equivalence. Report reports/dallmann_network_compatibility.json.

Numerical reuse check: unmodified Dallmann create_model with five cells, signed recurrent edges and 1,200 explicit-input steps agrees with the existing Torch reference (FP64 max voltage error 3.34e-13 mV, FP32 2.95e-5 mV) and native FP32 CUDA/cuSPARSE on RTX3070 Laptop (2.95e-5 mV). All 66 spikes match and two CUDA replays are bit-identical. Explicit input replaces Poisson randomness for scheduling comparison; this is not a biological trial or a full-graph test. Existing Shiu artifacts are preserved under separate report names. Reports: dallmann_brian_torch_equivalence.json and dallmann_cuda_brian_equivalence.json.

Full-CNS diagnostic readiness: reports/full_graph_chemistry_coverage.json audits all accepted IDs and every edge by source transmitter. Unclear source chemistry affects 589,524 rows, so a full-graph dynamics run must declare a physiological variant and uncertainty comparisons. The anatomical graph is ready, but chemistry annotations alone do not define a biologically validated executable full-CNS model. Missing annotations are retained; none silently becomes excitatory.
