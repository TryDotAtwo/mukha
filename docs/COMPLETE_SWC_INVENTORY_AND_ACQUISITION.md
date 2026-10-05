# Complete published SWC inventory and MoLab acquisition

The missing historical compressed inventory was regenerated entirely in foreground MoLab from the official GCS object-list endpoint. All 212 metadata pages were archived as fourteen completed segments, each remotely verified before proceeding. The exact 167216 graph body IDs were restored from immutable HF and separately archived before reconciliation. Current listing contains 211573 SWCs; all 167216 selected graph IDs have an object, with no missing IDs and 9034068018 published source bytes, matching the historical total. Generations, sizes, MD5, CRC32C and object names are preserved. This proves current generation-pinned availability, not acquired or biologically complete morphology.

Complete inventory and 164-shard plan (1024 selected bodies per full shard) HF 965d416f6ed49f2b856dca6b36d5e51a772e6c6d, manifest 1ea8b4678a0ee3b48104f9076e6d6ff6f7e160ccd51808e8f2bf930e748d1ea9. Inventory SHA256 b6fb9190b4b6801cb639e129e859fc8d0b1e8fca0538d09a3436bd4a5c26476e. The plan retains all metadata segment receipts. Source closure HF 97c4da4f67c705eb396ea038b081f7c6b5dd96a0; graph identity closure 6d5f1dbc597e1120488f4a57a1abf9c54148be17. All remotely verified. Source/transport: remote_work/regenerate_complete_swc_inventory.py.

## First completed source shard

Shard0 acquired all 1024 generation-pinned files with zero source errors in 18.404804691999743 seconds using eight foreground workers. Each source size and MD5 was checked; per-file SHA256 and generation ledger were published with the immutable source tar before structural processing. Source shard HF 811a855b377f7951c75a48e5f9f722cf86d2f6c6, manifest bfc527f15ee2cd5c1cfa473a41a383be4109664661362e57cd41cf0aa237710f.

The pinned existing auditor inspected 11461411 SWC nodes. Zero empty, malformed, duplicate-ID, missing-parent, nonfinite or cyclic files under its defined checks. There are 163 multi-root files, retained explicitly; no zero-length-edge files. This covers 1024/167216 (0.6123815902784422%) of the selected population in this MoLab acquisition family. Historical local files and six anatomical candidate SWCs are not added to this fraction without exact union verification.

Completed structural audit HF 2d133b13bdeadccca2d74b6e58fab6006617c815, manifest 0847094f9e7472dbc6ea200aefc57d2fb6381f9be1a5f62b57acbf257f431f95. Source/auditor/shard-plan closure HF 36f99ce872eca8b1e47f32239c038e61cb729e51. Transport: remote_work/acquire_complete_swc_shard.py. No local data or result download and no local computation.

## Storage and remaining boundaries

MoLab statvfs reports a near-2^63 free-byte value. The plan's mechanically computed disk_admitted=true is therefore not proof of actual sandbox quota or the required 50-GiB final-asset reserve. Only bounded first-shard staging and successful immutable publication are measured. Do not use this virtual number to admit unbounded accumulation. Future stages must retain bounded shard working space and verified HF recoverability, with any cleanup limited to their own completed published MoLab files.

163 source shards remain in this family. Continue exact plan order with immediate source/archive/audit receipts before the next shard. Structural checks do not establish coarse SWC morphological completeness, EM quality, actual synapse placement or whole-CNS geometry admission. Physiological calibration, local plasticity, embodied visual/contact control, full native performance, three training seeds, KSP evaluation and recordings remain required. Learning remains disabled and all original gates remain open.
