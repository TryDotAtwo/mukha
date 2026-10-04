"""Stratify full published KC-MBON contacts for gamma1 candidates in MoLab."""
import importlib.util,json,os,shutil
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import HfApi,hf_hub_download
ROOT=Path('/tmp/fly-yamada-anatomy-20261004')
REV='9ec22f9cb1b0358ee8bef432dd1c9c44c36bb4b8'
REPO='TryDotAtwo/faithful-fly-artifacts'
OBJECTS={'nodes.feather':'4335bd9cb4c0098c36e879ae64e97c76ce4fea96a6ad200b16d99aa5d1d0f5e2','contacts-a.parquet':'888ea69ade19b0376b57c60ee75c5f93102285e2d98f9943619145e449b0f801','contacts-b.parquet':'f1f3f40216b0e58865ae4b9b725c7a2c4d8a28b7f1e270a044ecb925702bb596'}
def main():
    ROOT.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('archive','/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    api=HfApi(token=os.environ['HF_TOKEN'])
    if not api.repo_info(REPO,repo_type='dataset').private or api.whoami()['name']!='TryDotAtwo':raise RuntimeError('Archive identity')
    a.require_commit_capacity(api,REPO,commits_needed=3)
    def publish(names):
        r=a.publish(ROOT,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':a.digest(ROOT/n)} for n in names}})
        if not r.get('verified'):raise RuntimeError('Unverified publication')
        print('ANATOMY_RECEIPT',json.dumps(r),flush=True);return r
    publish(['audit.py','source-pin.json'])
    for name,sha in OBJECTS.items():
        path=Path(hf_hub_download(REPO,'objects/'+sha,repo_type='dataset',revision=REV,token=os.environ['HF_TOKEN']))
        if a.digest(path)!=sha:raise RuntimeError('Input checksum '+name)
        dest=ROOT/name
        if dest.exists() and a.digest(dest)!=sha:raise RuntimeError('Changed recovered input')
        if not dest.exists():shutil.copyfile(path,dest)
    (ROOT/'input-identity.json').write_text(json.dumps({'revision':REV,'objects':OBJECTS,'scope':'Original full KC-MBON contact extraction; annotation labels are candidate identities'},indent=2))
    receipt=publish(list(OBJECTS)+['input-identity.json'])
    nodes=pd.read_feather(ROOT/'nodes.feather',columns=['bodyId','class','type','instance'])
    if len(nodes)!=167216 or not nodes.bodyId.is_unique:raise RuntimeError('Wrong node population')
    kc=nodes[nodes['class'].eq('Kenyon_Cell')]
    mb=nodes[nodes['class'].eq('MBON') & nodes['type'].eq('MBON11')]
    contacts=pd.concat([pq.read_table(ROOT/n,columns=['body_pre','body_post','primary_post']).to_pandas() for n in ('contacts-a.parquet','contacts-b.parquet')],ignore_index=True)
    if len(contacts)!=463640 or len(kc)!=4064:raise RuntimeError('Wrong full contact coverage')
    if not contacts.body_pre.isin(kc.bodyId).all():raise RuntimeError('Non-KC source')
    selected=contacts[contacts.body_post.isin(mb.bodyId)].merge(kc[['bodyId','type','instance']].rename(columns={'bodyId':'body_pre','type':'kc_type','instance':'kc_instance'}),on='body_pre',validate='many_to_one')
    groups=selected.groupby(['body_post','kc_type','primary_post'],dropna=False).size().reset_index(name='contacts')
    groups.to_csv(ROOT/'gamma1-candidate-contact-strata.csv',index=False)
    result={'scope':'All published KC-MBON contacts stratified by source KC annotation for name-matched MBON11 candidates; not a gamma1 compartment assignment','nodes':len(nodes),'all_kc_mbon_contacts':len(contacts),'kc_cells':len(kc),'input_receipt':receipt,'candidate_mbons':mb.to_dict(orient='records'),'selected_contacts':len(selected),'unique_presynaptic_kcs':int(selected.body_pre.nunique()),'kc_type_contact_counts':selected.groupby('kc_type',dropna=False).size().to_dict(),'kc_type_cell_counts':kc.groupby('type',dropna=False).size().to_dict(),'roi_contact_counts':selected.groupby('primary_post',dropna=False).size().to_dict(),'mapping_accepted':False,'plasticity_enabled':False,'limits':'KC labels and broad ROI do not establish gamma1 microcompartment, recorded animal identity, receptor action or local efficacy.'}
    (ROOT/'report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    final=publish(['gamma1-candidate-contact-strata.csv','report.json'])
    print('ANATOMY_PUBLIC_REPORT',json.dumps(result,ensure_ascii=False),flush=True)
    print('ANATOMY_FINAL_RECEIPT',json.dumps(final),flush=True)
if __name__=='__main__':main()
