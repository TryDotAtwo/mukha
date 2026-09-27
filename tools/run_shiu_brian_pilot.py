"""Original author's full Brian2 network with exactly the recorded pilot inputs."""
import hashlib
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/python-reference'))
import brian2 as b
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,default=ROOT/'configs/shiu_sugar_pilot.json')
    parser.add_argument('--output',type=Path,default=ROOT/'build/shiu_brian_pilot.json')
    parser.add_argument('--dtype',choices=['float64','float32'],default='float64')
    args = parser.parse_args()
    started = time.monotonic()
    protocol_path = args.protocol
    protocol = json.loads(protocol_path.read_text())
    source = ROOT/'data/reference/shiu_2024'
    lock = json.loads((ROOT/'reports/shiu_reference_sources.json').read_text())
    for name in ('model.py','2023_03_23_completeness_630_final.csv','2023_03_23_connectivity_630_final.parquet'):
        record = next(r for r in lock['files'] if Path(r['path']).name==name)
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Pinned author file changed: '+name)
    spec = importlib.util.spec_from_file_location('author_shiu',source/'model.py')
    author = importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
    b.start_scope();b.defaultclock.dt = protocol['dt_ms']*b.ms
    b.prefs.codegen.target = 'numpy'
    b.prefs.core.default_float_dtype = np.float64 if args.dtype=='float64' else np.float32
    neurons,synapses,spikes = author.create_model(source/'2023_03_23_completeness_630_final.csv',
        source/'2023_03_23_connectivity_630_final.parquet',dict(author.default_params))
    targets = np.asarray(protocol['sensory'],dtype=int)
    neurons.rfc[targets] = 0*b.ms
    index = {int(i):j for j,i in enumerate(targets)}
    inputs = np.zeros((protocol['steps'],len(targets)))
    for ev in protocol['events']: inputs[ev['tick'],index[ev['neuron']]] += protocol['voltage_jump_mv']
    cursor = [0]
    @b.network_operation(dt=b.defaultclock.dt,when='synapses',order=1)
    def recorded_input():
        # All these targets have zero refractory time, as in author.poi().
        neurons.v[targets] = neurons.v[targets] + inputs[cursor[0]]*b.mV
        cursor[0] += 1
    voltage = b.StateMonitor(neurons,'v',record=[protocol['target_index']],when='end')
    net = b.Network(neurons,synapses,spikes,recorded_input,voltage)
    print(json.dumps(dict(stage='running',neurons=len(neurons),edges=len(synapses),setup_seconds=time.monotonic()-started)),flush=True)
    net.run(protocol['steps']*b.defaultclock.dt,report='text',report_period=30*b.second)
    ticks = np.rint(np.asarray(spikes.t/b.defaultclock.dt)).astype(np.uint32)
    indices = np.asarray(spikes.i,dtype=np.uint32)
    ordering = np.lexsort((indices,ticks))
    events = np.stack((ticks[ordering],indices[ordering]),axis=1).astype('<u4')
    output = args.output.with_suffix('.spikes.bin')
    events.tofile(output)
    report = dict(backend='unmodified-author-equations-brian2-numpy',brian2_version=b.__version__,dtype=args.dtype,
                  nodes=len(neurons),edges=len(synapses),completed_ticks=cursor[0],network_spikes=len(indices),
                  target_spike_ticks=ticks[indices==protocol['target_index']].tolist(),
                  target_voltage_mv=np.asarray(voltage.v[0]/b.mV).tolist(),
                  wall_seconds=time.monotonic()-started,
                  protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                  author_commit=lock['commit'],
                  scope='full author graph, one seed; explicit shared inputs replace Poisson RNG; not complete biological replication')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('nodes','edges','network_spikes','target_spike_ticks','wall_seconds')}))


if __name__ == '__main__': main()
