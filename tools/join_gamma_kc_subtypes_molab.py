import marimo._code_mode as cm

code = '''def join_gamma_kc_subtypes():
    import json, importlib.util, shutil, collections
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi, hf_hub_download
    import pyarrow as pa
    import pyarrow.feather as feather
    import pyarrow.parquet as pq
    load_dotenv('/marimo/.env')
    repo = 'TryDotAtwo/faithful-fly-artifacts'
    api = HfApi()
    if api.whoami()['name'] != 'TryDotAtwo' or not api.repo_info(repo, repo_type='dataset').private:
        raise RuntimeError('HF identity')
    spec = importlib.util.spec_from_file_location('kcs_archive', '/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py')
    archive = importlib.util.module_from_spec(spec); spec.loader.exec_module(archive)
    root = Path('/tmp/fly-gamma-kc-subtypes-20261005'); root.mkdir(exist_ok=True)
    if (root/'report.json').exists(): raise RuntimeError('Inspect completed subtype join before reuse')
    archive.require_commit_capacity(api, repo, commits_needed=3)
    def publish(names):
        receipt = archive.publish(root, {'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':archive.digest(root/n)} for n in names}})
        if not receipt.get('verified'): raise RuntimeError('HF publication failed; stop progression')
        print('KC_SUBTYPE_RECEIPT', json.dumps(receipt), flush=True)
        return receipt
    (root/'source.py').write_text(_KC_SUBTYPE_SOURCE)
    source = publish(['source.py'])
    classification = {'repo_id':repo,'repo_type':'dataset','revision':'39c79aac825b2e1e0a22677b2d4b9eaff79cd8f0','manifest':'manifests/692bde3910691681fdca1afffef4bc7a46ffbee594af501c0c5144a335cc2fda.json','sha256':'692bde3910691681fdca1afffef4bc7a46ffbee594af501c0c5144a335cc2fda','verified':True}
    archive.restore(root/'classification', classification)
    sha = '4335bd9cb4c0098c36e879ae64e97c76ce4fea96a6ad200b16d99aa5d1d0f5e2'
    rev = '9ec22f9cb1b0358ee8bef432dd1c9c44c36bb4b8'
    cached = Path(hf_hub_download(repo,'objects/'+sha,repo_type='dataset',revision=rev))
    if archive.digest(cached) != sha: raise RuntimeError('Annotation source changed')
    shutil.copyfile(cached, root/'nodes.feather')
    provenance = {'repo_id':repo,'revision':rev,'object':'objects/'+sha,'sha256':sha,'classification_receipt':classification}
    (root/'input-provenance.json').write_text(json.dumps(provenance,indent=2))
    inputs = publish(['nodes.feather','input-provenance.json'])
    try:
        nodes = feather.read_table(root/'nodes.feather',columns=['bodyId','class','type','instance']).to_pylist()
        assert len(nodes)==167216
        body_map = {int(row['bodyId']):row for row in nodes}
        assert len(body_map)==len(nodes)
        kcs = {body:row for body,row in body_map.items() if row['class']=='Kenyon_Cell'}
        mbons = {body:row for body,row in body_map.items() if row['class']=='MBON'}
        assert len(kcs)==4064 and len(mbons)==97
        table = pq.read_table(root/'classification'/'classified-candidates.parquet')
        assert table.num_rows==41460
        assert set(table['body_post'].to_pylist())=={10704,11402}
        for body in (10704,11402): assert mbons[body]['type']=='MBON11'
        pre_ids = table['body_pre'].to_pylist()
        assert all(int(body) in kcs for body in pre_ids)
        types = [kcs[int(body)]['type'] for body in pre_ids]
        instances = [kcs[int(body)]['instance'] for body in pre_ids]
        joined = table.append_column('source_contact_row',pa.array(range(table.num_rows),type=pa.int64())).append_column('kc_type_annotation',pa.array(types,type=pa.string())).append_column('kc_instance_annotation',pa.array(instances,type=pa.string()))
        for name in table.column_names: assert joined[name].equals(table[name])
        pq.write_table(joined, root/'classified-candidates-with-kc-subtypes.parquet',compression='zstd')
        groups = collections.Counter(); by_type = collections.defaultdict(collections.Counter); unique = collections.defaultdict(set)
        for row, typ in zip(table.select(['body_pre','body_post','primary_post','sampling_status_provisional']).to_pylist(),types):
            label = typ if typ is not None else '<missing>'
            status=row['sampling_status_provisional']
            groups[(row['body_post'],label,str(row['primary_post']),status)]+=1
            by_type[label][status]+=1; unique[label].add(int(row['body_pre']))
        assert sum(groups.values())==41460
        import csv
        with (root/'kc-subtype-roi-status-strata.csv').open('w',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(['body_post','kc_type_annotation','source_primary_post','sampling_status_provisional','contacts'])
            writer.writerows([(*key,value) for key,value in sorted(groups.items())])
        population=collections.Counter(row['type'] if row['type'] is not None else '<missing>' for row in kcs.values())
        report={'schema':'gamma-contact-kc-subtype-join-v1','source_receipt':source,'input_receipt':inputs,'classification_receipt':classification,'contacts':table.num_rows,'source_columns_preserved':table.column_names,'selected_population':len(nodes),'kc_population':len(kcs),'missing_body_joins':0,'missing_type_contacts':types.count(None),'candidate_mbons':[mbons[body] for body in (10704,11402)],'kc_type_population':dict(sorted(population.items())),'kc_type_contact_status_counts':{typ:dict(sorted(counts.items())) for typ,counts in sorted(by_type.items())},'kc_type_contacting_neurons':{typ:len(ids) for typ,ids in sorted(unique.items())},'contact_mask_admitted':False,'plasticity_enabled':False,'limits':'Exact pinned annotation join and provisional atlas stratification only. Cell subtype names are annotations, not independently measured identity. All subtypes and contacts retained. No gamma1/pedc, receptor, physiology, DAN territory or atlas-version admission.'}
        (root/'report.json').write_text(json.dumps(report,indent=2))
        (root/'join.log').write_text('All 41460 contacts joined by exact body ID; no missing presynaptic IDs; source columns and row order preserved; subtype/status/ROI strata reconcile exactly.\\n')
    except Exception as error:
        (root/'failure.json').write_text(json.dumps({'exception_type':type(error).__name__,'message':str(error),'source_receipt':source,'input_receipt':inputs},indent=2))
        publish(['failure.json']); raise
    final=publish(['classified-candidates-with-kc-subtypes.parquet','kc-subtype-roi-status-strata.csv','report.json','join.log'])
    (root/'final-receipt.json').write_text(json.dumps(final,indent=2))
    print('KC_SUBTYPE_REPORT',json.dumps(report),flush=True)
join_gamma_kc_subtypes()
'''
code = '_KC_SUBTYPE_SOURCE = ' + repr(code) + '\n' + code
async with cm.get_context() as ctx:
    if any(c.status == 'running' for c in ctx.cells.values()): raise RuntimeError('Foreground work active')
    if any(c.name == 'join_gamma_kc_subtypes' for c in ctx.cells.values()): raise RuntimeError('Inspect existing subtype stage')
    cell = ctx.create_cell(code,name='join_gamma_kc_subtypes',hide_code=False)
    ctx.run_cell(cell)

