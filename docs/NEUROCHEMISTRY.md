# Full-graph chemistry and uncertainty

`tools/audit_neurochemistry.py` verifies the pinned source chemistry table and
the graph ID/column/count arrays, joins by original body ID, and preserves all
prediction, consensus, confidence and ground_truth fields. Graph index is the
existing full-population order. No edge is dropped or reweighted.

The 167,216 candidate neural objects include 3,142 with consensus `unclear` and
514 without a chemistry record. The unclear group has 589,524 outgoing graph
rows (2,051,771 source synapse-count sum); the missing-record group has no
outgoing rows inside the accepted graph. This does not imply that those objects
are absent from biology or should be removed.

There are 20,128 differences between individual predictions and source consensus.
The source ground_truth field is populated on 85,484 rows. The field name is
preserved, but this audit does not establish that each individual reconstructed
cell was independently measured: type-level prior knowledge may be propagated.
Empty confidence is not zero confidence, and source consensus is not a receptor
map. The full aligned artifact is
`data/derived/malecns_neurochemistry/nodes.feather`; coverage and hashes are in
`reports/malecns_neurochemistry_audit.json`.

Before a full-CNS physiological run, declare receptor-dependent effect signs,
synaptic time constants and uncertainty variants. In particular, replacing all
unknown labels with zero weights would silently eliminate their physiological
influence despite retaining rows, and is not a neutral default. The modulatory
labels (dopamine, octopamine, serotonin) also require an explicit transmission
model instead of an unexamined fast excitatory/inhibitory-current assignment.
No effect mapping is enabled by this audit.
