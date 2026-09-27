# Native body diagnostic

`tools/export_body.py` checks all FlyGym files against the acquisition manifest,
then uses the pinned 2.1.0 author implementation to compose NeuroMechFly. Python
is only the model builder. The exported XML and mesh bytes are hashed.

The initial diagnostic uses the author `ALL_BIOLOGICAL` skeleton in yaw/pitch/roll
order, author neutral pose, simplified meshes, and the default passive joint
parameters (stiffness 10, damping 0.5, armature 1e-6 in model units). These
simulation parameters are not claimed to be measured MaleCNS physiology.
The thorax is static; no free-body rocket acceleration is present yet.

`tools/build_body_probe.cmd` compiles a C++ executable against MuJoCo 3.9.0.
`tools/check_body_native.py` verifies the export hashes and runs 10,000 native
steps with a 120-second wall-clock bound. Initialization uses the neutral keyframe
once. The loop calls `mj_step`; it does not overwrite pose or velocity, supply a
trajectory, or drive actuators. Nonfinite state, solver warnings, or inconsistent
simulation time fail the diagnostic. The report binds the executable, runtime and
model hashes. A passing result only establishes that this passive body can run.

Executed result (`reports/body_native.json`): 126 DoFs, 69 bodies and geoms,
10,000 steps, 0.99999999999990619 seconds, zero warnings, finite state.
Windows MuJoCo failed to open absolute Unicode mesh paths during composition;
the builder therefore supplies original mesh bytes through MjSpec assets and
exports unchanged bytes with relative ASCII filenames. Native loading uses the
relative model path from the workspace, avoiding that path conversion failure.

This is not the cockpit model. Joint actuation, physical contact with passive
controls, sensor mapping, rocket-frame acceleration, and neural motor mapping
remain unimplemented. There is no brain-driven movement or video evidence here.

Model lengths use millimetres and default gravity is 9810 mm/s². Other unit
conversions must be established from source evidence before coupling rocket and
cockpit physics. Do not silently treat numerical masses or torques as SI units.

Builder runtime: Python 3.12; isolated dependencies under `build/body-python`,
`build/body-python-extra`, and `build/body-render-python`. These paths must not
be placed in a Python 3.11 environment: binary wheels target CPython 3.12.

## Bounded motor diagnostic

`export_body.py --actuated` exports a separate model with 42 leg motor actuators
selected by the author LEGS_ACTIVE_ONLY preset. Each has control and force limits
[-1, 1] in model units. These are explicit engineering test values, not identified
motoneuron physiology. Passive springs remain unchanged. The passive export is
preserved independently.

Build with `tools/build_body_motor_probe.cmd`, run with
`python tools/check_body_native.py --motor`. Two native states start from the same
neutral pose. The baseline receives zero input. The other receives command 2 on
`c_thorax-lf_coxa-yaw-motor` during ticks 2000 through 3999 (zero-based), to test
the configured saturation. No state is overwritten after initialization.

Verified result: maximum applied actuator force 1, maximum joint position
difference 0.097633885118314861 radians, zero warnings. All 10,000 recorded rows
are finite and have the expected clock; poses match exactly before the pulse;
the applied force matches the declared pulse and stays within bounds. Both
trajectories and applied forces are in `build/body_motor_trace.csv`, SHA256 bound
by `reports/body_motor_native.json`. This is an engineering intervention, not
neural behavior. It does not yet establish paw-to-lever causality or justify the
motor mapping. The CSV records qpos, not the full resumable physical state.

## Passive control contact bench

`tools/export_contact.py` extends the separate motor export with one slider.
Its pad lies 0.01 mm beyond the neutral claw mesh's maximum Y coordinate. The
slider moves along Y, has limits [-0.05, 0.3] mm, mass 0.001, spring 0.5 and
damping 0.002 in model units. No actuator targets the slider. An explicit
MuJoCo contact pair joins the original lf_tarsus5 mesh and pad; unrelated
collision pairs are not enabled. This isolated fixture is not a finished cabin.

Build `tools/build_contact_probe.cmd`, run `python tools/check_contact_native.py`.
Four native simulations cross the motor pulse with contact enabled/disabled.
Disabling contact uses mjDSBL_CONTACT on a separate model; no state is reset
mid-run. The slider starts at rest; its axis has no gravity component.
Only pulse plus contact moves it (maximum 0.042211934829454983 mm). The other
three conditions remain exactly zero. No warnings occurred. The complete
40,000-row slider/contact trace and model/runtime hashes are bound by
`reports/contact_native.json`. Finite values, time and the absence of pre-pulse
movement are checked independently from the CSV. These results establish the
local mechanical link, not a biological policy, grasp, rocket input or video.

## Persistent runtime

`tools/build_body.cmd` builds `fly_body.dll`. Its C ABI owns model and mjData;
`fb_advance` applies bounded joint inputs without resets or per-call allocations.
Invalid dimensions, NaN or out-of-range input are rejected before mutation.
Numerical failure poisons the handle until explicit reset. Control position is
read from the physical slider joint. No internal test pulse is generated.

`fb_state/fb_restore` use mjSTATE_INTEGRATION (including solver warm-start state).
These are trusted, same-model in-memory snapshots only. There is no portable
checkpoint format, model identity check or arbitrary-file validation yet; do not
load externally edited arrays. `fb_contact_normal` now exposes a named
geometry's contact count and summed normal force in model units, with the
solver's own evaluation time. For Euler `mj_step`, this evaluation is one
integration step behind the post-step joint position. Restore invalidates
the contact observation until the next advance. It is not yet a calibrated
mechanoreceptor signal. Twenty checks in `reports/body_abi.json` include
chunk equivalence, continuation, invalid-input immutability, contact
observation and post-restore cache invalidation.

Rust feature `body` supplies an exclusive, non-Send/non-Sync RAII handle.
`body-diagnostic MODEL OUTPUT` executes the explicit engineering pulse. All 100
recorded samples match the native contact diagnostic exactly; evidence is in
`reports/body_rust_comparison.json`. The existing CUDA build remains separate
from this diagnostic's `build/rust-body` target directory.

The updated Rust diagnostic reads both `control_pad` and `lf_tarsus5` contact
through the native ABI and rejects disagreement between their paired contact
counts, normal forces or evaluation times in this fixture. The new
`fb_contact_points` ABI also returns each contact's world position, a unit
normal pointing into the queried geometry, the full world-frame force on
that geometry, and normal-force magnitude; a capacity check rejects
truncation. This uses [MuJoCo's contact convention](https://mujoco.readthedocs.io/en/latest/computation/):
its solver normal points from the first geom to the second, with opposite
forces on the two geoms. The ABI adjusts signs by the queried geom ID.
`reports/body_rust_contact.json` records 100 joint/contact samples over one
second: zero contacts in the first 20 quiet samples, 19 contact samples
during the 20 commanded pulse samples, maximum sampled normal force
0.021067634134089977 model units, and a 0.0001-s observation lag. This
fixture does not establish a biological touch receptor, grip stability or
KSP control.
The complete one-second trace has 26 nonzero foot-contact samples, each with
one point and a unit inward normal. `reports/body_abi.json` passes 20 checks,
including empty contact geometry, point/aggregate force equality, capacity
rejection, opposite pad/foot force vectors and invalidation after restore.
Contact positions are model/world
coordinates; they are not yet mapped to a measured sensillum position.
The neural input remains disconnected. The published MaleCNS annotation has
many front-leg mechanosensory candidates, but neither a measured transduction
law from this tarsal contact force nor a specific `lf_tarsus5` receptor body
ID has been validated. Feeding this force into an arbitrary graph node would
make a closed engineering circuit without establishing a biological one.
For example, the [MANC sensory annotation study](https://elifesciences.org/reviewed-preprints/97766)
identifies `SNpp53` as candidate **trochanteral** campaniform sensilla; that
name alone must not be used as a tarsal-pad sensor assignment. A future
mapping needs the peripheral sensillum location, source body ID and a
force/deflection-to-neural-response calibration on the same sensory modality.

`tools/audit_foreleg_tactile_identity.py` verifies the pinned graph-node
annotation and finds 288 `ProLN` mechanosensory-bristle rows across 17 types.
Only 21 carry a MANC body ID, and none of the checked annotation columns
names a tarsomere or `lf_tarsus5` (`reports/foreleg_tactile_identity.json`).
This is an annotation coverage result, not proof that no tarsal receptor is
among the 288. No individual ID is approved for contact transduction.

As a separate physiological target, [Tuthill and Wilson (Cell 2016)](https://www.sciencedirect.com/science/article/pii/S0092867416000544)
found that a single spike from an identified *femur bristle* produced a
reliable central EPSP at about 3 ms latency in their recorded cell classes.
This can challenge a future bristle-to-central synapse and delay model once
source-to-target identities and stimulation/recording operators are matched.
It does not calibrate force on this tarsal geometry or identify one of the
MaleCNS candidates above.

## Native diagnostic video

Build `tools/build_contact_video.cmd`, then run
`python tools/record_contact_video.py`. The native MuJoCo renderer records four
independent physical worlds: contact off/on crossed with a diagnostic joint
pulse off/on. The pulse is +1 from 0.5 to 1.5 simulated seconds. No actuator
targets the passive slider and no pose animation runs during integration.
The thorax is fixed; this is an isolated contact fixture, not a finished cockpit.

`build/contact_diagnostic.mp4` contains 90 frames at 1920x1080, 30 fps, covering
30,000 physics ticks (3 seconds). Only the contact-plus-pulse world moves the
slider: maximum 0.042507060983613724 mm and 10,642 contact samples. The other
three worlds remain at zero slider displacement. The observed OpenGL renderer
was Intel UHD Graphics; this result is not an RTX or real-time benchmark.

`reports/contact_video.json` binds the executable, model export, MP4 and frame
state journal by SHA256. `build/contact_video_frames.jsonl` stores 360 physical
qpos snapshots, with panel, tick, simulation time and joint command. This is a
frame journal, not a full-tick checkpoint or complete neural experiment log.
Frames are sampled directly from physics without interpolation; a blocking RGB
pipe to ffmpeg provides backpressure. Labels explicitly say diagnostic/no brain.
The MP4 was decoded and a frame visually inspected for anatomy, pad and labels.
This video demonstrates contact mechanics only: no neural motor mapping,
learning, rocket, KSP or connectome visualization is present.
