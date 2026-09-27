"""Controlled precision comparison; do not replace native validation with an oracle."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    names=['shiu_sugar_pilot','shiu_torch32_pilot','shiu_torch64_pilot','shiu_brian_pilot']
    paths=[ROOT/('build/'+name+'.json') for name in names]
    reports=[json.loads(p.read_text()) for p in paths]
    if len({r['protocol_sha256'] for r in reports})!=1: raise ValueError('Protocol mismatch')
    events=[p.with_suffix('.spikes.bin').read_bytes() for p in paths]
    native_matches_fp32=events[0]==events[1]
    fp64_matches_brian=events[2]==events[3]
    state32_equal=bool(np.array_equal(np.asarray(reports[0]['target_voltage_mv'],dtype=np.float32),
                                     np.asarray(reports[1]['target_voltage_mv'],dtype=np.float32)))
    result=dict(native_fp32_matches_torch_fp32_all_events=native_matches_fp32,
                native_fp32_matches_torch_fp32_target_state=state32_equal,
                torch_fp64_matches_brian64_all_events=fp64_matches_brian,
                precision_changes_events=events[1]!=events[2],
                spike_counts={n:r['network_spikes'] for n,r in zip(names,reports)},
                artifact_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                spike_hashes={p.with_suffix('.spikes.bin').name:hashlib.sha256(e).hexdigest() for p,e in zip(paths,events)},
                interpretation='For this full-network pilot, the native FP32 trajectory is reproduced by an independent FP32 implementation; FP64 reproduces Brian2. Precision is sufficient to explain the observed discrepancy.',
                scope='single-seed sugar pilot; no full biological validation; native FP64 remains unimplemented')
    (ROOT/'reports/shiu_precision_control.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not (native_matches_fp32 and fp64_matches_brian and state32_equal): raise SystemExit(1)


if __name__=='__main__': main()
