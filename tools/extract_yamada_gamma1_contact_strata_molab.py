"""Recover complete KC-MBON contacts and stratify MBON11 by KC subtype."""
import importlib.util,json,os,shutil
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from huggingface_hub import HfApi,hf_hub_download
ROOT=Path('/tmp/fly-yamada-contact-recovery-20261004')
SOURCE=Path('/tmp/fly-malecns-partner-source-20261004')
REPO='TryDotAtwo/faithful-fly-artifacts'
REV='9ec22f9cb1b0358ee8bef432dd1c9c44c36bb4b8'
HASHES={'nodes.feather':'4335bd9cb4c0098c36e879ae64e97c76ce4fea96a6ad200b16d99aa5d1d0f5e2','body_ids.npy':'6bad3ab247ccb08f958962dd2a3da97289822bb4fe1e345a936db1c8741e05f8','indptr.npy':'e8a40f6043b5fac9d7dc8f9746c2b770672eca3f3bea37b4d8a33935752820fe','indices.npy':'d24a26b19f088719ade13220f4b6d5d269633a49f20456c2a4a37942d0a72e0b','synapse_counts.npy':'578f95e75aa4c86600429a05a59d43d9fa9ece67b592f97c938e1d8523f46ba1'}
def main():
    ROOT.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('archive','/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    api=HfApi(token=os.environ['HF_TOKEN'])
    if not api.repo_info(REPO,repo_type='dataset').private or api.whoami()['name']!='TryDotAtwo':raise RuntimeError('Archive identity')
    a.require_commit_capacity(api,REPO,commits_needed=9)
    def publish(names):
        r=a.publish(ROOT,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':a.digest(ROOT/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('Unverified contact archive')
        print('CONTACT_RECOVERY_RECEIPT',json.dumps(r),flush=True);return r
    publish(['extract.py','source-pin.json'])
    closure=json.loads((SOURCE/'full-source-closure.json').read_text())
    if not closure['full_input_closure_complete'] or not closure['whole_source_md5_verified'] or closure['generation']!='1780494942562468':raise RuntimeError('Source not admitted')
    path=SOURCE/'syn-partners-pinned.feather'
    if path.stat().st_size!=closure['bytes'] or a.digest(path)!=closure['sha256']:raise RuntimeError('Assembled source changed')
    shutil.copyfile(SOURCE/'full-source-closure.json',ROOT/'full-source-closure.json')
    for name,sha in HASHES.items():
        cache=Path(hf_hub_download(REPO,'objects/'+sha,repo_type='dataset',revision=REV,token=os.environ['HF_TOKEN']))
        if a.digest(cache)!=sha:raise RuntimeError('Graph input changed '+name)
        if (ROOT/name).exists() and a.digest(ROOT/name)!=sha:raise RuntimeError('Existing graph input changed')
        if not (ROOT/name).exists():shutil.copyfile(cache,ROOT/name)
    input_receipt=publish(list(HASHES)+['full-source-closure.json'])
    nodes=pd.read_feather(ROOT/'nodes.feather',columns=['bodyId','class','type','instance'])
    body=np.load(ROOT/'body_ids.npy',mmap_mode='r')
    ptr=np.load(ROOT/'indptr.npy',mmap_mode='r')
    indices=np.load(ROOT/'indices.npy',mmap_mode='r')
    counts=np.load(ROOT/'synapse_counts.npy',mmap_mode='r')
    if len(nodes)!=167216 or not np.array_equal(body,nodes.bodyId.to_numpy()):raise RuntimeError('Population mismatch')
    kc=nodes[nodes['class'].eq('Kenyon_Cell')];mb=nodes[nodes['class'].eq('MBON')]
    if len(kc)!=4064 or len(mb)!=97:raise RuntimeError('Class coverage mismatch')
    kset=set(map(int,kc.bodyId));expected=Counter()
    for post in np.flatnonzero(nodes['class'].eq('MBON').to_numpy()):
        for edge in range(int(ptr[post]),int(ptr[post+1])):
            pre=int(body[indices[edge]])
            if pre in kset:expected[(pre,int(body[post]))]+=int(counts[edge])
    if len(expected)!=61210 or sum(expected.values())!=463640:raise RuntimeError('Unexpected CSR contact totals')
    receipts=[];source_rows=0;contact_rows=0;all_tables=[]
    with pa.memory_map(str(path),'r') as mmap:
        reader=pa.ipc.open_file(mmap)
        if reader.num_record_batches!=4759:raise RuntimeError('Unexpected source batch coverage')
        if reader.schema.names!=['x_pre','y_pre','z_pre','body_pre','conf_pre','x_post','y_post','z_post','body_post','conf_post','primary_post']:raise RuntimeError('Source schema changed')
        kv=pa.array(sorted(kset),type=pa.int64());mv=pa.array(sorted(map(int,mb.bodyId)),type=pa.int64())
        for start in range(0,reader.num_record_batches,1000):
            stop=min(start+1000,reader.num_record_batches);tables=[]
            for i in range(start,stop):
                batch=reader.get_batch(i);source_rows+=batch.num_rows
                mask=pc.and_(pc.is_in(batch.column('body_pre'),value_set=kv),pc.is_in(batch.column('body_post'),value_set=mv))
                selected=pa.Table.from_batches([batch]).filter(mask)
                if selected.num_rows:tables.append(selected)
                if (i+1)%100==0:print('CONTACT_SCAN_BATCH',i+1,reader.num_record_batches,flush=True)
            table=pa.concat_tables(tables) if tables else pa.Table.from_batches([],schema=reader.schema)
            for column in ('x_pre','y_pre','z_pre','x_post','y_post','z_post'):
                if table[column].null_count:raise RuntimeError('Null coordinate')
            name=f'contacts-{start:05d}-{stop:05d}.parquet';meta=name+'.json'
            if (ROOT/name).exists():raise RuntimeError('Inspect completed extraction shard before reuse')
            pq.write_table(table,ROOT/name,compression='zstd')
            (ROOT/meta).write_text(json.dumps({'start_batch':start,'stop_batch':stop,'contacts':table.num_rows,'source_rows_processed':source_rows,'source_sha256':closure['sha256'],'input_receipt':input_receipt},indent=2))
            receipts.append(publish([name,meta]));contact_rows+=table.num_rows;all_tables.append(table)
    full=pa.concat_tables(all_tables)
    observed=Counter(zip(full['body_pre'].to_pylist(),full['body_post'].to_pylist()))
    mismatch=[(pre,post,expected[(pre,post)],observed[(pre,post)]) for pre,post in expected.keys()|observed.keys() if expected[(pre,post)]!=observed[(pre,post)]]
    if mismatch or contact_rows!=463640:raise RuntimeError('Full per-pair CSR reconciliation failed '+str(mismatch[:5]))
    candidate=mb[mb['type'].eq('MBON11')]
    selected=full.to_pandas()
    selected=selected[selected.body_post.isin(candidate.bodyId)].merge(kc[['bodyId','type']].rename(columns={'bodyId':'body_pre','type':'kc_type'}),on='body_pre',validate='many_to_one')
    groups=selected.groupby(['body_post','kc_type','primary_post'],dropna=False).size().reset_index(name='contacts')
    groups.to_csv(ROOT/'gamma1-candidate-strata.csv',index=False)
    result={'status':'full_contact_recovery_and_stratification_complete','input_receipt':input_receipt,'source_rows':source_rows,'source_batches':4759,'contacts':contact_rows,'pairs':len(observed),'pair_mismatches':len(mismatch),'shard_receipts':receipts,'candidate_mbons':candidate.to_dict(orient='records'),'candidate_contacts':len(selected),'kc_type_contacts':{str(k):int(v) for k,v in selected.groupby('kc_type',dropna=False).size().items()},'kc_type_population':{str(k):int(v) for k,v in kc.groupby('type',dropna=False).size().items()},'roi_contacts':{str(k):int(v) for k,v in selected.groupby('primary_post',dropna=False).size().items()},'scope':'Complete published KC-MBON geometry and exact per-pair CSR correspondence; MBON11/KC subtype strata are annotation-matched candidates only','mapping_accepted':False,'plasticity_enabled':False,'limits':'Broad ROIs and cell names do not establish gamma1 microcompartment, measured receptor action or local efficacy.'}
    (ROOT/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    final=publish(['gamma1-candidate-strata.csv','report.json'])
    compact={k:v for k,v in result.items() if k not in ('shard_receipts','input_receipt')}
    print('CONTACT_RECOVERY_PUBLIC_REPORT',json.dumps(compact,ensure_ascii=False),flush=True)
    print('CONTACT_RECOVERY_FINAL_RECEIPT',json.dumps(final),flush=True)
if __name__=='__main__':main()
