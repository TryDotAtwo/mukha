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
    import gzip,io
    base='https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/'
    index=dep/'nvidia-Packages.gz'
    if index.exists():data=index.read_bytes()
    else:
        with urllib.request.urlopen(base+'Packages.gz',timeout=60) as response:
            data=response.read(20*1024*1024+1)
    if len(data)>20*1024*1024:raise RuntimeError('Package metadata unexpectedly large')
    index.write_bytes(data)
    text=gzip.decompress(data).decode('utf-8')
    if len(text)>64*1024*1024:raise RuntimeError('Package metadata unexpectedly large after decompression')
    selected=[]
    for paragraph in text.split('\n\n'):
        fields={}
        for line in paragraph.splitlines():
            if line and not line.startswith(' ') and ': ' in line:
                k,v=line.split(': ',1);fields[k]=v
        if fields.get('Package')=='cuda-sanitizer-13-0' and fields.get('Version')=='13.0.85-1' and fields.get('Architecture')=='amd64':
            selected.append(fields)
    if len(selected)!=1:raise RuntimeError('Pinned official sanitizer stanza not unique')
    fields=selected[0]
    name='cuda-sanitizer-13-0_13.0.85-1_amd64.deb'
    if fields['Filename'].removeprefix('./')!=name:raise RuntimeError('Unexpected official package path')
    package=dep/name
    if not package.exists():
        with urllib.request.urlopen(base+name,timeout=60) as response,package.open('xb') as output:shutil.copyfileobj(response,output,8<<20)
    if package.stat().st_size!=int(fields['Size']) or archive.digest(package)!=fields['SHA256']:raise RuntimeError('Official sanitizer CLI identity mismatch')
    metadata=dep/'sanitizer-cli-package.json'
    metadata.write_text(json.dumps({'repository':base,'fields':fields,'index_sha256':archive.digest(index)},indent=2))
    publish([package,metadata,index],'sanitizer-cli-package')
    unpacked=dep/'sanitizer-cli';unpacked.mkdir(exist_ok=True)
    payload=subprocess.check_output(['dpkg-deb','--fsys-tarfile',str(package)])
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as tf:tf.extractall(unpacked,filter='data')
    # The package also contains a 112-byte launcher for /usr/local installation.
    # Execute the verified ELF directly from its extracted sibling library directory.
    sanitizer=unpacked/'usr/local/cuda-13.0/compute-sanitizer/compute-sanitizer'
    with sanitizer.open('rb') as stream:
        if stream.read(4)!=b'\x7fELF':raise RuntimeError('Expected official sanitizer ELF')
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
