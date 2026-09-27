"""Report all preregistered JON doses, including negative readouts."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    rows=[]
    for rate in (0,100,220):
        protocol_path=ROOT/f'configs/shiu_jon{rate}_pilot.json'
        p=json.loads(protocol_path.read_text())
        comparison_path=ROOT/f'reports/shiu_jon{rate}_comparison.json'
        comparison=json.loads(comparison_path.read_text())
        if not comparison['numerical_comparison_passed'] or comparison['protocol_sha256']!=hashlib.sha256(protocol_path.read_bytes()).hexdigest():
            raise ValueError('Unverified protocol comparison')
        event_path=ROOT/f'build/shiu_jon{rate}_native64.spikes.bin'
        if hashlib.sha256(event_path.read_bytes()).hexdigest()!=comparison['spike_files'][event_path.name]:
            raise ValueError('Recorded spikes changed after comparison')
        events=np.fromfile(event_path,dtype='<u4').reshape(-1,2)
        readouts={name:dict(body_id=target['body_id'],spikes=int(np.count_nonzero(events[:,1]==target['index'])))
                  for name,target in p['secondary_readouts'].items()}
        rows.append(dict(input_rate_hz=rate,network_spikes=len(events),readouts=readouts,
                         all_native_spikes_match_brian=comparison['all_spike_events_exact'],
                         comparison_sha256=hashlib.sha256(comparison_path.read_bytes()).hexdigest()))
    result=dict(runs=rows,seeds_per_condition=1,
                zero_input_quiescent=rows[0]['network_spikes']==0,
                highest_dose_both_readouts_active=all(x['spikes']>0 for x in rows[-1]['readouts'].values()),
                scope='Neural responses on original author graph; 220 Hz was added after negative 100 Hz readouts and belongs to author sweep. No physical grooming, complete dose-response replication, or MaleCNS transfer claimed.',
                biological_gate_complete=False)
    (ROOT/'reports/shiu_grooming_pilot.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
