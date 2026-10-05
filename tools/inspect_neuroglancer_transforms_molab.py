import marimo._code_mode as cm
code='''def inspect_neuroglancer_transforms():
    import json,importlib.util
    from pathlib import Path
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env')
    api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('nt','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=2)
    root=Path('/tmp/fly-neuroglancer-transform-audit-20261005');root.mkdir(exist_ok=True)
    def publish(name):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{name:{'bytes':(root/name).stat().st_size,'sha256':a.digest(root/name)}}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('TRANSFORM_RECEIPT',json.dumps(r),flush=True);return r
    (root/'source.py').write_text(_TRANSFORM_SOURCE);source=publish('source.py')
    inputs=Path('/tmp/fly-neuprint-subcompartment-audit-20261005')
    prior=json.loads((inputs/'report.json').read_text())
    if a.digest(inputs/'dataset.json')!=prior['source_identities']['dataset.json']['sha256']:raise RuntimeError('Source drift')
    state=json.loads((inputs/'dataset.json').read_text())
    layers=[]
    for layer in state.get('layers',[]):
        layers.append({k:layer[k] for k in ('name','type','source','transform','coordinateSpace','localDimensions') if k in layer})
    report={'schema':'official-neuroglancer-transform-audit-v1','source_receipt':source,'dimensions':state.get('dimensions'),'layers':layers,'contact_mask_admitted':False,'scope':'Published layer source and transform metadata only; no registration equivalence assumed'}
    (root/'report.json').write_text(json.dumps(report,indent=2));publish('report.json')
    print('TRANSFORM_REPORT',json.dumps(report),flush=True)
inspect_neuroglancer_transforms()
'''
code='_TRANSFORM_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='neuroglancer_transform_audit' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='neuroglancer_transform_audit');ctx.run_cell(cell)

