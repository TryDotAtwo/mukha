# Compact notebook: one foreground operator

Target: faithful-fly-compact-recovery-v2. The historical full notebook's startup
failure, compact notebook pairing, and Dryad access are separate issues.

Proposed sole kernel operator: Astra 1. Astra 2 acknowledged; remaining peers
must acknowledge before a remote experiment. Other peers prepare/review local
code through MD. Never submit a second request while completion is unknown.

## Connection prerequisite

The explicitly requested marimo-pair skill and execute-code.sh are not installed
or discoverable in this session. The received token is masked; no usable private
connection file exists. No remote request, toast, active-cell check, GPU query or
HF_TOKEN-presence check has executed. Do not substitute old pairing files or an
unrequested transport. HTTP410 means stop without retry.

Credentials belong only outside repositories/artifacts, directory mode 700 and
file mode 600. MD contains only the private path and designated operator. Never
dump environment variables, process arguments, auth headers or raw session data.
Only boolean HF_TOKEN presence may be reported.

Once the skill and connection are available and ownership is acknowledged, send
a harmless probe/toast, then use supported session inspection for active cells,
processes, actual GPU and HF_TOKEN presence. Process names alone do not prove
cell idleness. Uncertain remote activity blocks a new job.

## Prepared bounded diagnostic

tools/run_pang_measurement_foreground.py uses CPU/local pinned inputs only. No
network, GPU, background work or secret access. It separates boundary choices
and ratio sign conventions on eight processed means. Supplied peak: signed
maximum in historical indices 2:31; ifi: median source time difference. Neither
choice is physical flash alignment or ROI bootstrap/model validation.

Run in an isolated restored checkpoint with source inputs and the new runner:

```sh
python tools/run_pang_measurement_foreground.py --output-root /marimo/mukha-foreground --run-id measurement-001 --location molab --preflight
python tools/run_pang_measurement_foreground.py --output-root /marimo/mukha-foreground --run-id measurement-001 --location molab
```

Submit serially through native transport only, with one synchronous child process
and a 120-second execution bound. All invocations share output-root/lock. This
first diagnostic requires no GPU job; no parallel GPU activity is permitted.

Local rehearsal completed; Molab execution remains pending. Existing run IDs are
rejected. Outputs: result.json, exact input/code copies, per-file SHA256 manifest,
tar.gz and archive SHA256 sidecar. A kernel path is not durable external storage:
retrieve the completed archive through the supported notebook file interface,
verify SHA256 after retrieval, then mark export complete. No next experiment
before this receipt. No private HF publication is required.

## Public source boundary

Dryad landing page returned HTTP200 and renders the README schema (ROI, stimulus,
photodiode/frame fields). Its own advertised workbook/README links returned
HTTP403; prior API downloads returned HTTP401. Error bodies are not source files.
Rendered README is useful documentation but not per-recording workbook contents.
No auth bypass or credential request was made.
