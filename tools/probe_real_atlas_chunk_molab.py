import marimo._code_mode as cm
code='''def probe_real_atlas_chunk():
    import json,importlib.util,urllib.request,urllib.parse,hashlib,base64,subprocess,sys
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    import pyarrow.parquet as pq
    load_dotenv('/marimo/.env');api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('rca','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-real-atlas-chunk-20261005');root.mkdir(exist_ok=True)
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=3)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('REAL_CHUNK_RECEIPT',json.dumps(r),flush=True);return r
    (root/'source.py').write_text(_REAL_CHUNK_SOURCE);source=publish(['source.py'])
    inputs=Path('/tmp/fly-mb-contact-shards-20261005')
    prior=json.loads((inputs/'original'/'report.json').read_text())
    for i,r in enumerate(prior['shard_receipts']):a.restore(inputs/f'shard-{i}',r)
    table=pq.read_table(inputs/'shard-0'/'contacts-00000-01000.parquet',filters=[('body_post','=',10704)],columns=['x_post','y_post','z_post'])
    if not table.num_rows:raise RuntimeError('Candidate contact missing')
    point=[int(table[n][0].as_py()) for n in ('x_post','y_post','z_post')]
    voxel=[v//32 for v in point];start=[v//64*64 for v in voxel];stop=[v+64 for v in start]
    shape=[64,64,64]
    key='_'.join(f'{s}-{e}' for s,e in zip(start,stop));name='rois/malecns-subcompartments-v3/256_256_256/'+key
    encoded=urllib.parse.quote(name,safe='')
    with urllib.request.urlopen('https://storage.googleapis.com/storage/v1/b/flyem-male-cns/o/'+encoded,timeout=30) as response:metadata=json.load(response)
    if int(metadata['size'])>4*1024*1024:raise RuntimeError('Chunk size bound')
    (root/'chunk-metadata.json').write_text(json.dumps(metadata,indent=2))
    with urllib.request.urlopen('https://storage.googleapis.com/download/storage/v1/b/flyem-male-cns/o/'+encoded+'?alt=media&generation='+metadata['generation'],timeout=30) as response:raw=response.read(4*1024*1024+1)
    if len(raw)!=int(metadata['size']) or base64.b64encode(hashlib.md5(raw).digest()).decode()!=metadata['md5Hash']:raise RuntimeError('Chunk source identity')
    (root/'chunk.bin').write_bytes(raw)
    config={'object':name,'generation':metadata['generation'],'point_8nm_candidate':point,'voxel_256nm_candidate':voxel,'start':start,'shape':shape,'local_point':[v-s for v,s in zip(voxel,start)],'mapping_admitted':False}
    (root/'config.json').write_text(json.dumps(config,indent=2));closure=publish(['chunk.bin','chunk-metadata.json','config.json'])
    probe=r"""import sys,json,gzip,struct
from pathlib import Path
sys.path.insert(0,'/tmp/fly-atlas-decoder-20261005/runtime')
import numpy as np,compressed_segmentation as c
root=Path('/tmp/fly-real-atlas-chunk-20261005');conf=json.loads((root/'config.json').read_text());raw=(root/'chunk.bin').read_bytes()
if raw[:2]==b'\x1f\x8b':raw=gzip.decompress(raw)
assert struct.unpack_from('<I',raw,0)[0]==1,'Single-channel header'
out=c.decompress(raw,tuple(conf['shape']),dtype=np.uint64,block_size=(8,8,8),order='F')
words=np.frombuffer(raw[4:],dtype='<u4')
def independent(x,y,z):
    gx,gy,gz=[(v+7)//8 for v in conf['shape']];block=x//8+gx*(y//8+gy*(z//8));h0=int(words[2*block]);h1=int(words[2*block+1]);bits=h0>>24;lookup=h0&0xffffff
    assert bits in (0,1,2,4,8,16,32)
    bit=bits*(x%8+8*(y%8+8*(z%8)));index=0 if bits==0 else (int(words[h1+bit//32])>>(bit%32))&((1<<bits)-1)
    offset=lookup+2*index
    return int(words[offset])+(int(words[offset+1])<<32)
points=[(x,y,z) for x in (0,7,8,31,63) for y in (0,7,8,31,63) for z in (0,7,8,31,63)]+[tuple(conf['local_point'])]
assert all(independent(*p)==int(out[p]) for p in points),'Independent decoder mismatch'
labels,counts=np.unique(out,return_counts=True)
assert all(0<=int(v)<=199 for v in labels),'Unknown atlas label'
print(json.dumps({'decoded_shape':list(out.shape),'independent_points':len(points),'independent_match':True,'local_candidate_label':int(out[tuple(conf['local_point'])]),'label_counts':{str(int(k)):int(v) for k,v in zip(labels,counts)},'single_channel_header':True,'mapping_admitted':False}))
"""
    (root/'decoder-probe.py').write_text(probe)
    with (root/'probe-output.json').open('w') as log:result=subprocess.run([sys.executable,str(root/'decoder-probe.py')],stdout=log,stderr=subprocess.STDOUT,timeout=90)
    if result.returncode:print((root/'probe-output.json').read_text()[-3000:],flush=True);raise RuntimeError('Chunk decoder probe failed')
    report={'schema':'real-atlas-chunk-decoder-probe-v1','source_receipt':source,'chunk_receipt':closure,'config':config,'decode':json.loads((root/'probe-output.json').read_text()),'scope':'One actual source-pinned chunk; candidate coordinate mapping unadmitted; no full contact mask or learning'}
    (root/'report.json').write_text(json.dumps(report,indent=2));publish(['decoder-probe.py','probe-output.json','report.json'])
    print('REAL_CHUNK_REPORT',json.dumps(report),flush=True)
probe_real_atlas_chunk()
'''
code='_REAL_CHUNK_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='probe_real_atlas_chunk' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='probe_real_atlas_chunk');ctx.run_cell(cell)

