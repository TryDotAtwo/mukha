"""Foreground full-author Shiu shared-input replay. All stages run only in MoLab."""
import argparse, importlib.util, json, os, shutil, subprocess, sys, tarfile, urllib.request
from pathlib import Path

REPO='TryDotAtwo/faithful-fly-artifacts'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--stage',choices=['setup','graph','build','reference','native','compare'],required=True)
    a=p.parse_args();root=a.root;source=root/'source'
    archive=module('replay_archive',Path('/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py'))
    runner=module('replay_runner',Path('/tmp/fly-shiu-inputs-20261004/tools/run_molab_conductance_finite.py'))
    from huggingface_hub import HfApi
    api=HfApi(token=os.environ['HF_TOKEN'])
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info(REPO,repo_type='dataset').private:raise RuntimeError('Archive identity mismatch')
    active=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip()
    if active:raise RuntimeError('Existing GPU work; do not compete')
    archive.require_commit_capacity(api,REPO,8 if a.stage=='setup' else 3)
    logs=root/'logs'
    receipts=root/'stage-receipts'
    def publish(paths,label):
        record={'schema':'faithful-fly-artifacts-v1','files':{str(path.relative_to(root)):{'bytes':path.stat().st_size,'sha256':archive.digest(path)} for path in paths}}
        receipt=archive.publish(root,record)
        (receipts/(label+'.json')).write_text(json.dumps(receipt,indent=2))
        print('REPLAY_STAGE_RECEIPT',label,json.dumps(receipt),flush=True)
        return receipt
    def run(command,label,outputs=()):
        log=logs/(label+'.log')
        if log.exists():raise FileExistsError('Existing stage; verify receipt before explicit recovery: '+label)
        status=runner.run_logged(command,source,log)
        paths=[log]+[path for path in outputs if path.is_file()]
        publish(paths,label)
        if status:raise RuntimeError('Stage failed and log archived: '+label)
    def require(label):
        receipt=json.loads((receipts/(label+'.json')).read_text())
        # Reverify pinned remote objects and corresponding local source before dependencies.
        archive.restore(root,receipt)
    if a.stage=='setup':
        root.mkdir(exist_ok=False);logs.mkdir();receipts.mkdir()
        subprocess.run(['git','init',str(source)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(source),'remote','add','origin','https://github.com/TryDotAtwo/mukha.git'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(source),'fetch','--depth=1','origin',a.source_commit],check=True,capture_output=True)
        subprocess.run(['git','-C',str(source),'checkout','--detach',a.source_commit],check=True,capture_output=True)
        if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=a.source_commit:raise RuntimeError('Source pin mismatch')
        inputs=source/'data/reference/shiu_2024';inputs.mkdir(parents=True,exist_ok=True)
        old=Path('/tmp/fly-shiu-inputs-20261004/data/reference/shiu_2024')
        expected={'model.py':'fc45837d7122c6ce2a7f3f2f23c515992e4b232aadb919efabb72337fac88e4e',
                  'figures.ipynb':'33cd73c0b4b4a291c51b7bab639c4fa28978e49e111ff0d6adbca5687addb84c',
                  '2023_03_23_completeness_630_final.csv':'e6b71e17671a9bdb05f55e4bc6774640a1418cb7a05125e0fc994ad40f9bfdfb',
                  '2023_03_23_connectivity_630_final.parquet':'94db8c650533bc36ffa3223f2e62325d5648b8d6bd31c3a4e1c804628c7557b3'}
        for name,digest in expected.items():
            if archive.digest(old/name)!=digest:raise RuntimeError('Restored input differs: '+name)
            if (inputs/name).exists():
                if archive.digest(inputs/name)!=digest:raise RuntimeError('Checkout has different input')
            else:shutil.copyfile(old/name,inputs/name)
        # Bundle TEXT source/build closure with explicit paths, excluding .git/data/secrets.
        bundle=root/'source-closure.tar.gz'
        names=['Cargo.toml','Cargo.lock','build.rs']
        names += [str(path.relative_to(source)) for folder in ('src','native') for path in (source/folder).rglob('*') if path.is_file() and path.suffix in ('.rs','.cpp','.h','.cu','.inc')]
        names += ['tools/'+name for name in ('build_shiu_graph.py','prepare_shiu_bitter_equivalence.py','run_shiu_brian_pilot.py','compare_shiu_pilot.py','run_molab_shiu_bitter_equivalence.py','hf_artifact_archive.py','run_molab_conductance_finite.py')]
        names += ['reports/shiu_reference_sources.json']
        with tarfile.open(bundle,'w:gz') as tf:
            for name in sorted(set(names)):tf.add(source/name,arcname=name,recursive=False)
        (root/'source-metadata.json').write_text(json.dumps({'commit':a.source_commit,'source_paths':names,'author_input_sha256':expected,'rust_version':'1.90.0','rust_release':'2025-09-18','cccl_dependency_reused_from':'/tmp/fly-finite-20261004-v4','sanitizer_available':bool(shutil.which('compute-sanitizer')),'scope':'Original author graph shared-input numerical trajectory'},indent=2))
        publish([bundle,root/'source-metadata.json']+list(inputs.iterdir()),'source-input')
        dependencies=root/'dependencies';dependencies.mkdir()
        toolchain=root/'toolchain'
        # Official pinned toolchain packages, hash checked and archived before installation.
        for component in ('rustc','cargo','rust-std'):
            name=component+'-1.90.0-x86_64-unknown-linux-gnu'
            url='https://static.rust-lang.org/dist/2025-09-18/'+name+'.tar.xz'
            package=dependencies/(name+'.tar.xz')
            with urllib.request.urlopen(url+'.sha256',timeout=30) as response:expected_hash=response.read().decode().split()[0]
            with urllib.request.urlopen(url,timeout=60) as response,package.open('xb') as out:shutil.copyfileobj(response,out,8<<20)
            if archive.digest(package)!=expected_hash:raise RuntimeError('Official toolchain package hash mismatch')
            (dependencies/(name+'.sha256')).write_text(expected_hash)
            publish([package,dependencies/(name+'.sha256')],component+'-package')
            with tarfile.open(package,'r:xz') as tf:tf.extractall(dependencies,filter='data')
            run(['sh',str(dependencies/name/'install.sh'),'--prefix='+str(toolchain),'--disable-ldconfig'],component+'-install')
        os.environ['PATH']=str(toolchain/'bin')+os.pathsep+os.environ['PATH']
        os.environ['CARGO_HOME']=str(root/'cargo-home')
        vendor=root/'vendor'
        run([str(toolchain/'bin/cargo'),'vendor','--locked',str(vendor)],'cargo-vendor')
        configuration=source/'.cargo/config.toml';configuration.parent.mkdir(exist_ok=True)
        configuration.write_text('[source.crates-io]\nreplace-with = "vendored-sources"\n[source.vendored-sources]\ndirectory = "'+str(vendor)+'"\n')
        vendor_bundle=root/'vendor-closure.tar.gz'
        with tarfile.open(vendor_bundle,'w:gz') as tf:tf.add(vendor,arcname='vendor')
        publish([vendor_bundle,configuration,source/'Cargo.lock'],'rust-dependencies')
        print('REPLAY_SETUP_COMPLETE',flush=True)
        return
    require('source-input')
    os.environ['PATH']=str(root/'toolchain/bin')+os.pathsep+os.environ['PATH']
    os.environ['CARGO_HOME']=str(root/'cargo-home')
    if a.stage=='graph':
        run([sys.executable,str(source/'tools/build_shiu_graph.py')],'author-graph')
        graph=source/'data/derived/shiu_2024'
        publish([path for path in graph.iterdir() if path.is_file()],'graph-closure')
        run([sys.executable,str(source/'tools/prepare_shiu_bitter_equivalence.py')],'input-protocol',[source/'configs/shiu_bitter_equivalence.json'])
    elif a.stage=='build':
        require('rust-dependencies')
        nvcc=shutil.which('nvcc');cuda=Path(nvcc).resolve().parent.parent
        cccl=Path('/tmp/fly-finite-20261004-v4/dependencies/cccl/nvidia/cu13/include')
        cccl_wheels=list(Path('/tmp/fly-finite-20261004-v4/dependencies').glob('*.whl'))
        if len(cccl_wheels)!=1:raise RuntimeError('Expected one archived CCCL wheel')
        libs=cuda/'lib';cusparse=libs/'libcusparse.so.12'
        build=source/'build';build.mkdir(exist_ok=True)
        metadata=root/'build-toolchain.json'
        metadata.write_text(json.dumps({'nvcc':subprocess.check_output([nvcc,'--version'],text=True),'rustc':subprocess.check_output(['rustc','--version'],text=True),'cargo':subprocess.check_output(['cargo','--version'],text=True),'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,compute_cap,memory.total,driver_version','--format=csv,noheader'],text=True),'cccl_wheel_sha256':archive.digest(cccl_wheels[0]),'cusparse_sha256':archive.digest(cusparse),'flags':['-DFF_FP64','--fmad=false','-O2','-arch=sm_120'],'numerical_scope':'FP64 author graph'},indent=2))
        publish([metadata,cccl_wheels[0]],'cuda-dependencies')
        lib=build/'libfly_cuda64.so'
        run([nvcc,'-DFF_FP64','-std=c++17','-O2','-arch=sm_120','--fmad=false','--shared','-Xcompiler=-fPIC','-I'+str(cccl),str(source/'native/cuda_probe.cu'),'-o',str(lib),'-Xlinker',str(cusparse),'-Xlinker=-rpath,'+str(libs)],'cuda64-build',[lib])
        os.environ['FF_CUDA_LIB_DIR']=str(build)
        run(['cargo','build','--release','--locked','--offline','--features','cuda64'],'rust-build',[source/'target/release/faithful-fly'])
        publish([metadata,lib,source/'target/release/faithful-fly',source/'Cargo.lock'],'build-closure')
    else:
        require('graph-closure');require('input-protocol')
        results=root/'results';results.mkdir(exist_ok=True)
        protocol=source/'configs/shiu_bitter_equivalence.json'
        if a.stage=='reference':
            run([sys.executable,str(source/'tools/run_shiu_brian_pilot.py'),'--protocol',str(protocol),'--output',str(results/'brian.json')],'brian-reference',[results/'brian.json',results/'brian.spikes.bin'])
        elif a.stage=='native':
            require('build-closure')
            os.environ['LD_LIBRARY_PATH']=str(source/'build')+os.pathsep+os.environ.get('LD_LIBRARY_PATH','')
            run([str(source/'target/release/faithful-fly'),'shiu-pilot',str(source/'data/derived/shiu_2024'),str(protocol),str(results/'native.json')],'native-replay',[results/'native.json',results/'native.spikes.bin',results/'native.checkpoint'])
        else:
            require('brian-reference');require('native-replay')
            run([sys.executable,str(source/'tools/compare_shiu_pilot.py'),'--candidate',str(results/'native.json'),'--reference',str(results/'brian.json'),'--report',str(results/'comparison.json')],'comparison',[results/'comparison.json'])
if __name__=='__main__':main()
