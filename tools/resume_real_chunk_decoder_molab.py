import marimo._code_mode as cm
code='''def resume_real_chunk_decoder():
    import json,importlib.util,subprocess,sys
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env');api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('rrc','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-real-atlas-chunk-20261005')
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=2)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('REAL_CHUNK_RESUME_RECEIPT',json.dumps(r),flush=True);return r
    a.restore(root,{'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'716ec2b80fa32b97643da42ef5c92a8a14da1c34','manifest':'manifests/73ab115ac7c1b712735bfbe17388511631679cf45be6fb428051ac23cf007864.json','sha256':'73ab115ac7c1b712735bfbe17388511631679cf45be6fb428051ac23cf007864','verified':True})
    old=(root/'decoder-probe.py').read_text()
    old_line=next(line for line in old.splitlines() if line.startswith('if raw[:2]'))
    revised=old.replace(old_line,'if raw[:2]==bytes((31,139)):raw=gzip.decompress(raw)')
    (root/'decoder-probe-v2.py').write_text(revised)
    (root/'resume-source.py').write_text(_REAL_CHUNK_RESUME_SOURCE)
    source=publish(['decoder-probe.py','probe-output.json','decoder-probe-v2.py','resume-source.py'])
    with (root/'probe-output-v2.json').open('w') as log:result=subprocess.run([sys.executable,str(root/'decoder-probe-v2.py')],stdout=log,stderr=subprocess.STDOUT,timeout=90)
    if result.returncode:print((root/'probe-output-v2.json').read_text()[-3000:],flush=True);raise RuntimeError('Decoder v2 failed')
    report={'schema':'real-atlas-chunk-decoder-probe-v2','source_receipt':source,'chunk_commit':'716ec2b80fa32b97643da42ef5c92a8a14da1c34','config':json.loads((root/'config.json').read_text()),'decode':json.loads((root/'probe-output-v2.json').read_text()),'scope':'One actual source-pinned chunk; candidate coordinate mapping unadmitted; no full contact mask or learning','repair':'Nested source serialization produced non-ASCII bytes literal; v2 uses integer byte constructor; original failure archived before rerun'}
    (root/'report-v2.json').write_text(json.dumps(report,indent=2));publish(['probe-output-v2.json','report-v2.json'])
    print('REAL_CHUNK_REPORT_V2',json.dumps(report),flush=True)
resume_real_chunk_decoder()
'''
code='_REAL_CHUNK_RESUME_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='resume_real_chunk_decoder' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='resume_real_chunk_decoder');ctx.run_cell(cell)

