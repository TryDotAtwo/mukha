"""Restore the verified replay closure only inside fresh MoLab. No rebuilding."""
import argparse,importlib.util,json,os,shutil,subprocess,tarfile,urllib.request
from pathlib import Path
REPO='TryDotAtwo/faithful-fly-artifacts'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def receipt(revision,sha):
    return {'repo_id':REPO,'repo_type':'dataset','revision':revision,'manifest':'manifests/'+sha+'.json','sha256':sha}
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);args=p.parse_args()
    from huggingface_hub import HfApi
    api=HfApi(token=os.environ['HF_TOKEN'])
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info(REPO,repo_type='dataset').private:raise RuntimeError('HF identity/access mismatch')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
    bootstrap=Path('/tmp/native-restore-hf-archive.py')
    pin='db6ff468ce7f4393ff5062a559d5ba996c90e82d'
    with urllib.request.urlopen('https://raw.githubusercontent.com/TryDotAtwo/mukha/'+pin+'/tools/hf_artifact_archive.py',timeout=30) as r:bootstrap.write_text(r.read().decode('utf-8'))
    archive=load('native_restore_archive',bootstrap)
    archive.require_commit_capacity(api,REPO,3)
    helper_receipt=receipt('cd3658647025080d8dd8d85574873dfbf1b51c81','38bc548533cf79066557938ac126f2bbc674ae6f0ff39fd919f84082be960f38')
    helper_root=Path('/tmp/fly-hf-capacity-20261004')
    archive.restore(helper_root,helper_receipt)
    if archive.digest(bootstrap)!=archive.digest(helper_root/'tools/hf_artifact_archive.py'):raise RuntimeError('Bootstrap differs from verified archive source')
    records={
        'source-input':receipt('57143ccf7b64dc0fdad45bac818d8713d7933055','1ae7bc2dfa3d4928d4cd273233c7686446b940763cdb6dc4856c4bf56eaaac06'),
        'complete-author-source':receipt('243c51d35dd299e9d62cfbcc7b5cd67a8070c366','d06fe3c730b6b1a3e3d5a1ae78ec67325299e44a2dacb914d77f237e958f8663'),
        'graph-closure':receipt('7da9fe5680a1fa88839f7295466014e327d41f6c','26b6665f94525d07726b9ff2c6ccd24c654d8391af17cc6d000ebdafab786b07'),
        'input-protocol':receipt('cb3513cce1cefe3fd1be6fd1224aa5a96d8c2991','20b0c13bfcd83b0df9e201cb3c9693689b80985650a528a3d383f27d413c0048'),
        'build-closure':receipt('771cb8ecef936d6fd62d10cd83fc66d67636476f','f62efbdc2c2e394305a41ee2bc1156be6ffc1d87a87c32f46add36d71a20f74b')
    }
    root=args.root
    root.mkdir(exist_ok=False);(root/'stage-receipts').mkdir();(root/'logs').mkdir()
    for label,r in records.items():
        result=archive.restore(root,r)
        (root/'stage-receipts'/(label+'.json')).write_text(json.dumps(r,indent=2))
        print('NATIVE_RESTORE_STAGE',label,json.dumps(result),flush=True)
    source=root/'source'
    checked=[]
    with tarfile.open(root/'source-closure.tar.gz','r:gz') as tf:
        members=tf.getmembers()
        for member in members:
            if not member.isfile():raise RuntimeError('Source closure expects regular files')
            archive.checked_path(source,member.name)
        tf.extractall(source,filter='data')
        for member in members:
            expected=tf.extractfile(member).read()
            if (source/member.name).read_bytes()!=expected:raise RuntimeError('Extracted source differs')
            checked.append(member.name)
    binary=source/'target/release/faithful-fly';binary.chmod(0o755)
    toolchain=json.loads((root/'build-toolchain.json').read_text())
    nvcc=shutil.which('nvcc')
    cuda=Path(nvcc).resolve().parent.parent
    if archive.digest(cuda/'lib/libcusparse.so.12')!=toolchain['cusparse_sha256']:raise RuntimeError('Restored binary runtime cuSPARSE differs; no replay admission')
    bridge=Path('/tmp/fly-shiu-inputs-20261004/tools');bridge.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source/'tools/run_molab_conductance_finite.py',bridge/'run_molab_conductance_finite.py')
    report={'lost_sandbox_http_status':410,'new_sandbox_restore':True,'receipts':records,
            'source_files_verified':checked,'source_bundle_sha256':archive.digest(root/'source-closure.tar.gz'),
            'binary_sha256':archive.digest(binary),'cuda_library_sha256':archive.digest(source/'build/libfly_cuda64.so'),
            'cusparse_runtime_matches_build':True,'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],text=True),
            'no_rebuild':True,'comparison_not_yet_run':True,'execution':'MoLab only'}
    path=root/'sandbox-recovery.json';path.write_text(json.dumps(report,indent=2))
    driver=Path(__file__)
    shutil.copyfile(driver,root/'restore_molab_shiu_bitter_equivalence.py')
    paths=[path,root/'restore_molab_shiu_bitter_equivalence.py']
    recovery=archive.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{str(q.relative_to(root)):{'bytes':q.stat().st_size,'sha256':archive.digest(q)} for q in paths}})
    print('NATIVE_SANDBOX_RECOVERY_RECEIPT',json.dumps(recovery),flush=True)
    print('NATIVE_RESTORE_READY',json.dumps({'binary_sha256':report['binary_sha256'],'source_bundle_sha256':report['source_bundle_sha256'],'rebuild':False}),flush=True)
if __name__=='__main__':main()
