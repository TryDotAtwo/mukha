# Image-driven native receptor path

`src/visual_input.rs` connects the native C++ point sampler to persistent CUDA
photoreceptors under Rust orchestration. Its advance interface accepts only a
linear RGB32F panorama and a duration in 0.1 ms ticks. It has no telemetry,
controller, reward or direct actuator input. Sampling and per-ray coefficients
produce photon rates; the verified receptor dynamics evolve without reset between
images. All buffers used by the advance path are preallocated.

This path currently requires `AssumedOptics`: explicit rays, nonnegative RGB
coefficients in photons/s per linear intensity unit, and a nonempty assumption
note. There is no built-in luminance conversion or arbitrary R7/R8 channel rule.
**These coefficients are engineering assumptions, not measured fly spectra.**
The example has two synthetic forward/rear rays, not MaleCNS neuron IDs. It does
not enable the unresolved real optical registrations in `VISION_MAPPING.md`.

The 8x4 example in `configs/visual_input_fixture.json` contains the actual four
images: darkness, a forward red patch, a rear red patch, darkness. The explicit
fixture conversion maps red intensity 1 to 100,000 photons/s. Sampling produces
[0,0], [100000,0], [0,100000], [0,0]. The corresponding receptor depolarizes when
illuminated. Closing the input does not reset membrane/adaptation state.
This establishes image causality within this component, not faithful fly vision.

## Time, recording and continuation

The fixture runner records every image's raw float32 little-endian SHA-256, frame
number, simulation tick and all nine receptor state rows. The input JSON retains
all pixels. The native receptor model is created once per episode. No scripted
pose, controller trajectory or output waveform is used.

Pipeline checkpoints wrap the complete native state with optical/source identity,
frame count, payload length and SHA-256. A changed optical configuration or
corrupted wrapper is rejected before restoring the native state. Scratch sample
and rate arrays are overwritten before use, and do not need serialization.
The wrapper allocates one complete checkpoint buffer and writes the native
payload directly into it, avoiding another full-population copy.

Checkpoint files are content-addressed and published before the report, so a
failed report update does not overwrite the previous referenced snapshot. The
underlying Rust file writer's atomicity limitations still apply. This snapshot
does not include a body, scene, rocket or CNS; future coupled checkpoints must
save those and the environmental clock too. Different Rust compiler/build
configurations are not yet cross-validated.

## Executed evidence

`reports/visual_input_fixture.json` records 2,600 ticks across four images. A
snapshot after frame 2 (tick 1,100) was restored in a separate process using
`visual-resume`; all final snapshot bytes have the same SHA-256 and all recorded
final states agree. `reports/visual_input_resumed.json` records that continuation.
`tools/check_visual_input.py` independently checks source/configuration identity,
input/pixel hashes, analytic photon rates, directional light responses, snapshot
metadata and the final-state hash. Evidence: `reports/visual_input_verification.json`.

Four Rust tests passed with both `vision,photon` features: optical ownership,
photon state/checkpoints, atomic checkpoint files and the integrated input path.
Invalid images and changed optical configurations preserve live state on rejection.
Native components retain their earlier independent reference/sanitizer evidence;
this test is not a new full-CNS or full-retina sanitizer run.

```powershell
$env:PATH = (Join-Path (Get-Location) 'build') + ';' + $env:PATH
cargo test --offline --features vision,photon
cargo run --offline --features vision,photon -- visual-fixture configs/visual_input_fixture.json reports/visual_input_fixture.json
$r = Get-Content reports/visual_input_fixture.json -Raw | ConvertFrom-Json
.\target\debug\faithful-fly.exe visual-resume configs/visual_input_fixture.json (Join-Path 'reports' $r.checkpoint_file) reports/visual_input_resumed.json
python tools/check_visual_input.py
```

Prerequisite: build the CUDA receptor DLL as documented in `PHOTON_NATIVE_API.md`.
Remaining work includes radiometric/spectral calibration, acceptance angles,
MaleCNS registration, live cabin imagery and graded full-CNS coupling. RGB images
alone do not establish any of those properties.

The image frame may now carry an explicit `local_to_world` head rotation.
`VisualInput::advance_image_with_pose` rotates the same local rays before
sampling each panorama; the matrix is recorded with the frame, so replay
supplies the identical pose sequence after checkpoint restore. A synthetic
two-ray fixture holds the bright image fixed while yawing 180 degrees:
receptor photon rates switch from `[100000, 0]` to `[0, 100000]` photons/s,
and the receptor membrane responses follow. Same-process and fresh-process
continuations have identical full final-state hashes. See
`reports/visual_head_pose_verification.json`. No real body pose stream,
MaleCNS optic-column registration, spectral calibration or full-CNS visual
drive is established by this fixture.

`tools/build_visual_body_pose_fixture.py` additionally reads the published
FlyMimic `default-pose` head transform through MuJoCo, then applies a prescribed
180-degree yaw to the model's thorax root and reads the transformed head
matrix. The measured matrix composition error against world yaw times the
source matrix was zero. Those two MuJoCo matrices, recorded per frame, drive
the same synthetic fixed-image two-ray visual path: photon rates switch
`[100000, 0]` to `[0, 100000]` photons/s, receptor voltage dominance swaps,
and fresh-process continuation has the identical final snapshot. See
`reports/visual_body_pose_source.json` and
`reports/visual_body_pose_verification.json`. FlyMimic's head is rigidly
attached to the thorax in this source model. The root yaw is a prescribed
coordinate intervention, not simulated flight, measured eye optics, or a
MaleCNS cell-to-ray registration.
