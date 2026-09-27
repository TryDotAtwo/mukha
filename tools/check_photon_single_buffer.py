import hashlib,json,subprocess
from pathlib import Path
root=Path('.').resolve();exe=root/'build/phototransduction_file_probe.exe';results=[]
for onset in (250,750):
 path=root/('build/file-one-buffer-'+str(onset)+'.bin')
 saved=subprocess.run([str(exe),'1000',str(onset),'save',str(path)],capture_output=True,text=True,check=True,timeout=120)
 final=Path(str(path)+'.final').read_bytes()
 restored=subprocess.run([str(exe),'1000',str(onset),'resume',str(path)],capture_output=True,text=True,check=True,timeout=120)
 assert Path(str(path)+'.final').read_bytes()==final
 assert saved.stdout.splitlines()[501:]==restored.stdout.splitlines()[1:]
 results.append({'onset':onset,'full_final_bytes_equal':True,'trace_continuation_equal':True,'snapshot_bytes':path.stat().st_size})
r={'scope':'Windows two-cell regression after reuse of a single host checkpoint buffer','passed':True,'cases':results,'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((root/'native/phototransduction_probe.cu').read_bytes()).hexdigest()}
(root/'reports/photon_single_buffer_checkpoint.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
