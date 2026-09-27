# Numerical reference contract

Source: philshiu/Drosophila_brain_model at
`91bdd1e7dcf193f3e7ca5a8933497fcef63b7960`, `model.py` (MIT), equation definitions
and Brian2 scheduling. This is an implementation contract, not evidence of
biological replication or successful transfer to MaleCNS.

Units in our runtime: milliseconds, millivolts. Baseline dt=0.1 ms, rest/reset
-52 mV, strict threshold v > -45 mV, membrane tau=20 ms, synaptic tau=5 ms,
refractory=2.2 ms, propagation delay=1.8 ms, per-contact scale=0.275 mV.
The original uses Brian2 `method='linear'`; forward Euler is not an equivalent
substitute. Both v and g derivatives are disabled during refractoriness.
Reset clears v and g. Incoming events during refractoriness must obey Brian2's
actual refractory-variable write semantics, which are verified experimentally.

Within a tick, reproduce state update -> threshold -> synapse delivery/external
Poisson voltage injection -> reset. A delayed current delivered after threshold
cannot cause a spike at that earlier threshold evaluation. The original Poisson
targets have their refractory interval set to zero. Record exact event times in
comparisons; identical seeds across different random generators are insufficient.

For the unfrozen linear system:

    a = exp(-dt / tau_m); b = exp(-dt / tau_s)
    g_new = b * g_old
    v_new = v_rest + a*(v_old-v_rest) + g_old*(a-b)*tau_s/(tau_m-tau_s)

The tau_m == tau_s limit is (dt/tau_m)*a*g_old.

Original source has `w = 0` in its neuron reset despite `w` not being declared in
the neuron equations. The unmodified source runs on Brian2 2.9.0 (see
reports/shiu_original_compatibility.json); retain its original equations. That
reset assignment must not be interpreted as erasing graph weights.

Incoming CSR stores destination rows, source columns and integer contact counts.
Topology/counts are immutable. Signs and physiological scales belong to a
separate model profile. No sign is inferred by the graph importer. A Shiu profile
is not automatically a justified transmitter/receptor profile for MaleCNS.
