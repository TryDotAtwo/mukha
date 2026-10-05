import marimo._code_mode as cm
code = '''def summarize_gamma_kc_families():
    import json, importlib.util, collections
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env'); api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('kc_family_archive','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py'); archive=importlib.util.module_from_spec(spec);spec.loader.exec_module(archive)
    root=Path('/tmp/fly-gamma-kc-family-summary-20261005');root.mkdir(exist_ok=True)
    archive.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=2)
    def publish(names):
        receipt=archive.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':archive.digest(root/n)} for n in names}})
        if not receipt.get('verified'):raise RuntimeError('HF publication failed')
        print('KC_FAMILY_RECEIPT',json.dumps(receipt),flush=True);return receipt
    receipt={'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'b0038a27253d4ebadb32c2ea2d75785085264a91','manifest':'manifests/877edae6b332a5e83a8635143cd198f2440389829ef872d7929d6f26a38b3ce7.json','sha256':'877edae6b332a5e83a8635143cd198f2440389829ef872d7929d6f26a38b3ce7','verified':True}
    (root/'source.py').write_text(_KC_FAMILY_SOURCE)
    (root/'input-receipt.json').write_text(json.dumps(receipt,indent=2))
    source=publish(['source.py','input-receipt.json'])
    archive.restore(root/'inputs',receipt)
    original=json.loads((root/'inputs'/'report.json').read_text())
    groups={'gamma':{'KCg','KCg-d','KCg-m','KCg-s1','KCg-s2','KCg-s3','KCg-s4'},'alpha_beta':{'KCab-c','KCab-m','KCab-p','KCab-s'},'alpha_prime_beta_prime':{"KCa'b'-ap1","KCa'b'-ap2","KCa'b'-m"}}
    assert set().union(*groups.values())==set(original['kc_type_contact_status_counts'])
    aggregate={}
    for family,types in groups.items():
        counts=collections.Counter()
        for typ in types:counts.update(original['kc_type_contact_status_counts'][typ])
        aggregate[family]={'contacts':sum(counts.values()),'status_counts':dict(sorted(counts.items())),'contacting_neurons':sum(original['kc_type_contacting_neurons'][typ] for typ in types)}
    assert sum(group['contacts'] for group in aggregate.values())==41460
    nongamma=sum(group['status_counts'].get('robust-expected-g1',0) for family,group in aggregate.items() if family!='gamma')
    allrobust=sum(group['status_counts'].get('robust-expected-g1',0) for group in aggregate.values())
    report={'schema':'gamma-kc-annotation-family-summary-v1','source_receipt':source,'input_receipt':receipt,'family_mapping':{k:sorted(v) for k,v in groups.items()},'families':aggregate,'nongamma_robust_expected_g1_contacts':nongamma,'nongamma_fraction_of_robust_expected_g1':nongamma/allrobust,'all_contacts':41460,'contact_mask_admitted':False,'plasticity_enabled':False,'limits':'Annotation family aggregation only; non-gamma rows are retained as anatomical candidates and controls, not relabelled or discarded. Atlas g1 alone cannot identify the complete gamma1pedc domain.'}
    (root/'report.json').write_text(json.dumps(report,indent=2))
    text='# Gamma KC family stratification — MoLab, 2026-10-05\\n\\nAll 41460 candidate contacts joined exactly to pinned KC annotations; no missing bodies/types. Original columns and row order preserved.\\n\\n'
    text+='| Annotation family | All contacts | Robust expected-g1 | Unknown neighborhood |\\n|---|---:|---:|---:|\\n'
    for family,group in aggregate.items():text+=f"| {family} | {group['contacts']} | {group['status_counts'].get('robust-expected-g1',0)} | {group['status_counts'].get('unknown-neighborhood',0)} |\\n"
    text+='\\nRobust atlas-g1 rows are not exclusively gamma-KC. Preserve all rows and separate KC-family physiology controls. Subtype annotations are not independent measured identity. Learning remains disabled; anatomy mask unadmitted.\\n\\nPrimary anatomy defines pedc as distal pedunculus core with MBON-gamma1pedc and PPL1-gamma1pedc co-innervation: https://pmc.ncbi.nlm.nih.gov/articles/PMC4273436/ (Figure 6). Whole PED is not a measured pedc mask. The atlas g1 route remains a provisional gamma-lobe sampling route, not complete gamma1pedc.\\n\\nVerified subtype input commit: b0038a27253d4ebadb32c2ea2d75785085264a91; manifest: 877edae6b332a5e83a8635143cd198f2440389829ef872d7929d6f26a38b3ce7.\\n'
    (root/'summary.md').write_text(text)
    final=publish(['report.json','summary.md'])
    (root/'final-receipt.json').write_text(json.dumps(final,indent=2))
    print('KC_FAMILY_REPORT',json.dumps(report),flush=True)
    print('KC_FAMILY_MARKDOWN',text,flush=True)
summarize_gamma_kc_families()
'''
code='_KC_FAMILY_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='summarize_gamma_kc_families' for c in ctx.cells.values()):raise RuntimeError('Inspect existing family summary')
    cell=ctx.create_cell(code,name='summarize_gamma_kc_families',hide_code=False);ctx.run_cell(cell)

