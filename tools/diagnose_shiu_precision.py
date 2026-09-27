"""Preserve first-divergence evidence without modifying acceptance tolerances."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [ROOT/('build/'+name+'.json') for name in ('shiu_diag_cuda','shiu_diag_brian64','shiu_diag_brian32')]
    cuda,b64,b32 = [json.loads(p.read_text()) for p in paths]
    if len({p['protocol_sha256'] for p in (cuda,b64,b32)})!=1: raise ValueError('Different diagnostic protocols')
    a,b = [np.fromfile(ROOT/('build/'+name+'.spikes.bin'),dtype='<u4').reshape(-1,2)
           for name in ('shiu_sugar_pilot','shiu_brian_pilot')]
    only = sorted(set(map(tuple,a)) ^ set(map(tuple,b)))
    tick,neuron = map(int,only[0])
    av,bv = np.asarray(cuda['target_voltage_mv']),np.asarray(b64['target_voltage_mv'])
    protocol = json.loads((ROOT/'build/shiu_diagnostic_protocol.json').read_text())
    if neuron!=protocol['target_index']: raise ValueError('Diagnostic observes a different neuron')
    result = dict(first_differing_tick=tick,first_differing_time_ms=tick*.1,neuron_index=neuron,
                  body_id=protocol['target_body_id'],
                  all_network_spikes_before_first_difference_exact=bool(np.array_equal(a[a[:,0]<tick],b[b[:,0]<tick])),
                  max_observed_neuron_voltage_error_before_difference_mv=float(np.max(np.abs(av[:tick]-bv[:tick]))),
                  brian64_voltage_at_difference_mv=float(bv[tick]),
                  brian32_voltage_at_difference_mv=b32['target_voltage_mv'][tick],
                  cuda_voltage_after_reset_mv=float(av[tick]),
                  threshold_mv=-45.0,cuda_spike_ticks=cuda['target_spike_ticks'],
                  brian64_spike_ticks=b64['target_spike_ticks'],brian32_spike_ticks=b32['target_spike_ticks'],
                  source_reports={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                  inference='First timing difference is consistent with floating-point rounding near threshold; do not infer a complete root-cause proof or relax the biological gate.',
                  next_check='Higher-precision full-network oracle with identical inputs and source weights; preserve equations and threshold.',
                  biological_gate_passed=False)
    (ROOT/'reports/shiu_precision_diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not k.endswith('spike_ticks')},indent=2))


if __name__ == '__main__': main()
