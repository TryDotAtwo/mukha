import marimo._code_mode as cm
code = '''def gamma_skeleton_bilateral_node_distances():
    import json,importlib.util,urllib.request,datetime
    from pathlib import Path
    import numpy as np,pyarrow as pa,pyarrow.parquet as pq
    from scipy.spatial import cKDTree
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env');api=HfApi();repo='TryDotAtwo/faithful-fly-artifacts'
    assert api.whoami()['name']=='TryDotAtwo' and api.repo_info(repo,repo_type='dataset').private
    spec=importlib.util.spec_from_file_location('geometry_archive','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-gamma-skeleton-bilateral-node-distances-20261005');root.mkdir(exist_ok=True)
    if (root/'source.py').exists():raise RuntimeError('Inspect existing stage')
    a.require_commit_capacity(api,repo,commits_needed=3)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        assert r.get('verified');print('NODE_GEOMETRY_RECEIPT',json.dumps(r),flush=True);return r
    def receipt(commit,manifest):return {'repo_id':repo,'repo_type':'dataset','revision':commit,'manifest':'manifests/'+manifest+'.json','sha256':manifest,'verified':True}
    url='https://male-cns.janelia.org/download/'
    with urllib.request.urlopen(url,timeout=30) as response:html=response.read(2000000)
    text=html.decode();assert 'coordinates specified in 8nm units' in text and 'expressed in voxel units' in text
    (root/'coordinate-source.html').write_bytes(html)
    (root/'source.py').write_text(_BILATERAL_NODE_GEOMETRY_SOURCE)
    (root/'coordinate-convention.json').write_text(json.dumps({'url':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'coordinate_unit_nm':8,'space':'Male CNS EM; unmirrored SWC and synapse coordinates','metric':'Nearest sampled coarse skeleton NODE, not segment/surface/release-site distance','input_commits':['6b93ffad58fa19aa69a7986f02b2ffe3a6500512','0a43cc898d3df9c1e2ed8fd378f0dca5994e284c','b0038a27253d4ebadb32c2ea2d75785085264a91']},indent=2))
    source=publish(['source.py','coordinate-source.html','coordinate-convention.json'])
    skeletons={};input_receipts=[]
    for group,commit,manifest in [('mbon','6b93ffad58fa19aa69a7986f02b2ffe3a6500512','ba3c3d13f86988b9df0201f145f55179163fa918417a1136bf9ebbc3b9d8c065'),('dan','0a43cc898d3df9c1e2ed8fd378f0dca5994e284c','048507293377137a895023acf0b79535f126878dc32fb47faad5fd4f19813f65')]:
        dest=root/group;r=receipt(commit,manifest);a.restore(dest,r);input_receipts.append(r)
        for item in json.loads((dest/'report.json').read_text())['candidates']:
            r=item['input_receipt'];a.restore(dest,r);input_receipts.append(r)
            body=int(item['annotation']['bodyId']);data=np.loadtxt(dest/(str(body)+'.swc'),comments='#',ndmin=2)
            assert data.shape[1]==7 and np.all(np.isfinite(data));skeletons[body]=data[:,2:5]*8
    contacts_receipt=receipt('b0038a27253d4ebadb32c2ea2d75785085264a91','877edae6b332a5e83a8635143cd198f2440389829ef872d7929d6f26a38b3ce7');a.restore(root/'contacts',contacts_receipt)
    table=pq.read_table(root/'contacts'/'classified-candidates-with-kc-subtypes.parquet');assert table.num_rows==41460
    xyz=np.column_stack([table[axis+'_post'].to_numpy() for axis in ('x','y','z')])*8
    body=table['body_post'].to_numpy();assert set(body)=={10704,11402}
    distances={};controls={};direct_checks=0
    for label,pairs in [('mbon',[(10704,10704),(11402,11402)]),('ppl101_L',[(10704,11900),(11402,11900)]),('ppl101_R',[(10704,11327),(11402,11327)]),('ppl102_L',[(10704,11618),(11402,11618)]),('ppl102_R',[(10704,13428),(11402,13428)])]:
        answer=np.full(len(body),np.nan)
        for target,skel in pairs:
            rows=np.flatnonzero(body==target);nodes=skeletons[skel];d,idx=cKDTree(nodes).query(xyz[rows],workers=1);answer[rows]=d
            for local in np.linspace(0,len(rows)-1,17,dtype=int):
                expected=np.linalg.norm(nodes-xyz[rows[local]],axis=1).min();assert np.isclose(d[local],expected,rtol=1e-12,atol=1e-8);direct_checks+=1
        assert np.all(np.isfinite(answer));distances[label]=answer;table=table.append_column('nearest_'+label+'_coarse_node_nm',pa.array(answer))
    pq.write_table(table,root/'contacts-with-node-distances.parquet',compression='zstd')
    frame=table.select(['body_post','sampling_status_provisional']+['nearest_'+label+'_coarse_node_nm' for label in distances]).to_pandas()
    strata=[]
    for (target,status),group in frame.groupby(['body_post','sampling_status_provisional'],observed=True):
        row={'body_post':int(target),'status':status,'contacts':len(group)}
        for label in distances:
            values=group['nearest_'+label+'_coarse_node_nm'].to_numpy();row[label+'_quantiles_nm']=dict(zip(['min','p25','median','p75','p95','max'],map(float,np.quantile(values,[0,.25,.5,.75,.95,1]))))
        strata.append(row)
    report={'contacts':len(body),'source_receipt':source,'input_receipts':input_receipts+[contacts_receipt],'direct_full_node_scan_checks':direct_checks,'strata':strata,'contact_mask_admitted':False,'plasticity_enabled':False,'limits':'Nearest coarse sampled-node distances only. No neurite surface, segment distance, synaptic connectivity or DAN release localization inferred. All rows and unknown atlas classifications retained.'}
    (root/'report.json').write_text(json.dumps(report,indent=2));final=publish(['contacts-with-node-distances.parquet','report.json']);print('NODE_GEOMETRY_REPORT',json.dumps(report),flush=True)
gamma_skeleton_bilateral_node_distances()
'''
code='_BILATERAL_NODE_GEOMETRY_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='gamma_skeleton_bilateral_node_distances' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='gamma_skeleton_bilateral_node_distances',hide_code=False);ctx.run_cell(cell)

