# Public scientific data snapshot

The release `data-2026-09-27` contains 12,506 local scientific files with
4,989,372,920 uncompressed bytes from `data/raw`, `data/derived` and
`data/reference`. It excludes 29 Python cache files and two local KSP logs.
Historical files available only in the private Hugging Face archive are outside
this snapshot; see `HF_ARCHIVE.md` for their receipts and access limitations.

Download from https://github.com/TryDotAtwo/mukha/releases/tag/data-2026-09-27
or use:

```sh
gh release download data-2026-09-27 --repo TryDotAtwo/mukha --dir download-data
```

The files are ZIP64 archives. Check these SHA-256 digests before extraction:

| Archive | SHA-256 |
| --- | --- |
| mukha-data-raw.zip | 3c122f2bcf3a74cd3c983eabc1a4917cef71e4aafd6495f06826fa23a2aad42a |
| mukha-data-derived.zip | 55c589a9fcf8e186df0a947c60fabe9a942d213c8f7acb5ee1fa1cb9f9737663 |
| mukha-data-reference.zip | c2b11df09093d4e5be83e96ead508e240dcd5614939bcbba35da07b0bac6cb4f |

Extract into a fresh clone: each archive entry already starts with `data/`.
Do not overwrite existing experiment outputs. `data-manifest.json` lists the
size and SHA-256 of each file; verify them before running an experiment.

The export checked that archive names and uncompressed sizes exactly match all
12,506 manifest entries, with no duplicates or parent-directory traversal.
Archive hashes establish identity, not biological validity or full historical
coverage. Upstream licenses and source notices remain in force.
