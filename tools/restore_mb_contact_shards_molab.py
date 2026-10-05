import marimo._code_mode as cm
code='''def restore_mb_contact_shards():
    import json,importlib.util
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env');api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('rs','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-mb-contact-shards-20261005');root.mkdir(exist_ok=True)
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=2)
    def publish(name):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{name:{'bytes':(root/name).stat().st_size,'sha256':a.digest(root/name)}}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('SHARD_RESTORE_RECEIPT',json.dumps(r),flush=True);return r
    (root/'source.py').write_text(_SHARD_RESTORE_SOURCE);source=publish('source.py')
    receipt={'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'633002a94ba6f474f65a482a69549623021ac7b3','manifest':'manifests/f7b6479c91af427831e9bc620accb592c9bc20dc04774cb01a920c751e50e155.json','sha256':'f7b6479c91af427831e9bc620accb592c9bc20dc04774cb01a920c751e50e155','verified':True}
    a.restore(root/'original',receipt)
    original=json.loads((root/'original'/'report.json').read_text())
    for i,shard in enumerate(original['shard_receipts']):
        a.restore(root/f'shard-{i}',shard)
        print('RESTORED_CONTACT_SHARD',i,flush=True)
    import pyarrow.parquet as pq
    rows=0;files=[]
    for p in sorted(root.glob('shard-*/*.parquet')):
        meta=pq.read_metadata(p);rows+=meta.num_rows
        files.append({'path':str(p),'rows':meta.num_rows,'schema':str(meta.schema.to_arrow_schema())})
    if rows!=463640 or len(files)!=5:raise RuntimeError('Contact closure mismatch')
    report={'schema':'verified-mb-contact-restore-v1','source_receipt':source,'original_receipt':receipt,'files':files,'contacts':rows,'volume_reader_packages':{n:importlib.util.find_spec(n) is not None for n in ('cloudvolume','compressed_segmentation','numpy','pyarrow')},'contact_mask_admitted':False}
    (root/'restore-report.json').write_text(json.dumps(report,indent=2));publish('restore-report.json')
    print('SHARD_RESTORE_REPORT',json.dumps(report),flush=True)
restore_mb_contact_shards()
'''
code='_SHARD_RESTORE_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='restore_mb_contact_shards' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='restore_mb_contact_shards');ctx.run_cell(cell)

