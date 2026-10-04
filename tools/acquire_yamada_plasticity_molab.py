"""Acquire primary gamma1 plasticity evidence in MoLab; never enable learning."""
import importlib.util,json,sys,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path('/tmp/fly-yamada-plasticity-20261004')
URL='https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/PMC11068490/unicode'
def main():
    ROOT.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('archive', '/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py')
    archive=importlib.util.module_from_spec(spec);spec.loader.exec_module(archive)
    def publish(names):
        receipt=archive.publish(ROOT,{'schema':'faithful-fly-artifacts-v1','files':{name:{'bytes':(ROOT/name).stat().st_size,'sha256':archive.digest(ROOT/name)} for name in names}})
        print('YAMADA_RECEIPT',json.dumps(receipt),flush=True)
        if not receipt.get('verified'):raise RuntimeError('Unverified archive')
        return receipt
    archive.require_commit_capacity(archive.HfApi(token=__import__('os').environ['HF_TOKEN']), 'TryDotAtwo/faithful-fly-artifacts',commits_needed=3)
    publish(['acquire_yamada.py','source-pin.json'])
    request=urllib.request.Request(URL,headers={'User-Agent':'faithful-fly-source-audit/1.0'})
    with urllib.request.urlopen(request,timeout=60) as response:
        raw=response.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise RuntimeError('Source exceeds bound')
    tree=ET.fromstring(raw)
    passages=[]
    for p in tree.findall('.//passage'):
        text=p.findtext('text') or ''
        infons={i.get('key'):i.text for i in p.findall('infon')}
        passages.append({'offset':p.findtext('offset'),'metadata':infons,'text':text})
    if not any('Cyclic nucleotide-induced bidirectional' in p['text'] for p in passages):raise RuntimeError('Wrong article')
    (ROOT/'PMC11068490.bioc.xml').write_bytes(raw)
    (ROOT/'acquisition.json').write_text(json.dumps({'url':URL,'pmcid':'PMC11068490','doi':'10.1113/JP285745','source_sha256':archive.digest(ROOT/'PMC11068490.bioc.xml'),'bytes':len(raw)},indent=2))
    receipt=publish(['PMC11068490.bioc.xml','acquisition.json'])
    selected=[p for p in passages if any(k in p['text'].lower() for k in ('forskolin','pairing protocol','bay 41','female','male flies','data availability','reasonable request'))]
    (ROOT/'source-evidence.json').write_text(json.dumps({'source_receipt':receipt,'passages':selected},ensure_ascii=False,indent=2))
    report={'status':'source_acquired; biological_validation_open','source_receipt':receipt,'source_url':'https://pmc.ncbi.nlm.nih.gov/articles/PMC11068490/','compartment':'KC to MBON gamma1pedc','constraints':['Low-dose forskolin alone differs from forskolin paired with KC activation.','Require activity-dependent presynaptic LTD and paired-pulse readout.','High-dose forskolin alone is a distinct intervention.','Compare active and inactive KC cAMP observations separately.','Keep gamma and alpha/beta KC durations separate.','Keep gamma1 independent from Handler gamma4 calibration.'],'raw_recordings_available_to_model':False,'plasticity_enabled':False,'limits':'Source evidence only; no fitted rule, quantitative reproduction, MaleCNS contact mapping, or animal-level equivalence bound. Nonsignificance is not exact equality.','next_experiment':'Freeze separate gamma1 paired/unpaired controls and observation mapping before testing native candidate rules.'}
    (ROOT/'report.json').write_text(json.dumps(report,indent=2))
    final=publish(['source-evidence.json','report.json'])
    print('YAMADA_PUBLIC_REPORT',json.dumps(report),flush=True)
    print('YAMADA_FINAL_RECEIPT',json.dumps(final),flush=True)
if __name__=='__main__':main()
