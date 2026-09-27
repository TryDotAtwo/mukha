"""Paired full-MaleCNS visual flashes in the original configured bridge."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import time

import numpy as np


WIDTHS={'':3555*2,'.brain':7370,'.feedback':3377*2,
        '.recurrent':3555*2,'.remaining':3377*2+3555}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


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


def inspect(path,width):
    values=np.memmap(path,dtype='<f8',mode='r')
    assert values.size==1020*width and np.isfinite(values).all(),path
    del values
    return {'bytes':path.stat().st_size,'sha256':digest(path)}


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    baseline=root/'data/derived/visual_feedback_flash_v1'
    out=root/'data/derived/visual_feedback_coupled_flash_v1'
    out.mkdir(parents=True,exist_ok=True)
    bridge=root/'build/visual_feedback_ablation_coupled'
    receptor=root/'build/libfly_photon_coupled_current_diagnostic.so'
    source=root/'native/visual_feedback_ablation.cpp'
    short=json.loads((root/'data/derived/visual_feedback_coupled_short_v1/report.json').read_text())
    assert digest(bridge)==short['candidate_binary_sha256']
    assert digest(source)==short['source_sha256']
    assert digest(receptor)==short['candidate_photon_sha256']
    assert bridge.stat().st_mode & 0o100
    existing=subprocess.run(['ps','-eo','comm'],capture_output=True,text=True,check=True).stdout
    assert 'visual_feedback' not in existing,'Another visual bridge process is active'
    spec={'scope':'Full configured visual bridge, original profile/routes/graph, only receptor numerical implementation changed',
          'baseline_folder':str(baseline),'short_report':str(root/'data/derived/visual_feedback_coupled_short_v1/report.json'),
          'bridge_sha256':digest(bridge),'receptor_sha256':digest(receptor),'source_sha256':digest(source),
          'conditions':['gray','light','dark'],'seed':19503,'dt_ms':0.1,'ticks':10200,
          'biological_gate_passed':False,'limitations':'One seed; uncalibrated flux and engineered gains; diagnostic only.'}
    spec_path=out/'spec.json'
    if spec_path.exists():assert json.loads(spec_path.read_text())==spec
    else:spec_path.write_text(json.dumps(spec,indent=2))
    for name in ('gray','light','dark'):
        old=baseline/('intact_'+name)
        old_spec=json.loads((old/'spec.json').read_text())
        assert digest(root/'build/visual_feedback_ablation')==old_spec['inputs']['build/visual_feedback_ablation']['sha256']
        assert digest(source)==old_spec['inputs']['native/visual_feedback_ablation.cpp']['sha256']
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
            print('CONFIGURED_FLASH_ALREADY_ARCHIVED',name,json.loads(receipt_path.read_text()),flush=True)
            continue
        assert not any(folder.iterdir()),'Partial condition; inspect before retry'
        stimulus=folder/'stimulus.bin'
        shutil.copyfile(old/'stimulus.bin',stimulus)
        assert digest(stimulus)==digest(old/'stimulus.bin')
        prefix=folder/'output.bin'
        args=list(old_spec['command'])
        args[0]=str(bridge)
        args[3]=str(prefix)
        args[13]=str(stimulus)
        assert args[14]=='10200' and args[20]=='on' and args[21]=='feedback-intact'
        print('CONFIGURED_FLASH_START',name,flush=True)
        start=time.monotonic()
        log_path=folder/'run.log'
        with log_path.open('w') as log:
            process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            for line in process.stdout:
                log.write(line)
                log.flush()
                if 'native tick' in line:print('CONFIGURED_FLASH_PROGRESS',name,line.strip(),flush=True)
                if time.monotonic()-start>540:
                    process.terminate();process.wait()
                    raise RuntimeError(f'{name} exceeded 540s')
            if process.wait():raise RuntimeError(f'{name} native bridge failed; see {log_path}')
        outputs={}
        for suffix,width in WIDTHS.items():
            path=Path(str(prefix)+suffix)
            outputs[path.name]=inspect(path,width)
        events=Path(str(prefix)+'.events')
        spikes=check_events(events)
        outputs[events.name]={'bytes':events.stat().st_size,'sha256':digest(events)}
        if name!='gray':
            gray=out/'gray/output.bin'
            for suffix,width in WIDTHS.items():
                with Path(str(prefix)+suffix).open('rb') as a,Path(str(gray)+suffix).open('rb') as b:
                    assert a.read(500*width*8)==b.read(500*width*8),f'preflash {name}{suffix}'
        report={'condition':name,'wall_s':time.monotonic()-start,'spikes':spikes,
                'command':args,'old_spec_sha256':digest(old/'spec.json'),
                'stimulus_matches_old':True,'outputs':outputs,
                'preflash_gray_equal':True if name!='gray' else None,
                'biological_gate_passed':False}
        report_path.write_text(json.dumps(report,indent=2))
        print('CONFIGURED_FLASH_CONDITION_COMPLETE',name,json.dumps({'wall_s':report['wall_s'],'spikes':spikes}),flush=True)
        files=[spec_path,source,bridge,receptor,stimulus,log_path,report_path,
               root/'tools/run_feedback_bridge_coupled_flash.py']
        files.extend(folder/file for file in outputs)
        manifest={'schema':'faithful-fly-artifacts-v1',
                  'scope':f'Full configured MaleCNS visual {name} flash with coupled-current receptor, one seed; not biological validation',
                  'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
        receipt=publish(root,manifest)
        receipt_path.write_text(json.dumps(receipt,indent=2))
        print('CONFIGURED_FLASH_ARCHIVE',name,json.dumps(receipt),flush=True)
    return {'complete':True,'conditions':['gray','light','dark']}


if __name__=='__main__':run()
