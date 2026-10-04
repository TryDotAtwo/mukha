"""Unfiltered memcheck of the preregistered full graph replay, MoLab only."""
import argparse,importlib.util,json,os,shutil,subprocess,sys,tarfile,urllib.request
from pathlib import Path
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);args=p.parse_args()
    root=args.root;source=root/'source'
    archive=load('memcheck_archive',Path('/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py'))
    runner=load('memcheck_runner',source/'tools/run_molab_conductance_finite.py')
    from huggingface_hub import HfApi
    api=HfApi(token=os.environ['HF_TOKEN'])
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('HF identity mismatch')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip():raise RuntimeError('Existing GPU process')
    archive.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',4)
    def publish(paths,label):
        receipt=archive.publish(root,{'schema':'faithful-fly-artifacts-v1','files':{str(path.relative_to(root)):{'bytes':path.stat().st_size,'sha256':archive.digest(path)} for path in paths}})
        (root/'stage-receipts'/(label+'.json')).write_text(json.dumps(receipt,indent=2))
        print('MEMCHECK_RECEIPT',label,json.dumps(receipt),flush=True)
    for label in ('source-input','graph-closure','input-protocol','build-closure','brian-reference','native-replay'):
        archive.restore(root,json.loads((root/'stage-receipts'/(label+'.json')).read_text()))
    dep=root/'dependencies';dep.mkdir(exist_ok=True)
    name='cuda_sanitizer_api-linux-x86_64-13.0.48-archive.tar.xz'
    package=dep/name
    expected='f5f5ebda21f924270cb6603f139fa94497e975d547c2a1dfc80a6ffc053230a9'
    url='https://developer.download.nvidia.com/compute/cuda/redist/cuda_sanitizer_api/linux-x86_64/'+name
    if not package.exists():
        with urllib.request.urlopen(url,timeout=60) as response,package.open('xb') as output:shutil.copyfileobj(response,output,8<<20)
    if package.stat().st_size!=11396236 or archive.digest(package)!=expected:raise RuntimeError('Official sanitizer package identity mismatch')
    metadata=dep/'sanitizer-package.json'
    metadata.write_text(json.dumps({'url':url,'sha256':expected,'bytes':11396236,'manifest':'https://developer.download.nvidia.com/compute/cuda/redist/redistrib_13.0.0.json','component_version':'13.0.48'},indent=2))
    publish([package,metadata],'sanitizer-package')
    with tarfile.open(package,'r:xz') as tf:tf.extractall(dep,filter='data')
    candidates=[path for path in dep.rglob('compute-sanitizer') if path.is_file()]
    if len(candidates)!=1:raise RuntimeError('Sanitizer CLI not supplied by pinned package; no memcheck claim')
    sanitizer=candidates[0]
    os.environ['LD_LIBRARY_PATH']=str(source/'build')+os.pathsep+os.environ.get('LD_LIBRARY_PATH','')
    binary=source/'target/release/faithful-fly'
    protocol=source/'configs/shiu_bitter_equivalence.json'
    output=root/'results/native-memcheck.json'
    log=root/'logs/native-memcheck.log'
    if output.exists() or log.exists():raise FileExistsError('Existing instrumented run; verify before recovery')
    command=[str(sanitizer),'--tool','memcheck','--leak-check','full','--error-exitcode','97',str(binary),'shiu-pilot',str(source/'data/derived/shiu_2024'),str(protocol),str(output)]
    runtime=root/'memcheck-runtime.json'
    runtime.write_text(json.dumps({'command':command,'sanitizer_version':subprocess.check_output([str(sanitizer),'--version'],text=True),'binary_sha256':archive.digest(binary),'cuda_library_sha256':archive.digest(source/'build/libfly_cuda64.so'),'protocol_sha256':archive.digest(protocol),'kernel_filters':False,'suppressions':False,'api_error_reporting_disabled':False,'scope':'Full original author graph, one fixed-input trajectory; no global race proof or MaleCNS physiology'},indent=2))
    publish([runtime],'memcheck-runtime')
    status=runner.run_logged(command,source,log)
    paths=[log]
    paths.extend(path for path in (output,output.with_suffix('.spikes.bin'),output.with_suffix('.checkpoint')) if path.is_file())
    publish(paths,'native-memcheck')
    if status or 'ERROR SUMMARY: 0 errors' not in log.read_text():raise RuntimeError('Memcheck did not prove zero errors; results archived')
    compared=root/'results/memcheck-comparison.json'
    compare_log=root/'logs/memcheck-comparison.log'
    status=runner.run_logged([sys.executable,str(source/'tools/compare_shiu_pilot.py'),'--candidate',str(output),'--reference',str(root/'results/brian.json'),'--report',str(compared),'--instrumentation','memcheck'],source,compare_log)
    publish([compare_log]+([compared] if compared.exists() else []),'memcheck-comparison')
    if status:raise RuntimeError('Instrumented trajectory differs; archived')
if __name__=='__main__':main()
