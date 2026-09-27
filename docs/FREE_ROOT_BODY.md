# Free-root FlyMimic diagnostic

The pinned public FlyMimic XML fixes `Thorax` to the world. The prior muscle,
foot-pad, and neural-contact diagnostics therefore test articulated legs on a
fixed body, not the trajectory of a free fly.

`tools/probe_flymimic_free_root.py` adds only a MuJoCo six-DOF `freejoint` to
the published thorax. It prepends the author's thorax position and quaternion
to the existing `default-pose` keyframe, preserving all 14 original joint
coordinates exactly. The resulting model has seven more `qpos` and six more
`qvel` coordinates, with the same actuator and tendon counts. Both the
modified XML and numerical traces are hash-bound in
`reports/flymimic_free_root_local.json`.

With all muscle controls held at 0.0001 for 100 ms, zero gravity gave no
contacts and maximum whole-body center-of-mass drift of 1.85e-6 mm. The root
itself moved slightly as the legs changed shape, as expected for internal
motion. With the source gravity of 9801 mm/s² and the source floor present,
the first exact floor contact occurred at tick 142 (14.2 ms); the body then
continued in contact. Extending that same gravity case to 2 s ended with
thorax-local up almost opposite world up (dot product **-0.994710**). At that
point the head, thorax and both wings touched the floor. This is an inverted
collapsed pose, not a seated operator. All cases completed without MuJoCo
warnings.

This is a negative physical gate for unsupported free flight: the pinned model
has no aerodynamic wing forces or active flight controller in this variant.
It does not establish a stable fly inside a cockpit, a body-to-vision pose
stream, a landing controller, or KSP behavior. It keeps the published geometry
and muscle mechanisms available for a later body/cabin model.

## Explicit harness and contact diagnostic

`tools/probe_flymimic_harness.py` adds a named MuJoCo weld constraint from the
free thorax to a world-anchored seat reference. The relative pose is computed
as the exact inverse of the published thorax pose. Its declared `solref`
`[0.001, 1]` and `solimp` `[0.9999, 0.9999, 0.001, 0.5, 2]` make this a strong
but finite-compliance engineering harness. After 2 s at source gravity and
low muscle activation, the largest root translation from its anchor was
0.00001896 mm, thorax-up dot world-up was 0.99999968, and there were no floor
contacts or MuJoCo warnings. This support replaces the unrestrained body's
inverted collapse; it is mechanically close to a fixed thorax and is not a
measured fly seat. See `reports/flymimic_harness_local.json`.

The harness changes the 2-s passive joint state relative to the fixed-root
model (maximum coordinate difference about 0.245 rad), so
`tools/probe_flymimic_harness_contact.py` derived new symmetric pad positions
from the harnessed foot mesh. In eight side/contact/pulse conditions, only
positive-X pad + enabled contact + full-strength tibia-extensor pulse produced
foot-pad contacts (204 samples, first tick 221) and passive slide travel
(0.124263 mm). The three matched positive-X controls had zero exact contacts
and slide motion. Knee traces matched before the pulse; slide motion was zero
before first contact. The pad geometry, harness stiffness, pulse and eventual
motor-unit command remain unvalidated. See
`reports/flymimic_harness_contact_local.json`.

## Moving cabin frame

`tools/probe_flymimic_moving_cabin.py` reparents both the named harness target
and the passive pad under a MuJoCo `cabin_frame` body. The thorax weld now
references that frame rather than the static world. A prescribed, smooth
vertical cabin displacement `0.05*(1-cos(2*pi*t/0.1))` mm over 100 ms has
0.1-mm peak amplitude and zero endpoint displacement/velocity. It is a
diagnostic motion, not a rocket trajectory.

Eight runs crossed static/moving frame, contact enabled/disabled, and an
artificial tibia-extensor pulse. Static-frame slide trace matched the previous
harnessed contact trace exactly. During cabin motion, maximum root displacement
relative to the frame was 0.005946 mm. Only contact plus pulse moved the
passive slider: 227 exact foot-pad contact samples starting at tick 221 and
0.109519-mm peak slide, versus 204 samples and 0.124263 mm with the static
frame. The other three moving-frame controls had zero exact contacts and
slide; the active slide was zero before first contact. Full traces, XML and
hashes are in `reports/flymimic_moving_cabin_local.json`. The cabin motion,
harness and muscle pulse remain prescribed; there is no rocket-to-body
feedback, neural motor command, measured seat or KSP execution.

## Native rocket driven cabin

`tools/native_cabin_loop.py` advances the existing native radial rocket from
the previous passive slide position, then moves the harness/pad cabin frame to
the new rocket position before stepping the FlyMimic body. The MuJoCo frame
translates at the rocket's initial -20 m/s, so its local cabin displacement is
`(altitude - initial_altitude - initial_velocity*time)*1000` mm; the body's
initial velocity is zero in that frame. Native radial gravity is queried from
the plant and converted from m/s² to mm/s². This avoids a large false impact
from driving a MuJoCo `mocap` body through the full initial -20 m/s translation.
The distant floor is kept at -2,500,000 mm and exact floor contact is rejected.

The initial 0.01-mm foot-to-pad gap failed a control: cabin acceleration alone
caused contact at tick 186, before the muscle pulse at 200, producing a
0.012238-mm slide and nonzero engine throttle. This is a real false actuation
of that mechanical fixture, not a muscle response. A declared exploratory
pad-offset sweep of 0, 0.05, 0.10 and 0.20 mm showed that 0.05 and 0.10 mm
removed no-pulse contact while preserving pulse-driven contact; 0.20 mm
removed both. The 0.05-mm offset is a provisional engineering clearance, not
a biological or cockpit measurement.

At 0.05 mm, only the contact-enabled pulse moved the slide: first exact contact
and motion at tick 255, first throttle command at tick 256, peak slide
0.169170 mm. Native rocket altitude after 100 ms was 2497.992751 m versus
2497.992074 m ballistic. The coupled cabin trace first differed from the
ballistic-motion ablation in slide at tick 261 and altitude at tick 330; the
maximum differences were only 5.86e-6 mm and 2.12e-8 m. Contact-disabled
controls and the no-pulse case stayed at zero slide/throttle. These are
numerical observations, not validated moving-cabin feedback: the independent
zero-gravity Galilean control in `reports/mocap_galilean_check.json` gave a
37.9615-mm relative root error and 0.247-rad joint error after 10 ms. Thus the
`mocap` plus weld construction does not preserve the intended frame motion.
Full numerical traces, source hashes and
all gap outcomes are in `reports/native_cabin_gap_verification.json` and the
referenced reports. The muscle pulse is prescribed; no MaleCNS output, trained
policy or KSP execution is present.

## Cabin-local effective-gravity diagnostic

`tools/probe_harness_effective_g.py` instead keeps the harness and pad fixed
in a nonrotating, co-falling cabin frame. For radial world gravity `g` and
rocket acceleration `a = g + thrust/m`, local effective gravity is
`g - a = -thrust/m`, converted to mm/s². This avoids prescribed `mocap`
translation. It remains a diagnostic with an uncalibrated foot clearance and
prescribed full-strength tibia-extensor pulse. At the exploratory 0.10-mm pad
offset, no-pulse and contact-disabled controls had zero slide; pulse plus
contact first moved the slide at tick 440 and the throttle at tick 441, with
0.024728-mm peak slide. The feedback-on and feedback-off slide traces differed
by at most 5.92e-8 mm. At 0.05 mm, a no-pulse contact appeared at tick 599;
at 0.20 mm, neither case contacted. See
`reports/harness_effective_g_gap_100um_local.json` and neighboring gap reports.
This sensitivity does not establish physiological contact, cockpit validity,
or useful landing control.
The native ABI arithmetic and tick synchronization were checked independently
for zero, intermediate and full diagnostic slider inputs over 100 ticks each
in `reports/rocket_cabin_frame_check.json`. That check confirms the stated
effective-gravity calculation; it does not validate contact dynamics.

A replay with the recorded candidate MaleCNS graph neuron 156979 event ticks
190 and 641 used a hypothetical 0.1 actuator command per spike and 20-ms
decay (`reports/harness_effective_g_gap_100um_events_local.json`). At the same
0.10-mm exploratory pad offset, first exact contact and slide occurred at
tick 476, first throttle at 477, and peak slide was 0.005834 mm. No-event and
contact-disabled cases stayed at zero. Feedback changed slide by at most
2.70e-9 mm over 100 ms. The event source is a sign-diagnostic candidate; its
motor-unit identity, sign, and muscle gain are not biologically established.
This is event replay, not a closed sensory-neural control loop.
Replaying the alternative unclear-transmitter-sign run moved the second
candidate spike from tick 641 to 761. The generated muscle-control traces
first differ at tick 641 (maximum command difference 0.1), while the stored
contact, slide, throttle and rocket-velocity traces are exactly identical
through 1000 ticks. An extended trace localizes the lost effect: muscle
activation differs at tick 641 by up to 0.1929, muscle force from tick 642 by
up to 57.87 in MuJoCo's model units, and knee angle from tick 642 by up to
0.007283 rad. The last exact foot-pad contact was at tick 559; none occurred
after the sign-dependent second spike. The event therefore changes limb
mechanics but has no observed cockpit or rocket effect in this fixture and
window. Identical cockpit output cannot validate its sign or physiological
role. See
`reports/harness_effective_g_gap_100um_events_unclear_inhibitory_local.json`.

The exploratory candidate-event clearance sweep in
`reports/cabin_event_gap_sweep.json` sampled additional pad offsets of 50,
75, 100, 125, 150, 175 and 200 µm. At 50 and 75 µm, the no-event control
also contacted and moved the slider (first contact ticks 599 and 813).
At 100 µm, events moved the slider without that control leak. From 125 µm
upward, events did not contact the pad. Thus only one sampled clearance met
both conditions, and it was selected after inspecting the fixture. This is
strong gap sensitivity, not a calibrated physiological contact geometry.

The preflight relaxation state is another material variable. The Earth-gravity
relaxation used above ends with left-front knee pitch 0.806424 rad. Relaxing
the same author keyframe for 2 s at zero gravity instead ends at 1.126326 rad;
with the Earth-placed pad and 100-µm offset, neither event nor no-event case
contacts (`reports/harness_effective_g_gap_100um_events_zero_g_relax_local.json`).
Placing the pad from the new relaxed foot surface by the same `bbox high X +
0.02 mm + 0.10 mm` rule restores event-driven contact at tick 419 and throttle
at tick 420, with 0.020761-mm peak slide and zero no-event slide
(`reports/harness_effective_g_gap_100um_events_zero_g_relax_relaxed_pad_local.json`).
This distinguishes initial-pose dependence from the ability of a retargeted
diagnostic pad to contact the foot. Neither pad placement is measured cockpit
geometry; the abrupt Earth-to-freefall transition in the first protocol is
not a validated launch history.

`tools/probe_live_cabin_claw.py` then advanced the complete native FP64
MaleCNS graph, harnessed FlyMimic body, and radial rocket every 0.1 ms for
100 ms in the zero-gravity-relaxed, foot-relative pad fixture. The declared
SNpp50 knee-position encoder and candidate motor-to-muscle filter are still
unmeasured hypotheses; ten artificial central voltage jumps remain present.
With sensor feedback blocked, the graph had 5,001 events and motor candidate
spikes at ticks 190/641. The negative-position sensor hypothesis produced
35 SNpp50 spikes, 4,754 total events and motor spikes at 190/612. The sensor
drive reached 114.42 mV. First sensor-spike difference was tick 212, first
motor-spike difference tick 612, and knee motion first differed at tick 613.
Exact foot-pad contact had already ended at tick 510. Thus contact, slide,
throttle and rocket-velocity traces were identical between these two cases;
peak slide was 0.020761 mm. Breaking the motor output or contact prevented
all slide and throttle motion. See `reports/live_cabin_claw_local.json` and
its hashed neural-event and physical traces. This is a live numerical loop
with a negative cockpit-feedback result, not biological claw validation or
landing control.

The matched central-drive ablation removed only the ten artificial voltage
jumps. With no jump, all four 100-ms cases had zero graph spikes, exact
contacts, slide motion and throttle; the negative-position encoder saw only
0.005994 mV peak drive from passive knee drift. In the periodic-jump run it
produced 35 SNpp50 spikes. The paired reports, event files and traces are
hash-checked by `tools/check_live_cabin_central_necessity.py`; see
`reports/live_cabin_central_necessity.json`. This establishes that the
observed fixture response depends on artificial central excitation, not that
the biological animal requires it.

### Phase-corrected v2 rerun (2026-09-24)

The v1 reports above are historical. After zero-g relaxation, both probe scripts
now call `mj_forward` before using world geometry to place the pad. The v2
reports also state which trace values describe the start or end of each MuJoCo
step. New runs use separate `_v2` paths, leaving v1 data intact.

At a 100 µm relaxed-pad gap with recorded motor events, the v2 harness probe
observed contact at tick 419 in the event/contact case, slide
0.0207610267 mm, and peak effective gravity 120.914618 mm/s² with feedback.
No-event and contact-off controls had zero slide. The v1 feedback case had
0.0207606672 mm of slide and 120.912502 mm/s² peak effective gravity;
the correction changes those numbers slightly, not the qualitative outcome.
See `reports/harness_effective_g_gap_100um_events_zero_g_relax_relaxed_pad_v2_local.json`.

The complete-graph v2 probe again had 35 negative-sensor spikes under periodic
artificial central drive, with motor spikes at ticks 190 and 612 and slide
0.0207610267 mm. With central drive removed, all four controls had zero graph
events, contacts, slide, and throttle over 100 ms. The paired v2 traces and
event files were hash-checked by `tools/check_live_cabin_central_necessity.py`;
see `reports/live_cabin_claw_v2_local.json`,
`reports/live_cabin_claw_no_central_v2_local.json`, and
`reports/live_cabin_central_necessity_v2.json`.

The sensory voltage conversion and motor filter remain unvalidated; the periodic
central jumps are artificial. These tests establish a local causal diagnostic
only. They do not establish biological reactions, local plasticity, KSP cabin
control, or landing performance.
