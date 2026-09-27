"""Summarize a matched pair only after both native/reference comparisons pass."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    protocols=[json.loads((ROOT/f'configs/shiu_sugar100_bitter{rate}_pilot.json').read_text()) for rate in (0,100)]
    if protocols[0]['sensory']!=protocols[1]['sensory'] or protocols[0]['graph_manifest_sha256']!=protocols[1]['graph_manifest_sha256']:
        raise ValueError('Unmatched graph or sensory refractory settings')
    comparisons=[ROOT/f'reports/shiu_bitter{rate}_comparison.json' for rate in (0,100)]
    reports=[json.loads(path.read_text()) for path in comparisons]
    for rate,protocol,report in zip((0,100),protocols,reports):
        path=ROOT/f'configs/shiu_sugar100_bitter{rate}_pilot.json'
        if report['protocol_sha256']!=hashlib.sha256(path.read_bytes()).hexdigest() or not report['numerical_comparison_passed']:
            raise ValueError('Pilot comparison not verified')
    baseline,stimulated=[r['target_spike_count'] for r in reports]
    result=dict(condition='sugar 100 Hz; bitter 0 versus 100 Hz',
                baseline_mn9_spikes=baseline,bitter_mn9_spikes=stimulated,
                suppression_observed=stimulated<baseline,
                native_matches_brian_every_event=all(r['all_spike_events_exact'] for r in reports),
                runs_per_condition=1,simulation_ms=protocols[0]['steps']*protocols[0]['dt_ms'],
                comparison_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in comparisons},
                scope='single paired pilot on original author graph; not the full dose-response sweep, population statistics, or MaleCNS transfer',
                biological_gate_complete=False)
    (ROOT/'reports/shiu_bitter_pair.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
