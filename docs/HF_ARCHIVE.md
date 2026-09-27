# Hugging Face artifact archive

Calculations, hashing, builds, uploads and restoration run in Molab. Windows
holds only source and orchestration code.

Private dataset: `TryDotAtwo/faithful-fly-artifacts`.
Authentication: `HF_TOKEN` in Molab Secrets (`.env`), scoped to this repository.
Never copy credentials into notebook source, artifact manifests, or logs.

`tools/hf_artifact_archive.py` publishes explicitly enumerated files as
`objects/<sha256>`, verifies remote LFS SHA256 or Git blob identity, then commits
the manifest. The receipt pins the immutable HF commit. Restoration verifies
the manifest and every downloaded file and refuses to overwrite differing files.

First recovery archive:

- Commit: `bfd5754bc9ae67d13e91567cc59e5c48d2b65fa8`.
- Manifest: `manifests/37ee090b455924c7762512dfc9fa05ba8d3f2694473964ba6d791971e01b1801.json`.
- 391 file paths; 313 distinct content objects.
- This is a **partial recovery**, not a full model/training checkpoint.
- Full roundtrip passed in a fresh Molab directory: all 391 files, 1,254,254,578
  bytes, downloaded from this commit and SHA256 verified.

The September 16 Molab sandbox loss left 329 cache containers (~1.07 GB).
Exact byte-literal extraction matched 383 of 749 latest manifest paths.
The archive additionally includes verified available files, source recovery code,
archive tooling and the loss report. Missing original recordings cannot be
described as recovered; they must be reproduced from pinned sources and inputs.

The old marimo cache remains supplementary. In-session `CACHE_VERIFIED` messages
do not establish cross-session persistence. Do not split or disguise data as source
to evade platform limits.

Before long experiments, publish a complete input/source manifest. At announced
checkpoint boundaries publish the completed immutable checkpoint and its receipt.
Resume only from receipts whose referenced objects have passed SHA256 validation.
Do not upload a checkpoint while simulation is mutating it.

No-network contract tests: `tools/check_hf_artifact_archive.py` (run in Molab).
They cover traversal/symlink rejection, remote digest mismatch before manifest
publication, byte-exact restore, refusal to overwrite, and private-repo enforcement.
They do not substitute for a real HF roundtrip.

## Complete graph recovery archive

Commit `b9cb4884e14c39a2e0e6d0781e8a7d743d64bbf0`, manifest
`manifests/82d3d7ae1569326ce420cb7bf31754ad4a498086c25470a3ba11f6e64eba0405.json`.
23 file paths / 22 unique objects. Contains all three pinned MaleCNS exports,
all eight rebuilt CSR/data files, updated graph manifest, provenance reports,
six reconstructed native source files and graph builder. Server object hashes
verified. Both archives were subsequently restored into a fresh Molab sandbox:
391 and 23 paths respectively passed byte-count and SHA256 verification.

All eight rebuilt graph files matched their pre-loss byte counts and SHA256.
The graph retains 167216 candidate objects, 25587572 edge rows and 124193283
contacts from 151856684 source rows. These are graph reconstruction checks,
not biological validation.

The following additional runtime inputs were regenerated with exact previous
hashes but were **not archived before the next HTTP410**:
`brain_body_graph.bin`, `lamina_native_photon_v1/graph.bin`,
`image_lamina_probe_v1/rays.bin`, `visual_fullgraph_bridge_v1/outgoing.bin`,
`recurrent_lamina_bridge_v1/incoming.bin`. Recipe:
`build/molab_restore_runtime_inputs_v3.py`.

Visual library reconstruction reached a linker failure: CUDA static libraries
exist in `/tmp/fly-cuda-13.1.1/lib`, but nvcc did not find them by default.
Author VisTrans sources passed hashes. Planned fix and remaining linking recipe:
`build/molab_link_visual_runtime_v3.py`. That request received HTTP410 before
execution. A later fresh-session recovery fixed the library search paths,
materialized the source bundle and completed the photon, retina, continuous
CNS and remaining-route builds. VisTrans build identity:
`8f3eae84b1b13162b068dc72b6dc3ea1bcc42e017addd3c1be5e1174c5a12e16`.

The 100 ms remaining-route **off** fixture then matched all six historical
outputs byte-for-byte. The **on** case emitted an active heartbeat, after which
the SSE stream ended without a completion event; independent discovery returned
HTTP 410. Its result is unverified. Neither these new runtime inputs nor rebuilt
binaries reached HF before that loss. No new biological validation is claimed.

Recovery must now archive rebuilt runtime inputs and binaries before launching
the regression, and archive each completed case separately. This preserves
completed work even if the next case loses its sandbox. Keep the main notebook
tab available across turns; browser-tab lifetime is not proof of sandbox health.

## Runtime archive before regression

Commit `1b729c9f601489275c18fea50b27a11869403501`, manifest
`manifests/4d78821cdb940d88ae598c5701d18548224a4b7461956896a3342dfe90f85f3e.json`.
130 paths, 124 unique objects, 319583544 bytes. Remote object hashes verified.
Fresh-directory download and SHA256 verification passed for all 130 paths.
Includes restored runtime inputs, native sources, tools, shared libraries and
remaining-route executable. It is neither a training checkpoint nor a complete
CUDA SDK. This receipt was published before the new GPU regression.

The subsequent **on** fixture completed all 1000 neural ticks (100 ms), with
all six outputs byte-exact against the historical fixture. Its eight files
(six outputs, log, report) were archived and server hashes verified:
commit `4b6eaaf8fa14109990c79e4e76ef42cbe387c544`, manifest
`manifests/f66412808ece08a13743319c04d4fbc412cd057e68d0f85bb02230be51d77ec1.json`.
This establishes numerical recovery of the two original short fixtures across
the two sessions. It does not validate physiology, learning, or rocket control.

## Counter-RNG checkpoint replay (2026-09-24)

The compact [Molab recovery notebook](https://molab.marimo.io/notebooks/nb_6tmwBC8Dq1922wWciRPctp) ran on an NVIDIA RTX PRO 6000 Blackwell Server Edition. It downloaded a pinned binary (SHA256 `179130e1eb50e9de1bac9df4c52f27a1efc379167cf5a40b6a30267afc090a31`) and input manifest (SHA256 `0d9a3984bf89f1fedf41e13a27de4d52e7c804d6b891e988e1b2232c95ffd39c`). The one-receptor, ten-tick replay passed exact same-process, split-call and fresh-process checkpoint continuation checks and rejected an old checkpoint version before mutation. This does not establish biological behavior, training or landing performance.

Five replay files were published at commit `23b6f0d34d2600ac756c874a590e8e1457af6cd5`, manifest `manifests/5c6722539249b905828ff06dc89910757bb96bd7a66d0ccfd95719f73ca904a8.json`. Four remote content objects were verified. A restore into a fresh Molab directory downloaded and SHA256-verified all five paths at that commit.

## Shiu reference source recovery (2026-09-24)

The current Molab session lacked the original Shiu source files. Four files
(`model.py`, `figures.ipynb`, completeness CSV, connectivity Parquet) were
downloaded there from author commit `91bdd1e7dcf193f3e7ca5a8933497fcef63b7960`.
Each matched the pinned byte count and SHA256 in
`reports/shiu_reference_sources.json`. They were uploaded to the private HF
dataset at commit `a2fdddf64fdabf86e91867d8f121f902d5b9afea`, manifest
`manifests/5059135bde29edf968e58ccf85ff5d0776364120eec6fd2d8bbe624a35c8f7b0.json`
(four files, 89,733,684 bytes). The manifest path is visible at the pinned
revision. A fresh-directory archive restore remains to be checked. Brian2
2.9.0 failed to import against the session's NumPy (`ndarray.ptp` removed);
updating to Brian2 2.10.1 via the Molab package UI restored successful import.
No new biological run is implied.
