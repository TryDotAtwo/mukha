# MaleCNS SWC union through shard 0104

Verified in MoLab on 2026-10-05. Private dataset TryDotAtwo/faithful-fly-artifacts.

107,520 / 167,216 distinct SWCs; coverage_fraction 0.6430006697923644. Source bytes 5,860,014,367; SWC nodes 175,512,911; multi-root files 7,855 retained. Zero duplicate body IDs. All defined structural checks pass. Exact planned body-ID/generation/byte-size/MD5 reconciliation passes.

| Artifact | HF commit | Manifest SHA256 |
|---|---|---|
| Union source closure | 6e4d5a86cfc4246bd3142ca9db813334c95bd1dd | e1a99012c6f1e8201a08e6c6c0d1abf36fa96ad2a4003b05f76f864fbd9894db |
| Union report | 34690770150428b9b5669869ae9fac5ef5c5eb9a | 5a84c04ca2eef76cf8deeeae8455578a4667020a7282e61af217a04f36e45d0c |
| Shard 0103 input | 03bf9a3380fd7dda05e28b36618199089041a1ce | 8646df6115ea97b76f70f0a483ed2f5eb2022d232cb264c86c87dbf3c33e2a76 |
| Shard 0103 audit | 39eac755d5cf88eef2e6f41856e4abd136ad1e66 | f8814e69e3cdc48181dcb7747d9fd8a883acc50fef0f149cfaac3bf3ed02d09f |
| Shard 0104 input | 12357cc9b056e5f0741a128ff815e95bc69596ea | ae8fb8132c9654bd09105cbabb4194373dfe4a07d637f72e5972e88ec0fdbca2 |
| Shard 0104 audit | 1d522f598a234dab5f8ab6b54d705de683faff4b | 3c1528eb10adccf03d25e57ed6f85671643e83d34099365af61702eca7c3e9b1 |

Manifests are manifests/<SHA256>.json. report.json contains all 105 immutable predecessor-chain receipts. Each manifest/object SHA256 and size is verified before reconciling the planned entries and computing the union.

## Recovery evidence

The previous recovery transport handle was absent. An authoritative code-mode observation found cell YVks interrupted during shard 0103 download after at least 960 completions; no interrupt cause inferred. Original recovery closure HF 2c158ea4ea10f281bec57fcffac8b60a7fd5a2c9, manifest 31e69d92afa37142ee1df272fc85f6cbfc740e2dc40fa75bd082e641be73e17a, was restored in MoLab and all four original source/input files matched SHA256. Resumption closure HF d4ee8fa8c364d6af1369b39638a73aa7cf873467, manifest a9edfce4613706ad3f07f854c8520d46277de4ae4a722ac2653a8e02542ed9e0, was published before input processing. Existing cached SWCs were rechecked against byte count and MD5 rather than redownloaded. All 1,024 files passed; acquisition took 0.823936492 seconds. Audit: 786,371 nodes, 94 multi-root files, structural pass.

Shard 0104 completed normally: 1,024 files, 763,141 nodes, 76 multi-root files, structural pass. Each completed input archive and audit was published and remotely verified before dependent work.

Next shard 0105; 59 planned shards remain. All computation, verification and publication were in visible foreground MoLab cells, one heavy operation at a time. Local work was text editing and transport. Actual sandbox quota remains unknown; virtual statvfs does not prove the reserve. Staging remains bounded and recoverable on HF.

Source-byte/topology verification does not establish complete morphology, EM correctness, synapse-site geometry or biological fidelity. Historical local/candidate skeletons excluded. Geometry admission false, plasticity and training disabled. The full WORK_PLAN goal remains active: full MaleCNS provenance and geometry, validated physiology/local plasticity, physical embodied cockpit control without hidden autopilot, native runtime, three independent trainings with at least 90/100 withheld Mun successes each, and synchronized reproducible recordings.
