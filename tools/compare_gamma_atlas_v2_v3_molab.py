import marimo._code_mode as cm
probe=r'''import sys,json,gzip,struct,itertools
from pathlib import Path
sys.path.insert(0,'/tmp/fly-atlas-decoder-20261005/runtime')
import numpy as np,compressed_segmentation as c,pyarrow as pa,pyarrow.parquet as pq
root=Path('/tmp/fly-gamma-contact-sampling-v2-20261005')
closure=json.loads((root/'acquisition-report.json').read_text())
volumes={};checks=0
def independent(words,shape,x,y,z):
    gx,gy,gz=[(v+7)//8 for v in shape];b=x//8+gx*(y//8+gy*(z//8));h0=int(words[2*b]);h1=int(words[2*b+1]);bits=h0>>24;lookup=h0&0xffffff
    assert bits in (0,1,2,4,8,16,32)
    bit=bits*(x%8+8*(y%8+8*(z%8)));index=0 if bits==0 else (int(words[h1+bit//32])>>(bit%32))&((1<<bits)-1);off=lookup+2*index
    return int(words[off])+(int(words[off+1])<<32)
for item in closure['objects']:
    key=item['object'].rsplit('/',1)[1];ranges=[tuple(map(int,p.split('-'))) for p in key.split('_')];start=np.array([p[0] for p in ranges]);shape=tuple(p[1]-p[0] for p in ranges)
    if 'path' not in item:volumes[tuple(start//64)]=None;continue
    raw=(root/item['path']).read_bytes()
    if raw[:2]==bytes((31,139)):raw=gzip.decompress(raw)
    assert struct.unpack_from('<I',raw,0)[0]==1
    out=c.decompress(raw,shape,dtype=np.uint64,block_size=(8,8,8),order='F')
    words=np.frombuffer(raw[4:],dtype='<u4')
    for point in itertools.product(*[(0,min(7,s-1),min(8,s-1),s-1) for s in shape]):
        assert independent(words,shape,*point)==int(out[point]);checks+=1
    assert np.all(out<=199)
    volumes[tuple(start//64)]=out
    print('DECODED_CHUNK',len(volumes),len(closure['objects']),flush=True)
table=pq.read_table(root/'candidate-contacts.parquet');n=table.num_rows;assert n==41460
offsets=np.array(list(itertools.product((-1,0,1),repeat=3)),dtype=np.int64);center=int(np.flatnonzero(np.all(offsets==0,axis=1))[0]);labels={}
for side in ('pre','post'):
    xyz=np.column_stack([table[axis+'_'+side].to_numpy() for axis in ('x','y','z')]).astype(np.int64)//32
    query=(xyz[:,None,:]+offsets[None,:,:]).reshape(-1,3);chunks=query//64;local=query%64;answer=np.full(len(query),-1,dtype=np.int64)
    unique,inverse=np.unique(chunks,axis=0,return_inverse=True)
    for i,key in enumerate(unique):
        assert tuple(key) in volumes,'Missing planned chunk'
        volume=volumes[tuple(key)]
        if volume is None:continue
        selected=np.flatnonzero(inverse==i);pos=local[selected];answer[selected]=volume[pos[:,0],pos[:,1],pos[:,2]]
    labels[side]=answer.reshape(n,27)
body=table['body_post'].to_numpy();expected=np.where(body==10704,190,195)
pre=labels['pre'][:,center];post=labels['post'][:,center]
unknown=np.any(labels['pre']<0,axis=1)|np.any(labels['post']<0,axis=1)
robust=np.all(labels['pre']==expected[:,None],axis=1)&np.all(labels['post']==expected[:,None],axis=1)
both=(pre==expected)&(post==expected)
near=np.any(labels['pre']==expected[:,None],axis=1)|np.any(labels['post']==expected[:,None],axis=1)
status=np.where(unknown,'unknown-neighborhood',np.where(robust,'robust-expected-g1',np.where(both,'center-g1-boundary-sensitive',np.where(near,'near-g1-boundary-sensitive','outside-expected-g1'))))
counts={str(k):int(v) for k,v in zip(*np.unique(status,return_counts=True))};assert sum(counts.values())==n
result=table.append_column('atlas_pre_center',pa.array(pre)).append_column('atlas_post_center',pa.array(post)).append_column('expected_g1_label_provisional',pa.array(expected)).append_column('sampling_status_provisional',pa.array(status)).append_column('pre_neighborhood_labels',pa.array(labels['pre'].tolist(),type=pa.list_(pa.int64()))).append_column('post_neighborhood_labels',pa.array(labels['post'].tolist(),type=pa.list_(pa.int64())))
pq.write_table(result,root/'classified-candidates.parquet',compression='zstd')
frame=result.select(['body_post','primary_post','atlas_pre_center','atlas_post_center','sampling_status_provisional']).to_pandas()
groups=frame.groupby(['body_post','primary_post','atlas_pre_center','atlas_post_center','sampling_status_provisional'],observed=True,dropna=False).size().reset_index(name='contacts');groups.to_csv(root/'classification-strata.csv',index=False)
summary={'schema':'gamma-contact-provisional-volume-classification-v1','contacts':n,'status_counts':counts,'pre_center_counts':{str(k):int(v) for k,v in zip(*np.unique(pre,return_counts=True))},'post_center_counts':{str(k):int(v) for k,v in zip(*np.unique(post,return_counts=True))},'both_centers_expected_g1':int(both.sum()),'robust_expected_g1':int(robust.sum()),'boundary_near_g1':int(near.sum()),'unknown_neighborhood':int(unknown.sum()),'independent_decoder_points':checks,'available_chunks':closure['available_chunks'],'missing_chunks':closure['missing_chunks'],'boundary_radius_nm':256,'source_coordinate_units_assumed_nm':8,'atlas_version':2,'hemisphere_mapping_provisional':{'10704':190,'11402':195},'contact_mask_admitted':False,'plasticity_enabled':False,'limits':'Provisional voxel sampling only. No independent bilateral landmark/DAN-territory validation, gamma1-pedc semantics, version sensitivity, receptor or physiological validation. Missing chunks remain unknown, not zero. All contacts retained.'}
v3=pq.read_table(root/'v3'/'classified-candidates-with-kc-subtypes.parquet')
assert v3.num_rows==n
for col in table.column_names:assert table[col].equals(v3[col])
p2=json.loads((root/'v2-properties.json').read_text())['inline'];p3=json.loads((root/'v3-properties.json').read_text())['inline']
def labelmap(p):return dict(zip(map(int,p['ids']),next(v['values'] for v in p['properties'] if v['type']=='label')))
assert labelmap(p2)==labelmap(p3),'Raw IDs require semantic normalization'
previous=np.array(v3['sampling_status_provisional'].to_pylist())
transitions={}
for old,new in zip(previous,status):transitions[str(old)+' -> '+str(new)]=transitions.get(str(old)+' -> '+str(new),0)+1
changes={};known_changes={}
for side in ('pre','post'):
    old=np.array(v3[side+'_neighborhood_labels'].to_pylist(),dtype=np.int64)
    delta=old!=labels[side];known=(old>=0)&(labels[side]>=0)
    changes[side]={'neighborhood_queries':int(delta.sum()),'contacts_any_neighbor':int(np.any(delta,axis=1).sum()),'center_contacts':int(delta[:,center].sum())}
    known_changes[side]={'neighborhood_queries':int((delta&known).sum()),'contacts_any_known_neighbor':int(np.any(delta&known,axis=1).sum())}
comparison={'schema':'gamma-atlas-v2-v3-full-contact-comparison-v1','contacts':n,'v2_status_counts':counts,'v3_status_counts':{str(k):int(v) for k,v in zip(*np.unique(previous,return_counts=True))},'status_transitions':transitions,'changed_status_contacts':int(np.count_nonzero(previous!=status)),'endpoint_label_changes':changes,'known_label_changes':known_changes,'robust_g1_both_versions':int(np.count_nonzero((previous=='robust-expected-g1')&(status=='robust-expected-g1'))),'same_gamma_label_mapping':True,'contact_mask_admitted':False,'plasticity_enabled':False,'limits':'Full candidate contact and 27-neighbor comparison of v2/v3 only; unknown remains unknown. No v1, independent anatomy, pedc, DAN territory or physiology admission.'}
(root/'comparison-numeric-report.json').write_text(json.dumps(comparison,indent=2));print('ATLAS_VERSION_COMPARISON',json.dumps(comparison),flush=True)
(root/'classification-numeric-report.json').write_text(json.dumps(summary,indent=2));print('GAMMA_CLASSIFICATION_NUMERIC_REPORT',json.dumps(summary),flush=True)
'''
code='''def compare_gamma_atlas_v2_v3():
    import json,importlib.util,subprocess,sys
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env');api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('gcc','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-gamma-contact-sampling-v2-20261005')
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=3)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('GAMMA_CLASSIFICATION_RECEIPT',json.dumps(r),flush=True);return r
    (root/'classify-source.py').write_text(_GAMMA_CLASSIFY_SOURCE);(root/'classify-probe.py').write_text(_GAMMA_CLASSIFY_PROBE)
    source=publish(['classify-source.py','classify-probe.py'])
    a.restore(root,{'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'c78cc667e5d43c9e1c62239ee8959501edca6851','manifest':'manifests/d187e5a57c02b5da5a2a53ef888472fa3dd62883ca856d056870a3129c233c0b.json','sha256':'d187e5a57c02b5da5a2a53ef888472fa3dd62883ca856d056870a3129c233c0b','verified':True})
    closure=json.loads((root/'acquisition-report.json').read_text())
    if closure['requested_chunks']!=157 or len(closure['objects'])!=157:raise RuntimeError('Incomplete acquisition')
    for receipt in closure['segment_receipts']:a.restore(root,receipt)
    a.restore(root,{'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'f4153cc33a77074a13563ed6e2f3213b647f1c91','manifest':'manifests/e0481ebae5f585933edcfbfe16f41d2dc19ead452918ffa16a49d3ed094895f0.json','sha256':'e0481ebae5f585933edcfbfe16f41d2dc19ead452918ffa16a49d3ed094895f0','verified':True})
    a.restore(root,closure['metadata_receipt'])
    a.restore(root/'v3',{'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'b0038a27253d4ebadb32c2ea2d75785085264a91','manifest':'manifests/877edae6b332a5e83a8635143cd198f2440389829ef872d7929d6f26a38b3ce7.json','sha256':'877edae6b332a5e83a8635143cd198f2440389829ef872d7929d6f26a38b3ce7','verified':True})
    meta=Path('/tmp/fly-neuprint-subcompartment-audit-20261005');prior=json.loads((meta/'report.json').read_text())
    if a.digest(meta/'v3-properties.json')!=prior['source_identities']['v3-properties.json']['sha256']:raise RuntimeError('Properties drift')
    (root/'v3-properties.json').write_bytes((meta/'v3-properties.json').read_bytes())
    properties_receipt=publish(['v3-properties.json'])
    with (root/'classification.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'-u',str(root/'classify-probe.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in process.stdout:log.write(line);log.flush();print(line.rstrip(),flush=True)
        rc=process.wait()
    if rc:publish(['classification.log']);raise RuntimeError('Classification failed')
    report=json.loads((root/'classification-numeric-report.json').read_text());report['source_receipt']=source
    (root/'classification-report.json').write_text(json.dumps(report,indent=2))
    comparison=json.loads((root/'comparison-numeric-report.json').read_text());comparison.update({'source_receipt':source,'v2_input_receipt':{'revision':'c78cc667e5d43c9e1c62239ee8959501edca6851','manifest':'d187e5a57c02b5da5a2a53ef888472fa3dd62883ca856d056870a3129c233c0b'},'v3_input_revision':'b0038a27253d4ebadb32c2ea2d75785085264a91','properties_receipt':properties_receipt})
    (root/'comparison-report.json').write_text(json.dumps(comparison,indent=2))
    final=publish(['comparison-numeric-report.json','comparison-report.json','classified-candidates.parquet','classification-strata.csv','classification-numeric-report.json','classification-report.json','classification.log'])
    print('ATLAS_COMPARISON_FINAL_RECEIPT',json.dumps(final),flush=True)
compare_gamma_atlas_v2_v3()
'''
code='_GAMMA_CLASSIFY_PROBE = '+repr(probe)+'\n_GAMMA_CLASSIFY_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='compare_gamma_atlas_v2_v3' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='compare_gamma_atlas_v2_v3',hide_code=False);ctx.run_cell(cell)



