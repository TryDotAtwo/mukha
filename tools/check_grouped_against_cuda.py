"""Compare grouped CPU law with the unchanged fixed-input CUDA reaction kernel."""
from pathlib import Path
import hashlib
import json
import math
import statistics
import subprocess
import time

import numpy as np


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def run(root=Path('/marimo/fly-project')):
    root=Path(root)
    from hf_artifact_archive import publish
    source=root/'native/vistrans_fixed_input_probe.cu'
    kernel=root/'native/phototransduction_safe.cuh'
    cpu_report=json.loads((root/'data/derived/grouped_vistrans_cpu_v1/report.json').read_text())
    assert cpu_report['microvilli_per_receptor']==128 and cpu_report['ticks']==20
    folder=root/'data/derived/grouped_vistrans_cuda_compare_v1'
    folder.mkdir(parents=True,exist_ok=False)
    binary=folder/'vistrans_fixed_input_probe'
    rows_path=folder/'rows.bin'
    nvcc=root/'build/cuda-13.1.1/bin/nvcc'
    cuda=nvcc.parent.parent
    build=[str(nvcc),'-std=c++17','-O2','-lineinfo','-arch=sm_120','--fmad=false',
           '-I','native','-I',str(cuda/'include'),'-L',str(cuda/'lib'),
           str(source.relative_to(root)),'-o',str(binary.relative_to(root))]
    compiled=subprocess.run(build,cwd=root,capture_output=True,text=True,timeout=120)
    if compiled.returncode:raise RuntimeError(compiled.stderr[-2000:])
    command=[str(binary),str(rows_path),'512','128','20','19503']
    start=time.perf_counter()
    executed=subprocess.run(command,capture_output=True,text=True,timeout=120)
    wall=time.perf_counter()-start
    if executed.returncode:raise RuntimeError(executed.stderr[-2000:])
    rows=np.fromfile(rows_path,dtype='<i4')
    assert rows.size==512*4
    rows=rows.reshape(512,4)
    assert np.all(rows>=0) and np.all(rows[:,0]<=128)
    names=('basal_count','sum_x0','sum_x5','sum_x6')
    cpu={entry['metric']:entry for entry in cpu_report['comparisons']}
    comparisons=[]
    for i,name in enumerate(names):
        values=rows[:,i].tolist()
        gpu_mean=statistics.mean(values)
        gpu_sd=statistics.pstdev(values)
        cpu_mean=cpu[name]['grouped_mean']
        cpu_sd=cpu[name]['grouped_sd']
        se=math.sqrt(gpu_sd*gpu_sd/512+cpu_sd*cpu_sd/500)
        z=(gpu_mean-cpu_mean)/se if se else (0. if gpu_mean==cpu_mean else math.inf)
        record={'metric':name,'cuda_mean':gpu_mean,'cuda_sd':gpu_sd,
                'grouped_cpu_mean':cpu_mean,'grouped_cpu_sd':cpu_sd,
                'mean_difference_standard_errors':z}
        comparisons.append(record)
        print('GROUPED_CUDA_METRIC',json.dumps(record),flush=True)
    passed=all(abs(record['mean_difference_standard_errors'])<4.5 for record in comparisons)
    report={'scope':'Fixed-input original CUDA VisTrans reactions versus grouped CPU law, independent ensembles',
            'source_sha256':digest(source),'kernel_sha256':digest(kernel),
            'binary_sha256':digest(binary),'cpu_reference_report_sha256':digest(root/'data/derived/grouped_vistrans_cpu_v1/report.json'),
            'build_command':build,'run_command':command,'cuda_wall_s':wall,
            'receptors':512,'microvilli_each':128,'ticks':20,'dt_ms':0.1,
            'vm_mV':-56,'ns':1,'photon_rate_s':50000,'seed':19503,
            'comparisons':comparisons,'screen_passed':passed,
            'limitations':'One fixed-input setting; CPU uses float64/PCG, GPU uses mixed precision/XORWOW. A 4.5-SE mean screen is not proof of full distribution equivalence or GPU speedup.'}
    report_path=folder/'report.json'
    report_path.write_text(json.dumps(report,indent=2))
    files=[source,kernel,binary,rows_path,report_path,
           root/'tools/check_grouped_against_cuda.py']
    manifest={'schema':'faithful-fly-artifacts-v1','scope':report['scope'],
              'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    receipt=publish(root,manifest)
    print('GROUPED_CUDA_RESULT',json.dumps({'screen_passed':passed,'cuda_wall_s':wall}),flush=True)
    print('GROUPED_CUDA_ARCHIVE',json.dumps(receipt),flush=True)
    if not passed:raise RuntimeError('CUDA/grouped distribution screen failed')
    return receipt


if __name__=='__main__':run()
