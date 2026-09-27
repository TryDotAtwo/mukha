# Compact notebook: one foreground operator

Target: faithful-fly-compact-recovery-v2. The historical full notebook's startup
failure, compact notebook pairing, and Dryad access are separate issues.

Sole kernel operator: Astra 1, acknowledged by all three peers. Other peers prepare/review local
code through MD. Never submit a second request while completion is unknown.

## Connection prerequisite

The official marimo-team/marimo-pair skill was acquired and read. Connection,
mandatory help(cm), scratchpad probe and requested toast succeeded. Live context
showed two stale cells, none running/queued. NVIDIA RTX PRO 6000 Blackwell reported
97887 MiB total, zero GPU use/processes. HF_TOKEN was absent; only presence was
checked. Credentials remain outside repositories. HTTP410 means stop without retry.

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

Local rehearsal and one Molab measurement execution completed. Existing run IDs are
rejected. Outputs: result.json, exact input/code copies, per-file SHA256 manifest,
tar.gz and archive SHA256 sidecar. A kernel path is not durable external storage:
retrieve the completed archive through the supported notebook file interface,
verify SHA256 after retrieval, then mark export complete. No next experiment
before this receipt. No private HF publication is required.

The child interpreter initially failed preflight importing an adjacent tool. The
successful foreground launcher explicitly prepends the staged tools directory to
sys.path before runpy.run_path; no scientific parameter changed. Python 3.13.11,
NumPy 2.4.6 and SciPy 1.18.0 were observed. Reported arithmetic duration excludes
imports, transfer and transport, and is not a GPU/whole-runtime benchmark.

Runner revision ea7f494 pins the historical comparator before use and labels the
combined onset/endpoint/crossing changes. Result: eight processed-mean rows,
not physiological validation. The retrieved archive SHA256 is
713ffec2e9f62553b8a4b350b29611fd02c26f822a96ae93ec8a9617e640b6c2;
21622 bytes, all 12 manifested files verified outside the notebook. Independent
review is requested from Astra 2/3/4; see the receipt report for final status.

## Public source boundary

Dryad landing page returned HTTP200 and renders the README schema (ROI, stimulus,
photodiode/frame fields). Its own advertised workbook/README links returned
HTTP403; prior API downloads returned HTTP401. Error bodies are not source files.
Rendered README is useful documentation but not per-recording workbook contents.
No auth bypass or credential request was made.
