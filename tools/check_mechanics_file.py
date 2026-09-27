"""Fresh-process replay plus malformed-file and mismatched-model rejection."""
import hashlib,json,os,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
exe=ROOT/'build/mechanics_file_probe.exe';model=ROOT/'data/derived/contact_diagnostic/body.xml'
dll=ROOT/'data/reference/mujoco_3.9.0/bin/mujoco.dll'
env=os.environ.copy();env['PATH']=str(dll.parent)+os.pathsep+env.get('PATH','')
def run(output,tick,source=None,xml=model):
    args=[str(exe),str(xml),str(output),str(tick)]
    if source is not None:args.append(str(source))
    return subprocess.run(args,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace")
full=ROOT/'build/mc_full.bin';mid=ROOT/'build/mc_mid.bin';resumed=ROOT/'build/mc_resumed.bin'
for output,tick,source in [(full,10000,None),(mid,3000,None),(resumed,10000,mid)]:
    r=run(output,tick,source);assert r.returncode==0,r.stderr
assert full.read_bytes()==resumed.read_bytes()
raw=mid.read_bytes();bad=ROOT/'build/mc_bad.bin';output=ROOT/'build/mc_rejected.bin'
cases={'truncated':raw[:-1],'trailing':raw+b'x','bad_magic':b'x'+raw[1:],
       'payload_flip':raw[:-1]+bytes([raw[-1]^1]),'metadata_flip':raw[:24]+bytes([raw[24]^1])+raw[25:]}
rejected=[]
for name,data in cases.items():
    bad.write_bytes(data);output.write_bytes(b'existing output must survive')
    r=run(output,10000,bad)
    assert r.returncode!=0 and output.read_bytes()==b'existing output must survive'
    rejected.append(name)
tree=ET.parse(model)
tree.getroot().find('compiler').set('meshdir',os.path.relpath(model.parent,ROOT/'build'))
pad=tree.getroot().find(".//geom[@name='control_pad']");pad.set('mass',str(float(pad.get('mass'))*2))
alternate=ROOT/'build/mc_alternate_model.xml';tree.write(alternate,encoding='utf-8')
# Prove the alternate model itself loads before using it for a rejection case.
r=run(ROOT/'build/mc_alternate_fresh.bin',0,xml=alternate);assert r.returncode==0,r.stderr
r=run(output,10000,mid,alternate)
assert r.returncode!=0 and 'model/schema/tick mismatch' in r.stderr
assert output.read_bytes()==b'existing output must survive'
rejected.append('different_compiled_model')
paths=[exe,model,dll,full,mid,resumed,ROOT/'native/mechanics_file_probe.cpp',ROOT/'native/rocket_vertical.h',
       ROOT/'native/atomic_checkpoint.hpp',Path(__file__)]
report=dict(exact_fresh_process_continuation=True,checkpoint_tick=3000,end_tick=10000,
    checkpoint_bytes=len(raw),rejected_cases=rejected,
    scope='Same executable/dependencies, airborne radial mechanical diagnostic only',
    limitations=['FNV checksum detects accidental changes; not authentication',
                 'Format uses host float64/uint64 layout; no cross-platform portability',
                 'Loader does not enforce executable/library identity; external hashes must be checked',
                 'No brain, sensor, RNG, or recorder state'],
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(ROOT/'reports/mechanics_file_checkpoint.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='hashes'},indent=2))
