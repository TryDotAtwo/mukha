# Original Shiu Figure 3A replication in MoLab

This protocol reproduces the full original author sugar/bitter frequency grid, using the original author graph rather than transferring parameters to MaleCNS. The full grid contains 121 conditions (0 to 200 Hz in 20 Hz steps for each population) and 30 one-second trials per condition. Each condition is a shard; a completed shard does not complete Gate B.

Author model and notebook are pinned to philshiu/Drosophila_brain_model commit 91bdd1e7dcf193f3e7ca5a8933497fcef63b7960. Population identities and frequencies are extracted from notebook cell 23; cells 24–25 define simulation and aggregation. The harness verifies hashes of the author model, notebook, neuron CSV and full connectivity Parquet. It calls unchanged author create_model and poi, with original parameters except the explicitly selected rates. Both populations retain the author's zero refractory setting, including a population driven at 0 Hz.

Execution uses Brian2 numpy float64 with dt=0.1 ms. Each condition has fixed independent trial seeds specified before the first trial. These seeds establish reproducibility; conditions are not claimed to share identical sugar event streams. Record every network spike and the MN9 trial rate. Report both population and sample SD, pending confirmation of the author's aggregation convention.

All execution is inside a visible foreground MoLab cell. The source, inputs, protocol and package versions receive a verified immutable private HF receipt before simulation. Each completed trial (report plus complete spike events) is published before the next trial. HF failure stops the condition. The condition summary contains the trial receipts; the foreground terminal log is archived on normal completion or reported subprocess failure.

No automatic re-run of a partially completed condition is allowed. Inspect the same live cell/process first; preserve already published trial identities and remote incomplete files. The current harness refuses a pre-existing condition output directory. Recovery must verify receipts and resume only missing trials, rather than silently replacing evidence.

The initial execution order begins with sugar=100/bitter=0, then sugar=100/bitter=100, followed by the remaining preregistered grid conditions. Outcomes must not change the grid, seeds, weights or stop criteria. Author aggregate data should be acquired and pinned separately before claiming quantitative reproduction. Existing one-seed pilots support neither this full grid nor MaleCNS physiology.

Remaining Gate B requirements include author aggregate comparison, independent native numerical equivalence over the recorded inputs, separate MaleCNS transfer, sugar/bitter/grooming biology and the Huang memory requirement. The local plasticity and final three-seed KSP acceptance gates remain open.
