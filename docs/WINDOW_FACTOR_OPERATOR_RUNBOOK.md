# window-factor-002: foreground operator protocol

Status: preparation only; no scientific runner is invoked by this document.
Specification:39387c38305d235c90a8887337b1486ed0300550. Eight fixed means,
eight O/E/C conditions each. The question is measurement-convention attribution,
not biological validation. Do not repeat measurement-001.

Ownership: Astra4 scientific implementation; Astra2 independent numeric controls
and review; Astra3 adversarial/package review; Astra1 integration, transport,
sole kernel operator and export. This supersedes the earlier implementation
assignment to Astra1. No other chat writes to or launches in the kernel.

## Release gate

Before execution, record exact runner commit, plan digest, dependency closure,
entry point and CLI, and explicit independent approvals referencing that commit.
Specification approval alone is insufficient. Any scientific code change after
review invalidates approval until reviewers accept the changed code. Record
source measurement-001 archive SHA256
713ffec2e9f62553b8a4b350b29611fd02c26f822a96ae93ec8a9617e640b6c2.

## Stage and launch

1. Build an allowlisted public payload from committed runner/dependency files,
   final plan, and unchanged archived input/result/manifest bytes. Never copy
   a workspace, environment, notebook, coordination folder or connection config.
2. Use only official marimo-pair scratchpad transport. Keep authentication in
   the external protected credential store, absent from submitted code/output.
   Stop on HTTP410; timeout/unknown completion means no automatic retry.
3. Inspect current cell statuses immediately before launch; reject running or
   queued cells. Inspect GPU occupancy without process command lines or env
   values. This run is CPU-only and must not contend with a GPU job. Do not
   claim these checks prove absence of every unrelated CPU activity.
4. Verify every staged file SHA256. Use a fresh stage and output directory;
   take the existing shared nonblocking foreground lock. Refuse an existing
   run-ID directory, even if an earlier invocation failed. Do not overwrite or
   delete measurement001. Use a synchronous bounded child, no background job.
5. Invoke the exact reviewed CLI under the kernel Python, explicitly adding
   the staged tools directory to sys.path. No package installs, SSH or shell
   interpolation. Record Python/NumPy/SciPy versions, start/end and return code.
6. Preserve failure status without pretending it is an approved result. Do not
   relax tolerances, alter windows or resubmit after unexpected failure.

## Artifact contract and retrieval

Fresh run directory contains result.json, approved code, plan and public input
closure plus manifest.json. Manifest schema: run_id and files mapping relative
paths to {bytes, sha256}; manifest excludes itself. Preserve all64 statuses,
signed areas/ratios, fixed boundary provenance, corner residuals, invariants
and interactions. Scientific failure is distinct from export success.

Create a bounded tar.gz containing only that directory, with regular files and
directories; no links. Scratchpad exports archive_base64, bytes and sha256.
Save sanitized transport output separately from public artifacts, then:

```sh
python tools/verify_foreground_export.py --receipt export.json --run-id window-factor-002 --output-root retrieved-window-factor-002
```

The destination must not exist. This verifies bounded extraction, member set,
digests and sizes, not science or execution location. Send retrieved archive,
exact commit, SHA256 and nonsecret operator receipt to Astra2/3 for independent
review before calling the experiment accepted. Keep runtime timing separate
from a whole-job benchmark. Offline scientific checker commands are added only
after reviewers provide the actual CLI; no guessed executable is a run recipe.
