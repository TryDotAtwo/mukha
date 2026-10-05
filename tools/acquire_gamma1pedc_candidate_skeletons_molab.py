import marimo._code_mode as cm
code = '''def acquire_gamma1pedc_candidate_skeletons():
    import json,importlib.util,urllib.request,urllib.parse,base64,hashlib,collections
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    import pyarrow.feather as feather
    import numpy as np
    load_dotenv('/marimo/.env');api=HfApi();repo='TryDotAtwo/faithful-fly-artifacts'
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info(repo,repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('pedc_archive','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-gamma1pedc-candidate-skeletons-20261005');root.mkdir(exist_ok=True)
    if (root/'source.py').exists():raise RuntimeError('Inspect existing anatomy stage')
    a.require_commit_capacity(api,repo,commits_needed=12)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication failed')
        print('PEDC_SKELETON_RECEIPT',json.dumps(r),flush=True);return r
    (root/'source.py').write_text(_PEDC_SKELETON_SOURCE);source=publish(['source.py'])
    inputs={'repo_id':repo,'repo_type':'dataset','revision':'730ad0486c321891428c3f4499818c4accedb474','manifest':'manifests/b91d7732abea2724fc0ca7b59f338eb7ebe00b911998be0d8d6b09bb87109d6b.json','sha256':'b91d7732abea2724fc0ca7b59f338eb7ebe00b911998be0d8d6b09bb87109d6b','verified':True}
    a.restore(root/'annotations',inputs)
    nodes=feather.read_table(root/'annotations'/'nodes.feather',columns=['bodyId','class','type','instance']).to_pylist()
    assert len(nodes)==167216
    candidates=[r for r in nodes if 'y1pedc' in str(r['instance']).lower() or 'gamma1pedc' in str(r['instance']).lower()]
    assert {10704,11402}.issubset({int(r['bodyId']) for r in candidates})
    if not 2<=len(candidates)<=10:raise RuntimeError('Review unexpected candidate scope')
    (root/'plan.json').write_text(json.dumps({'annotation_receipt':inputs,'candidates':candidates,'selection':'Exact source annotation y1pedc/gamma1pedc substring; candidates only','max_object_bytes':128*1024*1024,'units_admitted':False,'plasticity_enabled':False},indent=2))
    plan=publish(['plan.json']);print('PEDC_CANDIDATES',json.dumps(candidates),flush=True)
    results=[];receipts=[]
    for row in candidates:
        body=int(row['bodyId']);obj=f'v1.0/segmentation/skeletons-malecns/skeletons-swc/{body}.swc';encoded=urllib.parse.quote(obj,safe='')
        with urllib.request.urlopen('https://storage.googleapis.com/storage/v1/b/flyem-male-cns/o/'+encoded,timeout=30) as response:meta=json.load(response)
        if int(meta['size'])>128*1024*1024:raise RuntimeError('Skeleton size bound')
        with urllib.request.urlopen('https://storage.googleapis.com/download/storage/v1/b/flyem-male-cns/o/'+encoded+'?alt=media&generation='+meta['generation'],timeout=60) as response:raw=response.read(128*1024*1024+1)
        if len(raw)!=int(meta['size']) or base64.b64encode(hashlib.md5(raw).digest()).decode()!=meta['md5Hash']:raise RuntimeError('Skeleton published identity mismatch')
        name=str(body)+'.swc';(root/name).write_bytes(raw);(root/(name+'.gcs.json')).write_text(json.dumps(meta,indent=2))
        receipt=publish([name,name+'.gcs.json']);receipts.append(receipt)
        data=np.loadtxt(root/name,comments='#',ndmin=2);assert data.shape[1]==7 and len(data)>0
        assert np.all(np.isfinite(data))
        assert np.all(data[:,[0,1,6]]==np.floor(data[:,[0,1,6]]))
        ids=data[:,0].astype(np.int64);parents=data[:,6].astype(np.int64);assert len(np.unique(ids))==len(ids)
        lookup=dict(zip(map(int,ids),map(int,parents)));assert all(p==-1 or p in lookup for p in lookup.values())
        seen=set();cycles=[]
        for start in lookup:
            trail=set();point=start
            while point!=-1 and point not in seen:
                if point in trail:cycles.append(point);break
                trail.add(point);point=lookup[point]
            seen.update(trail)
        assert not cycles
        assert np.all(data[:,5]>=0)
        result={'annotation':row,'object':obj,'generation':meta['generation'],'bytes':len(raw),'sha256':a.digest(root/name),'input_receipt':receipt,'swc_nodes':len(data),'roots':int(np.count_nonzero(parents==-1)),'swc_type_counts':{str(k):int(v) for k,v in zip(*np.unique(data[:,1].astype(np.int64),return_counts=True))},'coordinate_min':data[:,2:5].min(axis=0).tolist(),'coordinate_max':data[:,2:5].max(axis=0).tolist(),'comments':[line for line in raw.decode().splitlines() if line.startswith('#')][:20],'syntax_parent_cycle_finite_checks_passed':True,'units_admitted':False,'axon_dendrite_partition_admitted':False,'biological_morphology_complete':False}
        (root/(str(body)+'-audit.json')).write_text(json.dumps(result,indent=2));audit=publish([str(body)+'-audit.json']);result['audit_receipt']=audit;results.append(result)
        print('PEDC_SKELETON_AUDIT',json.dumps(result),flush=True)
    report={'schema':'gamma1pedc-candidate-skeleton-acquisition-v1','source_receipt':source,'plan_receipt':plan,'annotation_receipt':inputs,'candidates':results,'skeleton_receipts':receipts,'contact_mask_admitted':False,'plasticity_enabled':False,'limits':'Source-name matched candidates and structural SWC checks only. No complete morphology, coordinate registration/units, axon-dendrite partition, DAN release-site localization or gamma1pedc mask admission.'}
    (root/'report.json').write_text(json.dumps(report,indent=2));final=publish(['report.json']);print('PEDC_SKELETON_REPORT',json.dumps(report),flush=True)
acquire_gamma1pedc_candidate_skeletons()
'''
code='_PEDC_SKELETON_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground work active')
    if any(c.name=='gamma1pedc_candidate_skeletons' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='gamma1pedc_candidate_skeletons',hide_code=False);ctx.run_cell(cell)

