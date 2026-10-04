# Project execution policy

User instruction, 2026-10-04.

- Do not use subagents.
- GitHub is the source of truth for code. Use isolated branches and reviewable PRs; bind each remote execution to an immutable source commit and any declared patch.
- ALL project computation runs only in MoLab: CPU/GPU work, builds, tests, numerical checks, project helpers, data hashing/verification, training, simulation and rendering.
- On the user's computer, only read/edit text source, configurations, instructions and reports, and operate the remote transport. Do not download datasets, models, archives, binaries, checkpoints, videos or other experimental outputs there.
- Use the private Hugging Face dataset TryDotAtwo/faithful-fly-artifacts for durable results. Downloads/restoration and caches stay in MoLab.
- Before computation, verify the live notebook identity, active cells/processes and HF access. Do not duplicate or interrupt another live workload. Keep heavy work attached to a visible foreground notebook cell/SSE; one heavy workload per sandbox.
- Publish the source/input closure before the dependent experiment. Immediately publish each completed immutable shard, condition, checkpoint, log segment and result. Require server digest verification and an immutable HF commit/manifest receipt before advancing to the next stage.
- Never hash/upload a mutating checkpoint. Segment long recordings and logs into completed immutable parts.
- If HF publication fails, retain the completed files in the same MoLab session and stop advancing. If MoLab is unavailable, report the missing connection; no local computation/download fallback.
- Keep HF_TOKEN in MoLab Secrets and pairing credentials only in transport. Never publish credentials, tokenized URLs, private session files or unrestricted directory dumps.
- Historical local commands and runbooks are superseded by this policy. Do not erase historical evidence or call an instruction change a verified upload/test.
- Preserve the accepted WORK_PLAN biological/contact-control/KSP contract. Numerical replay, anatomical coverage, physiology, learning and KSP evaluation are separate gates. Do not mark a gate passed without its own evidence.
