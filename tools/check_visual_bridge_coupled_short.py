"""Paired 100-ms full-CNS visual bridge with only receptor library changed."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def check_events(path,ticks):
    total=0
    with Path(path).open('rb') as stream:
        for tick in range(ticks):
            header=np.fromfile(stream,'<u4',2)
            assert len(header)==2 and int(header[0])==tick and int(header[1])<=167216
            ids=np.fromfile(stream,'<u4',int(header[1]))
            assert len(ids)==int(header[1]) and np.all(ids<167216)
            total+=len(ids)
        assert not stream.read(1)
    return total


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import digest,publish
    output=root/'data/derived/visual_bridge_coupled_short_v1'
    output.mkdir(parents=True,exist_ok=True)
    assert sorted(p.name for p in output.iterdir()) in ([],['gray_stimulus.bin']), 'Refusing to overwrite run outputs'
    source=root/'native/explicit_capacitance_bridge.cpp'
    original=root/'build/explicit_capacitance_bridge'
    coupled=root/'build/explicit_capacitance_bridge_coupled'
    command=['g++','-O2','-std=c++17',str(source),'-L'+str(root/'build'),
             '-lfly_photon_coupled_current_diagnostic','-lretina',
             '-lgraded_heterogeneous','-lmembrane_current_density',
             '-lfly_cuda64_continuous_drive','-levent_conductance',
             '-Wl,-rpath,'+str(root/'build'),'-o',str(coupled)]
    subprocess.run(command,check=True,capture_output=True,text=True)
    linked=subprocess.run(['ldd',str(coupled)],check=True,capture_output=True,text=True).stdout
    assert 'libfly_photon_coupled_current_diagnostic.so' in linked
    assert 'libfly_photon.so =>' not in linked
    assert original.is_file()
    original_sha=sha(original)
    original.chmod(original.stat().st_mode | stat.S_IXUSR)
    assert sha(original)==original_sha and os.access(original,os.X_OK)
    base=json.loads((root/'data/derived/noise_selected_recording_v1/manifest.json').read_text())['command']
    assert len(base)==16 and base[14]=='1000'
    stimulus=np.full(1000,0.5,np.float64)
    stimulus_path=output/'gray_stimulus.bin'
    stimulus.tofile(stimulus_path)
    incoming=root/'data/derived/recurrent_lamina_bridge_v1/incoming.bin'
    records=[]
    data={}
    widths={'':3555*2,'.brain':7370,'.feedback':3377*2,'.recurrent':3555*2}
    for name,exe in [('baseline',original),('coupled',coupled)]:
        prefix=output/(name+'.bin')
        args=list(base)
        args[0]=str(exe)
        args[3]=str(prefix)
        args[13]=str(stimulus_path)
        args.extend([str(incoming),'0.000001'])
        start=time.perf_counter()
        process=subprocess.run(args,capture_output=True,text=True,timeout=120)
        if process.returncode:
            print('VISUAL_BRIDGE_RUN_ERROR',name,process.stdout[-1000:],process.stderr[-3000:],flush=True)
            raise RuntimeError(f'{name} bridge failed: {process.returncode}')
        (output/(name+'.log')).write_text(process.stdout+'\n'+process.stderr)
        rec={'condition':name,'wall_s':time.perf_counter()-start,'binary_sha256':sha(exe),
             'command':args,'files':{}}
        for suffix,width in widths.items():
            path=Path(str(prefix)+suffix)
            values=np.memmap(path,dtype='<f8',mode='r')
            assert values.size==100*width and np.isfinite(values).all(),(name,suffix,values.size)
            data[(name,suffix)]=np.asarray(values).copy()
            rec['files'][path.name]={'bytes':path.stat().st_size,'sha256':sha(path)}
            del values
        event_path=Path(str(prefix)+'.events')
        rec['spikes']=check_events(event_path,1000)
        rec['files'][event_path.name]={'bytes':event_path.stat().st_size,'sha256':sha(event_path)}
        records.append(rec)
        print('VISUAL_BRIDGE_SHORT_CASE',json.dumps({'condition':name,'wall_s':rec['wall_s'],'spikes':rec['spikes']}),flush=True)
    comparisons={}
    for suffix in widths:
        a=data[('baseline',suffix)]
        b=data[('coupled',suffix)]
        delta=b-a
        comparisons[suffix or 'receptor_and_lamina']={'max_abs_difference':float(np.max(np.abs(delta))),
            'rmse':float(np.sqrt(np.mean(delta*delta))),
            'exact':bool(np.array_equal(a,b))}
    report={'scope':'Paired 100ms native complete CNS visual bridge; same inputs/graphs/other libraries, receptor numerical variant only',
            'source_sha256':sha(source),'baseline_photon_sha256':sha(root/'build/libfly_photon.so'),
            'coupled_photon_sha256':sha(root/'build/libfly_photon_coupled_current_diagnostic.so'),
            'build_command':command,'linked_libraries':linked,'runs':records,
            'comparisons':comparisons,'biological_gate_passed':False,
            'limitations':'Gray-only 100ms; engineering integration, not biological flash validation.'}
    report_path=output/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[report_path,stimulus_path,source,coupled]
    for name in ('baseline','coupled'):
        files.append(output/(name+'.log'))
        files.extend(Path(str(output/(name+'.bin'))+suffix) for suffix in (*widths.keys(),'.events'))
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('VISUAL_BRIDGE_SHORT_COMPARISON',json.dumps(comparisons),flush=True)
    print('VISUAL_BRIDGE_SHORT_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':
    run()
