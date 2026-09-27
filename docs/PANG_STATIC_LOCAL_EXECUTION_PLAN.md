# One local static-control execution: operator contract

Protocol704843a695224448470a70527ce8db3649570a16 is approved by all three
reviewers; see PANG_STATIC_PROTOCOL_REVIEW_RECEIPT.md. Approved protocol file
SHA2569968b2b5a734441483e0a6391e55a4dbb9edf3fe72de445b78a821d48cac4665.

Owner: Astra4 implements one runner and synthetic tests in its own worktree;
Astra2 reviews numerical behavior, Astra3 provenance/leakage/typed failures.
Astra1 integrates and is the sole actual operator. Do not duplicate the runner.

## Launch gate

No real fit until BOTH reviewers explicitly approve the SAME exact runner
commit. Record their message identifiers, reviewed commit, runner SHA256 and
configuration/protocol hashes. A change to executable code/config invalidates
the gate until re-reviewed. Before launching, ensure the imported runner bytes
match those reviewed, and validate the frozen archive and eight source hashes.
Use the published temporal003 archive as the source/baseline package; never
refit H0/H1. Interface/command will be recorded from the delivered runner, not
guessed before delivery. An absent approval blocks fitting, not preparation.

## Venue and single-run policy

Run ID proposed: static-control-004. Venue: LOCAL synchronous foreground CPU,
not Molab. No transport retry, GPU, SSH, background process, resource purchase
or environment/secret enumeration. Limit BLAS/OpenMP threads to one through
explicit thread settings. Use a fresh nonexistent output destination; never
overwrite prior results. Record UTC start/end, return code, elapsed duration,
Python/NumPy/SciPy versions, exact command (relative public paths), execution
venue, code/config/source hashes and both code approvals. Capture bounded
stdout/stderr without environment dumps or private paths in public receipts.

Run only once after gate closure. If execution fails, preserve the partial
receipt/output and identify the cause; do not silently retry or refit with
different settings. A repair affecting calculations requires renewed review.

## Export and independent result closure

Preserve the complete six-condition output including undefined keys, candidate
diagnostics, selected identities, separate H0 fallback where applicable, signed
and magnitude support measures, and frozen baseline scores. Include copied
reviewed code/config/protocol and hash-bound inputs or their public source
archive reference. Manifest every result artifact with SHA256. Archive safely
under reports/recorded_runs, keeping old archives byte-identical. Exclude all
credentials and private filesystem references from public artifacts.

Send the exact new archive/hash to Astra2 for independent numerical result
review and Astra3 for provenance/structure review; Astra4 interprets the full
vector, not just L2/highLum/light. Preserve exploratory reuse and unequal model
complexity. temporal003 all_six_improved=false is immutable. End this model
sweep after ONE cubic comparison and its independent review regardless of
outcome, as specified in the frozen protocol. No further adaptive variant fit.

Final publication: one incremental Git bundle from public
339ac3f1c511960a79dd21777c2476951f2fc5dc to the final integrated code/results/
review HEAD; provide bundle SHA256, prerequisite, actual verdicts and offline
commands. Until the runner and reviews exist, a preparation bundle must be
explicitly labelled as such and must not claim a completed experiment.
