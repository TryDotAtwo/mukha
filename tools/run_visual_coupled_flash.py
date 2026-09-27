"""Run/verify/archive full-CNS flash conditions with coupled-current receptors."""
from pathlib import Path
import hashlib
import json
import subprocess
import time

import numpy as np


WIDTHS={'':3555*2,'.brain':7370,'.feedback':3377*2,'.recurrent':3555*2}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def check_events(path):
    count=0
    with Path(path).open('rb') as stream:
        for tick in range(10200):
            header=np.fromfile(stream,'<u4',2)
            assert len(header)==2 and int(header[0])==tick and int(header[1])<=167216
            ids=np.fromfile(stream,'<u4',int(header[1]))
            assert len(ids)==int(header[1]) and np.all(ids<167216)
            count+=len(ids)
        assert not stream.read(1)
    return count


def inspect_file(path,suffix):
    value=np.memmap(path,dtype='<f8',mode='r')
    assert value.size==1020*WIDTHS[suffix],(path,value.size)
    assert np.isfinite(value).all(),path
    del value
    return {'bytes':path.stat().st_size,'sha256':digest(path)}


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    out=root/'data/derived/visual_coupled_flash_v1'
    out.mkdir(parents=True,exist_ok=True)
    bridge=root/'build/explicit_capacitance_bridge_coupled'
    source=root/'native/explicit_capacitance_bridge.cpp'
    receptor=root/'build/libfly_photon_coupled_current_diagnostic.so'
    short=json.loads((root/'data/derived/visual_bridge_coupled_short_v1/report.json').read_text())
    assert digest(bridge)==short['runs'][1]['binary_sha256']
    assert digest(source)==short['source_sha256']
    assert digest(receptor)==short['coupled_photon_sha256']
    assert bridge.is_file() and bridge.stat().st_mode & 0o100
    existing=subprocess.run(['ps','-eo','comm'],capture_output=True,text=True,check=True).stdout
    assert 'explicit_capaci' not in existing,'Another visual bridge process is active'
    base=json.loads((root/'data/derived/noise_selected_recording_v1/manifest.json').read_text())['command']
    assert len(base)==16
    spec={'scope':'Native full-MaleCNS gray/light/dark flash with a separate coupled-current exact-gate receptor variant',
          'conditions':['gray','light','dark'],'seed':19503,
          'dt_neural_ms':0.1,'gray_before_ms':500,'pulse_ms':20,'gray_after_ms':500,
          'photon_rate_gray_s':50000,'light_s':100000,'dark_s':0,
          'mapped_visual_receptors':1843,'full_receptor_population':3377,
          'graph_input_sha256':digest(Path(base[1])),
          'rays_sha256':digest(Path(base[2])),
          'outgoing_sha256':digest(Path(base[11])),
          'incoming_sha256':digest(root/'data/derived/recurrent_lamina_bridge_v1/incoming.bin'),
          'bridge_sha256':digest(bridge),'receptor_sha256':digest(receptor),
          'receptor_numerical_change':'exact HH gates and current voltage coupling within membrane substeps',
          'biological_gate_passed':False,
          'limitations':'Uncalibrated light, engineering neural gains, male/female transfer, short adaptation, no body/KSP.'}
    spec_path=out/'spec.json'
    if spec_path.exists():
        assert json.loads(spec_path.read_text())==spec,'Spec changed during run'
    else:
        spec_path.write_text(json.dumps(spec,indent=2))
    for name,level in [('gray',0.5),('light',1.0),('dark',0.0)]:
        folder=out/name
        folder.mkdir(exist_ok=True)
        report_path=folder/'report.json'
        receipt_path=folder/'receipt.json'
        if receipt_path.exists():
            report=json.loads(report_path.read_text())
            assert report['condition']==name
            for file,entry in report['outputs'].items():
                path=folder/file
                assert path.stat().st_size==entry['bytes'] and digest(path)==entry['sha256']
            print('COUPLED_FLASH_ALREADY_ARCHIVED',name,json.loads(receipt_path.read_text()),flush=True)
            continue
        assert not report_path.exists(),'Completed condition lacks archive receipt; inspect before retry'
        assert not any(folder.iterdir()),'Partial condition exists; inspect before retry'
        stimulus=np.full(10200,0.5,np.float64)
        stimulus[5000:5200]=level
        stimulus_path=folder/'stimulus.bin'
        stimulus.tofile(stimulus_path)
        prefix=folder/'output.bin'
        args=list(base)
        args[0]=str(bridge)
        args[3]=str(prefix)
        args[13]=str(stimulus_path)
        args[14]='10200'
        args.extend([str(root/'data/derived/recurrent_lamina_bridge_v1/incoming.bin'),'0.000001'])
        print('COUPLED_FLASH_START',name,flush=True)
        start=time.monotonic()
        log_path=folder/'run.log'
        with log_path.open('w') as log:
            process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            for line in process.stdout:
                log.write(line)
                log.flush()
                if 'native tick' in line:
                    print('COUPLED_FLASH_PROGRESS',name,line.strip(),flush=True)
                if time.monotonic()-start>540:
                    process.terminate();process.wait()
                    raise RuntimeError(f'{name} episode exceeded 540s')
            if process.wait()!=0:
                raise RuntimeError(f'{name} native bridge failed; see {log_path}')
        outputs={}
        for suffix in WIDTHS:
            path=Path(str(prefix)+suffix)
            outputs[path.name]=inspect_file(path,suffix)
        event_path=Path(str(prefix)+'.events')
        spikes=check_events(event_path)
        outputs[event_path.name]={'bytes':event_path.stat().st_size,'sha256':digest(event_path)}
        if name!='gray':
            gray=out/'gray'/'output.bin'
            for suffix,width in WIDTHS.items():
                with Path(str(prefix)+suffix).open('rb') as a,Path(str(gray)+suffix).open('rb') as b:
                    length=500*width*8
                    assert a.read(length)==b.read(length),f'{name}{suffix} preflash mismatch'
        report={'condition':name,'wall_s':time.monotonic()-start,'spikes':spikes,
                'command':args,'outputs':outputs,'preflash_gray_equal':True if name!='gray' else None,
                'biological_gate_passed':False}
        report_path.write_text(json.dumps(report,indent=2))
        print('COUPLED_FLASH_CONDITION_COMPLETE',name,json.dumps({'wall_s':report['wall_s'],'spikes':spikes}),flush=True)
        files=[spec_path,source,bridge,receptor,stimulus_path,log_path,report_path]
        files.extend(folder/file for file in outputs)
        manifest={'schema':'faithful-fly-artifacts-v1',
                  'scope':f'Full-MaleCNS visual coupled-current {name} flash condition, single seed; not biological validation',
                  'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
        receipt=publish(root,manifest)
        receipt_path.write_text(json.dumps(receipt,indent=2))
        print('COUPLED_FLASH_ARCHIVE',name,json.dumps(receipt),flush=True)
    return {'conditions':['gray','light','dark'],'complete':True}


if __name__=='__main__':
    run()
