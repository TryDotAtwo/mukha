"""Inspect official MaleCNS brain ROI labels; never infer teaching masks."""
import importlib.util,json,os,re,urllib.request,urllib.error
from pathlib import Path
from huggingface_hub import HfApi
ROOT=Path('/tmp/fly-gamma1-roi-audit-20261004')
BASE='https://storage.googleapis.com/flyem-male-cns/rois/'
def main():
    ROOT.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('archive','/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    api=HfApi(token=os.environ['HF_TOKEN'])
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('Archive identity')
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=6)
    def publish(names):
        r=a.publish(ROOT,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':a.digest(ROOT/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('Unverified ROI source')
        print('ROI_RECEIPT',json.dumps(r),flush=True);return r
    publish(['audit.py','source-pin.json'])
    def acquire(url,name):
        if (ROOT/name).exists() and (ROOT/(name+'.identity.json')).exists():
            record=json.loads((ROOT/(name+'.identity.json')).read_text())
            if record['url']!=url or a.digest(ROOT/name)!=record['sha256']:raise RuntimeError('Changed saved metadata')
            receipt=publish([name,name+'.identity.json'])
            return record,receipt,json.loads((ROOT/name).read_bytes()) if record['http_status']==200 else None
        status=200;generation=None
        try:
            with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=30) as response:generation=response.headers.get('x-goog-generation')
            pinned=url+('?generation='+generation if generation else '')
            with urllib.request.urlopen(pinned,timeout=30) as response:raw=response.read(2*1024*1024+1);status=response.status
        except urllib.error.HTTPError as error:raw=error.read(2*1024*1024+1);status=error.code;pinned=url
        if len(raw)>2*1024*1024:raise RuntimeError('Metadata bound exceeded')
        (ROOT/name).write_bytes(raw)
        record={'url':url,'pinned_url':pinned,'generation':generation,'http_status':status,'bytes':len(raw),'sha256':a.digest(ROOT/name)}
        (ROOT/(name+'.identity.json')).write_text(json.dumps(record,indent=2))
        receipt=publish([name,name+'.identity.json'])
        return record,receipt,json.loads(raw) if status==200 else None
    results=[]
    for version in ('fullbrain-roi-v4','fullbrain-roi-v5'):
        url=BASE+version+'/info'
        identity,receipt,info=acquire(url,version+'-info.json')
        result={'atlas':version,'info_identity':identity,'info_receipt':receipt,'labels':[],'status':'info_unavailable'}
        if info is not None:
            relative=info.get('segment_properties')
            result['segment_properties']=relative;result['status']='labels_unavailable'
            if isinstance(relative,str) and relative and not relative.startswith(('/', 'http:', 'https:', 'gs:')) and '..' not in relative.split('/'):
                propurl=BASE+version+'/'+relative.rstrip('/')+'/info'
                pid,prec,props=acquire(propurl,version+'-properties.json')
                result['properties_identity']=pid;result['properties_receipt']=prec
                if props is not None:
                    inline=props.get('inline',{})
                    fields=inline.get('properties',[])
                    labels=[p['values'] for p in fields if p.get('type')=='label']
                    if len(labels)!=1 or len(labels[0])!=len(inline.get('ids',[])):raise RuntimeError('Ambiguous label coverage')
                    result['labels']=labels[0];result['label_count']=len(labels[0]);result['status']='labels_inspected'
                    result['microcompartment_name_matches']=[label for label in labels[0] if re.search(r'(^|[^a-z])(g[1-5]|gamma[1-5]|γ[1-5])([(_ -]|$)|pedc',label.lower())]
                    result['mushroom_body_labels']=[label for label in labels[0] if re.match(r"^(gL|PED|aL|bL|a'L|b'L)",label)]
        results.append(result)
    report={'scope':'Official fullbrain ROI v4/v5 info and explicitly referenced segment label properties only','results':results,'gamma1_contact_mask_assigned':False,'plasticity_enabled':False,'limits':'Absence of named microcompartments in these atlas labels does not establish absence of every published or neuPrint compartment source. Broad lobar labels cannot directly assign gamma1 contact identity. No volume, mesh or geometry classification performed.'}
    (ROOT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    final=publish(['report.json'])
    print('ROI_PUBLIC_REPORT',json.dumps(report,ensure_ascii=False),flush=True)
    print('ROI_FINAL_RECEIPT',json.dumps(final),flush=True)
if __name__=='__main__':main()
