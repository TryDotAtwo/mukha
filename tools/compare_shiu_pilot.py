"""Compare every spike from the native and author full-graph pilot."""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,default=ROOT/'build/shiu_sugar_pilot.json')
    parser.add_argument('--reference',type=Path,default=ROOT/'build/shiu_brian_pilot.json')
    parser.add_argument('--report',type=Path,default=ROOT/'reports/shiu_sugar_pilot_comparison.json')
    parser.add_argument('--instrumentation',choices=['none','memcheck'],default='none')
    args=parser.parse_args()
    gpu_path,brian_path = args.candidate,args.reference
    gpu,brian = [json.loads(p.read_text()) for p in (gpu_path,brian_path)]
    if gpu['protocol_sha256']!=brian['protocol_sha256'] or gpu['completed_ticks']!=brian['completed_ticks']:
        raise ValueError('Different protocols or completed intervals')
    events = []
    event_paths = [gpu_path.with_suffix('.spikes.bin'),brian_path.with_suffix('.spikes.bin')]
    for path,report in zip(event_paths,(gpu,brian)):
        if path.stat().st_size%8: raise ValueError('Truncated event record')
        a = np.fromfile(path,dtype='<u4').reshape(-1,2)
        if len(a)!=report['network_spikes']: raise ValueError('Reported count differs from recorded events')
        if np.any(a[:,0]>=report['completed_ticks']) or np.any(a[:,1]>=report['nodes']): raise ValueError('Event out of bounds')
        events.append(a)
    keys = [a[:,0].astype(np.uint64)*(2**32)+a[:,1] for a in events]
    only_gpu = np.setdiff1d(keys[0],keys[1])
    only_brian = np.setdiff1d(keys[1],keys[0])
    voltage_error = float(np.max(np.abs(np.asarray(gpu['target_voltage_mv'])-np.asarray(brian['target_voltage_mv']))))
    target_exact = gpu['target_spike_ticks']==brian['target_spike_ticks']
    exact = np.array_equal(events[0],events[1])
    result = dict(candidate_backend=gpu['backend'],instrumentation=args.instrumentation,
                  nodes=gpu['nodes'],edges=gpu['edges'],steps=gpu['completed_ticks'],
                  protocol_sha256=gpu['protocol_sha256'],all_spike_events_exact=exact,
                  gpu_spikes=gpu['network_spikes'],brian_spikes=brian['network_spikes'],
                  gpu_only_events=len(only_gpu),brian_only_events=len(only_brian),
                  target_spikes_exact=target_exact,target_spike_count=len(gpu['target_spike_ticks']),
                  max_target_voltage_error_mv=voltage_error,voltage_tolerance_mv=.002,
                  numerical_comparison_passed=bool(exact and target_exact and voltage_error<.002),
                  predicted_target_responded=bool(gpu['target_spike_ticks']),
                  gpu_wall_seconds=gpu['wall_seconds'],brian_wall_seconds=brian['wall_seconds'],
                  source_reports={p.name:sha(p) for p in (gpu_path,brian_path)},
                  spike_files={p.name:sha(p) for p in event_paths},
                  scope='original full author graph, one preregistered pilot, shared inputs; biological replication gate remains open')
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['numerical_comparison_passed']: raise SystemExit(1)


if __name__ == '__main__': main()
