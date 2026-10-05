# Native release sanitizer environment limitation

Live foreground MoLab inspection found no installed Compute Sanitizer. Availability receipt: HF f69991d61f50e1409652d80fc245c37a87677096, manifest 60c2004c7b520235a8188593228740c8add523788f21294a9410ce5e3794ee70.

Two official NVIDIA distributions were downloaded only in MoLab, verified against their respective published redistributable manifests and archived before extraction/use:

- CUDA 13.0.2 sanitizer component 13.0.85: HF 01bb17ae78f216df60d230f417e6783e64071edd, manifest 48cfba8115d8456bb60458a5e47638996408b1e13d4482a8f88d632498b86455.
- CUDA 13.2.0 sanitizer component 13.2.23: HF ba254517e318da80af097653ba5440b7c9239a33, manifest 8fba7ca26fbb570f0e16448327381bdfd0be238e5eda3e2e49f5f3f023edc57c.

Both memcheck attempts terminated with exit 86 and Device not supported before any model kernel executed, followed by cudaErrorUnknown on initial cudaMalloc. Logs/reports were immediately archived. Version 13.0.85 failure: HF b7debf38a2aa81a74c948e9e0b94d201690e79da, manifest d3cabee85d45a395e5c0c2e1818e985b813e436302e6ccd59fa0b79eb932b076. Version 13.2.23 failure: HF c41fdc165faac4694c141ee0f9902edd73cca51c, manifest f2117114b89f794e5ba22609cf64ca13fad44e582ff5d8c26af49981b73bbe06. No memcheck pass or kernel memory defect is established. Initcheck/racecheck/synccheck were not run because memcheck did not admit execution.

A subsequent uninstrumented control on the exact same immutable native build passed the original mixed-input state/reset/chunk/invalid-configuration fixture. GPU reports NVIDIA RTX PRO 6000 Blackwell Server Edition, driver 595.71.05, compute mode Default, virtualization None. This establishes that ordinary execution remained operational after the terminal attempts. It does not explain the unsupported-device error or replace instrumentation. Do not infer vGPU as the cause.

Complete control source/report/log/arrays HF a2b46fc45bd7606f9afbe5578b775a3ff3eda76d, manifest 2779f8832f5ba2fe32e9198687227ad3f3005d77487146d9d6f1df421735cc29; all remotely verified. Durable sources: remote_work/sanitize_native_release.py, sanitize_native_release_v2.py, sanitize_native_release_v3.py and check_release_gpu_after_sanitizer.py, source closures preserved on HF.

The sanitizer gate remains open. It requires a MoLab GPU/session configuration that supports Compute Sanitizer instrumentation, or a separately justified compatible toolchain in this session. Do not keep retrying identical unsupported configurations or switch to local execution. Continue independent checkpoint/source work; full-graph release admission and learning remain disabled. All original project gates remain open.
