"""Build the stateful receptor library with a source/toolchain-bound snapshot ID."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--nvcc',required=True)
parser.add_argument('--arch',required=True)
args=parser.parse_args()
nvcc=Path(args.nvcc).resolve(strict=True)
flags=['-std=c++17','-O2','-lineinfo',f'-arch={args.arch}','--fmad=false','-shared']
files=['native/photon.cu','native/photon.h','native/phototransduction_safe.cuh',
       'native/photocurrent_safe.cuh','build/photoreceptor_author_hh.cu',
       'build/photoreceptor_author_adaptation.cu','tools/build_photon.py','tools/archive_photon_build.py']
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
include=nvcc.parent.parent/'include'
cuda_headers=sorted(set(include.glob('curand*.h')) | {include/'cuda_runtime.h',include/'cuda_runtime_api.h'})
if not (include/'curand_kernel.h').is_file(): raise RuntimeError('Pinned cuRAND headers are required')
manifest={'sources':{name:sha(ROOT/name) for name in files},'flags':flags,
          'nvcc_version':subprocess.check_output([str(nvcc),'--version'],text=True),
          'nvcc_sha256':sha(nvcc),'cuda_headers':{p.name:sha(p) for p in cuda_headers},
          'platform':os.name}
host=shutil.which('cl.exe' if os.name=='nt' else 'g++')
if not host: raise RuntimeError('Native host compiler is not on PATH')
manifest['host_compiler_sha256']=sha(Path(host))
identity=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
(ROOT/'build').mkdir(exist_ok=True)
(ROOT/'build/photon_build_id.h').write_text('#pragma once\n#define FP_BUILD_ID "'+identity+'"\n')
library=ROOT/('build/fly_photon.dll' if os.name=='nt' else 'build/libfly_photon.so')
command=[str(nvcc),*flags,'native/photon.cu','-o',str(library.relative_to(ROOT))]
subprocess.run(command,cwd=ROOT,check=True)
assert all(sha(ROOT/name)==value for name,value in manifest['sources'].items()),'Source changed during build'
manifest.update(build_identity=identity,command=command,binary_sha256=sha(library))
(ROOT/'reports/photon_build.json').write_text(json.dumps(manifest,indent=2))
from archive_photon_build import archive_build
archive_build()
print('PHOTON_BUILD_ID',identity)
