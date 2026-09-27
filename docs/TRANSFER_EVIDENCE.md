# MaleCNS transfer evidence and unresolved mappings

The pinned MaleCNS annotation export identifies MN9_L (body 10331) and MN9_R
(body 16949), with FlyWire type CB0701. It also contains 163 candidate labellar
gustatory cells under the declared neural population policy. These are source
annotations, not accepted one-to-one mappings from the original Shiu specimen.

The type, instance and receptorType fields do not directly name sugar/bitter
subpopulations. The synonyms field supplies 10 additional central taste-related
candidates: DNg28 (Bitter-SEL), GNG056 (Sugar SEL LN), GNG540/GNG550 (Sugar SEL PN).
These must not be silently substituted for peripheral gustatory receptor inputs.

[Yao and Scott 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8930643/) describes
taste-responsive serotonergic SEL populations downstream of sensory detection.
That biological role explains why a taste-related synonym alone does not identify
the correct receptor-neuron input. Reconstruction-linked sensory identity and
cross-specimen correspondence still need validation.

`tools/audit_transfer_candidates.py` verifies the source hash and exports raw
annotation fields, candidate reasons and an explicit unvalidated status into
`reports/malecns_transfer_candidates.csv`. The audit does not assign transmitter
signs, sensory stimulation masks or motor mappings for the MaleCNS model.

## Published MaleCNS taste subtype crosswalk (2026)

[Tastekin et al., Cell 2026](https://doi.org/10.1016/j.cell.2026.08.016)
associate labellar LB1a–d with bitter Gr33a projections and LB3b–c with
sweet Gr64f projections; LB3b also overlaps the Ir56b low-salt projection.
These are subtype-level anatomical/driver-line associations, not receptor
measurements in each segmented cell. Their [Table S1](https://ars.els-cdn.com/content/image/1-s2.0-S0092867426009438-mmc2.xlsx)
lists MaleCNS body IDs. The SHA-pinned audit in
`tools/audit_tastekin2026_crosswalk.py` matches all 38 LB1a–d, all 23 LB3c,
all 34 LB3b–c, and both MN9 cells to our selected graph with zero local type
mismatches. Of 1,441 MaleCNS GRNs in Table S1, 1,427 belong to the selected
neural graph; the 14 absent IDs have no assigned subtype in this table.
See `reports/tastekin2026_malecns_crosswalk.json` for exact IDs and hashes.

The earlier statement above concerns the old annotation fields' lack of
literal sugar/bitter names. The new paper supplies a candidate population
mapping for an experiment. Physiological stimulation parameters,
transmitter signs, and independent response validation remain open; no
biological transfer result is claimed from this crosswalk alone.

## Full-graph diagnostic with candidate taste populations

`tools/probe_tastekin_malecns_mn9.py` used the source-linked masks above on the
full 167,216-node native FP64 graph. The immutable report is
`reports/tastekin2026_malecns_mn9_probe.json`. Over 100 ms, ten identical
direct 68.75-mV jumps per selected sensory cell produced 230/230 spikes in
the 23 LB3c cells and 380/380 in the 38 LB1a–d cells, including the combined
condition. Baseline yielded no spikes. With the unclear-transmitter sign set
to excitatory, sweet alone produced 11 left and 3 right MN9 spikes; with that
sign inhibitory, sweet alone produced 6 left and 0 right. Bitter alone and
sweet plus bitter produced zero MN9 spikes under either sign assumption.

This is a conditional circuit effect, not a biological response match. The
input is direct and uncalibrated, the uniform LIF and transmitter-sign rules
are uncertain, no preparation-matched MN9 response trace was compared, and
the excitatory-sign combined condition drove mean left-MN9 voltage to
-103 mV, an immediate warning against physiological interpretation. These
results do not satisfy the biological validation gate.

`tools/audit_tastekin_mn9_anatomy.py` reads the pinned original CSR and writes
`reports/tastekin2026_mn9_anatomy.json`. Neither selected taste population has
a direct edge to either MN9. At two-edge depth, 22 left-MN9 presynaptic
intermediates receive at least one LB3c edge and 10 receive an LB1a–d edge;
the right-MN9 counts are 10 and 2. Left MN9 has 278 incoming edges and 6,012
contacts, whereas right MN9 has 137 edges and 556 contacts. These counts are
anatomical connectivity, not proof that the simulated suppression traverses
those exact paths. The strong left/right reconstruction asymmetry further
limits interpretation of motor response counts.

`tools/probe_tastekin_mn9_large_inputs.py` repeated the unmodified FP64
sweet-only and combined runs and verified an exact match of the left-MN9
spike ticks with the first report. In `reports/tastekin2026_mn9_large_inputs.json`,
left-MN9 voltage reached -65.07 mV under sweet input and -141.67 mV under
combined input. Among its 20 largest absolute-weight incoming edges, the
464-contact cholinergic source 10833 fired 5 versus 0 times, the 359-contact
cholinergic source 10881 fired 4 versus 0 times, while 357-contact GABA source
13754 fired 9 versus 8 and 142-contact GABA source 523679 fired 12 versus 11.
Thus strong modeled excitation disappeared while strong modeled inhibition
persisted. This is trace-level association, not a causal edge ablation or a
physiological mechanism. The current-based model permits this extreme voltage
because its synaptic current has no reversal-potential bound; tuning its gain
to make this output look biological would not validate the underlying model.

## Independent premotor intervention check

[Shiu et al. 2022, Figure 5](https://pmc.ncbi.nlm.nih.gov/articles/PMC9292995/)
measured calcium responses during optogenetic sweet GRN, bitter GRN, and
combined activation in live flies: sweet plus bitter reduced Roundup relative
to sweet alone, while upstream G2N-1 was not detectably changed. The paper
identifies Scapula as a bitter-pathway neuron projecting to Roundup/Rounddown.
The pinned MaleCNS annotation gives candidate Roundup body IDs 26764/523040,
G2N-1 IDs 31018/89638, and Scapula IDs 11896/12811/12900; their cross-specimen
identities remain annotation-level mappings.

`tools/probe_tastekin_premotor.py` measured these seven neurons in the same
untuned 100-ms FP64 trials as above. The saved
`reports/tastekin2026_premotor_probe.json` independently reproduced the original
MN9 and input spike ticks exactly. Roundup spike counts were 29 sweet-only
versus 1 combined with unclear synapses assigned excitatory, and 9 versus 2
with them inhibitory. G2N-1 counts were 11 versus 10 and 10 versus 12,
respectively. Bitter-only activated Scapula candidates (56 and 37 total
spikes, respectively). Thus the *direction and anatomical stage* of a model
effect agree qualitatively with the published intervention under these two
sign assumptions. No calcium forward model, matched light dose/timing,
population-level statistics, hunger-state modulation, or independently
calibrated membrane and synaptic parameters exist here. Some model voltages
are strongly hyperpolarized (Roundup R reached -92 mV in the combined
excitatory-unclear run). This remains a preliminary qualitative comparison,
not biological replication or approval of the current-based model.

The author's [Figure 5 source workbook](https://cdn.elifesciences.org/articles/79887/elife-79887-fig5-data1-v3.xlsx)
is now pinned locally and audited by `tools/audit_shiu2022_fig5_source.py` in
`reports/shiu2022_fig5_source_audit.json`. Its 0.67-second sampling has three
four-frame light-on periods beginning at 9.38, 21.44, and 33.50 seconds.
An exploratory median across flies of mean light-on fluorescence (ΔF/F,
not the published AUC) is 0.543 for Roundup sweet, 0.061 for Roundup combined,
1.628 for G2N-1 sweet, and 1.368 for G2N-1 combined. These are observations
on 7, 8, 7, and 7 flies respectively. The workbook sheet titles say *fed*
animals while the published Figure 5 caption says *food-deprived* animals;
the condition discrepancy is unresolved. The 100-ms simulated direct-spike
probe is far shorter than the ~53-second recorded interval and lacks a
fluorescence observation model. Its spike-count ratios must not be compared
numerically to these ΔF/F values.

The article methods specify the Figure 5 optogenetic AUC window as frames
15–18 and three 2-second, 660-nm light pulses at 10-second intervals. The
updated source audit also computes the per-fly trapezoidal AUC in those frames:
median frame-unit AUC is 3.019 (Roundup sweet), 0.492 (Roundup combined),
7.130 (G2N-1 sweet), and 7.390 (G2N-1 combined). These are medians of the
source traces, not a reproduced Quade statistical test. The methods specify
female progeny for calcium imaging, whereas the graph is male. Gr5a-LexA and
Gr66a-LexA optogenetic driver populations are not proven to equal our narrower
LB3c and LB1a–d MaleCNS masks. This cross-sex, driver-mask, time-scale, and
observation-model mismatch prevents a quantitative biological fit claim.

The source-locked motif audit `tools/audit_tastekin_feeding_motif.py` reports
exact MaleCNS CSR edges in `reports/tastekin2026_feeding_motif.json`:
LB1a–d→Scapula 105 edges/2,302 contacts, LB3c→G2N-1 35/519,
Scapula→Roundup 3/251, Scapula→Rounddown 3/395, and G2N-1→Roundup 4/114.
There are no direct LB1a–d→G2N-1 edges. However, MaleCNS also contains
Scapula→G2N-1 4 edges/35 contacts, whereas the Shiu 2022 FAFB description
places Scapula input at premotor Roundup/Rounddown rather than second-order
appetitive cells. This is a real cross-dataset difference under the present
name matching; it could reflect specimen, reconstruction, or matching errors.
Do not erase those MaleCNS edges to force agreement. Their functional effect
and receptor sign remain unknown.

`tools/ablate_tastekin_scapula_edges.py` now tests the motif in the existing
full graph by zeroing weights only in temporary arrays. Its
`reports/tastekin2026_scapula_edge_ablation.json` confirms the intact replay
matches the earlier target spike ticks exactly and all variants retain 610
sensory input spikes. Removing the three Scapula→Roundup edges (251 contacts)
increased Roundup from 1 to 6 spikes under the excitatory-unclear hypothesis
and from 2 to 5 under the inhibitory-unclear hypothesis. Removing the three
Scapula→Rounddown edges instead yielded 0 and 2 Roundup spikes. This supports
a causal inhibitory contribution of the Scapula→Roundup edges *inside this
specific model*. The rescue is partial compared with sweet-only Roundup
counts of 29 and 9, and network feedback makes the Rounddown control
imperfectly isolated. No biological edge-specific intervention, receptor
measurement, or valid membrane-voltage fit has been established.

A separate full-CSR native conductance runtime is described in
`docs/CONDUCTANCE_CANDIDATE.md`. It passes independent numerical fixtures
and a full-graph reset replay, but its receptor-channel assignments,
conductance magnitudes and reversal potentials remain conditional. The
bounded voltages in that engine do not validate the taste response.
Its four-variant sweet-only versus sweet-plus-bitter comparison is recorded
in `reports/malecns_conductance_taste_comparison.json`. Roundup suppression
appears at E_inh=-70 mV, but disappears or reverses at -48 mV; G2N-1 has no
stable direction. Under the excitatory unknown-sign hypothesis, sweet-only
input also recruits bitter-candidate cells recurrently. The taste-response
robustness gate therefore fails for this conductance candidate.
The temporary three-edge Scapula→Roundup conductance cut rescues 4 or 10
Roundup spikes at -70 mV, but changes no Roundup spike counts at -48 mV
(`reports/malecns_conductance_scapula_cut_comparison.json`). This isolates a
conditional model mechanism; it does not measure the receptor action in vivo.
