"""Paired 100 ms full visual-bridge check with one changed receptor library."""
from pathlib import Path
import hashlib
import json
import subprocess
import time

import numpy as np


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def event_prefix(path, ticks):
    with Path(path).open('rb') as stream:
        for tick in range(ticks):
            header=np.fromfile(stream, '<u4', 2)
            assert len(header)==2 and int(header[0])==tick
            ids=np.fromfile(stream, '<u4', int(header[1]))
            assert len(ids)==int(header[1])
        return stream.tell()


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    prior=root/'data/derived/visual_feedback_flash_v1/intact_gray'
    spec=json.loads((prior/'spec.json').read_text())
    source=root/'native/visual_feedback_ablation.cpp'
    old_binary=root/'build/visual_feedback_ablation'
    new_binary=root/'build/visual_feedback_ablation_coupled'
    for name in ('native/visual_feedback_ablation.cpp','build/visual_feedback_ablation','build/libfly_photon.so'):
        assert digest(root/name)==spec['inputs'][name]['sha256'], name
    build=['g++','-O2','-std=c++17',str(source),'-L'+str(root/'build'),
           '-lfly_photon_coupled_current_diagnostic','-lretina',
           '-lgraded_heterogeneous','-lmembrane_current_density',
           '-lfly_cuda64_continuous_drive','-levent_conductance',
           '-Wl,-rpath,'+str(root/'build'),'-o',str(new_binary)]
    subprocess.run(build,check=True,capture_output=True,text=True)
    linked=subprocess.run(['ldd',str(new_binary)],check=True,capture_output=True,text=True).stdout
    assert 'libfly_photon_coupled_current_diagnostic.so' in linked
    assert 'libfly_photon.so =>' not in linked
    assert new_binary.is_file() and old_binary.is_file()
    folder=root/'data/derived/visual_feedback_coupled_short_v1'
    folder.mkdir(parents=True,exist_ok=False)
    stimulus=folder/'stimulus.bin'
    source_stimulus=np.memmap(prior/'stimulus.bin',dtype='<f8',mode='r')
    assert len(source_stimulus)==10200
    np.asarray(source_stimulus[:1000]).tofile(stimulus)
    command=list(spec['command'])
    command[0]=str(new_binary)
    command[3]=str(folder/'output.bin')
    command[13]=str(stimulus)
    command[14]='1000'
    start=time.perf_counter()
    result=subprocess.run(command,capture_output=True,text=True,timeout=120)
    (folder/'run.log').write_text(result.stdout+'\n'+result.stderr)
    if result.returncode:raise RuntimeError(f'paired full bridge failed: {result.returncode}: {result.stderr[-1000:]}')
    widths={'':3555*2,'.brain':7370,'.feedback':3377*2,'.recurrent':3555*2,'.remaining':3377*2+3555}
    comparisons={}
    for suffix,width in widths.items():
        old=np.memmap(prior/('output.bin'+suffix),dtype='<f8',mode='r')[:100*width]
        new=np.memmap(folder/('output.bin'+suffix),dtype='<f8',mode='r')
        assert new.size==100*width and np.isfinite(new).all()
        delta=new-old
        comparisons[suffix or 'lamina']={
            'max_abs':float(np.max(np.abs(delta))),
            'rmse':float(np.sqrt(np.mean(delta*delta))),
            'exact':bool(np.array_equal(old,new))}
    old_events=prior/'output.bin.events'
    new_events=folder/'output.bin.events'
    old_bytes=event_prefix(old_events,1000)
    new_bytes=event_prefix(new_events,1000)
    assert new_events.stat().st_size==new_bytes
    events_equal=old_events.open('rb').read(old_bytes)==new_events.read_bytes()
    report={'scope':'Paired 100ms full configured visual bridge; only photon library differs',
            'baseline_manifest':str(prior/'receipt.json'),
            'baseline_binary_sha256':digest(old_binary),
            'candidate_binary_sha256':digest(new_binary),
            'source_sha256':digest(source),
            'baseline_photon_sha256':digest(root/'build/libfly_photon.so'),
            'candidate_photon_sha256':digest(root/'build/libfly_photon_coupled_current_diagnostic.so'),
            'build_command':build,'command':command,'ldd':linked,
            'wall_s':time.perf_counter()-start,'comparisons':comparisons,
            'events_equal':events_equal,'biological_gate_passed':False,
            'limitations':'Gray-only 100ms; no flash or biological acceptance.'}
    report_path=folder/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[source,new_binary,stimulus,report_path,folder/'run.log',root/'tools/check_feedback_bridge_coupled_short.py']
    files.extend(folder/('output.bin'+suffix) for suffix in (*widths.keys(),'.events'))
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('CONFIGURED_BRIDGE_SHORT',json.dumps({'wall_s':report['wall_s'],'events_equal':events_equal,'comparisons':comparisons}),flush=True)
    print('CONFIGURED_BRIDGE_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':run()
