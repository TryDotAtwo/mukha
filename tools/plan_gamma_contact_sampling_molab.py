import marimo._code_mode as cm
code='''def plan_gamma_contact_sampling():
    import json,importlib.util
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    import numpy as np,pyarrow as pa,pyarrow.parquet as pq
    load_dotenv('/marimo/.env');api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('gcp','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-gamma-contact-sampling-20261005');root.mkdir(exist_ok=True)
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=2)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('GAMMA_PLAN_RECEIPT',json.dumps(r),flush=True);return r
    (root/'plan-source.py').write_text(_GAMMA_PLAN_SOURCE);source=publish(['plan-source.py'])
    inputs=Path('/tmp/fly-mb-contact-shards-20261005');original=json.loads((inputs/'original'/'report.json').read_text())
    for i,r in enumerate(original['shard_receipts']):a.restore(inputs/f'shard-{i}',r)
    tables=[pq.read_table(p,filters=[('body_post','in',[10704,11402])]) for p in sorted(inputs.glob('shard-*/*.parquet'))]
    table=pa.concat_tables(tables)
    if table.num_rows!=41460:raise RuntimeError('MBON11 candidate contact mismatch')
    pq.write_table(table,root/'candidate-contacts.parquet',compression='zstd')
    chunks=set();bounds={};coords={}
    for side in ('pre','post'):
        xyz=np.column_stack([table[axis+'_'+side].to_numpy() for axis in ('x','y','z')]).astype(np.int64)
        bounds[side]={'min':xyz.min(axis=0).tolist(),'max':xyz.max(axis=0).tolist()}
        vox=xyz//32
        if np.any(vox<0) or np.any(vox>=np.array([2011,1296,1100])):raise RuntimeError('Candidate coordinates out of atlas bounds')
        coords[side]=vox
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    for c in np.unique((vox+np.array([dx,dy,dz]))//64,axis=0):chunks.add(tuple(map(int,c)))
    delta=np.column_stack([table[x+'_pre'].to_numpy()-table[x+'_post'].to_numpy() for x in ('x','y','z')]).astype(np.float64)
    distances=np.sqrt((delta*delta).sum(axis=1))*8
    keys=['_'.join(f'{64*c}-{min(64*c+64,size)}' for c,size in zip(chunk,(2011,1296,1100))) for chunk in sorted(chunks)]
    report={'schema':'gamma-contact-sparse-sampling-plan-v1','source_receipt':source,'contacts':table.num_rows,'candidate_body_ids':[10704,11402],'source_coordinate_bounds':bounds,'candidate_voxel_ratio':32,'coordinate_mapping_admitted':False,'atlas_version':3,'neighbor_offsets':[-1,0,1],'unique_chunks':len(keys),'chunk_keys':keys,'decoded_upper_bound_bytes':len(keys)*64**3*8,'pre_post_distance_nm_candidate_quantiles':{str(q):float(np.quantile(distances,q)) for q in (0,.5,.9,.99,1)},'broad_primary_post_counts':table['primary_post'].to_pandas().value_counts().to_dict(),'contact_mask_admitted':False,'scope':'Acquisition plan for all MBON11 candidate contacts; provisional source coordinate convention'}
    (root/'plan.json').write_text(json.dumps(report,indent=2));publish(['candidate-contacts.parquet','plan.json'])
    print('GAMMA_SAMPLING_PLAN',json.dumps(report),flush=True)
plan_gamma_contact_sampling()
'''
code='_GAMMA_PLAN_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='plan_gamma_contact_sampling' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='plan_gamma_contact_sampling');ctx.run_cell(cell)

