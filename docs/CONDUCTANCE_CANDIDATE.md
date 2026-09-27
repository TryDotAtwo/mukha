# Parameterized conductance runtime: numerical candidate

`native/cuda_conductance.cu` and `native/cuda_conductance.h` implement an
additional FP64 whole-CSR CUDA runtime. They do not replace the existing
current-based runtime or modify the MaleCNS source graph. The caller supplies
two **nonnegative, per-edge** conductance increments and both reversal
potentials. This separates presynaptic transmitter annotation from a
postsynaptic effect; it does not infer receptor identity from transmitter name.

The per-cell membrane substep uses the exact constant-conductance solution

```
G = 1 + g_exc + g_inh
V_inf = (V_rest + g_exc E_exc + g_inh E_inh) / G
V_next = V_inf + (V - V_inf) exp(-dt G / tau_m)
```

The conductance states then decay exponentially and receive delayed CSR
presynaptic events. They continue to decay and accumulate during refractory
periods. A direct voltage jump is a separate input channel. `fc_reset`
clears membrane, conductance, refractory and delay-ring state so an episode
can be replayed without rebuilding the large graph. This engine has no
checkpoint, plasticity, graded-cell, receptor-type, or body-coupling API yet.

Build with `tools/build_cuda_conductance.cmd`. The independent two-cell
reference `tools/check_cuda_conductance.py` verifies zero, excitatory,
inhibitory and mixed cases against a Python recurrence, exact chunk
equivalence, and exact replay after reset; see
`reports/cuda_conductance_abi_reset.json`.

`tools/probe_full_conductance_malecns.py` exercises all 167,216 nodes and
25,587,572 retained edges using the same candidate taste inputs as the
current-based diagnostic. `tools/summarize_full_conductance_malecns.py`
verifies source/DLL hashes, one report per separate process, finite states,
and non-input voltage bounds. For one conditional variant, the full 100-ms
spike trace was repeated exactly after `fc_reset`. The four results and hashes
are in `reports/malecns_conductance_candidate_summary.json`.

These runs use a deliberately provisional 0.005 dimensionless conductance
increment per contact, E_exc=0 mV and E_inh=-70 or -48 mV. A [recording in
other adult fly brain neurons](https://pmc.ncbi.nlm.nih.gov/articles/PMC3125135/)
reported a GABA current reversal near -48 mV; this is **not** a Roundup or
MaleCNS-wide measurement. The -70-mV point is hypothetical. At rest -52 mV,
a -48-mV chloride reversal can be depolarizing even when it shunts excitation;
the name `g_inh` is a channel label, not proof of inhibition on every cell.
Scapula's predicted glutamate transmitter likewise does not identify the
postsynaptic receptor. The source chemistry audit explicitly lacks a receptor
map (`docs/NEUROCHEMISTRY.md`).

For the same direct input train, total network events span 110,649 to
1,256,774 in 100 ms across the four variants. When unclear-labelled sources
are assigned to the excitatory channel, the taste-input cells themselves
generate 236 or 294 additional recurrent events beyond the 610 directly
elicited spikes. Thus the conditional network trajectories differ strongly,
even though non-input voltages remain within the selected reversal bounds.
This validates a numerical capability and exposes parameter uncertainty; it
does not reproduce a biological taste trace or license these values as the
native MaleCNS physiology. The full-graph trials were run in separate
processes after an earlier memory-pressure failure. A dedicated
`tools/check_cuda_conductance_full_recreate.py` zero-weight lifecycle test now
creates, advances, and destroys two full-CSR handles sequentially in one
process; both pass and CUDA free memory returns exactly to its initial value
after each destruction (`reports/cuda_conductance_full_recreate.json`). This
rules out a persistent GPU allocation leak in that controlled case. It does
not establish the cause of the earlier resource failure under the larger
Python data-loading workload. `fc_reset` avoids reconstruction for repeated
episodes.

## Taste-condition comparison: negative robustness result

`tools/compare_conductance_taste_conditions.py` checks four sweet-only runs
against four sweet-plus-bitter runs with the same graph, binary and parameter
choices. The machine-readable comparisons and input-report SHA-256 hashes are
in `reports/malecns_conductance_taste_comparison.json`. Roundup spikes change
from sweet-only to combined as follows:

| E_inh (mV) | Unknown source sign | Sweet | Combined | Difference |
| ---: | ---: | ---: | ---: | ---: |
| -70 | +1 | 69 | 59 | -10 |
| -70 | -1 | 40 | 13 | -27 |
| -48 | +1 | 74 | 76 | +2 |
| -48 | -1 | 74 | 74 | 0 |

Thus Roundup suppression does not survive both reversal-potential choices.
With unknown sources assigned excitatory effects, sweet-only stimulation also
elicits 179 or 332 spikes in bitter-candidate cells through recurrence. These
are model events, not direct bitter input. The conditions are therefore not
isolated at the sensory population level in those variants. G2N-1 also lacks
a consistent direction (11→8, 7→10, 50→52, 44→45). This comparison fails
the proposed taste-response robustness gate; it is neither biological
validation nor a reason to select only the favorable -70-mV variants.

To test the proposed Scapula route without changing the source graph,
`tools/probe_full_conductance_malecns.py --cut-scapula-roundup` sets only the
three source-verified Scapula→Roundup conductances (251 contacts) to zero in
temporary arrays. `tools/compare_conductance_scapula_cut.py` binds all four
cut runs to their intact counterparts by graph, binary, crosswalk and report
hashes in `reports/malecns_conductance_scapula_cut_comparison.json`. Under
combined sweet-plus-bitter input, Roundup counts are 59→63 and 13→23 when
E_inh=-70 mV; they are 76→76 and 74→74 when E_inh=-48 mV. Input-population
spike counts are equal within every intact/cut pair. The route has an effect
in the -70-mV conditional model and no spike-count effect in the -48-mV
conditional model. This does not identify the physiological receptor, and
the spike-count readout can miss subthreshold effects.
