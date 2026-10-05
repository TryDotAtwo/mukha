# MaleCNS SWC acquisition: shards 0000–0100

Verified in MoLab on 2026-10-05. Private HF dataset: TryDotAtwo/faithful-fly-artifacts.

- 103,424 distinct SWCs / 167,216 graph bodies; coverage_fraction 0.6185054061812266.
- 5,760,694,430 verified source bytes; 172,493,395 SWC nodes.
- 7,537 multi-root files retained; zero duplicate body IDs.
- Exact planned ID/generation/byte-size/MD5 reconciliation passes; all defined structural checks pass.
- Next shard 0101; 63 planned shards remain.

## Immutable evidence

| Artifact | HF commit | Manifest SHA256 |
|---|---|---|
| Union source closure | 2409ad701f8a0e294072e3a39834c7c662f9d947 | 2eec4395d11269797c75607cbd4983454d6360e16708713c4ebdf2b533dd5edd |
| Union report | 4b5574fef9c1eadb08ba63ed24904db02fe42480 | 6a4d3a120441ee55dc44b94942d757232ea1c71c4b1474c65684aae2356a740b |
| Shard 0100 acquisition | 85ff369d171bcbe7a441cd281352853293f966cc | 54398bc476d14a3c68456fd6fc081beee7246ef5b5329466392a45e27b2b718d |
| Shard 0100 audit | ae41a2944b7c2648b40c2e7a8afdfcaf0d7caef2 | fc2692f23b5a0ed533bc71f4c43b9e061f1b9440298d6159580a333b7a9e956d |

Manifest paths are manifests/<SHA256>.json at the listed immutable commits. report.json contains all 101 per-shard receipts. Union computation traverses the predecessor chain, verifies manifest/object SHA256 and sizes, and reconciles each entry with pinned planned inputs.

Shards 0097–0100 each contain 1,024 files. Nodes respectively: 729,547; 776,707; 726,814; 757,500. Multi-root files respectively: 71; 72; 84; 87. All pass basic structural auditing.

## Execution and limits

All computation and artifact publication ran in the visible foreground MoLab notebook, one heavy operation at a time. Every source closure, acquisition and audit was published and remotely verified before dependent work. Local operations were source-text editing and transport.

The union SSE stream ended prematurely. The existing cell was observed through marimo code mode: idle, errors=[], with the complete verified report receipt. No computation was restarted.

Actual sandbox quota remains unknown; virtual statvfs is not proof of a 50 GiB reserve. Staging is bounded and HF-recoverable. Source-byte and topology checks do not establish morphology completeness, EM segmentation correctness, synapse-site geometry or biological fidelity. Historical local/candidate skeletons are excluded. Geometry admission false; plasticity and training disabled.

The full WORK_PLAN objective remains active: full MaleCNS provenance and geometry, validated physiology and local plasticity, physical embodied cockpit interaction without hidden autopilot, native runtime, three independent trainings each with at least 90 successes among 100 withheld Mun starts, and synchronized reproducible recordings.
