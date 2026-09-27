# Graded visual transmission reference

Pinned sources: neurokernel/lamina at
1dc2d80912ab1be87fb06c0d46d930270a3033d2 and neurokernel/neurodriver at
ddafe14295b6fea83e236b3c2ae0334741ed47c9. Acquisition tools preserve author
licenses and content hashes in reports/lamina_reference_sources.json and
reports/neurodriver_graded_sources.json. Neither package was installed or executed.

The historical cartridge uses PowerGPotGPot and MorrisLecar components, rather
than a spike encoder. The current conductance template computes
g=min(saturation,slope*max(0,Vpre-threshold)^power). This output is conductance,
not a signed current; reversal potential and postsynaptic voltage must be applied
by the surrounding current calculation. Scale and delays are also external to
this current template. They must not be silently omitted or folded into raw
MaleCNS synapse counts without a documented calibration.

tools/audit_graded_interface.py verifies all source hashes and inspects ASTs
without executing author code. All nine historical MorrisLecar parameter maps
lack the exact current required keys V_K, g_Ca and g_K: the old file uses V_k,
G_Ca and G_k. This is a concrete API mismatch, not evidence that the equations
are biologically incompatible. Name and semantic reconciliation must precede
execution. Evidence: reports/graded_interface_audit.json. Automatic transfer is
disabled; no MaleCNS cell or edge is replaced by the author cartridge graph.

Required continuation: reproduce a conductance/reversal/delay fixture from the
pinned sources, reconcile the old and current equations, then test graded
light-response transfer. Whole-CNS coupling remains unimplemented; a reference
cartridge is not a substitute for the accepted full MaleCNS population.

The source acquisition now includes NDComponent, LPU and Aggregator at the same
Neurodriver commit. Historical lamina.py multiplies both slope and saturation by
scale and removes that field. Current Aggregator sums g*(Erev-Vpost), using the
postsynaptic voltage and delayed conductance buffer. Current LPU maps delay to
max(round(delay/dt),1)-1. With dt=0.0001 s, a 0.001 s delay yields buffer offset 9;
literal 1 yields 9,999. Offset alone is not complete latency: scheduler phase
and implicit tick separation must also be reproduced. Historical delay units
must be reconciled, not inferred just from the matching field name.

native/graded_probe.cpp implements an independent scalar equation fixture using
the historical R1-to-L1 example (threshold -80, slope .00002, saturation .0008,
scale 40, reversal -80). Five analytic cases test below threshold, threshold,
linear response, saturation and postsynaptic voltage below reversal. All pass
in compiled C++ FP64; reports/graded_transfer_fixture.json records output and
hashes. At Vpre=-60 and Vpost=-50, g=.016 and I=-.48; with Vpost=-90, the same
conductance gives I=+.16. A transmitter label alone is therefore insufficient
to hard-code current sign. These are arithmetic checks, not a dynamic synapse,
delay implementation, measured physiology or enabled MaleCNS coupling.

## Dynamic membrane reference

tools/extract_morris_kernel.py materializes the unchanged current author FP64
MorrisLecar kernel with its license. tools/build_morris_probe.cmd builds the GPU
driver. It explicitly translates the three parameter names while preserving
the historical L1 numerical values. Four injected-current protocols (0, -.48,
+.48 and a -.96 pulse at 0.2..0.4 s) run for one second, with ten 10-us membrane
substeps per recorded 0.1-ms tick. tools/check_morris_membrane.py independently
integrates scalar CPU equations using simultaneous old-state derivatives.
All 10,000 recorded V/n states match within 7.105427357601002e-15 mV and
5.551115123125783e-17 respectively. Evidence:
reports/morris_membrane_comparison.json. This validates numerical equations at
those parameter values, not historical scheduler equivalence, measured L1
physiology, delayed circuit coupling or transfer to MaleCNS.


## Dynamic single-edge diagnostic

`native/graded_path_probe.cu` replays the pinned 2-second photoreceptor onset trace into four independent Morris-Lecar cells: dark, light delayed 1 ms, light disconnected, and light without delay. Current is computed from delayed voltage and postsynaptic voltage at the outer step start, then held for ten membrane substeps. This is an explicit engineering schedule, not a claim about the original Neurodriver scheduler. Historical R1-L1 values are diagnostic parameters, not a MaleCNS mapping.

`python tools/check_graded_path.py` independently integrates every step on CPU, verifies the source trace hash and binary input, and checks disconnection and delay. Maximum voltage error is 7.11e-15 mV, disconnected light equals dark exactly, and onset shifts from index 5129 to 5139 (1 ms). Maximum connected effect is 1.85038 mV. Evidence: `reports/graded_path_comparison.json`. No full MaleCNS network, biological fit, or learning is established by this test.
