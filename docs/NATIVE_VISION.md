# Native pixel sampling

`native/retina.h` defines the C ABI for a fixed ray lookup into an
equirectangular panorama. `fv_create` validates unit directions and precomputes
four pixel offsets and bilinear weights per ray. `fv_sample` allocates nothing,
accepts only an RGB image and writes RGB samples. There is no telemetry input,
decision network, reward, neural stimulation or actuator output in this module.

Coordinate contract: +X forward, +Y left, +Z up. Panorama pixel centers have
longitude `2*pi*((x+.5)/width-.5)` and latitude `pi*(.5-(y+.5)/height)`.
Longitude wraps across the panorama seam; latitude clamps at the outer pixel
centers. Input is finite nonnegative linear RGB32F, not gamma-encoded screenshot
bytes. Width and height must both be at least two. Buffers must be disjoint;
invalid dimensions, nonfinite/negative pixels and overlapping buffers are
rejected before any output mutation. A handle owns its copied lookup table.

This is engineering point sampling, not a compound-eye acceptance kernel or
photoreceptor model. RGB channels are not R7/R8 spectral responses. It does not
establish camera origins, body registration, MaleCNS identities, optical blur,
adaptation, neural superposition or spike generation. No brain input is enabled.

Build the standalone DLL with `tools/build_retina.cmd`. Run
`python tools/check_retina.py`: an independent Torch CPU grid sampler is compared
on all 1,709 source rays plus seven axis/seam/pole directions, for constant and
random images at three resolutions. Maximum difference is 1.1920928955078125e-7.
An analytic column/row image separately checks forward, left, right, rear, up and
down conventions. Invalid-input tests verify unchanged outputs and alias rejection.
Evidence: `reports/retina_native.json` binds source rays and native DLL hashes.

Rust feature `vision` statically builds the same C++ source and exposes an owning
non-Send/non-Sync handle in `src/vision.rs`. The Rust wrapper checks slice lengths
and uses separate borrows for input and output. Its regression checks lookup
lifetime after the ray vector is dropped, repeated sampling and rejected input.
Command: `cargo test --offline --features vision --target-dir build/rust-vision`.
No live camera, brain or body runtime is coupled by this module yet.

The sampler is now coupled to persistent native photoreceptors by Rust in
`VISUAL_INPUT_PIPELINE.md`. That executed fixture uses two synthetic rays and
explicitly assumed RGB-to-photon coefficients. It does not establish calibrated
fly optics or enable MaleCNS anatomical input assignments.

`fv_sample_oriented` rotates body-local rays into panorama/world coordinates
with an explicit row-major right-handed rotation for each image. It does not
change the handle or receptor state. Invalid/reflection matrices leave output
unchanged. An independent NumPy oracle checked identity, 90-degree yaw and
45-degree pitch for 80 rays on a nonuniform 37x19 RGB image; maximum absolute
error was zero in that fixture, and identity matched the static sampler
exactly. See `reports/retina_orientation.json`. This tests geometric image
sampling, not a measured alignment of FlyMimic eyes and MaleCNS cells.
