# Complete DAN synapse-point selection — 2026-10-05

All download, integrity checks and processing ran in MoLab foreground cells PzKx and zAHh. No dataset downloaded locally.

Full MaleCNS syn-points minconf0.5 source acquired:
- GCS object v1.0/connectome-data/flat-connectome/syn-points-male-cns-v1.0-minconf-0.5.feather
- generation 1780494991007477, 13061489098 bytes
- size and GCS CRC32C verified
- immutable input HF commit a9c46d71aa5c7e8b05bffa2f1160fc075958ea81
- input manifest b6253f60c131df400be543152940058a72115aa3fdeb76f664f45200086793f1
- acquisition report HF cbfdbe017da24437abd6b226ba472afd96397f7c; manifest a7633dfad8e5f4361bbee6261d615d2f25aba756bcca7ff3296d130454cee194
- google-crc32c 1.7.1 cp313 manylinux x86_64 wheel verified against PyPI SHA256 and archived BEFORE import: HF 5fda5b34bbb6448f611ef4781413a0240bc3c10a.
Full source archived and verified before dependent selection.

All 5455 Arrow record batches scanned; 357489383 source rows. Exact body selection includes four PPL101/PPL102 candidates, both pre and post, with all original columns preserved.

| body | annotation | PreSyn | PostSyn |
|---|---|---:|---:|
| 11327 | PPL101(y1ped)_R | 2604 | 18414 |
| 11900 | PPL101(y1ped)_L | 2433 | 21518 |
| 11618 | PPL102(y1)_L | 1689 | 10192 |
| 13428 | PPL102(y1)_R | 1636 | 9089 |

Selected 67575 points, including 8362 PreSyn. Zero duplicate kind+x+y+z rows. This exhausts the selected bodies in the source-defined minconf0.5 table, not all biological release sites.

Selection source HF afbc235f08971c1ae9314c0ae8e174c9d4e2d071; manifest 9d3cb02075aead924f6fb50c36e55ca6c0090a061f818794e9f113ebefa98b39.
Selection result HF a9d36c843814ce8a3f497a197df053d64d900c6d; manifest c3f39e692a67acca13bbbaec942f1d51b8654f5c2402db0b0bc0ef930421896e.
Remote full source /tmp/fly-full-synpoints-20261005
Remote selection /tmp/fly-dan-synpoints-selection-20261005

Open gate: sample actual PreSyn coordinates against atlas gamma1, pedc and MBON contacts, retain missing coverage, compare bilateral territory; independently validate physiology. No contact mask/plasticity/learning admitted.
