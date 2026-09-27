# Rocket environment implementation status

## Synchronized CNS/body/rocket checkpoint diagnostic

`native/rocket_vertical_abi.cpp` now exports an airborne diagnostic snapshot
and restore constructor. It stores time, altitude, velocity, fuel, thrust and
the contact flag; the restore constructor rejects nonfinite and terminal
states. `tools/build_rocket_vertical_checkpoint_abi.cmd` builds a separate
DLL so previous rocket evidence remains bound to its original binary.

`tools/check_synced_cns_body_rocket_checkpoint.py` extends the verified
250-tick full-MaleCNS/FlyMimic checkpoint with a one-way rocket replay from
the body's measured contact-slider position at each step start. The first
nonzero throttle and first velocity difference from an all-zero-command
ballistic control both occur at tick 317. At tick 500 the velocity difference
is +0.0001665868 m/s. A fresh rocket handle and a separate process each
restore the saved state and reproduce the remaining 250 rocket states exactly.
The report and hash-pinned snapshot are in
`reports/synced_cns_body_rocket_checkpoint.json`,
`reports/synced_cns_body_rocket_resume.json`, and
`data/derived/synced_cns_body_rocket_checkpoint_v1`.

This is a synchronized one-way checkpoint: the saved CNS/body continuation
drives the rocket, but rocket acceleration does not feed back into the body.
It is not a full KSP state, trained controller or landing checkpoint.

## Live two-way checkpoint and feedback control

`tools/check_closed_cns_body_rocket_checkpoint.py` now advances the full
native FP64 MaleCNS, source FlyMimic body, and radial rocket on the same
0.1-ms clock. The body slide sampled at step start commands the rocket;
the rocket's thrust-derived effective cabin gravity is applied to the next
FlyMimic step. The first nonzero slide command occurs at tick 270 and the
first nonzero cabin acceleration at tick 271. The connected diagnostic has
272 exact foot-pad contact samples, three candidate motor spikes, 70 total
neural events, and 0.137119-mm maximum slide over 100 ms. This remains a
fixed-thorax, co-falling radial approximation with hypothetical sensory and
motor mappings.

At tick 500, the script saves the 29,430,080-byte brain state, MuJoCo
integration state, rocket state, and scalar motor-filter activation. Fresh
handles in the same process reproduced all 15 signals and every event through
tick 1000 exactly; `--resume-only` did so again in a separate process after
verifying file hashes. Evidence is in
`reports/closed_cns_body_rocket_checkpoint.json`,
`reports/closed_cns_body_rocket_resume.json`, and
`data/derived/closed_cns_body_rocket_checkpoint_v1`.

The `--feedback-off` control keeps the same initial states, contact path,
neural encoder and rocket plant but applies zero rocket acceleration to
FlyMimic. The first knee and slider differences occur at tick 271, sensory
drive differs at tick 272, and rocket velocity at tick 307. Maximum
differences are 0.00006485 rad knee, 0.00001014 mm slider, 8.20e-8 mV
sensory drive and 1.29e-6 m/s rocket velocity. Both branches have exactly
the same 70 neural events and candidate motor voltage in this 100-ms window.
See `reports/closed_cns_body_rocket_feedback_control.json`. This verifies
a small mechanical feedback effect, not neural control adaptation or
physiological feedback strength.

## Synchronized diagnostic video

`tools/check_closed_cns_body_rocket_checkpoint.py --capture-only` replayed
the same 1000-tick closed run and matched all 15 original signals and every
neural event exactly. It saved full MuJoCo integration state and rocket state
after every tenth tick, giving 100 frames at 1-ms simulated intervals.
`tools/render_closed_cns_body_rocket_video.py` restores those body states to
MuJoCo and renders the physical pad and fly geometry beside timestamped
neural, contact, slider and rocket readouts. Contact is explicitly labeled
as the step-start sample; the body pose is the post-step state. The 100
frames form a 4-second, 25-fps MP4, so playback is 40 times slower than
simulation. A second independent render from the saved states reproduced
both the uncompressed RGB stream hash and the MP4 file hash exactly on this
machine. The source, camera, encoder configuration, timestamps, preview and
hashes are in `reports/closed_cns_body_rocket_capture.json`,
`reports/closed_cns_body_rocket_video.json`, and
`data/derived/closed_cns_body_rocket_video_v1`.

This clip proves a reproducible diagnostic recording path. It is not footage
from KSP, trained behavior, or a biological reaction.

## Mechanical file checkpoint diagnostic

`native/mechanics_file_probe.cpp` writes a versioned 7,864-byte checkpoint using
the existing exclusive-pending, flush/sync/rename writer. It contains the 971
MuJoCo integration values, six rocket values, scheduler tick, compiled MuJoCo
model fingerprint and corruption checksum. Physics parameters and pulse schedule
remain fixed by this diagnostic executable. Model identity includes serialized
compiled model data, rather than the XML path alone.

`tools/check_mechanics_file.py` ran an uninterrupted process and two separate
save/resume processes. Checkpoint at tick 3,000, resumed to tick 10,000: final
files match byte for byte. Truncation, trailing bytes, wrong magic, payload and
metadata changes, and a separately loadable model with doubled pad mass are
rejected. Existing output survives every rejection. Evidence:
`reports/mechanics_file_checkpoint.json`.

This is a trusted same-build diagnostic format, not a portable or authenticated
experiment checkpoint. FNV detects accidental changes. Native float64/uint64
layout is used; executable and library identity must be checked against external
SHA-256 evidence because the loader does not enforce them. It supports airborne
radial states only and omits brain, sensors, RNG and recorder state. Build with
`tools/build_mechanics_file_probe.cmd`; arguments: XML, output file, stop tick,
optional input checkpoint. Verify with `python tools/check_mechanics_file.py`.

## Coupled-state continuation

`native/mechanics_checkpoint_probe.cpp` snapshots the closed radial mechanical
loop at tick 3,000 during the diagnostic joint pulse. A fresh `mjData` receives
all 971 `mjSTATE_INTEGRATION` values, and a fresh radial plant receives the rocket
state. The fixture retains the scheduler tick. Cabin effective gravity is derived
again from the rocket at each next step rather than silently left at another
instance's value.

All 7,000 subsequent body integration states and all rocket state fields equal
the uninterrupted branch exactly; no MuJoCo warnings occur. Build with
`tools/build_mechanics_checkpoint_probe.cmd`, then run
`python tools/check_mechanics_checkpoint.py`. Evidence is pinned in
`reports/mechanics_checkpoint.json`.

This is a same-process, same-model in-memory test at 0.1 ms. It proves continuation
of that computation, not timestep accuracy. A portable file format, standalone
process restore, immutable full model dependency manifest, neural/sensory/RNG
state and recorder continuation remain required for full experiment checkpoints.

## Extended mechanical step refinement

Further driven-pair runs at 6.25, 3.125 and 1.5625 microseconds used one rebuilt
executable and added 2,240,000 checked physics records. Their final feedback
velocity effects are 0.01893538, 0.01919244 and 0.01937321 m/s, respectively.
The last relative change is 0.9331%, below the declared 1% diagnostic comparison
threshold. Clock, command sampling and effective-acceleration checks pass.
This establishes only the last refinement comparison for this one-second
mechanical trajectory, not general convergence, longer-flight accuracy or an
appropriate production step. It does not validate a neural controller.

The previous four-resolution report remains unchanged. New evidence and hashes
are in `reports/closed_mechanics_refinement.json`, checked by
`tools/check_mechanics_refinement.py`. Additional executable options are
`sixteenthstep`, `thirtysecondstep`, `sixtyfourthstep`; scales above two run only
the contact-plus-pulse pair with feedback enabled/disabled. No other controls
or physical parameters were changed during the refinement.

## Closed radial mechanics

`native/closed_mechanics_probe.cpp` adds rocket-to-body acceleration. For a
nonrotating radial cabin, body-frame effective gravity is world gravity minus
cabin acceleration, hence `-thrust / mass`. MuJoCo receives this acceleration
in mm/s². Both control position and cabin acceleration are sampled at the start
of the shared step. The supported thorax stays fixed in the cabin frame.
This uniform-field approximation has no rotation or tidal terms. It does not
implement a sensor or feed numerical rocket telemetry into a neural policy.

The new diagnostic starts with zero effective gravity, replacing the previous
Earth-gravity body fixture. It crosses feedback/contact/pulse interventions at
100 and 50 microseconds; the driven feedback pair is also run at 25 and 12.5
microseconds. `tools/check_closed_mechanics.py` checks 480,000 records, source
position sampling, clock agreement, engine recurrence and independently derived
`g_world - a_cabin`. Freefall gives exactly zero effective weight. Disconnected
contact and no-pulse cases match ballistic baselines. With contact and pulse,
acceleration feedback changes joint/slider motion and therefore rocket motion.

The final velocity effect rises from 0.01012359 to 0.01487404, 0.01746957 and
0.01849317 m/s as the step shrinks. The last change is still 5.535%; magnitude
convergence is **not established**. This is a material numerical limitation,
not evidence of a calibrated sensory/motor loop. Report:
`reports/closed_mechanics_causality.json`. Build with
`tools/build_closed_mechanics_probe.cmd`; executable arguments are model XML,
output CSV and optional `halfstep`, `quarterstep` or `eighthstep`.

## Live contact-to-thrust diagnostic

`native/contact_rocket_probe.cpp` advances the actual supported NeuroMechFly
MuJoCo model and radial rocket together at 0.1 ms. At the start of each step,
the passive slider's measured position sets throttle as `clamp(q_mm/0.3,0,1)`.
The 0..0.3 mm travel is an explicit engineering mapping. The same start-of-step
sample is held while both solvers advance; no end-of-step position is used
retroactively. No rocket state selects joint commands. The fixture applies a
fixed diagnostic joint pulse and verifies no actuator directly drives the slider.

Four one-second interventions cross enabled/disabled contact with pulse/no pulse.
`tools/check_contact_rocket.py` verifies all 40,000 records, shared clocks, exact
position-to-command mapping, engine lag and fuel recurrence. Disabling contact
makes the pulse trajectory bit-identical to the no-pulse baseline. Enabled
contact without the pulse also equals baseline. Contact plus pulse reaches
throttle 0.14070645 and changes velocity by up to 0.47649395 m/s.
Evidence: `reports/contact_rocket_causality.json`.

Build with `tools/build_contact_rocket_probe.cmd`; place the pinned MuJoCo `bin`
directory on PATH and run the executable with
`data/derived/contact_diagnostic/body.xml build/contact_rocket_trace.csv`.
This is one-way coupling only. The body retains diagnostic gravity and fixed
support; rocket acceleration is not yet fed back. There is no brain, calibrated
motor mapping, three-axis stick, vision, or landing in this diagnostic.

`native/rocket_vertical.h` implements the radial first curriculum stage in C++
FP64: inverse-square gravity, changing propellant mass, bounded throttle,
first-order engine lag, fuel exhaustion, and terminal first surface contact.
Engine force and integrated impulse are analytic for each held command;
altitude and velocity use RK4. Fuel exhaustion splits the step. Surface contact
is bracketed within the step, including descent followed by an upward velocity
reversal. Contact records impact velocity and time; it does not declare a
successful landing or simulate ten seconds of stability.

All quantities are SI. Parameters are caller supplied. Test radius 200,000 m and
mu 6.5e10 are diagnostic constants, not a verified KSP/Mun parameter export.
`advance_diagnostic` is explicitly fixture-only input; no runtime cockpit or fly
controller is connected. This API must not become an alternate command route
around physical controls in the integrated experiment.

Build with `tools/build_rocket_vertical_probe.cmd`, then run
`python tools/check_rocket_vertical.py`. Five independent checks compare against
adaptive SciPy DOP853, plus the vacuum rocket equation. The maximum component
error over these fixtures is 1.54e-8 (SI numerical values). Fuel-limited thrust
and contact time agree; the substep-crossing case detects impact even though
an unconstrained full step would finish above ground. Source and executable
hashes are in `reports/rocket_vertical_validation.json`.

This is not the final six-degree-of-freedom plant. Rotation, lateral motion,
landing gear/contact mechanics, body-frame accelerations, native environment
ABI, image capture, CUDA batching, cockpit command provenance, replay and KSP
calibration remain to be implemented. Event checks here are tested for the
listed radial trajectories, not proven for arbitrary high-energy pathological
states. No training, fly landing, or final mission criterion has passed.
