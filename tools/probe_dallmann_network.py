"""Execute only inspected author defaults/create_model on a two-cell fixture."""
import ast,json,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/python-reference'))
import pandas as pd
import brian2 as b
from textwrap import dedent
source=ROOT/'data/reference/feco_inhibition/code/simulation_model.py'
tree=ast.parse(source.read_text())
selected=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='default_params' for t in node.targets):selected.append(node)
    if isinstance(node,ast.FunctionDef) and node.name=='create_model':selected.append(node)
assert len(selected)==2
scope=dict(pd=pd,dedent=dedent)
for name in ['NeuronGroup','Synapses','SpikeMonitor','mV','ms','Hz']:scope[name]=getattr(b,name)
exec(compile(ast.Module(body=selected,type_ignores=[]),str(source),'exec'),scope)
b.prefs.codegen.target='numpy'
results={};traces={}
with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
    p=Path(folder)
    pd.DataFrame(index=[10,20]).to_csv(p/'nodes.csv')
    pd.DataFrame(dict(Presynaptic_Index=[0],Postsynaptic_Index=[1],
        **{'Excitatory x Connectivity':[20]})).to_parquet(p/'edges.parquet')
    for name,reset in [('unmodified',scope['default_params']['eq_rst']),
                       ('remove_w_diagnostic','v = v_rst; g = 0 * mV')]:
        b.start_scope();b.defaultclock.dt=.1*b.ms
        params=dict(scope['default_params'],eq_rst=reset)
        try:
            n,s,sp=scope['create_model'](p/'nodes.csv',p/'edges.parquet',params)
            n.g[0]=100*b.mV
            state=b.StateMonitor(n,['v','g'],record=True)
            b.Network(n,s,sp,state).run(20*b.ms)
            traces[name]=(state.v[:]/b.mV,state.g[:]/b.mV,sp.i[:],sp.t[:]/b.ms)
            results[name]=dict(runs=True,spikes=int(sp.num_spikes),
                spike_neurons=sp.i[:].tolist(),spike_times_ms=(sp.t[:]/b.ms).tolist())
        except Exception as e:
            results[name]=dict(runs=False,error=str(e),cause=repr(e.__cause__))
if len(traces)==2:
    import numpy as np
    identical=all(np.array_equal(a,c) for a,c in zip(traces['unmodified'],traces['remove_w_diagnostic']))
else:identical=None
report=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),brian2_version=b.__version__,
    results=results,traces_identical=identical,biological_replication=False,source_modified=False)
(ROOT/'reports/dallmann_network_compatibility.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
