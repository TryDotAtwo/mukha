# Dm9: evidence before parameter assignment

[Schnaitmann et al. (2024)](https://doi.org/10.3389/fnmol.2024.1347540) supports
Ort-dependent photoreceptor inhibition of Dm9 and excitatory support from Dm9 to
inner photoreceptors. Reduced support can yield net inhibitory feedback. The
glutamate mechanism is proposed; EKAR is not established for this connection.
The study measures calcium in female flies, so voltage conversion and MaleCNS
transfer need testing. An additional Ort-independent R7 excitation remains a
circuit constraint, not permission to invent a second transmitter per edge.

The publisher HTML is retained with its SHA-256 in
`reports/dm9_physiology_source.json`. Machine-readable qualitative evidence is in
`configs/visual_physiology_evidence.json`. No conductance, reversal potential or
delay has been fitted. These entries are evidence labels, not executable weights.

## Binding to this dataset

`tools/audit_dm9_evidence.py` checks the original graph, chemistry, visual-boundary
and column-assignment hashes. The accepted graph has 273 Dm9 objects; all have
source consensus label glutamate. Across the full graph these objects have
21,398 incoming and 39,299 outgoing edge rows, including non-photoreceptor inputs.
The evidence is restricted to explicitly typed R7p/R7y/R8p/R8y objects. Ambiguous
and dorsal-rim types are not silently included. Axo-axonal candidates additionally
require opposite R7/R8 roles and an identical author-assigned column.

| Candidate evidence family | Rows | Contact count |
|---|---:|---:|
| Named inner receptor to Dm9 | 2,916 | 42,030 |
| Dm9 to named inner receptor | 3,359 | 88,907 |
| Same-column R7/R8 pair | 1,567 | 29,566 |

All 99,411 original visual-boundary rows remain, with 91,569 unassigned to these
narrow families. Their absence from a family is not an instruction to remove
them. Runtime flags remain false. See `reports/dm9_physiology_evidence.json` and
`data/derived/dm9_physiology_evidence_v1`. Neither a global glutamate sign nor the
net sign of a recurrent path is a calibrated direct-synapse model.

`tools/build_dm9_direct_support_variant.py` pins a separate, disabled sign
alternative for the narrow Dm9→named R7/R8 family. It verifies exact CSR
row, source and contact-count correspondence against the current FP64
diagnostic binary. The sparse patch lists 3,359 edge rows and 88,907
contacts from 222 Dm9 objects to 1,594 inner-photoreceptor objects; every
other graph row remains outside this patch. Offsets and all input hashes are
in `data/derived/dm9_direct_support_variant_v1/csr_edge_offsets.npy` and
`reports/dm9_direct_support_variant.json`. The operation would flip those
direct weights from negative to positive in an explicitly named sensitivity
run. It is not enabled in the native runtime. The source paper reports
likely direct excitatory glutamatergic support while describing net feedback
inhibition; no postsynaptic receptor, conductance, individual male-cell
transfer, or quantitative response has been established.

`tools/probe_dm9_direct_support_variant.py` compared the two full-CNS FP64
graphs under exactly the same artificial 68.75-mV Dm9 voltage pulses every
10 ms for 100 ms. The source was selected by maximum Dm9→named-inner-
photoreceptor contact count, and the target by its maximum direct contact
count, before inspecting dynamics. Both runs generated the same ten source
spikes. The blanket-glutamate-negative baseline generated ten total spikes
and zero selected target spikes; the sparse direct-support alternative
generated 41 total and three selected target spikes, first at 23 ms. The
selected target voltage traces differ by up to 17.682 mV. All source, graph,
DLL, patch, event and voltage hashes are in
`reports/dm9_direct_support_probe.json`, with traces in
`data/derived/dm9_direct_support_probe_v1`. This confirms a large model
sensitivity to the sign choice under artificial central stimulation. It
does not test natural light delivery, the net feedback sign, or biological
agreement. The variant remains disabled in the main runtime.

## Natural-input gate after the sign sensitivity run

The existing coupled flash experiment stimulates mapped R1–R6 cells and
reads L1/L2. It does not supply photon-driven R7/R8 states to the Dm9
subcircuit. The source MaleCNS column workbooks identify 1,299 R7 and 1,329
R8 cells, but `reports/visual_column_boundary_reconciliation.json` confirms
they have no assigned optical rays. The local Rust camera-to-receptor path
uses two synthetic rays with assumed RGB coefficients, not those MaleCNS
identities. Thus the Dm9 artificial-pulse result cannot yet be rerun as a
natural-light experiment by changing an input filename.

The next executable comparison needs a source-backed mapping from each
tested R7/R8 cell to an optical axis and spectral acceptance, persistent
phototransduction under a measured light waveform, and the same complete
MaleCNS graph/initial state in both Dm9 sign variants. It must preserve the
other 25,584,213 edge rows and compare direct R7/R8 activity, Dm9 activity,
and downstream responses against independent recordings. Neither a global
glutamate sign flip nor an RGB-channel shortcut resolves this gate. The
published Dm9 evidence uses female calcium recordings, so a male voltage
comparison also requires an explicit observation and transfer analysis.

## Quantitative evidence still missing

The [Heath et al. (2020) availability statement](https://pmc.ncbi.nlm.nih.gov/articles/PMC6981066/)
offers modeling code and raw recordings on request; its linked analysis software
is not itself the circuit model. No author contact was made. The 2024 article
also offers raw data from its authors. We have not acquired those recordings or
claimed a numerical fit. Published curves, a calcium observation model, stimulus
spectra, genetic intervention semantics and independent holdout conditions must
be reconciled before a quantitative replication can pass.
