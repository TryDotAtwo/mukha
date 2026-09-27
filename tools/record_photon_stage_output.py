"""Persist the stage timings printed by the instrumented receptor binary."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    original=root/'data/derived/photon_stage_profile_v1'
    binary=original/'libfly_photon_stage_profile.so'
    prior=json.loads((original/'report.json').read_text())
    assert digest(binary)==prior['profile_binary_sha256']
    code='''from pathlib import Path
from profile_photon_coupled_stages import run_library
result,_=run_library(Path('/marimo/fly-project/data/derived/photon_stage_profile_v1/libfly_photon_stage_profile.so'),3377,30000,100)
print('PHOTON_PROFILE_RUN',result,flush=True)
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=root/'tools',
                          capture_output=True,text=True,timeout=120)
    if result.returncode:raise RuntimeError(result.stderr[-2000:])
    match=re.search(r'PHOTON_STAGE_MS h2d=([\d.]+) transduction=([\d.]+) current=([\d.]+) hh=([\d.]+) update=([\d.]+) readback_check=([\d.]+) ticks=(\d+)',result.stdout)
    assert match and int(match.group(7))==100
    names=['h2d','transduction','current','hh','update','readback_check']
    stages={name:float(value) for name,value in zip(names,match.groups()[:6])}
    folder=root/'data/derived/photon_stage_record_v1'
    folder.mkdir(parents=True,exist_ok=False)
    log=folder/'stage_stdout.log'
    log.write_text(result.stdout)
    report={'scope':'Captured 100-step full-resolution CUDA stage output from previously archived instrumented receptor binary',
            'profile_binary_sha256':digest(binary),'prior_report_sha256':digest(original/'report.json'),
            'stage_ms':stages,'sum_stage_ms':sum(stages.values()),'ticks':100,
            'limitations':'Extra synchronization in the instrumented build; one run.'}
    path=folder/'report.json'
    path.write_text(json.dumps(report,indent=2))
    files=[path,log,root/'tools/record_photon_stage_output.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('PHOTON_STAGE_RECORD',json.dumps(report),flush=True)
    print('PHOTON_STAGE_RECORD_ARCHIVE',json.dumps(receipt),flush=True)
    return receipt


if __name__=='__main__':run()
