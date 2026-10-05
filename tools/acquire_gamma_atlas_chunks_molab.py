import marimo._code_mode as cm
code='''def acquire_gamma_atlas_chunks():
    import json,importlib.util,urllib.request,urllib.parse,urllib.error,hashlib,base64
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env');api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('gca','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-gamma-contact-sampling-20261005');chunks=root/'chunks';chunks.mkdir(exist_ok=True)
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=18)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('GAMMA_CHUNKS_RECEIPT',json.dumps(r),flush=True);return r
    (root/'acquire-source.py').write_text(_GAMMA_ACQUIRE_SOURCE);source=publish(['acquire-source.py'])
    a.restore(root,{'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'f4153cc33a77074a13563ed6e2f3213b647f1c91','manifest':'manifests/e0481ebae5f585933edcfbfe16f41d2dc19ead452918ffa16a49d3ed094895f0.json','sha256':'e0481ebae5f585933edcfbfe16f41d2dc19ead452918ffa16a49d3ed094895f0','verified':True})
    plan=json.loads((root/'plan.json').read_text());keys=plan['chunk_keys']
    if len(keys)!=157:raise RuntimeError('Plan scope drift')
    identities=[];receipts=[];total=0
    for start in range(0,len(keys),10):
        names=[]
        for key in keys[start:start+10]:
            name='rois/malecns-subcompartments-v3/256_256_256/'+key;encoded=urllib.parse.quote(name,safe='')
            try:
                with urllib.request.urlopen('https://storage.googleapis.com/storage/v1/b/flyem-male-cns/o/'+encoded,timeout=30) as response:metadata=json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code!=404:raise
                missing={'object':name,'status':'metadata_HTTP404','classification':'unknown until sparse omission semantics verified'}
                local='chunks/'+key+'.missing.json';(root/local).write_text(json.dumps(missing,indent=2));names.append(local);identities.append(missing);continue
            if int(metadata['size'])>4*1024*1024:raise RuntimeError('Chunk byte bound')
            local='chunks/'+key+'.gcs.json';(root/local).write_text(json.dumps(metadata,indent=2));names.append(local)
            with urllib.request.urlopen('https://storage.googleapis.com/download/storage/v1/b/flyem-male-cns/o/'+encoded+'?alt=media&generation='+metadata['generation'],timeout=30) as response:raw=response.read(4*1024*1024+1)
            if len(raw)!=int(metadata['size']) or base64.b64encode(hashlib.md5(raw).digest()).decode()!=metadata['md5Hash']:raise RuntimeError('Published chunk identity mismatch')
            local='chunks/'+key+'.bin';(root/local).write_bytes(raw);names.append(local);total+=len(raw)
            if total>128*1024*1024:raise RuntimeError('Compressed closure byte bound')
            identities.append({'object':name,'generation':metadata['generation'],'bytes':len(raw),'sha256':a.digest(root/local),'path':local})
        segment=f'acquisition-segment-{start:03d}.json'
        (root/segment).write_text(json.dumps({'start':start,'stop':min(start+10,len(keys)),'completed_objects':identities[start:start+10]},indent=2));names.append(segment)
        receipts.append(publish(names));print('GAMMA_CHUNKS_ARCHIVED',min(start+10,len(keys)),len(keys),flush=True)
    report={'schema':'gamma-sparse-atlas-input-closure-v1','source_receipt':source,'objects':identities,'segment_receipts':receipts,'requested_chunks':len(keys),'available_chunks':sum('path' in x for x in identities),'missing_chunks':sum('path' not in x for x in identities),'compressed_bytes':total,'contact_mask_admitted':False,'scope':'Input acquisition only; no missing chunk assumed zero; no contact classification or learning'}
    (root/'acquisition-report.json').write_text(json.dumps(report,indent=2));publish(['acquisition-report.json'])
    print('GAMMA_CHUNK_ACQUISITION_SUMMARY',json.dumps({k:v for k,v in report.items() if k not in ('objects','segment_receipts')}),flush=True)
acquire_gamma_atlas_chunks()
'''
code='_GAMMA_ACQUIRE_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='acquire_gamma_atlas_chunks' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='acquire_gamma_atlas_chunks');ctx.run_cell(cell)

