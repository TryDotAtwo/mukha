"""Independent FP64 GPU oracle; deliberately research Python, not the native runtime."""
import hashlib
import argparse
import json
import math
import time
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dtype',choices=['float64','float32'],default='float64')
    args=parser.parse_args()
    start = time.monotonic()
    protocol_path = ROOT/'configs/shiu_sugar_pilot.json'
    p = json.loads(protocol_path.read_text())
    graph = ROOT/'data/derived/shiu_2024'
    if hashlib.sha256((graph/'manifest.json').read_bytes()).hexdigest()!=p['graph_manifest_sha256']:
        raise ValueError('Protocol graph mismatch')
    manifest = json.loads((graph/'manifest.json').read_text())
    for name,record in manifest['files'].items():
        if hashlib.sha256((graph/name).read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Graph artifact changed')
    n = manifest['nodes'];device = torch.device('cuda')
    dtype = torch.float64 if args.dtype=='float64' else torch.float32
    row = torch.tensor(np.load(graph/'indptr.npy').astype(np.int64),device=device)
    col = torch.tensor(np.load(graph/'indices.npy').astype(np.int64),device=device)
    # Reconstruct from exact integer source counts; do not widen rounded FP32 weights.
    weights = torch.tensor(np.load(graph/'signed_synapse_counts.npy').astype(np.float64)*.275,device=device,dtype=dtype)
    matrix = torch.sparse_csr_tensor(row,col,weights,size=(n,n),device=device)
    v = torch.full((n,),-52.,dtype=dtype,device=device);g = torch.zeros_like(v)
    next_allowed = torch.zeros(n,dtype=torch.int64,device=device)
    refractory = torch.full_like(next_allowed,22);refractory[p['sensory']] = 0
    ring = torch.zeros((19,n),dtype=dtype,device=device)
    cap = 32;spike_buffer = torch.zeros((cap,n),dtype=torch.bool,device=device)
    voltage = torch.empty(p['steps'],dtype=dtype,device=device)
    drive_host = np.zeros((cap,n),dtype=np.float64)
    a,b = math.exp(-.1/20),math.exp(-.1/5);c = (a-b)*5/15
    cursor = total = 0
    target_ticks = []
    output = ROOT/('build/shiu_torch'+args.dtype.removeprefix('float')+'_pilot.json')
    with output.with_suffix('.spikes.bin').open('xb') as stream, torch.no_grad():
        for begin in range(0,p['steps'],cap):
            steps = min(cap,p['steps']-begin);drive_host.fill(0)
            while cursor<len(p['events']) and p['events'][cursor]['tick']<begin+steps:
                ev=p['events'][cursor];drive_host[ev['tick']-begin,ev['neuron']]+=p['voltage_jump_mv'];cursor+=1
            drive = torch.tensor(drive_host[:steps],device=device,dtype=dtype)
            for local in range(steps):
                tick = begin+local
                allowed = tick>=next_allowed
                v = torch.where(allowed,-52+a*(v+52)+c*g,v)
                g = torch.where(allowed,b*g,g)
                fired = allowed & (v>-45)
                ring[tick%19].copy_(fired)
                incoming = torch.sparse.mm(matrix,ring[(tick-18)%19,:,None]).flatten()
                g += torch.where(allowed,incoming,0.)
                v += torch.where(allowed,drive[local],0.)
                v = torch.where(fired,-52.,v);g = torch.where(fired,0.,g)
                next_allowed = torch.where(fired,tick+refractory,next_allowed)
                spike_buffer[local].copy_(fired);voltage[tick] = v[p['target_index']]
            recorded = spike_buffer[:steps].cpu().numpy()
            ticks,neurons = np.nonzero(recorded)
            np.stack((ticks+begin,neurons),axis=1).astype('<u4').tofile(stream)
            total += len(ticks)
            target_ticks.extend((np.flatnonzero(recorded[:,p['target_index']])+begin).tolist())
            if (begin+steps)%1024==0: print(json.dumps(dict(completed_ticks=begin+steps,network_spikes=total)),flush=True)
    report = dict(backend='research-pytorch-cuda-'+args.dtype,torch_version=torch.__version__,
                  hardware=torch.cuda.get_device_name(),nodes=n,edges=manifest['edges'],completed_ticks=p['steps'],
                  network_spikes=total,target_spike_ticks=target_ticks,target_voltage_mv=voltage.cpu().tolist(),
                  protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                  wall_seconds=time.monotonic()-start,
                  scope='precision diagnostic oracle on complete original graph; not a native implementation or biological replication')
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('network_spikes','target_spike_ticks','wall_seconds')}))


if __name__=='__main__': main()
