"""MoLab-only Huang native Figure 5d replay with immutable stage receipts."""
import importlib.util,json,os,queue,threading,subprocess,sys,time,urllib.request,shutil,tarfile,shlex
from pathlib import Path
from huggingface_hub import HfApi
ROOT=Path('/tmp/fly-huang-native-20261004')
PIN='28c8adb140fb33327fe3754f02ca422b5f9350c1'
FILES=['native/huang.cpp','native/huang.h','reference/huang.py','reference/huang_native.py','tools/check_huang_figure.py','tools/fetch_huang_reference.py']
def main():
    ROOT.mkdir(exist_ok=True);(ROOT/'build').mkdir(exist_ok=True);(ROOT/'reports').mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('archive','/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    api=HfApi(token=os.environ['HF_TOKEN'])
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('Archive identity')
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=8)
    def publish(names):
        r=a.publish(ROOT,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':a.digest(ROOT/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('Unverified stage')
        print('HUANG_RECEIPT',json.dumps(r),flush=True);return r
    def run(command,log):
        dest=ROOT/log;dest.parent.mkdir(exist_ok=True)
        if dest.exists():raise RuntimeError('Inspect existing stage log before reuse')
        q=queue.Queue();started=time.monotonic()
        process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        def reader():
            try:
                for line in process.stdout:q.put(line)
            finally:q.put(None)
        thread=threading.Thread(target=reader,daemon=True);thread.start()
        try:
            with dest.open('w') as stream:
                while True:
                    try:line=q.get(timeout=15)
                    except queue.Empty:
                        print('HUANG_FOREGROUND_SECONDS',round(time.monotonic()-started,1),flush=True)
                        if time.monotonic()-started>1800:raise RuntimeError('Stage wall bound exceeded')
                        continue
                    if line is None:break
                    stream.write(line);stream.flush();print(line.rstrip(),flush=True)
            return process.wait()
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
    publish(['run.py','source-pin.json'])
    for name in FILES:
        path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():raise RuntimeError('Inspect existing project source before reuse')
        with urllib.request.urlopen('https://raw.githubusercontent.com/TryDotAtwo/mukha/'+PIN+'/'+name,timeout=30) as response:path.write_bytes(response.read())
    source_receipt=publish(FILES)
    status=run([sys.executable,'tools/fetch_huang_reference.py'],'logs/acquisition.log')
    inputs=[p.relative_to(ROOT).as_posix() for p in (ROOT/'data/reference/huang_2024').rglob('*') if p.is_file()]
    names=['logs/acquisition.log']+inputs
    if (ROOT/'reports/huang_reference_sources.json').exists():names.append('reports/huang_reference_sources.json')
    input_receipt=publish(names)
    if status:raise RuntimeError('Author acquisition failed; completed files archived')
    compiler=shutil.which('g++')
    if not compiler:raise RuntimeError('Native compiler unavailable in MoLab')
    version=subprocess.check_output([compiler,'--version'],text=True)
    dependency=subprocess.check_output([compiler,'-std=c++17','-M','native/huang.cpp'],cwd=ROOT,text=True)
    headers=shlex.split(dependency.replace(chr(92)+chr(10),' '))[1:]
    paths=sorted({Path(h) if Path(h).is_absolute() else ROOT/h for h in headers}|{Path(compiler).resolve()})
    if len(paths)>4096 or sum(p.stat().st_size for p in paths)>100*1024*1024:raise RuntimeError('Build dependency bound exceeded')
    with tarfile.open(ROOT/'build/build-inputs.tar.gz','w:gz') as archive:
        for p in paths:archive.add(p,arcname=p.as_posix().lstrip('/'),recursive=False)
    command=[compiler,'-std=c++17','-O2','-ffp-contract=off','-shared','-fPIC','native/huang.cpp','-o','build/huang_reference.dll']
    (ROOT/'build/build-protocol.json').write_text(json.dumps({'source_commit':PIN,'compiler':compiler,'compiler_version':version,'compiler_sha256':a.digest(Path(compiler).resolve()),'command':command,'comparison_command':[sys.executable,'tools/check_huang_figure.py','--native'],'protocols':108,'numeric_values':1944,'tolerance':1e-8,'full_cns_plasticity_validated':False},indent=2))
    build_input_receipt=publish(['build/build-inputs.tar.gz','build/build-protocol.json'])
    status=run(command,'logs/build.log')
    names=['logs/build.log']
    if (ROOT/'build/huang_reference.dll').exists():names.append('build/huang_reference.dll')
    build_receipt=publish(names)
    if status:raise RuntimeError('Native build failed; log archived')
    status=run([sys.executable,'tools/check_huang_figure.py','--native'],'logs/native-comparison.log')
    names=['logs/native-comparison.log']
    for n in ('build/huang_native_figure5d_prediction.npy','reports/huang_native_figure5d_comparison.json'):
        if (ROOT/n).exists():names.append(n)
    result_receipt=publish(names)
    if status:raise RuntimeError('Native comparison failed; completed results archived')
    report=json.loads((ROOT/'reports/huang_native_figure5d_comparison.json').read_text())
    report['execution']='MoLab foreground only; ELF shared library retained historical DLL filename for unchanged ctypes harness'
    report['stage_receipts']={'source':source_receipt,'inputs':input_receipt,'build_inputs':build_input_receipt,'build':build_receipt,'comparison':result_receipt}
    (ROOT/'reports/huang_native_molab.json').write_text(json.dumps(report,indent=2))
    final=publish(['reports/huang_native_molab.json'])
    print('HUANG_PUBLIC_REPORT',json.dumps(report),flush=True)
    print('HUANG_FINAL_RECEIPT',json.dumps(final),flush=True)
if __name__=='__main__':main()
