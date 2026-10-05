"""Finish the generation-pinned source; archive each part before advancing."""
import importlib.util,json,sys,hashlib,os
from pathlib import Path
ROOT=Path('/tmp/fly-malecns-partner-source-20261004')
def main():
    spec=importlib.util.spec_from_file_location('archive','/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    spec=importlib.util.spec_from_file_location('range_source',ROOT/'acquire.py')
    ranges=importlib.util.module_from_spec(spec);spec.loader.exec_module(ranges)
    def publish(names):
        r=a.publish(ROOT,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':a.digest(ROOT/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('Unverified source closure')
        print('PARTNER_CLOSURE_RECEIPT',json.dumps(r),flush=True);return r
    publish(['finish.py','finish-source-pin.json'])
    receipts=[]
    for part in range(13):
        rp=ROOT/f'receipt-{part:03d}.json'
        if rp.exists():
            receipt=json.loads(rp.read_text());a.restore(ROOT,receipt)
            print('PARTNER_SOURCE_REVERIFIED',part,flush=True)
        else:
            sys.argv=[str(ROOT/'acquire.py'),'--part',str(part)]
            ranges.main()
            receipt=json.loads(rp.read_text())
        receipts.append(receipt)
    dest=ROOT/'syn-partners-pinned.feather';tmp=ROOT/'syn-partners-pinned.feather.partial'
    if dest.exists() or tmp.exists():raise RuntimeError('Inspect existing composition before reuse')
    md5=hashlib.md5();sha=hashlib.sha256();size=0
    with tmp.open('xb') as out:
        for part in range(13):
            with (ROOT/f'part-{part:03d}.bin').open('rb') as stream:
                while True:
                    block=stream.read(8*1024*1024)
                    if not block:break
                    out.write(block);md5.update(block);sha.update(block);size+=len(block)
            print('PARTNER_SOURCE_COMPOSED',part,size,flush=True)
    if size!=6777179098 or md5.hexdigest()!='58efcf712f8c4d4de5f2ad51e97def76':raise RuntimeError('Full source failed published MD5/size; partial retained')
    tmp.rename(dest)
    report={'status':'full_pinned_source_acquired','generation':'1780494942562468','bytes':size,'md5':md5.hexdigest(),'sha256':sha.hexdigest(),'whole_source_md5_verified':True,'parts':13,'part_receipts':receipts,'storage':'HF immutable source ranges; assembled file remains in MoLab only','full_input_closure_complete':True,'contacts_extracted':False,'mapping_accepted':False,'plasticity_enabled':False}
    (ROOT/'full-source-closure.json').write_text(json.dumps(report,indent=2))
    final=publish(['full-source-closure.json'])
    print('PARTNER_FULL_SOURCE_COMPLETE',json.dumps({'bytes':size,'parts':13,'md5_verified':True,'sha256':sha.hexdigest(),'receipt':final,'contacts_extracted':False}),flush=True)
if __name__=='__main__':main()
