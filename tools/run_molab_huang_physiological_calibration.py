"""MoLab-only original Huang calibration protocol; not held-out biology."""
import importlib.util,json,os,shutil,subprocess,sys,urllib.request,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from huggingface_hub import HfApi

ROOT=Path('/tmp/fly-huang-physiological-v3-20261005')
OLD=Path('/tmp/fly-huang-native-20261004')
PIN='69987d6e38cb9da1a49879267ff4114c5450348b'

def workbook_observations(path):
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    result={}
    with zipfile.ZipFile(path) as z:
        shared=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
        rels={x.attrib['Id']:x.attrib['Target'] for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',ns):
            target=rels[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
            name=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            values={'Mean':[],'Sem':[]}
            columns=['C','D','E','F','G','H','K','L','M','N','O','P']
            for row in ET.fromstring(z.read(name)).findall('m:sheetData/m:row',ns):
                labels=[];numbers={}
                for cell in row.findall('m:c',ns):
                    val=cell.find('m:v',ns)
                    if val is None:continue
                    if cell.get('t')=='s':labels.append(shared[int(val.text)])
                    elif cell.get('t','n')=='n':
                        column=''.join(c for c in cell.get('r') if c.isalpha())
                        if column not in columns:raise ValueError('Unexpected numeric workbook column')
                        numbers[column]=float(val.text)
                    else:raise ValueError('Unexpected nonnumeric observation')
                kinds=[kind for kind in values if kind in labels]
                if kinds:
                    if len(kinds)!=1:raise ValueError('Ambiguous aggregate workbook row')
                    values[kinds[0]].append([numbers.get(column,float('nan')) for column in columns])
            mean=np.asarray(values['Mean']);sem=np.asarray(values['Sem'])
            if mean.shape!=(6,12) or sem.shape!=(6,12):raise ValueError('Workbook population shape')
            result[sheet.get('name')]=(mean.reshape(6,2,6),sem.reshape(6,2,6))
    return result

def main():
    ROOT.mkdir(exist_ok=True)
    if (ROOT/'summary.json').exists():raise RuntimeError('Inspect completed experiment before reuse')
    spec=importlib.util.spec_from_file_location('archive','/tmp/fly-hf-capacity-20261004/tools/hf_artifact_archive.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    api=HfApi(token=os.environ['HF_TOKEN'])
    if api.whoami()['name']!='TryDotAtwo' or not api.repo_info('TryDotAtwo/faithful-fly-artifacts',repo_type='dataset').private:raise RuntimeError('Archive identity')
    a.require_commit_capacity(api,'TryDotAtwo/faithful-fly-artifacts',commits_needed=10)
    def publish(names):
        receipt=a.publish(ROOT,{'schema':'faithful-fly-artifacts-v1','files':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':a.digest(ROOT/n)} for n in names}})
        if not receipt.get('verified'):raise RuntimeError('Unverified HF stage')
        print('PHYSIOLOGICAL_RECEIPT',json.dumps(receipt),flush=True)
        return receipt
    runner_receipt=publish(['run.py','source-pin.json'])
    original_receipt={'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'62d48988ff2712c029a61912b4ec6cd0e0e4d8d1','manifest':'manifests/82d4d201bc953ac385ca291996bd07e3cbb4aa0d4d8dff272d72ffec55e4fa42.json','sha256':'82d4d201bc953ac385ca291996bd07e3cbb4aa0d4d8dff272d72ffec55e4fa42','verified':True}
    a.restore(OLD,original_receipt)
    if a.digest(OLD/'build/huang_reference.dll')!='2cfd084e87f2e2722840ecc30b8e2fc1744e31da67a973b4f11b47047e4a5e66':raise RuntimeError('Native build identity drift')
    for folder in ('reference','build','tools','reports','native'):(ROOT/folder).mkdir(exist_ok=True)
    for name in ('reference/huang.py','reference/huang_native.py'):
        with urllib.request.urlopen('https://raw.githubusercontent.com/TryDotAtwo/mukha/'+PIN+'/'+name,timeout=30) as response:(ROOT/name).write_bytes(response.read())
    for name in ('build/huang_reference.dll','native/huang.cpp','native/huang.h','tools/check_huang_figure.py','reports/huang_reference_sources.json'):shutil.copyfile(OLD/name,ROOT/name)
    shutil.copytree(OLD/'data/reference/huang_2024',ROOT/'data/reference/huang_2024',dirs_exist_ok=True)
    closure=[p.relative_to(ROOT).as_posix() for folder in ('reference','build','tools','data','reports','native') for p in (ROOT/folder).rglob('*') if p.is_file()]
    inputs=publish(closure)
    regression={'repo_id':'TryDotAtwo/faithful-fly-artifacts','repo_type':'dataset','revision':'f052bd2f4c8c89eb35876ea01239a36a0418d5b3','manifest':'manifests/bef0982675d72f41541956f40c04f525d2b13e9c550f0048a869dc77a074176f.json','sha256':'bef0982675d72f41541956f40c04f525d2b13e9c550f0048a869dc77a074176f','verified':True}
    a.restore(ROOT,regression)
    regression_report=json.loads((ROOT/'reports/huang_native_figure5d_comparison.json').read_text())
    if not regression_report['passed'] or regression_report['library_sha256']!=a.digest(ROOT/'build/huang_reference.dll') or regression_report['translation_sha256']!=a.digest(ROOT/'reference/huang.py'):raise RuntimeError('Previously passed regression identity drift')
    print('FIGURE5D_REGRESSION_REUSED',json.dumps(regression_report),flush=True)
    sys.path.insert(0,str(ROOT))
    modules_loaded=[]
    for name in ('huang','huang_native'):
        spec=importlib.util.spec_from_file_location('physiological_'+name,ROOT/'reference'/f'{name}.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);modules_loaded.append(module)
    huang,huang_native=modules_loaded
    events=huang.physiological_protocol()
    if len(events)!=51 or sum(bool(e[4]) for e in events)!=12 or sum(e[3] for e in events)!=6:raise RuntimeError('Original protocol contract')
    observations=workbook_observations(ROOT/'data/reference/huang_2024/data_and_parameters/Imaging_24hr_data.xlsx')
    conditions=[]
    for modules in (2,3):
        for odor in ('ACVvsETA','OCTvsBEN'):
            key=f'{modules}modules-{odor}'
            params=huang.physiological_parameters(ROOT/f'data/reference/huang_2024/data_and_parameters/Dx_steady_state_nonlinear_3_27-Mar-2023_{modules}modules.mat',odor)
            ref=huang.simulate(params,events,return_all=True)
            native=huang_native.simulate(params,events,return_all=True)
            prediction=huang_native.simulate(params,events)
            reference_imaging=huang.simulate(params,events)
            if prediction.shape!=(6,2,6) or ref.shape!=(51,6) or not np.isfinite(ref).all() or not np.isfinite(native).all():raise RuntimeError('Output shape/nonfinite trajectory')
            error=float(np.max(np.abs(native-ref)))
            imaging_error=float(np.max(np.abs(prediction-reference_imaging)))
            mean,sem=observations[odor]
            included=np.ones(mean.shape,dtype=bool)
            if modules==2:included[[1,4],:,:]=False
            if not np.array_equal(np.isfinite(mean),np.isfinite(sem)):raise RuntimeError('Unmatched mean/SEM missing observation')
            mask=included&np.isfinite(mean)&np.isfinite(sem)
            if not np.all(sem[mask]>0):raise RuntimeError('Nonpositive SEM in observed calibration cells')
            residual=prediction-mean
            report={'schema':'huang-original-calibration-native-v1','modules':modules,'odor_pair':odor,'events':51,'imaging_sessions':6,'all_event_values':306,'imaging_values':72,'tolerance':1e-8,'native_reference_max_abs_error':error,'imaging_max_abs_error':imaging_error,'numerical_passed':error<1e-8 and imaging_error<1e-8,'included_calibration_observations':int(mask.sum()),'included_observations_per_session':[int(mask[:,:,i].sum()) for i in range(6)],'missing_observations_preserved':True,'calibration_rmse':float(np.sqrt(np.mean(residual[mask]**2))),'calibration_sem_weighted_squared_error':float(np.sum((residual[mask]/sem[mask])**2)),'independent_biological_validation':False,'parameters_refitted':False,'scope':'Original aggregate mean/SEM calibration; supplied fit includes all six sessions, including 24hr.'}
            np.savez(ROOT/(key+'.npz'),native_all_events=native,reference_all_events=ref,prediction=prediction,mean=mean,sem=sem,included=mask)
            (ROOT/(key+'.json')).write_text(json.dumps(report,indent=2))
            receipt=publish([key+'.npz',key+'.json'])
            conditions.append({'report':report,'receipt':receipt})
            print('PHYSIOLOGICAL_CONDITION',json.dumps(report),flush=True)
            if not report['numerical_passed']:raise RuntimeError('Numerical mismatch; completed condition archived')
    summary={'schema':'huang-six-session-molab-v1','source_commit':PIN,'author_commit':'5d7c08a9a88f923169a0c3008aca68af421e9a7f','execution':'MoLab foreground only; unchanged native FP64 library','runner_receipt':runner_receipt,'inputs_receipt':inputs,'figure5d_regression_receipt':regression,'conditions':conditions,'independent_biological_validation':False,'contact_learning_enabled':False}
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2))
    receipt=publish(['summary.json'])
    print('PHYSIOLOGICAL_SUMMARY',json.dumps(summary),flush=True)
    print('PHYSIOLOGICAL_FINAL_RECEIPT',json.dumps(receipt),flush=True)

if __name__=='__main__':main()

