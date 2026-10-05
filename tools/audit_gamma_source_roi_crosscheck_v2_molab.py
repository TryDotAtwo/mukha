import marimo._code_mode as cm

code = '''def audit_gamma_source_roi_crosscheck_v2():
    import json, importlib.util, collections
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    import pyarrow.parquet as pq
    load_dotenv('/marimo/.env')
    api = HfApi()
    if api.whoami()['name'] != 'TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts', repo_type='dataset').private:
        raise RuntimeError('HF identity')
    spec = importlib.util.spec_from_file_location('grc_archive', '/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py')
    archive = importlib.util.module_from_spec(spec); spec.loader.exec_module(archive)
    root = Path('/tmp/fly-gamma-source-roi-crosscheck-v2-20261005'); root.mkdir(exist_ok=True)
    archive.require_commit_capacity(api, 'TryDotAtwo/faithful-fly-artifacts', commits_needed=3)
    def publish(names):
        receipt = archive.publish(root, {'schema':'faithful-fly-artifacts-v1', 'files':{n:{'bytes':(root/n).stat().st_size,'sha256':archive.digest(root/n)} for n in names}})
        if not receipt.get('verified'): raise RuntimeError('HF publication failed')
        print('GAMMA_ROI_CROSSCHECK_RECEIPT', json.dumps(receipt), flush=True)
        return receipt
    (root/'source.py').write_text(_GAMMA_ROI_CROSSCHECK_SOURCE)
    source = publish(['source.py'])
    classification = {'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'39c79aac825b2e1e0a22677b2d4b9eaff79cd8f0','manifest':'manifests/692bde3910691681fdca1afffef4bc7a46ffbee594af501c0c5144a335cc2fda.json','sha256':'692bde3910691681fdca1afffef4bc7a46ffbee594af501c0c5144a335cc2fda','verified':True}
    archive.restore(root/'classification', classification)
    meta = Path('/tmp/fly-neuprint-subcompartment-audit-20261005')
    meta_report = json.loads((meta/'report.json').read_text())
    for name in ('v3-properties.json','debug.json'):
        if archive.digest(meta/name) != meta_report['source_identities'][name]['sha256']: raise RuntimeError('Metadata drift')
        (root/name).write_bytes((meta/name).read_bytes())
    (root/'metadata-provenance.json').write_text(json.dumps(meta_report['source_identities'],indent=2))
    inputs = publish(['v3-properties.json','debug.json','metadata-provenance.json'])
    props = json.loads((root/'v3-properties.json').read_text())['inline']
    names = next(p['values'] for p in props['properties'] if p['type']=='label')
    labels = dict(zip(map(int,props['ids']),names)); labels[-1]='unknown'; labels[0]='background'
    rows = pq.read_table(root/'classification'/'classified-candidates.parquet').to_pylist()
    original = json.loads((root/'classification'/'classification-report.json').read_text())
    assert len(rows) == original['contacts'] == 41460
    counts = collections.Counter(); strata = collections.Counter(); lateral = collections.Counter(); side_counts = collections.Counter()
    for row in rows:
        pre = row['pre_neighborhood_labels']; post = row['post_neighborhood_labels']
        assert len(pre)==len(post)==27
        assert pre[13]==row['atlas_pre_center'] and post[13]==row['atlas_post_center']
        expected = row['expected_g1_label_provisional']
        if any(v<0 for v in pre+post): status='unknown-neighborhood'
        elif all(v==expected for v in pre+post): status='robust-expected-g1'
        elif pre[13]==post[13]==expected: status='center-g1-boundary-sensitive'
        elif expected in pre or expected in post: status='near-g1-boundary-sensitive'
        else: status='outside-expected-g1'
        assert status==row['sampling_status_provisional']
        counts[status]+=1
        for end in ('post',):
            roi = str(row['primary_'+end]); value = row['atlas_'+end+'_center']; label = labels[value]
            strata[(str(row['body_post']),end,roi,label,status)]+=1
            side = 'L' if roi.endswith('(L)') else 'R' if roi.endswith('(R)') else None
            atlas_side = 'L' if label.endswith('(L)') else 'R' if label.endswith('(R)') else None
            if side and atlas_side:
                lateral[(end,side,atlas_side)]+=1
            side_counts[(str(row['body_post']),end,label)]+=1
    assert dict(counts)==original['status_counts']
    assert sum(strata.values())==len(rows)
    import csv
    with (root/'source-roi-atlas-strata.csv').open('w',newline='') as out:
        writer=csv.writer(out);writer.writerow(['body_post','endpoint','source_primary_roi','atlas_center_label','status','contacts'])
        writer.writerows([(*key,value) for key,value in sorted(strata.items())])
    mismatches=sum(n for (end,s,a),n in lateral.items() if s!=a)
    ped={end:dict(collections.Counter({label:sum(n for (body,e,roi,l,status),n in strata.items() if e==end and roi.startswith('PED') and l==label) for label in labels.values()})) for end in ('pre','post')}
    ped={end:{label:n for label,n in values.items() if n} for end,values in ped.items()}
    report={'schema':'gamma-source-roi-crosscheck-v1','source_receipt':source,'classification_receipt':classification,'metadata_receipt':inputs,'contacts':len(rows),'independent_scalar_status_counts':dict(counts),'lateral_comparable_endpoints':sum(lateral.values()),'lateral_mismatch_endpoints':mismatches,'lateral_counts':[{'endpoint':e,'source_side':s,'atlas_side':a,'contacts':n} for (e,s,a),n in sorted(lateral.items())],'ped_source_center_atlas_counts':ped,'contact_mask_admitted':False,'plasticity_enabled':False,'limits':'Same-specimen source primary ROI versus coarse atlas is a consistency diagnostic, not independent landmark registration. PED is a broad ROI and not synonymous with pedc. No DAN territory, atlas-version, receptor or physiological admission.'}
    (root/'report.json').write_text(json.dumps(report,indent=2))
    final=publish(['source-roi-atlas-strata.csv','report.json'])
    (root/'final-receipt.json').write_text(json.dumps(final,indent=2))
    print('GAMMA_ROI_CROSSCHECK_REPORT',json.dumps(report),flush=True)
audit_gamma_source_roi_crosscheck_v2()
'''
code = '_GAMMA_ROI_CROSSCHECK_SOURCE = ' + repr(code) + '\n' + code
async with cm.get_context() as ctx:
    if any(c.status == 'running' for c in ctx.cells.values()):
        raise RuntimeError('Existing foreground work')
    if any(c.name == 'audit_gamma_source_roi_crosscheck_v2' for c in ctx.cells.values()):
        raise RuntimeError('Inspect existing crosscheck before rerun')
    cell = ctx.create_cell(code, name='audit_gamma_source_roi_crosscheck_v2', hide_code=False)
    ctx.run_cell(cell)


