# Huang/Luo recurrent mushroom-body reference

Pinned author repository: schnitzer-lab/Luo_Huang_2024_MB_model, commit
5d7c08a9a88f923169a0c3008aca68af421e9a7f. The acquisition script verifies Git
blob IDs and records SHA256 for 30 source/data files. The author README specifies
GPL-3.0-or-later; the research translation retains this attribution and license
notice. This is a separate reference model, not an enabled native CNS component.

`reference/huang.py` translates the author recurrent equation simulation for the
Figure 5d protocol. It uses the stored fitted parameter means and MATLAB column
major parameter packing. It preserves odor adaptation, bounded MBON activation,
the author's ten fixed recurrence iterations (not a converged nonlinear solver),
punishment-dependent weight induction, and the three-hour decay transition.
The author protocol modifies the first imaging session's final ISI to 300 seconds;
this detail is preserved rather than silently standardized.

`tools/check_huang_figure.py` compares all 18 numeric image CData arrays stored in
the author's MATLAB FIG artifact with the translation. These are numerical data,
not values digitized from a rendered plot. Panel order follows the source figure
construction; there is no nearest-panel matching or parameter refit.

Executed result: 108 protocols (9 valences x 12 rest intervals), 1944 values,
maximum absolute error 7.105427357601002e-15, tolerance 1e-8.
Evidence: `reports/huang_figure5d_comparison.json`, which binds source manifest,
translation and prediction hashes. MATLAB/Octave was not executed. This test
reproduces saved author simulation results, not independent held-out biological
data, every figure, or the original parameter-fitting procedure.

## Limits of transfer

This model uses aggregate odor inputs and six DAN/MBON variables with updates
over experimental bouts. Its effective weights can be negative, representing
combined pathways. It is not a ready-made local per-spike plasticity rule on the
MaleCNS connectome. The full spiking model must preserve cell identities and
anatomical synapses; importing these effective weights as new direct connections
would require explicit justification and would not be a faithful literal transfer.

Next requirements: reproduce further memory/decay protocols, relate variables
to actual cell populations, define and test a local implementation hypothesis,
calibrate against separate biological observations, and document uncertainty.
Rocket reward must not silently replace the published training stimuli in this
reference. No MaleCNS synapse has been trained by this implementation.

## Full MaleCNS mushroom-body anatomy boundary

`tools/audit_mb_plasticity_boundary.py` verifies the accepted graph manifest and
six source artifact hashes, then counts exact source CSR rows among cells whose
original `class` is `Kenyon_Cell`, `MBON`, or `DAN`. The accepted graph contains
4,064 Kenyon cells, 97 MBONs, and 340 DANs. It has 61,210 KC-to-MBON rows
(463,640 contacts), 3,160 DAN-to-MBON rows (39,711 contacts), and 129,113
DAN-to-KC rows (225,127 contacts). The report also records all nine directed
class pairs and per-MBON input counts; see
`reports/malecns_mb_plasticity_boundary.json`.

These are anatomical edge counts, not measured plastic synapses. The aggregate
Huang variables do not identify a specific MaleCNS KC-to-MBON row, dopamine
compartment, eligibility trace, receptor, learning rate, or decay law. A
DAN-to-MBON or DAN-to-KC chemical contact is not proof that a given KC-to-MBON
synapse receives a local teaching signal. The runtime remains disabled until
those assignments have independent biological support and separate
calibration/held-out tests.

The locally pinned source edge table has only `body_pre`, `body_post`, and
`weight`; it contains no synapse coordinates or compartment labels. The
official MaleCNS release separately provides a 6.8 GB synapse-partner table
with both contact coordinates and `primary_post` neuropil labels. Its full
4,759-batch table was streamed in a foreground CPU Molab notebook in two
nonoverlapping ranges, then scanned again with every read pinned to GCS
generation `1780494942562468`. The downloaded Parquet files preserve every
one of the 463,640 KC-to-MBON contacts. The pinned full result matches the
earlier two ranges row for row in source order and by SHA-256 after transfer.
`tools/reconcile_mb_synapse_locations.py`
independently compared coordinate rows with all 61,210 original graph pairs:
zero pair-count mismatches. SHA-256, source object identity and all 28
primary-neuropil counts are in
`reports/malecns_mb_synapse_reconciliation.json`. The filtered data are under
`data/derived/mb_synapse_locations_v1/molab_full`; the 6.8 GB source table was
not copied onto the local disk. All 97 MBON instance
names and 326/340 DAN instance names contain parenthesized anatomical labels,
but no KC instance does. Names cannot assign an individual KC-to-MBON contact
to a local dopamine compartment. The source neurotransmitter table gives all
4,064 KC an acetylcholine consensus; MBONs split 50 acetylcholine, 26
glutamate, and 21 GABA. Of 340 DANs, 338 have dopamine consensus and two
PPL203 cells have `unclear` consensus despite a serotonin prediction. Their
source IDs and all counts are preserved in the report. Treating every DAN as
identical dopamine input would silently override these source uncertainties.

Handler et al. 2019 (Cell, DOI `10.1016/j.cell.2019.05.040`) provide a
physiological transfer target in the γ4 mushroom-body compartment. Their
observable is the pre/post change in a KC-evoked, GCaMP6s MBON dendritic
calcium response, not an individually measured synaptic weight. DAN stimulation
before KC stimulation potentiated this response; concurrent or later DAN
stimulation depressed it. DopR1 and DopR2 knockout controls separated the
opposing directions. The paper states that its raw data and custom analysis
scripts are available upon request. A subset of original preparation-level
Figure 2/5 values is redistributed in the published Gkanias et al. model
repository; its pinned local workbook and provenance are under
`data/reference/handler2019`. `tools/analyze_handler_timing_data.py` verified
all 31 paired Figure 2 values against the plotted deltas and means. Mean
post-minus-pre responses at ISI -6, -1.2, -0.6, 0, +0.5 and +6 seconds are
+0.192, +1.575, +0.244, -1.089, -0.793 and -0.089 respectively; see
`reports/handler2019_fig2_timing_data.json` for per-preparation values and
descriptive 95% intervals. The workbook does not supply Figure 6 receptor-null
preparations or identify MaleCNS per-contact kinetics.
The new paired data also reject the simple monotonic DAN-before-KC exponential
trace independently of receptor-null signs: mean potentiation at -0.6 s is
+0.244 versus +1.575 at -1.2 s, though that trace predicts the nearer
stimulus has at least as large an effect. All five -1.2 s preparation deltas
exceed all six -0.6 s deltas. An exploratory exact one-sided permutation check
gives 1/462 (unadjusted); this does not identify the opposing process.
The same pinned workbook includes six cAMP preparations and seven ER-calcium
preparations per ISI in KC axons. `tools/analyze_handler_second_messenger.py`
reconstructs Figure 5E/F: each preparation is normalized across the six tested
ISIs, then mean normalized negative ER calcium minus mean normalized cAMP is
compared with the γ4 MBON response change. The six values correlate at
Pearson r=0.967 with the MBON means (`reports/handler2019_fig5_second_messenger.json`).
This is an exploratory re-analysis of the paper's own conditions, with separate
imaging preparations, not independent validation or a causal fit. Its
normalization uses the entire six-condition series after acquisition; using
that future-aware normalization as an online local teaching signal would be
invalid. A candidate rule needs local dynamic receptor/second-messenger
states and independent withheld physiological conditions before graph use.
For the online observation contract, `tools/audit_handler_observation_windows.py`
reconstructs every Figure 5D summary directly from the 0.1-s reporter traces.
The cAMP summary is the inclusive 4-s post-DAN window (41 samples); ER-lumen
calcium is the inclusive 1-s post-KC window (11 samples). All reconstructed
preparation values agree exactly with the workbook (`reports/handler2019_observation_windows.json`).
The paper also normalizes reporter fluorescence against a 2–4-s prestimulus
baseline. A future local rule must match those reporter observation operations
when compared with source physiology; raw molecular state is not itself the
published fluorescent readout.
An isolated causal event-kernel screen (`tools/fit_handler_causal_messenger.py`)
fits raw wild-type cAMP means with a DAN baseline plus decayed KC/DAN
coincidence (tau 1.03 s), and negative ER-lumen response with a two-stage
DAN trace gated at KC (tau 1.11 s). Both fit the six source means in sample,
but the ER timing is poorly identified: retrospective leave-one-ISI-out mean
absolute error is 0.050 versus 0.0065 for cAMP, and omitting -0.6 s predicts
0.243 instead of measured 0.062. Adding nonnegative ER potentiation and cAMP
depression branches fitted to wild-type MBON means gives MBON RMSE 0.244 and
still predicts zero for DopR1-null forward pairing, contradicting the measured
weak potentiation. See `reports/handler2019_causal_messenger_kernel.json`.
The candidate is rejected as a local rule; the fit is exploratory, uses only
window means rather than reporter timecourses, and supplies no MaleCNS
contact-specific DAN input or receptor state.
An independent γ4 induction constraint comes from [Cohn et al., Cell 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4732734/):
58E02-positive γ4/γ5 DAN activation without concurrent KC stimulation
potentiated later KC-evoked γ4 MBON currents/responses, whereas temporal
KC/DAN pairing depressed γ4 MBON signaling. Thus a rule that requires an
active KC trace for every update predicts zero in the DAN-only induction
condition and fails this cross-protocol challenge. “DAN-only” describes the
induction event; KC test stimulation before and after induction measured the
change. The source also found strong compartment dependence, so this does not
license a global dopamine potentiation of every KC contact. Assay, genotype,
stimulus and reporter differences prevent pooling numeric values with Handler
Figure 2/5, but a future γ4 candidate must explicitly test both conditions.
`tools/audit_handler_transfer.py`
identifies the two name-matched MaleCNS MBON05(y4>y1y2) candidates with 36,320
KC contacts, 50 PAM08(y4) and 14 PAM07(y4<y1y2) candidates, and no KC
`receptorType` entries in the accepted node table. The MBON05 KC contacts are
predominantly labelled broad `gL`, which does not isolate γ4. DAN-to-MBON05
chemical graph input exists, but cannot locate dopamine release relative to
individual KC contacts. See `reports/malecns_handler_gamma4_transfer.json`.
This leaves the per-contact teaching signal and receptor state unassigned;
plasticity remains disabled.

The isolated one-sided KC/DAN eligibility rule has now been checked against
the Handler γ4 receptor-null signs (`tools/audit_handler_one_sided_rule.py`).
It fails both knockout directions for every positive time constant: deleting
DopR1 predicts zero forward change where the measured MBON response weakly
potentiates; deleting DopR2 predicts zero backward change where it depresses.
If receptor deletion only removes an additive branch and calcium-response sign
tracks local efficacy, the observations imply a negative DopR1 contribution
larger than the positive DopR2 contribution for forward pairing, with the
opposite dominance for backward pairing. This is a conditional sign constraint,
not an identified mechanism or fitted parameter set. The report includes a
numerical satisfiability witness and explicit model-only unpaired/learning-off checks;
it does not license assigning dopamine compartments or enabling graph plasticity.

The contact table also resolves a structural issue for any future local rule:
the same KC presynaptic coordinate can have several MBON postsynaptic partners.
`tools/build_mb_contact_layout.py` makes a flat source-order contact view over
all 61,210 KC→MBON rows of the unchanged full CSR. A presynaptic site key is
`(body_pre,x_pre,y_pre,z_pre)` in the published 8-nm coordinate grid; each
contact retains a separate postsynaptic coordinate, confidence and ROI label.
There are 391,849 such keys for 463,640 contacts. Of these keys, 65,275 have
multiple distinct MBON partners, covering 137,062 contact rows; the maximum
within this MBON-only view is five partners. The coordinate key can merge
separate ultrastructure within one voxel, and it excludes KC partners outside
the MBON class, so it is an operational site identity rather than a proof of a
complete biological bouton. A flat site/contact/edge SoA plus grouped offsets
is stored under `data/derived/mb_synapse_state_layout_v1`.
`tools/verify_mb_contact_layout.py` independently reconstructs every source
contact field, checks its global CSR edge and verifies exact counts for all
61,210 edges. See `reports/malecns_mb_contact_layout.json`.

This distinction is biologically material: [Pribbenow et al., eLife 2022](https://elifesciences.org/articles/80445)
report postsynaptic
cholinergic plasticity in M4/6 MBONs and shared KC presynaptic partners. It
does not prove that the Handler γ4 MBON05 protocol uses the same expression
site. A candidate local model must therefore declare which state is shared by
a KC output site and which is contact-specific, rather than duplicating an
assumed presynaptic variable independently for each graph edge.

[Hiramatsu et al., eLife 2025](https://elifesciences.org/articles/98358)
provide an additional receptor-localization constraint. Cell-specific imaging
found endogenous Dop1R1 and Dop2R signals near both KC presynaptic and
postsynaptic sites in the tested α/β and γ neurons. In the Brp-marked KC
active-zone experiment, some puncta had receptor signal nearby and others had
barely detectable signal; the authors interpret this as heterogeneity among
release sites. Their examples include α3 and γ5, not an identified MaleCNS
γ4 contact. The study also found both receptor types in γ1 MBON dendrites,
which demonstrates that receptor expression cannot be inferred solely from a
KC presynaptic class label. These observations rule out treating every KC site
as having one measured, uniform receptor state. They do not identify Dop1R1
or Dop2R for any coordinate key in our MaleCNS contact layout, quantify a
local receptor concentration there, or determine its learning rule. Keep both
site-shared and contact-specific hypotheses explicit and plasticity disabled.

A second generation-pinned scan retained 81,367 chemical partner rows with
presynaptic sites from name-matched PAM08(y4), PAM07(y4<y1y2), and the
PAM01(y5) anatomical control in the broad `gL(L/R)` source ROIs. The filtered
file SHA-256 and source generation are in
`data/derived/mb_synapse_locations_v1/molab_full/pam-y4-y5-gl-report.json`.
`tools/compare_pam_mb_spatial.py` compares each KC→MBON contact to the nearest
unique PAM output site within the same broad ROI. For the dominant MBON05
contact sets, 95.7–96.6% of contacts were nearer PAM08(y4) than PAM01(y5);
MBON01(y5B′2a) controls showed the opposite pattern (4.3–8.1%). Equalizing
the number of PAM sites across groups over ten fixed random seeds preserved
both directions, as did aggregation by distinct KC. MBON27(y5d) controls were
mixed (61.1–66.5% nearer PAM08), so this proxy does not cleanly resolve every
named γ subdivision. See `reports/malecns_pam_mb_spatial.json`. A nearest
chemical synapse is not a measured dopamine release site, diffusion radius,
receptor state, or functional teaching signal. No contact has been assigned
plasticity from this spatial comparison.

The author Huang fitting code names three aggregate modules: γ1pedc,
α′2α2/α2sc and α3. `tools/audit_huang_module_transfer.py` preserves eight
name-matched MaleCNS MBON candidates and six DAN candidates, without accepting
cross-dataset identities. The candidate MBONs receive 77,602 of the extracted
KC contacts. For MBON11 (γ1pedc label), 25,190/41,460 are in broad `gL`,
9,104 in `PED`, with others elsewhere. `aL` dominates MBON18 and MBON14
contacts, but `aL` does not distinguish α2 from α3. Source `primary_post`
labels and aggregate Huang variables cannot identify all individual local
plastic synapses or their dopamine compartments. See
`reports/malecns_huang_module_anatomy.json`. The anatomical contact extraction
and pair reconciliation are complete; local learning remains unvalidated.

## Native reference

`tools/build_huang.cmd` builds the C++ FP64 reference in `native/huang.cpp`.
It uses fixed-size arrays and no allocation in the event loop. The narrow C ABI
accepts aggregate parameters and declared experimental events; it never accesses
the MaleCNS graph or rocket state. This GPL-derived reference remains separate
from the spiking runtime.

`python tools/check_huang_figure.py --native` passes the same 1944 author numeric
values with maximum error 7.105427357601002e-15. Source and library hashes are in
`reports/huang_native_figure5d_comparison.json`. A further 21 cases around and
beyond the three-hour decay switch, including 24-hour rests, agree with NumPy
within the same error (`reports/huang_decay_branch_checks.json`). Those 21 cases
are numerical implementation comparisons, not additional independently measured
biological evidence. Python loads parameters and compares results; the native
event dynamics are executed in C++.

## Gamma4 contact-resolution audit

`tools/audit_gamma4_contact_roi_boundary.py` rechecks the SHA-256 of the
pinned full 463,640-contact KC-to-MBON table, joins its postsynaptic IDs to
the accepted MaleCNS node table, and enumerates the six MBON instances whose
source names contain `y4`. They receive 49,708 KC contacts; 44,120 (88.76%)
have `gL(L)` or `gL(R)` as `primary_post`. The remaining contacts carry
other ROI labels. The 28 distinct `primary_post` labels contain no explicit
gamma4 label. See `reports/malecns_gamma4_contact_roi_boundary.json`.

This establishes candidate cells and broad gamma-lobe locations, not which
individual synapses belong to gamma4. The `y4` name filter also includes
multi-compartment MBONs and is not a functional cell match to the Handler
preparation. Do not enable the Handler-derived timing rule on these contacts
until subcompartment and DAN/receptor assignments have source-backed evidence.

`tools/audit_gamma4_shared_kc_sites.py` checks the pinned contact-layout file
hashes and maps these six name-matched MBONs back to their exact CSR target
rows. Their 49,708 KC contacts occupy 45,077 operational presynaptic
coordinate keys. Of those keys, 7,921 also contain contacts to other MBONs;
8,198 candidate contacts (16.49%) lie on these shared keys. See
`reports/malecns_gamma4_shared_kc_sites.json`. A KC-site-wide learning state
would therefore affect contacts outside the six candidates unless its update
is explicitly gated per contact; a contact-only state would omit a possible
shared presynaptic component. Neither choice is licensed by this count.
The 8-nm coordinate key can merge separate ultrastructure and omits non-MBON
partners; no gamma4 subcompartment, receptor, or plasticity rule is assigned.
Restricting both candidate and other-MBON contacts to broad `gL(L/R)` leaves
44,120 candidate contacts on 39,930 keys; 6,342 keys and 6,559 candidate
contacts (14.87%) are shared with other MBONs in that same broad ROI. This
rules out dismissing the sharing as contacts elsewhere, but `gL` does not
isolate γ4 and the coordinate key is still only an operational proxy.

## Lateral KC anatomy as a separate learning constraint

[Manoim et al. (Current Biology 2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9613607/)
report strong lateral γ-KC axonal interactions and an mAChR-B-dependent
stimulus-specific conditioning effect. `tools/audit_kc_lateral_subtypes.py`
checks the accepted graph hashes and all 642,933 directed KC→KC rows
(1,153,845 contacts), then groups source `type` labels without changing the
graph. The 1,557 γ-KCs have 200.20 distinct KC input partners on average;
305,841 of their 311,707 incoming KC rows (98.12%) originate from γ-KCs.
For α/β, 244,283/247,995 incoming rows (98.50%) are within group; for
α′/β′, 77,215/83,209 (92.80%) are within group. The full matrix, two
unresolved KC types and one source self-row are recorded in
`reports/malecns_kc_lateral_subtypes.json`.

The pinned source synapse-partner table was then scanned through all 4,759
record batches at GCS generation `1780494942562468` by
`tools/extract_kc_synapse_locations.py`. The 1,153,845 retained KC→KC contact
rows reconcile **for every one** of the 642,933 directed CSR pairs, with zero
count mismatches (`data/derived/kc_synapse_locations_v1/reconciliation.json`).
The source table has no separate synapse ID. The coordinate/ROI audit retained
all rows: no missing coordinates, missing ROI, nonfinite confidence values or
exact duplicate full rows were found. The 11 source columns and per-chunk
SHA-256 identities are checked by `tools/audit_kc_lateral_contact_rois.py`.

Of 507,343 γ→γ contacts, 413,441 (81.49%) have `primary_post` in broad
`gL(L/R)`; the corresponding within-group fractions are 20,519/424,741
(4.83%) for α/β and 16,435/204,797 (8.03%) for α′/β′. The remaining γ→γ
contacts occur across CRE, PED, CA and other source ROIs, not just the γ lobe.
All source ROI counts and type-pair checks are in
`reports/malecns_kc_lateral_contact_rois.json`. This is an anatomical
localization result, not a replication of the published hemibrain measurement
or a physiological validation. `primary_post` locates the postsynaptic side
coarsely; `gL` does not distinguish γ4 or establish the presynaptic axonal
ultrastructure. No SWC-to-contact coordinate transform or individual receptor
assignment is accepted here, and the studies use different specimens and
annotation releases. The large retained KC→KC subnetwork cannot be ignored
by default when proposing stimulus-specific learning, but mAChR-B function
and local plasticity remain unvalidated and disabled. The [publisher's data availability
statement](https://www.sciencedirect.com/science/article/pii/S0960982222014518)
says figure-generating data and code are available from the corresponding
author upon request; the published paper alone does not supply preparation-level
data for a new independent parameter fit.

### Held-out mAChR-B intervention (proposed, not passed)

Figure 5 of Manoim et al. supplies a distinct causal challenge for any
future lateral KC mechanism. Its experiment applies acetylcholine to KC
axons while measuring a cAMP reporter, compares control with mAChR-B
knockdown, and compares dopamine alone with dopamine plus acetylcholine.
The challenge must be specified before using its observations to select
mechanism parameters:

1. Freeze the graph, receptor assignment, observation operator and all
   parameters using evidence other than these Figure 5 conditions.
2. Drive the same declared acetylcholine and dopamine interventions into
   control and mAChR-B knockdown preparations. Knockdown may alter only the
   declared receptor pathway; the observation operator and other parameters
   remain identical. TTX, when present in the source condition, is an
   explicit intervention rather than an unrecorded change to circuit input.
3. Compare predicted reporter time courses or preregistered response windows
   with preparation-level source data, including uncertainty and the
   experimental sample sizes. Preserve a no-lateral-pathway ablation.
4. Count the gate as passed only if one frozen model accounts for the
   direction and magnitude of all contrasts under the same observation
   operator. A sign match alone is a qualitative consistency check, not a
   quantitative replication or evidence of local plasticity.

The publication's figures show the intervention directions, but the
preparation-level Figure 5 values and analysis code have not been obtained
here. The published data-availability statement directs requests to the
corresponding author. Therefore this held-out challenge is **unrun**, its
numerical tolerance is unset, and it cannot unlock the biological gate.
