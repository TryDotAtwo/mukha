# KC-to-MBON contact restoration in current MoLab sandbox

On 2026-10-05 foreground cell `restore_mb_contact_shards` restored all five immutable contact shards directly from verified HF receipts. The original report was restored at immutable commit `633002a94ba6f474f65a482a69549623021ac7b3` and its recorded shard receipts drove restoration; source scans were not repeated. Restored row counts: 447723, 6449, 7758, 1710, 0; total 463640. Coordinates are int32 x/y/z for both pre and post, with body IDs, confidence and primary_post fields. This checks restored byte identity and table coverage; it does not yet prove coordinate units or classify gamma compartments.

The fresh sandbox has NumPy and PyArrow but neither cloudvolume nor compressed_segmentation. A source-pinned volume decoder/runtime closure is needed before sparse atlas sampling. All data remain in MoLab; no local data download or computation occurred.

Verified private dataset `TryDotAtwo/faithful-fly-artifacts`: stage source commit `497714958f7e279474eaa54f756b3e9605d16005`, manifest `19b0b75bb9e1bb4bd9291b12e94fff882146bf627f6623a207585e9eef2a20a5`; final restoration report commit `7fad5cfae03c638a016d8546ca472a05ae1b2db1`, manifest `5ac11dca521f94d37d1f5c5de0912c3fe7b607e6b81c19ac29707b09bcab4f75`. Contact mask admission and biological learning remain open.
