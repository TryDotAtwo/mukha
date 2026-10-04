"""Acquire one immutable range of the pinned full MaleCNS partner source."""
import argparse,importlib.util,json,os,time,urllib.request
from pathlib import Path
from huggingface_hub import HfApi
URL='https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/syn-partners-male-cns-v1.0-minconf-0.5.feather?generation=1780494942562468'
TOTAL=6777179098
CHUNK=536870912
ROOT=Path('/tmp/fly-malecns-partner-source-20261004')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--part',type=int,required=True);args=parser.parse_args()
    part=args.part
    if not 0<=part<(TOTAL+CHUNK-1)//CHUNK:raise ValueError('Part outside source')
    ROOT.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('archive','/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    api=HfApi(token=os.environ['HF_TOKEN'])
    if not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private or api.whoami()['name']!='TryDotAtwo':raise RuntimeError('Archive identity')
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=2)
    def publish(names):
        r=a.publish(ROOT,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':a.digest(ROOT/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('Unverified range archive')
        print('PARTNER_SOURCE_RECEIPT',json.dumps(r),flush=True);return r
    publish(['acquire.py','source-pin.json'])
    start=part*CHUNK;end=min(TOTAL,start+CHUNK)-1
    name=f'part-{part:03d}.bin';dest=ROOT/name;tmp=ROOT/(name+'.partial')
    if dest.exists():raise RuntimeError('Inspect completed part before reuse; no blind overwrite')
    request=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{end}'})
    print('PARTNER_SOURCE_BEGIN',json.dumps({'part':part,'parts':(TOTAL+CHUNK-1)//CHUNK,'start':start,'end':end,'bytes':end-start+1}),flush=True)
    with urllib.request.urlopen(request,timeout=60) as response:
        expected=f'bytes {start}-{end}/{TOTAL}'
        if response.status!=206 or response.headers.get('Content-Range')!=expected:raise RuntimeError('Pinned source range mismatch')
        generation=response.headers.get('x-goog-generation')
        if generation!='1780494942562468':raise RuntimeError('Generation mismatch')
        headers={k:response.headers.get(k) for k in ('Content-Range','ETag','x-goog-generation','x-goog-hash')}
        if (headers['ETag'] or '').strip('"')!='58efcf712f8c4d4de5f2ad51e97def76':raise RuntimeError('Source ETag changed')
        amount=0;last=time.monotonic()
        with tmp.open('xb') as stream:
            while True:
                block=response.read(8*1024*1024)
                if not block:break
                stream.write(block);amount+=len(block)
                if amount>end-start+1:raise RuntimeError('Oversized source range')
                if time.monotonic()-last>=15:print('PARTNER_SOURCE_BYTES',amount,flush=True);last=time.monotonic()
    if amount!=end-start+1:raise RuntimeError('Incomplete source range retained')
    tmp.rename(dest)
    meta={'url':URL,'headers':headers,'part':part,'parts':(TOTAL+CHUNK-1)//CHUNK,'start':start,'end':end,'bytes':amount,'sha256':a.digest(dest),'whole_source_md5_expected':'58efcf712f8c4d4de5f2ad51e97def76','whole_source_md5_verified':False,'full_input_closure_complete':False,'analysis_started':False}
    metaname=f'part-{part:03d}.json';(ROOT/metaname).write_text(json.dumps(meta,indent=2))
    receipt=publish([name,metaname])
    (ROOT/f'receipt-{part:03d}.json').write_text(json.dumps(receipt,indent=2))
    print('PARTNER_SOURCE_PART_COMPLETE',json.dumps({'part':part,'bytes':amount,'receipt':receipt,'whole_source_complete':False}),flush=True)
if __name__=='__main__':main()
