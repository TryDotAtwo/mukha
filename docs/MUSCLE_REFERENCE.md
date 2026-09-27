# Data-driven leg muscle reference

The current direct joint-torque diagnostic moves the fly's leg but did not
bring its claw into contact with the passive throttle pad. Its torque limit,
spike gain and filter are engineering choices, not measured muscle physiology.
Do not infer from the failed contact that the biological fly could not reach
the control.

[Özdil et al., *Musculoskeletal simulation of limb movement biomechanics in
Drosophila melanogaster*](https://arxiv.org/abs/2509.06426) publish an
anatomically informed Hill-type muscle model in MuJoCo. Their
[FlyMimic source](https://github.com/gizemozd/FlyMimic) is a reference for
muscle-tendon mechanics, not a trained MaleCNS interface or a replacement
brain. The source was pinned in Molab at commit
`9ea1131626cd76f7203b74076ef8f0e9cab30bef`. The model XML SHA256 is
`d67ff06d0c684599f00d5f33f8f8ac8ced01ab994c41341b551f8148b6d8aa0b`.

The pinned archive's 72 mesh files and XML (73 paths; 21,306,283
uncompressed bytes) each matched the Git blob SHA and size in that commit.
The source tarball SHA256 is
`889c6e244c95501c957bf0e2d8ab94dcdc0fd36293fcab9d7840e908341d4207`.
These were remotely verified and restored by SHA256 from private HF revision
`81b63678263be1d157c2e24f09c5c61ae3961667`, manifest
`manifests/0a78107deb763bbbd2acdd4e028555cbc178ae3e00a62f6cf4ce07cebae79663.json`.
The separate XML inventory is at revision
`9364b819eaa2ac8ebc471fcf7a2c55086cf7167c`.

MuJoCo 3.14.0 compiled the extracted model in Molab: 73 bodies, 14 active
joints, 15 actuators, 15 tendons, 71 mesh assets, at a 0.1-ms physics step.
The left front leg has seven named joint degrees of freedom. Two muscle
actuators cross its tibial joint: `LFTibia_flex_93434` and
`LFTibia_extensor_93932`. In an isolated 100-ms intervention with all
activations at 0.0001, driving the extensor at 1.0 from tick 200 through 599
changed `joint_LFTibia_pitch` by up to 0.411480 rad compared with the
baseline. Both 1000-tick runs were finite and had no MuJoCo warnings. The
full traces and report were remotely verified and restored at HF revision
`468c280f32b9a3c28d3a57a4fcab28f922bf671b`, manifest
`manifests/5fcb2582c96c500bd9150e4f2900ac4dabfa2a0f9be1ea923045c40e9961c94e.json`.
`tools/check_flymimic_muscle.py` records the diagnostic procedure.

This is evidence that the published muscle actuator causes joint motion in
the pinned model. It is not evidence of physiological activation strength,
contact with the cockpit, or a neuron-to-muscle mapping. In our MaleCNS
curated target table, two left-front tibia-extensor candidates have a
curated-group/label agreement, while five labelled left-front tibia-flexor
candidates lack a curated group. Neither count proves one-to-one identity
with FlyMimic's two tibial actuators. The next mechanical gate is an explicit
anatomical model and axis crosswalk, followed by held-out force/kinematic
checks and a pad-contact intervention. No new motor mapping is enabled.

An initial passive-throttle contact intervention now ran in Molab on the
published FlyMimic model. The `LFTarsus5_geom` mesh at neutral pose spans
Y = 0.286297–0.339346 in the model's millimetre coordinates. A 0.15 × 0.01 ×
0.15 mm half-size passive pad was placed on its positive-Y side with a
0.01-mm surface gap. The pad has a Y slide joint, spring and damping, and no
actuator. The experiment crossed foot-pad contact enabled/disabled with the
same extensor pulse enabled/disabled, for 1000 MuJoCo ticks per condition.
Exact `LFTarsus5_geom`–`throttle_pad` contacts were zero in all four cases,
and the slider stayed at zero. The foot moved toward negative Y in both pulse
conditions; the pulse reduced that excursion but did not bring the foot to
this pad. An initial broad contact counter included unrelated fly contacts;
the archived report uses exact geom IDs and corrects that error.

The report and both model variants were published to the private HF dataset
at revision `a55ae956b8e0643d5e05a69981ed54336a631a4c`, manifest
`manifests/a4b3516ec8fc89f1504ef2486fd8095e2ab9927e8630bbd62c4a2c917845bfe0.json`.
All three files restored with SHA256 verification into a fresh Molab folder.
This is a negative test of one fixed pad location, not evidence that the
muscle cannot operate a suitably placed passive lever. The next mechanical
step is a declared anatomical axis/position crosswalk before another contact
trial; later placements chosen from these trajectories must be marked
exploratory and separately validated.

A second **exploratory** fixture was selected after inspecting the prior foot
trajectory: a passive pad at model coordinates `(-0.56, 0, 1.68)` mm, normal to
the negative-X foot motion. Its slide axis is `(-1, 0, 0)`; there is no
actuator targeting the slide joint. In four 100-ms runs, disconnecting the
explicit foot-pad pair kept the slider exactly at zero with or without the
muscle pulse. With contact, the no-pulse run made 113 exact foot-pad contacts
and reached 0.0163085 mm of slider displacement; the extensor-pulse run made
67 contacts and reached 0.00842636 mm. The contact traces were identical
before pulse onset at tick 200. The maximum paired slider difference was
0.00794548 mm; the pulse **reduced** peak travel. No MuJoCo warnings occurred.
This shows a causal muscle effect on a passive physical lever in this one
fixture; it does not show intended lever operation by a neural controller or
independently validated cabin geometry. Baseline motion is substantial.

The executed source `tools/check_flymimic_throttle_x.py`, two XML variants,
full 1000-tick traces and report are in the private HF dataset at revision
`9aea14560ac8865dee3177dc41fd4341e20b5c21`, manifest
`manifests/57d69e3a7de8fd7dc35ecc52ac1c90f785477325bf41a6ccbfa85a404a02eada.json`.
All five artifacts passed fresh-directory SHA256 restoration in Molab.
The source is preserved in that archive; it has not yet been imported into
this local checkout. A held-out mechanical design must specify the seat,
body pose, lever location and load *before* running the muscle intervention.

To separate active muscle motion from the large initial passive transient,
the author model was advanced for 20,000 steps (2 s) at activation 0.0001
before any intervention. At that point the maximum absolute joint speed was
0.001596 in model units/s. The full `qpos`, `qvel` and muscle-activation state
was copied into each test. Two pads were placed symmetrically, 0.01 mm beyond
the negative- and positive-X surfaces of the *relaxed* `LFTarsus5_geom` mesh.
The X axis was motivated by earlier trajectory exploration, so this is still
not a wholly independent cockpit design; the individual positions came only
from the shared pre-pulse geometry.

The resulting eight 100-ms conditions crossed side, explicit contact and
extensor pulse. The single condition with negative-X pad, contact and pulse
produced 236 exact foot-pad contacts, beginning at tick 39, and moved the
passive slider by up to **0.139131 mm**. Every other condition had zero
foot-pad contacts and zero slider displacement. No slider actuator was
present, the same relaxed fly state started every run, and MuJoCo reported no
warnings. Thus the published muscle model can transmit a diagnostic pulse
through the physical foot to a passive control after relaxation. Activation
1.0 is an uncalibrated probe; neither the muscle activation nor the lever
load is yet validated against biological measurements. This is not a
MaleCNS-to-muscle mapping, cockpit controller or learned landing.

Executed source `tools/check_flymimic_rest_throttle.py`, four XML variants,
the starting state and all 1000-step traces, and the report were archived at
private HF revision `5e2a9137cf66a31c344e34587cc55c9a1bf9cde8`, manifest
`manifests/baeb0f2ce038c4100c1c60d740f0d64cdf31b426052c5588304fbdacaa787ab7.json`.
All seven files passed a fresh-directory SHA256 restore in Molab. The source
is in that archive; it has not yet been imported into this local checkout.
The next gates are calibrated muscle activation/load, full seated-body
integration, and a source-backed motor-unit correspondence.

## Recorded CNS event to muscle to lever diagnostic

The same pinned, relaxed FlyMimic body and passive negative-X pad were used
for an eight-condition intervention in Molab. Two original full-graph event
arrays were SHA256-verified against the first private HF archive. For MaleCNS
candidate 815344 (graph index 156979), the `unclear_excitatory` variant has
spikes at ticks 190/641 and the `unclear_inhibitory` variant at 190/761;
candidate 815678 (index 157213) has none in either 100-ms trace. These are
outputs of an artificial direct-drive, unvalidated LIF experiment, not
natural sensory responses. Assigning 815344 to the one FlyMimic left-front
tibia-extensor actuator is an explicit **hypothetical** interface.

An engineering exponential filter used gain 0.1 per spike, 20-ms time
constant, 0.1-ms steps and control clamp [0.0001, 1]. It was fixed before
examining the physical results. Each event variant crossed motor output
connected/disconnected and exact foot-pad contact connected/disconnected.
Only motor plus contact moved the passive slide: 62 exact contacts, first
contact and slide motion at tick 446, peak displacement 0.001548796 mm in
both event variants. No-contact and motor-disconnected slides remained
exactly zero. The first contact preceded the second spike in both variants.
Before the first spike, paired slide and knee traces matched exactly; the muscle
control trace matched an independently evaluated exponential sum within
7.7e-17. Maximum knee-angle differences from motor disconnection were
0.0335353 and 0.0304169 rad. No MuJoCo warnings or direct slide actuator
occurred. These checks establish a narrow causal path through the recorded
spike, assumed filter, published muscle model and physical contact in this
fixture. They do not establish physiological gain, correct motor-unit
identity, seated flight, closed sensory feedback or pilot competence.

The executed source, all recorded 1000-tick traces and report passed fresh-directory SHA256
restore from private HF revision `e182a60a26e92e01da491e602f8f8a71d6e6bbd7`,
manifest `manifests/634331d86a9a6e69c891a167e63b11a57955f17c7f6a5a2a307052cf908cad02.json`.
The trace SHA256 is
`cd9ec25fe09dffc3b6bfb87c077ad807e2e10ebf3164204b657fa2574927f9f3`.

## Sensitivity to the unmeasured spike-to-activation filter

The [FlyMimic paper](https://arxiv.org/abs/2509.06426) (v1 PDF pp. 4, 6, 9) describes anatomical
parameters from X-ray data, while maximum isometric force and contraction
velocity were estimated or optimized rather than directly measured. Its
learned policy supplies continuous per-muscle input in [0, 1]; the paper does
not establish a per-spike gain for either MaleCNS candidate. The pinned v1
PDF read in Molab has SHA256
`d6e39025763582d861554e668eaaff6719b0d295906a2dc0af8ddfa32b436a50`.
The acquired Azevedo et al. leg-motor appendix (PDF page 31, Figure A11;
`data/reference/azevedo2024_appendix/azevedo24_appendix.pdf`, SHA256
`822c298e50da9fee3ce75f1dabda040574eac9fc854fdf92837856a82c8515f6`)
shows distinct slow and fast tibia-extensor motor neurons. SETi targets the
distal, more pinnate fibers; FETi targets the proximal fibers. The local
FlyMimic `best_combined_cvt3.xml` has one left-front tibia-extensor muscle
actuator, `LFTibia_extensor_93932`, attached to one spatial tendon (XML lines
521-524 and 542). Its scalar control cannot independently express these two
published fiber targets. Splitting it into source-calibrated motor units would
require further geometry and force evidence; assigning either MaleCNS cell to
SETi/FETi requires a verified FANC-to-MANC cell crosswalk. Neither is enabled.

Locust SETi/FETi twitch data and Drosophila *flexor* force measurements are
different organisms or motor units, so they are not silently reused as this
extensor's calibration.

Before running, an engineering sensitivity grid fixed gains 0.025, 0.05, 0.1,
0.2 per spike and decay constants 10, 20, 50 ms. Both archived sign variants
were crossed with pad contact on/off: 48 separate 100-ms MuJoCo runs from the
same pinned relaxed fly state. Peak slide travel in mm with contact enabled
for the excitatory variant was:

| Gain per spike | 10 ms | 20 ms | 50 ms |
|---:|---:|---:|---:|
| 0.025 | 0 | 0 | 0 |
| 0.05 | 0 | 0 | 0 |
| 0.1 | 0 | 0.001549 | 0.012812 |
| 0.2 | 0.015908 | 0.023044 | 0.032990 |

The inhibitory-sign variant had the same zero/nonzero pattern and contact
counts; its 0.1/50-ms peak was 0.012274 mm, while the other nonzero peaks
matched to the displayed precision. Every no-contact run had exactly zero
slide displacement and foot-pad contacts. Thus contact occurred in only 5 of
12 filter settings per event variant. This fraction is a property of an
arbitrary grid, **not** an estimated probability for a biological fly.
Maximum control over the grid was 0.281152, so these cases did not reach the
upper clamp. The 0.1/20-ms central case matched the prior contact count and
slide trace to 9.4e-18 mm; knee traces differed by at most 2.3e-16 rad from
equivalent recurrence arithmetic. No parameter was selected after observing
contact, and the sweep does not calibrate the gain or transfer time.

The executable source, 48-condition traces and report passed fresh-directory
SHA256 restore from private HF revision
`64ff8a0c159c607e6df0c6682a168dfcab6c81ae`, manifest
`manifests/5b61848ca563b79e141c4b78d8c566dab6eec05c6dfbce85371322c55ba22ac1.json`.
Trace SHA256:
`870115f16a02b0c2f1656452c506bc819949ac28ab0edbf96907e2b787f23fd5`.
Rerunning requires the original event manifest (HF revision
`bfd5754bc9ae67d13e91567cc59e5c48d2b65fa8`), FlyMimic source model,
the relaxed-state fixture at revision
`5e2a9137cf66a31c344e34587cc55c9a1bf9cde8`, and the baseline replay
at revision `e182a60a26e92e01da491e602f8f8a71d6e6bbd7`.

## Local public-source restoration and mechanical replay (2026-09-24)

The pinned public FlyMimic commit `9ea1131626cd76f7203b74076ef8f0e9cab30bef`
can now be restored locally without the private HF archive. Run
`python tools/restore_flymimic_public.py`; it verifies the Git blob identity,
size and SHA-256 of the source XML, 71 STL files and source mesh ZIP. The
73 restored files total 21,306,283 bytes. The XML SHA-256 remains
`d67ff06d0c684599f00d5f33f8f8ac8ced01ab994c41341b551f8148b6d8aa0b`;
the source tarball SHA-256 is
`889c6e244c95501c957bf0e2d8ab94dcdc0fd36293fcab9d7840e908341d4207`.
See `reports/flymimic_public_restore.json` for every restored file.

For the local MuJoCo 3.14.0 replay, install that wheel under
`build/flymimic_pydeps` using
`python -m pip install --target build/flymimic_pydeps --no-deps mujoco==3.14.0`.
Then run `python tools/replay_flymimic_muscle_local.py`,
`python tools/audit_flymimic_foot_geometry.py`, and
`python tools/probe_flymimic_passive_throttle.py`. The loader passes the
verified XML and meshes as bytes because MuJoCo 3.14.0 could not open this
workspace's Cyrillic path by filename on Windows.

The isolated full-strength `LFTibia_extensor_93932` pulse produced a maximum
left-front knee difference of 0.4114802408 rad versus the no-pulse control,
reproducing the earlier six-decimal Molab measurement. The relaxed foot's
negative-X mesh surface was measured before placing a passive pad. Across
four 100-ms conditions, only contact enabled plus the same artificial muscle
pulse produced exact foot-pad contact (234 samples, first at tick 239) and
slider travel (maximum 0.1625979192 mm). The other three conditions had zero
exact contacts and zero slider movement. Pre-pulse knee traces were identical,
there was no direct slider actuator, and MuJoCo issued no warnings. Reports
and traces are under `reports/flymimic_*_local.json` and
`data/derived/flymimic_*`.

This local pad differs from the earlier private-HF contact fixture, so its
0.162598-mm displacement is a new mechanical diagnostic, not a numerical
replication of the archived 0.139131-mm result. Pad placement used relaxed
foot geometry, and the muscle pulse is prescribed. Neither experiment
establishes a MaleCNS motor-to-muscle mapping, physiological activation,
seated cabin operation, rocket feedback, learning, or KSP landing.

The same measured slider traces were then fed to the native radial rocket
plant with `cmd /c tools\\build_flymimic_rocket_replay.cmd` followed by
`python tools/check_flymimic_rocket_replay.py`. The native replay samples
the measured slide at the start of each 0.1-ms rocket step and applies the
existing `clamp(q / 0.3 mm, 0, 1)` throttle rule. First exact foot-pad contact
was at MuJoCo tick 239; throttle first became nonzero at rocket tick 240.
The peak throttle was 0.541795. Across the 100-ms replay, the maximum
velocity difference from the ballistic control was 0.035769 m/s. All three
controls had byte-identical numeric rocket trajectories. Independent engine
thrust and fuel recurrences passed; hashes and errors are in
`reports/flymimic_rocket_replay_local.json`. This is a one-way replay of a
prescribed muscle pulse, without rocket acceleration fed back into the fly.

A further exploratory loop uses `native/rocket_vertical_abi.cpp` to advance
that same native rocket during each MuJoCo step; run
`cmd /c tools\\build_rocket_vertical_abi.cmd` and
`python tools/probe_flymimic_rocket_feedback.py`. In a nonrotating co-falling
frame it applies the previous rocket thrust as uniform effective gravity
`-1000 * thrust / (1000 + fuel)` mm/s² to the fly model. Eight 100-ms cases
cross feedback, contact and prescribed pulse. Only contact plus pulse moves
the slider. Closed and open trajectories are identical through the first
nonzero command; feedback then changes the slide by at most
`1.5737215e-6` mm and rocket velocity by at most `2.6604984e-7` m/s.
Maximum effective gravity is 1395.18 mm/s². The fly was relaxed under its
source gravity and switched to a co-falling frame at diagnostic start;
this discontinuity and the fixed-body, uniform-gravity approximation limit
physical interpretation. The result establishes a numerical two-way
mechanical coupling in this fixture, not a calibrated aircraft cabin or
biological closed loop. See `reports/flymimic_rocket_feedback_local.json`.

The original local full-graph FP64 event arrays were also replayed through
this locally restored FlyMimic model with
`python tools/probe_flymimic_cns_event_contact.py`. The source event hashes
and diagnostic spec are recorded in
`reports/flymimic_cns_event_contact_local.json`. Candidate graph index
156979 fired at ticks 190/641 or 190/761 under the two unclear-sign
assumptions; index 157213 had no event. With the explicitly hypothetical
0.1-per-spike, 20-ms exponential activation filter, only motor-connected
plus contact-enabled conditions moved the passive slider. Both variants
produced 64 exact contacts, first at tick 446, and a maximum displacement of
0.001445874 mm. The six controls had zero slide motion and exact pad
contacts; knee traces matched before tick 190. The prior private-HF fixture
reported 62 contacts and 0.001548796 mm. These numbers should not be
equated: the local pad geometry differs. Event transfer remains open-loop,
and the motor-unit identity, activation gain and natural sensory drive are
unvalidated.

The resulting eight measured slide traces were replayed through the native
rocket plant with `python tools/check_flymimic_cns_event_rocket.py` after
building `tools/build_flymimic_rocket_replay.cmd`. In each connected-contact
variant, the first nonzero throttle was at tick 447, one tick after first
contact at tick 446. Peak throttle was 0.004813591 and the largest rocket
velocity difference versus the ballistic control over 100 ms was
0.000143223 m/s. Six disconnected controls produced exactly identical
rocket trajectories. Independent engine and fuel recurrences passed. See
`reports/flymimic_cns_event_rocket_local.json`. This remains a one-way replay
of artificially evoked full-graph events through a hypothetical motor map,
not a KSP run or learned landing controller.

The recorded-event file was then removed from the execution path in
`tools/probe_live_cns_flymimic.py`: each 0.1-ms tick advances the complete
native FP64 MaleCNS CUDA graph, reads candidate neuron 156979's actual spike,
and immediately steps four FlyMimic bodies crossing motor connection and
foot-pad contact. This local 100-ms run produced 5,001 complete-graph events,
exactly matching the earlier pinned event array. All four physical control,
contact and slide traces also matched the offline replay exactly. The
connected-contact case had 64 exact contact samples and 0.001445874-mm peak
slide; the other three had zero slide. Hashes, source graph size and exact
comparison flags are in `reports/live_cns_flymimic_local.json`. Artificial
voltage jumps still drive the CNS, the neuron-to-muscle assignment/filter
remain hypotheses, and fly sensory measurements are not fed back to neurons.
## Initial-pose correction (2026-09-24)

The isolated pulse, pad-contact, and slider experiments described below started
with MuJoCo's ordinary zero-coordinate reset and then applied 20,000 passive
low-activation steps. The published XML instead defines a `default-pose`
keyframe with left-front tibia pitch **1.862 rad**. Zero reset starts this joint
outside its declared [0.4789, 2.502] rad range; the passive zero-start settle
ended near **0.4736 rad**. Therefore the older local contact and closed-loop
results are reproducible *in that non-keyframe fixture*, but cannot establish
behavior from the author's initial pose or physiological stance.

`tools/audit_flymimic_keyframe_mechanics.py` separately reset to the published
keyframe. At the end of an isolated full-strength pulse, the extensor changed
knee pitch by **-0.473258 rad** relative to baseline, while the flexor changed
it by **+0.790246 rad**. The femur-tibia opening angle falls as pitch rises in
this configuration, so these are opposing extension/flexion actions. After a
two-second low-activation settle *from the keyframe* (pitch 0.860026 rad), the
corresponding differences were **-0.265014** and **+0.721853 rad**. No MuJoCo
warnings occurred. See `reports/flymimic_keyframe_mechanics_local.json` and
its hashed traces. These pulses are mechanics diagnostics, not measured neural
drive, a validated walking pose, or a contact-control result. All previous pad
placements must be re-evaluated against this keyframe-derived geometry.

`tools/probe_flymimic_keyframe_contact.py` rederived two symmetric X-side
pad positions from the foot mesh in both the direct keyframe and the 2-second
keyframe-derived passive state. It ran 16 cases crossing posture, side,
contact and extensor pulse. In the 2-second state, **only positive-X pad +
contact + pulse** touched the foot (92 exact contact samples, first at tick
220) and moved the passive slide (peak 0.227188 mm); all three same-posture,
same-side controls had zero contacts and zero slide. Pre-pulse knee traces
matched, and the slide was zero before first contact. The slide axis was
oriented +X for this side. In the direct keyframe, the same pad had contact
already at tick 95 even without a pulse, so that posture does not isolate
muscle-caused initial contact. See
`reports/flymimic_keyframe_contact_local.json`. Pad location, slide geometry,
and full-strength pulse are still exploratory, and no validated neural signal
or cockpit is implied.

The full native FP64 MaleCNS graph was then advanced live with this
keyframe-derived positive-X pad (`tools/probe_live_cns_flymimic.py
--keyframe-derived`). Its 5,001 neural events exactly reproduced the saved
full-graph reference for the same artificial central drive. The candidate
motor cell spiked at ticks 190 and 641. Under the assumed 0.1-per-spike,
20-ms muscle filter, the connected-contact condition had 142 exact pad
contacts, first at tick 247, and 0.048848-mm peak slide travel; slide motion
began at that contact. Disconnecting either motor output or contact kept
slide travel at zero. See `reports/live_cns_flymimic_keyframe_local.json`.
This tests the live neural-to-muscle-to-contact path from the source-derived
pose; artificial CNS input and unmeasured motor assignment/filter prevent a
biological-response claim.
