import marimo._code_mode as cm
code='''def prepare_atlas_decoder():
    import json,importlib.util,subprocess,sys,urllib.request,zipfile
    from pathlib import Path
    from packaging.utils import parse_wheel_filename
    from dotenv import load_dotenv
    from huggingface_hub import HfApi
    load_dotenv('/marimo/.env');api=HfApi()
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity')
    spec=importlib.util.spec_from_file_location('dec_archive','/tmp/fly-neuprint-input-inventory-20261005/hf_artifact_archive.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    root=Path('/tmp/fly-atlas-decoder-20261005');root.mkdir(exist_ok=True)
    wheels=root/'wheels';wheels.mkdir(exist_ok=True)
    target=root/'runtime'
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=3)
    def publish(names):
        r=a.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(root/n).stat().st_size,'sha256':a.digest(root/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('HF publication')
        print('DECODER_RECEIPT',json.dumps(r),flush=True);return r
    def run(args,name):
        with (root/name).open('w') as log:
            result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        if result.returncode:print((root/name).read_text()[-4000:],flush=True);raise RuntimeError('Decoder subprocess failed '+name)
    (root/'source.py').write_text(_DECODER_SOURCE)
    source=publish(['source.py'])
    run([sys.executable,'-m','pip','download','--index-url','https://pypi.org/simple','--only-binary=:all:','--dest',str(wheels),'compressed-segmentation==2.3.3'],'download.log')
    identities=[];names=['download.log']
    for wheel in sorted(wheels.glob('*.whl')):
        package,version,_,_=parse_wheel_filename(wheel.name)
        with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{version}/json',timeout=30) as response:meta=json.load(response)
        item=next(x for x in meta['urls'] if x['filename']==wheel.name)
        if wheel.stat().st_size!=item['size'] or a.digest(wheel)!=item['digests']['sha256']:raise RuntimeError('Published wheel identity mismatch')
        local=str(package)+'-pypi.json';(root/local).write_text(json.dumps(meta,indent=2));names.extend(['wheels/'+wheel.name,local])
        identities.append({'package':str(package),'version':str(version),'filename':wheel.name,'bytes':item['size'],'sha256':item['digests']['sha256']})
    closure=publish(names)
    run([sys.executable,'-m','pip','install','--no-index','--find-links',str(wheels),'--target',str(target),'compressed-segmentation==2.3.3'],'install.log')
    probe="import sys,json;sys.path.insert(0,"+repr(str(target))+");import numpy as np,compressed_segmentation as c; x,y,z=np.indices((17,19,23));labels=np.asfortranarray((x+100*y+10000*z).astype(np.uint64));raw=c.compress(labels,block_size=(8,8,8),order='F');out=c.decompress(raw,labels.shape,dtype=np.uint64,block_size=(8,8,8),order='F');assert np.array_equal(labels,out);print(json.dumps({'roundtrip':True,'shape':list(labels.shape),'dtype':str(labels.dtype),'order':'F','block_size':[8,8,8],'encoded_bytes':len(raw),'numpy_version':np.__version__,'decoder_file':c.__file__}))"
    run([sys.executable,'-c',probe],'roundtrip.json')
    report={'schema':'atlas-decoder-closure-v1','source_receipt':source,'wheel_closure':closure,'identities':identities,'runtime_path':str(target),'roundtrip':json.loads((root/'roundtrip.json').read_text()),'scope':'Asymmetric uint64 roundtrip only; no real atlas block or contact classification yet','contact_mask_admitted':False}
    (root/'report.json').write_text(json.dumps(report,indent=2));publish(['install.log','roundtrip.json','report.json'])
    print('DECODER_REPORT',json.dumps(report),flush=True)
prepare_atlas_decoder()
'''
code='_DECODER_SOURCE = '+repr(code)+'\n'+code
async with cm.get_context() as ctx:
    if any(c.status=='running' for c in ctx.cells.values()):raise RuntimeError('Foreground active')
    if any(c.name=='prepare_atlas_decoder' for c in ctx.cells.values()):raise RuntimeError('Inspect existing stage')
    cell=ctx.create_cell(code,name='prepare_atlas_decoder');ctx.run_cell(cell)

