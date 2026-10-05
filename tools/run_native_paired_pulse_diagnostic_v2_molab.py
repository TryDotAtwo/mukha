import marimo._code_mode as cm
probe = r'''import ctypes as ct,json,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]);name=sys.argv[2];gain=float(sys.argv[3]);pair=sys.argv[4]=='pair';zero=sys.argv[4]=='zero'
class Params(ct.Structure):
    _fields_=[(n,ct.c_double) for n in ('dt_ms','rest_mv','reset_mv','threshold_mv','membrane_ms','synapse_ms','reversal_exc_mv','reversal_inh_mv')]+[(n,ct.c_uint32) for n in ('refractory_ticks','delay_ticks')]
lib=ct.CDLL(str(root/'libconductance.so'));lib.fc_error.restype=ct.c_char_p
lib.fc_create.restype=ct.c_void_p
lib.fc_create.argtypes=[ct.c_uint32,ct.c_uint64,ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.c_void_p,Params,ct.c_uint32]
lib.fc_advance.argtypes=[ct.c_void_p,ct.c_uint32,ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.c_void_p];lib.fc_advance.restype=ct.c_int
lib.fc_destroy.argtypes=[ct.c_void_p]
steps=1024;rows=np.array([0,0,1],dtype=np.uint64);cols=np.array([0],dtype=np.uint32);we=np.array([gain],dtype=np.float64);wi=np.array([0.],dtype=np.float64);sensory=np.zeros(2,dtype=np.uint8)
p=Params(1.,-60.,-60.,-40.,20.,100.,0.,-80.,3,2)
def ptr(a):return a.ctypes.data_as(ct.c_void_p)
handle=lib.fc_create(2,1,ptr(rows),ptr(cols),ptr(we),ptr(wi),ptr(sensory),p,steps)
if not handle:raise RuntimeError(lib.fc_error().decode())
drive=np.zeros((steps,2),dtype=np.float64)
onsets=[] if zero else ([10,410] if pair else [10])
for tick in onsets:drive[tick,0]=50.
v=np.zeros_like(drive);ge=np.zeros_like(drive);gi=np.zeros_like(drive);spikes=np.zeros(drive.shape,dtype=np.uint8)
try:
    if lib.fc_advance(handle,steps,ptr(drive),ptr(v),ptr(ge),ptr(gi),ptr(spikes)):raise RuntimeError(lib.fc_error().decode())
finally:lib.fc_destroy(handle)
events=[tick+1 for tick in onsets];assert np.flatnonzero(spikes[:,0]).tolist()==events
assert not np.any(spikes[:,1]);assert not np.any(gi);assert not np.any(ge[:,0])
oracle=np.zeros(steps,dtype=np.float64)
for event in events:
    arrival=event+2;oracle[arrival:]+=gain*np.exp(-(np.arange(arrival,steps)-arrival)/100.)
error=float(np.max(np.abs(ge[:,1]-oracle)));assert error<1e-10
reference=np.zeros(steps,dtype=np.float64)
if not zero:reference[13:]=gain*np.exp(-(np.arange(13,steps)-13)/100.)
ratio=None
if pair:
    first=float(ge[13,1]);second=float(ge[413,1]-reference[413]);ratio=second/first
    assert abs(ratio-1.)<1e-10
np.savez_compressed(root/(name+'.npz'),voltage=v,conductance_exc=ge,conductance_inh=gi,spikes=spikes,drive=drive,independent_oracle=oracle)
result={'condition':name,'gain':gain,'onset_ticks':onsets,'observed_pre_event_ticks':events,'synaptic_arrival_ticks':[e+2 for e in events],'max_conductance_oracle_error':error,'tail_subtracted_ppr':ratio,'peak_normalized_current_mV_per_leak_conductance':float(np.max(ge[:,1])*60.),'software_tolerance':1e-10,'dt_ms':1.,'synapse_ms':100.,'holding_voltage_mv':-60.,'reversal_exc_mv':0.,'biological_parameters_admitted':False,'plasticity_enabled':False,'scope':'Existing native two-neuron conductance path; artificial direct-voltage event surrogate; normalized current, not measured absolute EPSC or optical stimulus reproduction.'}
(root/(name+'.json')).write_text(json.dumps(result,indent=2));print('PAIRED_PULSE_CONDITION',json.dumps(result),flush=True)
'''
code = '''def run_native_paired_pulse_diagnostic_v2():
    import json,importlib.util,urllib.request,hashlib,subprocess,sys,time,os
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env');api=HfApi();repo='TryDotAtwo/faithful-fly-artifacts'
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info(repo,repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('pp_archive','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-native-paired-pulse-v2-20261005');root.mkdir(exist_ok=True)
    if (root/'source.py').exists():raise RuntimeError('Inspect existing paired-pulse stage')
    a.require_commit_capacity(api,repo,commits_needed=9)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication failed; preserve outputs and stop')
        print('PAIRED_PULSE_RECEIPT',json.dumps(r),flush=True);return r
    pin='d06ce5a7a68b7a67828b57b15d9d989a3dd287bc'
    expected={'cuda_conductance.cu':'2afbb065cc45d61a2d6f3b9a6917fe8285762d4a','cuda_conductance.h':'cfa0da1bb64e8193a6d9c92f31aa8ae11565ee6d'}
    for name,blob in expected.items():
        with urllib.request.urlopen('https://raw.githubusercontent.com/TryDotAtwo/mukha/'+pin+'/native/'+name,timeout=30) as response:raw=response.read()
        if hashlib.sha1(('blob '+str(len(raw))+chr(0)).encode()+raw).hexdigest()!=blob:raise RuntimeError('Git blob changed')
        (root/name).write_bytes(raw)
    import zipfile
    with urllib.request.urlopen('https://pypi.org/pypi/nvidia-cuda-cccl/13.0.85/json',timeout=30) as response:cccl_meta=json.load(response)
    cccl_item=next(x for x in cccl_meta['urls'] if 'manylinux2014_x86_64' in x['filename'] and x['filename'].endswith('.whl'))
    wheel=root/cccl_item['filename']
    with urllib.request.urlopen(cccl_item['url'],timeout=60) as response:wheel.write_bytes(response.read())
    if wheel.stat().st_size!=cccl_item['size'] or a.digest(wheel)!=cccl_item['digests']['sha256']:raise RuntimeError('CCCL published identity mismatch')
    (root/'cccl-pypi.json').write_text(json.dumps(cccl_meta,indent=2))
    cccl_receipt=publish([wheel.name,'cccl-pypi.json'])
    target=root/'cccl';target.mkdir(exist_ok=True)
    with zipfile.ZipFile(wheel) as package:package.extractall(target)
    cccl=next(p.parent.parent for p in target.rglob('target') if p.parent.name=='nv')
    assert (cccl/'nv/target').exists()
    cuda=Path('/usr/local/lib/python3.13/site-packages/nvidia/cu13');nvcc=cuda/'bin/nvcc'
    cmd=[str(nvcc),'-std=c++17','-O2','-shared','-Xcompiler','-fPIC','-arch=sm_120','-I'+str(cccl),'-I'+str(cuda/'include'),str(root/'cuda_conductance.cu'),'-L'+str(cuda/'lib'),str(cuda/'lib/libcusparse.so.12'),'-Xlinker','-rpath','-Xlinker',str(cuda/'lib'),'-o',str(root/'libconductance.so')]
    paths=[nvcc,cuda/'include/cusparse.h',cuda/'lib/libcusparse.so.12']
    toolchain={'source_commit':pin,'git_blobs':expected,'command':cmd,'nvcc_version':subprocess.check_output([str(nvcc),'--version'],text=True),'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,compute_cap,driver_version','--format=csv,noheader'],text=True),'cccl_receipt':cccl_receipt,'key_runtime_inputs':{str(p):{'bytes':p.stat().st_size,'sha256':a.digest(p)} for p in paths},'limits':'Pinned source and key build/runtime identities; complete CUDA dependency wheels are not archived by this diagnostic.'}
    (root/'source.py').write_text(_PP_SOURCE);(root/'probe.py').write_text(_PP_PROBE);(root/'build-inputs.json').write_text(json.dumps(toolchain,indent=2))
    source=publish(['source.py','probe.py','build-inputs.json','cuda_conductance.cu','cuda_conductance.h'])
    with (root/'build.log').open('w') as log:
        process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
        while process.poll() is None:print('PAIRED_PULSE_BUILD_RUNNING',flush=True);time.sleep(5)
        rc=process.returncode
    if rc:publish(['build.log']);print((root/'build.log').read_text()[-3000:],flush=True);raise RuntimeError('Conductance build failed')
    build=publish(['libconductance.so','build.log'])
    receipts=[];reports=[]
    for name,gain,mode in [('zero',0.1,'zero'),('single',0.1,'single'),('pair',0.1,'pair'),('presynaptic_scalar_half',0.05,'pair'),('postsynaptic_scalar_half',0.05,'pair')]:
        with (root/(name+'.log')).open('w') as log:
            result=subprocess.run([sys.executable,'-u',str(root/'probe.py'),str(root),name,str(gain),mode],stdout=log,stderr=subprocess.STDOUT,timeout=120)
        if result.returncode:publish([name+'.log']);print((root/(name+'.log')).read_text()[-3000:],flush=True);raise RuntimeError('Condition failed '+name)
        r=publish([name+'.npz',name+'.json',name+'.log']);receipts.append(r)
        reports.append(json.loads((root/(name+'.json')).read_text()));print('PAIRED_PULSE_ARCHIVED',name,flush=True)
    import numpy as np
    with np.load(root/'presynaptic_scalar_half.npz') as pre,np.load(root/'postsynaptic_scalar_half.npz') as post:
        identical=all(np.array_equal(pre[key],post[key]) for key in pre.files)
    assert identical
    summary={'schema':'native-paired-pulse-software-diagnostic-v1','source_receipt':source,'build_receipt':build,'cccl_receipt':cccl_receipt,'condition_receipts':receipts,'conditions':reports,'presynaptic_and_postsynaptic_scalar_outputs_identical':identical,'contact_mask_admitted':False,'plasticity_enabled':False,'biological_acceptance':False,'limits':'Two-neuron numerical screen, not full MaleCNS or published three-minute optical schedule. Tail-subtracted PPR=1 is a fixed additive-kernel software identity, not a physiological target. Two equal scalar gain reductions cannot reproduce distinct release-probability versus postsynaptic-blockade effects. No mechanism or parameters were fitted. Full CUDA dependency closure not archived; no broad sanitizer or reproducible-build admission.'}
    (root/'report.json').write_text(json.dumps(summary,indent=2));final=publish(['report.json']);print('PAIRED_PULSE_REPORT',json.dumps(summary),flush=True)
run_native_paired_pulse_diagnostic_v2()
'''
code='_PP_PROBE = '+repr(probe)+'\n_PP_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='native_paired_pulse_diagnostic_v2' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='native_paired_pulse_diagnostic_v2',hide_code=False);ctx.run_cell(cell)


