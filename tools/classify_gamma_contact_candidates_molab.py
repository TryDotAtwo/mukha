import marimo._code_mode as cm
probe=r'''import sys,json,gzip,struct,itertools
from pathlib import Path
sys.path.insert(0,'/tmp/fly-atlas-decoder-20261005/runtime')
import numpy as np,compressed_segmentation as c,pyarrow as pa,pyarrow.parquet as pq
root=Path('/tmp/fly-gamma-contact-sampling-20261005')
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
summary={'schema':'gamma-contact-provisional-volume-classification-v1','contacts':n,'status_counts':counts,'pre_center_counts':{str(k):int(v) for k,v in zip(*np.unique(pre,return_counts=True))},'post_center_counts':{str(k):int(v) for k,v in zip(*np.unique(post,return_counts=True))},'both_centers_expected_g1':int(both.sum()),'robust_expected_g1':int(robust.sum()),'boundary_near_g1':int(near.sum()),'unknown_neighborhood':int(unknown.sum()),'independent_decoder_points':checks,'available_chunks':closure['available_chunks'],'missing_chunks':closure['missing_chunks'],'boundary_radius_nm':256,'source_coordinate_units_assumed_nm':8,'atlas_version':3,'hemisphere_mapping_provisional':{'10704':190,'11402':195},'contact_mask_admitted':False,'plasticity_enabled':False,'limits':'Provisional voxel sampling only. No independent bilateral landmark/DAN-territory validation, gamma1-pedc semantics, version sensitivity, receptor or physiological validation. Missing chunks remain unknown, not zero. All contacts retained.'}
(root/'classification-numeric-report.json').write_text(json.dumps(summary,indent=2));print('GAMMA_CLASSIFICATION_NUMERIC_REPORT',json.dumps(summary),flush=True)
'''
code='''def classify_gamma_contact_candidates():
    import json,importlib.util,subprocess,sys
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env');api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('gcc','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-gamma-contact-sampling-20261005')
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=2)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('GAMMA_CLASSIFICATION_RECEIPT',json.dumps(r),flush=True);return r
    (root/'classify-source.py').write_text(_GAMMA_CLASSIFY_SOURCE);(root/'classify-probe.py').write_text(_GAMMA_CLASSIFY_PROBE)
    source=publish(['classify-source.py','classify-probe.py'])
    a.restore(root,{'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'fd5ef6b95826bbe33d7dea0e719230a515796049','manifest':'manifests/11c50bc6df1322ba054fa1553d6e38183fa1b7931fb4dcbe86a2b58832d3c484.json','sha256':'11c50bc6df1322ba054fa1553d6e38183fa1b7931fb4dcbe86a2b58832d3c484','verified':True})
    closure=json.loads((root/'acquisition-report.json').read_text())
    if closure['requested_chunks']!=157 or len(closure['objects'])!=157:raise RuntimeError('Incomplete acquisition')
    for receipt in closure['segment_receipts']:a.restore(root,receipt)
    a.restore(root,{'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'f4153cc33a77074a13563ed6e2f3213b647f1c91','manifest':'manifests/e0481ebae5f585933edcfbfe16f41d2dc19ead452918ffa16a49d3ed094895f0.json','sha256':'e0481ebae5f585933edcfbfe16f41d2dc19ead452918ffa16a49d3ed094895f0','verified':True})
    with (root/'classification.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'-u',str(root/'classify-probe.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in process.stdout:log.write(line);log.flush();print(line.rstrip(),flush=True)
        rc=process.wait()
    if rc:publish(['classification.log']);raise RuntimeError('Classification failed')
    report=json.loads((root/'classification-numeric-report.json').read_text());report['source_receipt']=source
    (root/'classification-report.json').write_text(json.dumps(report,indent=2))
    publish(['classified-candidates.parquet','classification-strata.csv','classification-numeric-report.json','classification-report.json','classification.log'])
classify_gamma_contact_candidates()
'''
code='_GAMMA_CLASSIFY_PROBE = '+repr(probe)+'\n_GAMMA_CLASSIFY_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='classify_gamma_contact_candidates' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='classify_gamma_contact_candidates');ctx.run_cell(cell)

