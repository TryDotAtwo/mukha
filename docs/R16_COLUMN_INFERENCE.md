# R1-R6 column candidates from anatomical connectivity

`tools/infer_r16_columns.py` verifies all consumed full-graph arrays, preserves
their orientation, and enumerates actual R1-R6 connections into L1/L2/L3 cells
with source hex coordinates and soma side. The audit uses 4,426 anchor neurons
and records 8,550 original graph rows. It does not simulate a reduced network.

For each R1-R6 neuron and anchor type, contact counts are summed by column.
All sums are retained. A unique maximal column is a candidate; disagreement
between types or tied maxima remains unresolved. More than one agreeing anchor
type is reported separately from one-type-only support. The neuronal root-side
annotation must agree with the proposed column side. This is an inference from
anatomy, not a confidence-calibrated estimate or independently measured visual
receptive field. No arbitrary threshold, array-position mapping or fabricated
missing neuron is used.

Result on the complete accepted population of 3,377 R1-R6 cells:

- 3,235 have a common unique candidate across multiple anchor types.
- 90 have a candidate supported by one available anchor type only.
- 42 have no connections to the available coordinate-bearing anchors.
- 10 have tied or disagreeing candidates.

The source L1 coordinate conflict for body 534860 remains visible on every
affected edge and every input cell that touches it. All candidate records have
enabled=false. Evidence and hashes are in `reports/r16_column_inference.json`;
the full candidates and edge table are under `data/derived/malecns_optic_columns`.

Before use as image input, reconcile anatomical ambiguities, account for neural
superposition, register column coordinates to optical directions, and validate
the sensory transduction and motion/color responses. Agreement among downstream
cell types cannot establish these missing physiological properties.
