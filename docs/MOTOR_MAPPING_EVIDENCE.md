# Motor interface evidence ledger

Current interpretation: `mancBodyid` is a predicted match, while `mancGroup` is
curated. This is documented by the dataset tooling author:
https://natverse.org/malecns/reference/mcns_predict_group.html.
Exact lookup of a predicted ID does NOT validate cross-dataset identity.
The earlier predicted-ID audit below is retained as an uncertainty diagnostic.

`tools/audit_motor_candidates.py` verifies the pinned MaleCNS annotations and
joins every motor annotation to the actual full graph's body-ID array. It keeps
all 815 motor candidates, including 381 annotated leg motor neurons. This is an
inventory, not an enabled mapping or reduced neural simulation.

Leg annotation counts: front 135, middle 116, hind 130. A MANC body-ID match is
present for 360, absent for 21. All 381 lack rootSide. somaSide is preserved as
source metadata and must not silently become an effector-side assignment.
Named muscle groups include Ti flexor/extensor, Tr flexor/extensor, Fe reductor,
sternal rotators and long-tendon groups. Generic MN labels remain unresolved.

`reports/malecns_motor_candidates.csv` preserves original IDs, graph indices,
MANC matches, source names, nerves, soma metadata and matching notes. Approved
joint, torque sign, gain and mechanical evidence fields are intentionally empty.
`reports/malecns_motor_audit.json` binds source, graph-ID and output hashes.

The existing 42 FlyGym actuator channels do not imply that 381 motor neurons
can be assigned one-to-one to them. Multiple motor units may share a muscle;
muscles may affect multiple joint axes, and the simulated axis convention must
be checked explicitly. An engineer-defined aggregate interface is allowed by the
plan but must disclose these assumptions and be frozen before landing training.

Primary source leads located, not yet acquired or verified at cell level:

- Cheong et al., *Organization of circuits linking descending input to motor
  output in the Drosophila Male Adult Nerve Cord connectome*,
  https://elifesciences.org/articles/96084
- Azevedo et al., leg motor target identification appendix,
  https://faculty.washington.edu/tuthill/docs/azevedo24_appendix.pdf

The source target table was subsequently acquired (below). The Azevedo
appendix was acquired on 2026-09-24 as
`data/reference/azevedo2024_appendix/azevedo24_appendix.pdf` (46 pages, SHA256
`822c298e50da9fee3ce75f1dabda040574eac9fc854fdf92837856a82c8515f6`).
Its Table A4 (PDF page 11) identifies two FANC tibia-extensor MNs exiting the
ProLN; Figure A11 (PDF page 31, visually inspected) identifies MNs 39 and 40
as the slow and fast extensor tibiae (SETi and FETi). The figure and caption
place SETi terminals on distal, more pinnate femur fibers; the other extensor
targets proximal fibers. This establishes distinct motor units and fiber
targets in the published FANC anatomy, but supplies no FANC-number-to-MANC-ID
crosswalk. The similar-looking `MNfl39` MANC label must **not** be equated
with FANC MN 39 by its number. Cheong Supplementary file 3 assigns both MANC
groups 11657 (`MNfl41`) and 11706 (`MNfl39`) only the generic target
`Ti extensor`; its publication-match fields are empty for all four T1 rows.
Consequently neither MaleCNS candidate can yet be called SETi or FETi.
Next: find a published cell-level FANC↔MANC match or independently align the
two skeleton pairs before assigning the fast/slow unit or spike-to-force law.

The [neck-connective matching supplement](https://github.com/flyconnectome/2023neckconnective/blob/main/Supplemental_files/Supplemental_file13_other_MANC_FANC_matching.tsv)
provides an additional published, cell-level FANC/MANC table. Its exact bytes
are pinned locally at
`data/reference/fanc_manc_crosswalk/Supplemental_file13_other_MANC_FANC_matching.tsv`
(SHA256 `2d6598b55e690dbe5433f18311b8c74b1707d4044b22670fc41ce2fd87c3f9a7`).
`tools/audit_published_fanc_manc_ti_extensor.py` checks both source hashes
and writes `reports/published_fanc_manc_ti_extensor_audit.json`: 800 table
rows, zero matches for the four T1 MANC extensor IDs 11657, 13115, 12704,
11706, and two T3 extensor rows (13006, 13075). This is a coverage limit of
that supplement, not evidence that the T1 biological homologs do not exist.
It does not resolve the FANC MN 39/40 correspondence.

The [Azevedo et al. Nature supplement](https://media.springernature.com/original/springer-static/esm/art:10.1038%2Fs41586-024-07389-x/MediaObjects/41586_2024_7389_MOESM1_ESM.pdf)
provides a more direct FANC source: its Supplementary Table 1 (PDF page 2)
links the two T1 tibia-extensor reconstructions to an author-hosted
Neuroglancer state. `tools/audit_fanc_ti_extensor_source_ids.py` pins both
source files and follows that PDF link to the JSON; report
`reports/fanc_ti_extensor_source_ids.json` recovers FANC segment IDs
`648518346493238080` and `648518346495797355`. This closes the source-ID
lookup for the FANC **pair**. The link does not label which segment is MN 39
(SETi) or MN 40 (FETi), and neither FANC segment has a verified match to the
four MANC T1 IDs. These are candidates for a future registered morphology
comparison, not an approved MaleCNS motor map.

The Neuroglancer state also names an anonymous-access Google Cloud Storage
mesh source. We acquired its two segment fragments at their recorded object
generations (source transfers are gzip encoded; local files contain decoded
precomputed-mesh bytes). `tools/audit_fanc_ti_extensor_meshes.py` verifies
the four file hashes, parses vertices/faces, checks all face indices, and
writes `reports/fanc_ti_extensor_meshes.json`. The two meshes contain
2,623,059/1,642,995 vertices and 5,287,133/3,305,832 triangles. These are
the first pinned 3D FANC reconstructions for this specific comparison.
Acquiring a mesh does not establish its fast/slow label or a MANC identity;
the next anatomical step is registered, side-matched morphology using a
source-verified FANC→template transform and a measured ambiguity margin.

The mesh parser now treats vertices as little-endian **float32** nanometres;
an initial unsigned-integer interpretation gave invalid billion-nanometre
bounds and was corrected before any comparison. The corrected bounding boxes
are in `reports/fanc_ti_extensor_meshes.json`. With the pinned Elastix runtime
and H5 transform, `tools/screen_fanc_manc_ti_extensor_meshes.py` mapped 4,096
deterministically sampled surface vertices from each FANC mesh through
`FANC → FANCum_fixed → JRCVNC2018F_reflected → JRCVNC2018F → JRCVNC2018U`.
All transformed samples were finite and in the same gross coordinate range
as the MANC T1-left SWCs. The surface-to-SWC median distances for FANC
`648518346493238080` are 5.97 µm to MANC 11657 and 4.39 µm to 12704;
for FANC `648518346495797355`, 4.53 µm and 4.37 µm respectively. Both
surface samples nominally prefer 12704, so this metric provides **no
one-to-one assignment**. Unequal surface and centerline representations,
sample density, axon coverage and uncertain per-cell release limit the
comparison. See `reports/fanc_manc_ti_extensor_surface_screen.json`.
The next test needs matched skeleton representations and independent
registration checks before any identity or motor-unit claim.

`tools/simplify_fanc_ti_extensor_meshes.py` used pinned
`fast-simplification==0.2.0` to reduce the FANC meshes. The requested
200,000-face target was not reached: the outputs have 755,998 and 462,727
faces. A 20,000-vertex original sample has 99th-percentile distance about
204 nm to the nearest simplified vertex for both meshes, but this vertex
metric does not prove topology or fine-neurite preservation. The result and
file hashes are in `reports/fanc_ti_extensor_simplification.json`.
`tools/audit_fanc_ti_extensor_skeleton_fragments.py` then built wavefront
skeletons and found **1,380 and 1,510 connected components**, exactly the
component counts of the corresponding simplified meshes. The largest
component contains 82.3% and 49.0% of simplified mesh vertices respectively.
See `reports/fanc_ti_extensor_skeleton_fragments.json`. We have not yet
measured component connectivity in the original meshes, so the origin of
the fragmentation is unresolved. Running NBLAST on either fragmented
derived skeleton as if it were a complete neuron would be misleading;
individual fast/slow or MANC identities remain unassigned.

An exact component audit of the **original**, unmodified triangle meshes now
settles the fragmentation question: `tools/audit_fanc_ti_extensor_original_components.py`
finds 2,516 and 3,069 components before decimation; the largest components
contain 83.0% and 48.8% of original vertices. See
`reports/fanc_ti_extensor_original_components.json`. Thus the multiple
components are present in the published mesh source and cannot be blamed
solely on the simplification or wavefront method. The decimation changed
component counts, so its derived skeletons are especially unsuitable as
cell-complete anatomical ground truth. A curated source skeleton or a
source-validated fragment-reconnection procedure is needed before a
cell-level FANC↔MANC morphology claim.

A separate author [2021 FANC data release](https://github.com/htem/GridTape_VNC_paper/tree/main/neuron_reconstructions)
provides 69 manually traced left-T1 motor SWCs in native FANC space and
registered versions in the female VNC template. All 69 native SWCs are pinned
at commit `5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9` by
`tools/fetch_fanc_2021_t1_swcs.py`. An exhaustive same-space proximity screen
(`reports/fanc_2021_swc_to_ti_extensor_mesh_screen.json`) gives a distinct
top manual SWC for each later tibia-extensor mesh: FANC segment
`648518346493238080` → neuron 9001 (`L3#03`, median SWC-to-sampled-mesh
529 nm; second 1248 nm), and segment `648518346495797355` → neuron 581
(`L3#02`, 406 nm; second 1629 nm). This is a strong **cross-release
morphological candidate**, not a published segment-ID mapping; the reverse
surface-to-SWC medians are about 5 µm because the meshes contain many
fragments beyond the manual trees.

The complete registered female-template SWCs for neurons 581 and 9001 are
pinned by `tools/fetch_fanc_2021_extensor_template_swcs.py`. After converting
the native 2021 SWCs through the pinned `FANC → JRCVNC2018F` route,
`tools/validate_fanc_2021_template_registration.py` compared corresponding
nodes with those published template SWCs. Node IDs and parent links match
exactly. The largest coordinate residual is 0.0000174 µm for neuron 581
and 0.0000208 µm for neuron 9001. See
`reports/fanc_2021_template_registration_validation.json`. This validates
the registration implementation for these 2021 skeletons; it does not
validate the later mesh-to-SWC identities or a MANC cell match.

For the separate MANC comparison, we converted the published template
coordinates from nanometres to micrometres and applied the pinned
`JRCVNC2018F → JRCVNC2018U` H5 transform,
`tools/audit_fanc_2021_manc_t1_extensor_nblast.py` compared both with
MANC-left 11657 and 12704 using matched skeleton representations. At
dotprops k=10,20,40, **both** FANC skeletons score highest against MANC
12704. For k=20, neuron 581 scores 0.512/0.516 against 11657/12704;
neuron 9001 scores 0.433/0.556. The 581 margin is tiny and the two rows
do not produce a one-to-one crosswalk. See
`reports/fanc_2021_manc_t1_extensor_nblast.json`. Dataset release,
template and scoring-matrix limits remain; no fast/slow or MaleCNS-to-muscle
assignment follows from this result.

An independent native-space screen used the published flybrains
`FANC → MANC` landmark transform and pinned MANC **v1.2.1** native SWCs
11657 and 12704 from the Lee lab public archive. The source objects,
generations and hashes are in
`data/reference/manc_121_ti_extensor_native_swcs/source_manifest.json`.
The FANC→MANC nearest-skeleton median distances (µm) are 3.33/2.44 for
FANC 581 and 4.07/2.81 for FANC 9001, ordered as MANC 11657/12704.
Thus both again prefer 12704; this does not produce a one-to-one match.
See `reports/fanc_2021_manc_121_native_geometry.json`. The target release
differs from MANC v1.0, and nearest-point distance alone does not establish
cell identity. Neither motor assignment is approved.

As a specificity control, `tools/screen_all_fanc_2021_manc_121_t1_motors.py`
compared both target SWCs with **all 69** pinned 2021 FANC left-T1 motor
SWCs using the same transform and mean of both directional median
nearest-node distances. FANC 581 and 9001 rank first and second for
**both** MANC cells: for MANC 11657, 5.178 and 5.609 µm; for MANC 12704,
4.124 and 4.040 µm (9001 first). The next cell is farther at 6.458 and
5.648 µm, respectively. This supports the *pair-level* morphological
candidacy, but MANC 12704 separates 9001 from 581 by only 0.084 µm on
this metric, and both FANC cells have lower absolute distance to 12704.
The one-to-one assignment is therefore still not established. Full ranks
and distances: `reports/fanc_2021_manc_121_all_t1_motor_screen.json`.

## Acquired target table

The publisher's Supplementary file 3 is now acquired from
https://cdn.elifesciences.org/articles/96084/elife-96084-supp3-v1.csv
and pinned by SHA256 c46e3cec1a5114b8d981d5f0383012c8e7fcdebd6c4e3eaffe4ac3ba1def2e94.
`tools/join_motor_targets.py` performs a many-to-one exact MANC body-ID join;
there is no name-based fallback. The original source bytes are preserved.

Of 381 leg rows, 349 join, 11 have a MANC ID absent from this table and 21 have
no MANC ID. Among matched rows, 53 targets specify only a limb. All 349 have
empty match-certainty fields; absence is not assigned a numerical confidence.
There are 120 normalized label disagreements (strip whitespace and trailing
MN only), including generic labels replaced by muscle labels and potentially
substantive changes. These are not automatically classified as biological errors.
For example MaleCNS body 800589 is labelled Tr flexor MN, while its source MANC
match 13817 has target Sternal adductor. This requires source/version resolution.

MANC exit-nerve side agrees with MaleCNS somaSide wherever compared; this is
cross-dataset metadata consistency, not independent proof of target laterality.
All matched source fields, references and notes are preserved in
`reports/malecns_manc_motor_targets.csv`; disagreements in
`reports/motor_target_conflicts.csv`; counts and hashes in
`reports/motor_target_join.json`. No mechanical mapping is approved yet.

## Curated group resolution

`tools/resolve_curated_motor_groups.py` joins `mancGroup` to Supplementary file 3
group targets, requiring a unique target within each group. It preserves every
leg motor row. Of 381 cells, 150 have curated group targets agreeing with their
MaleCNS muscle label, 39 have only limb-level targets, and 192 lack a curated
group. There are no muscle-label conflicts among the uniquely named curated
targets. These 150 now have stronger annotation evidence; mechanics and neural
response are still not validated. No unresolved neuron is removed from the CNS.

Supplementary file 6 (serial leg groups) is also acquired and SHA-pinned in
`reports/curated_motor_resolution.json`: its 264 IDs shared with Supplementary
file 3 have no target disagreements. This checks consistency within the author
tables; it does not independently validate predicted MaleCNS body-ID matches.
The curated table is `reports/curated_motor_targets.csv`.

The body-800589 example above has no curated group and remains unresolved.
Body 801058 demonstrates why predicted IDs must not override curated metadata:
its predicted MANC ID points to Ti extensor, while curated group 15006 and the
MaleCNS label both identify Tr flexor. The runtime has never enabled these
predicted assignments; correction changes the evidence interpretation only.

## Model knee axes

`tools/calibrate_knee_axes.py` defines the knee opening angle using the vectors
from the tibia body origin to the trochanterfemur and tarsus1 origins. Across
neutral +/- 0.2 rad and two derivative step sizes, all six knee pitch axes close
the opening angle when q increases. This is a local geometric convention, not
a whole-range muscle moment-arm calculation. The static evaluations are not
simulation frames or recorded behavior.

`tools/check_knee_torques.py` then runs 18 independent native physical trials:
zero, +1 and -1 diagnostic torque for 10 ms on each knee. Relative to the zero
trial, q changes approximately +0.0181 and -0.0181 rad. No pose trajectory is
imposed. The body ABI now exposes named scalar joint position as a read-only
measurement, which can later feed explicit sensory transduction.

`configs/knee_interface_draft.json` contains 24 curated candidates with proposed
signs on six joints. It is disabled, with gain and activation time constant null.
Effector side from somaSide, pure knee torque and aggregation of accessory
flexors are declared engineering assumptions. It does not enable brain control,
exclude the remaining 357 leg motor neurons, or settle their mechanical roles.

## FlyMimic left-front tibia-extensor bridge audit

The original pinned MaleCNS annotation Feather, Cheong et al. Supplementary
file 3, and FlyMimic XML were independently re-read in Molab. Their SHA256
values matched the source locks. MaleCNS body 815344 (`Ti extensor MN_L`,
graph index 156979) references curated group 11657, `MNfl41` in the MANC
table. Body 815678 (`Ti extensor MN_R`, index 157213) references group 11706,
`MNfl39`. Both groups have left and right MANC members and target Ti extensor.
The two MaleCNS cells therefore cannot be treated automatically as a
homologous left/right pair or as one-to-one copies of a single simulated
actuator. The MaleCNS `rootSide` is empty for both; `somaSide` remains metadata,
not verified effector-side identity.

Cheong et al. Supplementary file 6 was independently downloaded and its
SHA256 checked against the pinned digest
`b56b0563f6a6000b2a43fbc7ebec46297668e8e3b6c6d596843d5ad5aab83a65`.
It assigns group 11657 to serial group 10347 (left body 11657, right body
13115), and group 11706 to serial group 10737 (left body 12704, right body
11706). All four rows are `Ti extensor MN`, subclass `fl`, target
`Ti extensor`. This independently resolves the group structure within the
published MANC annotations, but it does not identify either group as fast or
slow, prove a MaleCNS-to-MANC single-cell match, or show how the two biological
motor units should drive FlyMimic's one extensor actuator.
[Cheong et al. Supplementary file 6](https://cdn.elifesciences.org/articles/96084/elife-96084-supp6-v1.csv)
The executable audit `tools/report_tibia_extensor_serial_groups.py` writes
`reports/tibia_extensor_serial_groups.json` after checking the source digest,
both group IDs, serial IDs, targets and one soma on each side. The output
explicitly leaves fast/slow identity and activation mapping unresolved.
The MANC paper explicitly depicts serial extensor sets for slow and fast
extension, but the text available with Figure 7 does not label the numeric
serial sets as either role. Figure 5 supplement 1 also uses group 10347 as
an example where one member is less well reconstructed. The paired rows in
Supplementary file 6 therefore do not imply equal reconstruction quality or
equal physiology. Do not calibrate the two sides as identical from these IDs
alone. [MANC figures 5 and 7](https://elifesciences.org/articles/96084/figures)

The predicted `mancBodyid` for 815344 (10256) is absent from Supplementary
file 3. The predicted ID for 815678 (22126) exists there, but is `Tergotr. MN`
with target `Tergotr.`, not Ti extensor. Those predictions do not override the
curated group and cannot certify individual reconstruction identity. The
published FlyMimic XML has one named left-front tibia-extensor muscle-tendon
actuator, `LFTibia_extensor_93932`. The authors model 15 MTUs per foreleg and
note that physiological force parameters have limited direct measurements;
the model's muscle unit is not a neuron identity table.
[FlyMimic author project](https://gizemozd.github.io/fly_mimic/)

Executed source `tools/audit_lf_tibia_extensor_bridge.py`, the original 14-MB
MaleCNS annotation Feather, original MANC table and machine-readable report
were archived in private HF revision
`dcec7fca3973cef84be29da1709b5e8775ea9ed0`, manifest
`manifests/d57eceb5047d532c123b244cbdcf393bc6934b43ccab38d6c6cb6222122e3ca8.json`.
All four files passed fresh-directory SHA256 restore in Molab. The mapping
remains disabled: activation transfer, aggregation across motor units and
effector laterality still need independent evidence. The source and report
are in that archive; the executed script is not yet in this local checkout.

## Recorded CNS events for the tibia-extensor candidates

An archived full-graph, 100-ms FP64 LIF diagnostic was reopened in Molab from
HF commit `bfd5754bc9ae67d13e91567cc59e5c48d2b65fa8`. The original
manifest and both event arrays passed SHA256 checks. Graph index 156979
(MaleCNS body 815344) spiked at ticks 190 and 641 when unclear transmitter
signs were treated as excitatory, and at ticks 190 and 761 when treated as
inhibitory. Graph index 157213 (body 815678) did not spike in either variant.
The neural step was 0.1 ms. Changing this one sign assumption shifts the
second observed event by 12 ms; the count alone hides that sensitivity.

The archived protocol uses ten **artificial voltage jumps** to body 10056,
uniform LIF parameters and unvalidated transmitter assignments. These events
are actual output of the full native graph under that declared protocol, not
natural sensory responses or evidence of correct motor physiology. The
protocol explicitly has `biological_validation=false` and no body connection.
They can support a labelled diagnostic replay through a muscle, but cannot
set a physiological spike-to-force gain or justify a pilot controller.

The machine-readable event audit was published to the private HF dataset at
revision `4b887c58f6c00dff4f98829c0723352879da386a`, manifest
`manifests/9338b7752aa0e11507d481eaba9bfb3aee86aa29b1ba1a31fb9d59c7994fa294.json`.
Its SHA256 is `87b74c54815ce57d4042923b1d0ebdb5e52394b42e4847219bd921b5bfc02386`;
fresh-directory restoration in Molab verified the report and its event assertions.
The executable audit source was then archived together with that exact report
at revision `3c85a259d5b6e4ebca23929a086ea695e5392f2f`, manifest
`manifests/19c77c1828b869dc5ca16c44589ef47512e4ab33dc9a81eaeee066225081f8b2.json`.
Both files passed a fresh-directory SHA256 restore, and the restored source
passed Python compilation. The source digest is
`16d5156d1c3624c65041a1694dd598961ccbbfddb02a419c853ccf7bc64867ed`.
An explicitly hypothetical event-to-muscle replay subsequently produced
physical foot-pad contact and passive slide motion under an engineering
filter. It did not resolve the individual MaleCNS-to-MANC identity or prove
muscle activation physiology. See `docs/MUSCLE_REFERENCE.md` for the
intervention and its controls.
