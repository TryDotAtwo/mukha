"""Check pinned historical model parameter names against pinned current runtime."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    for name,folder in [('lamina_reference_sources','lamina'),('neurodriver_graded_sources','neurodriver_graded')]:
        lock=json.loads((ROOT/f'reports/{name}.json').read_text())
        for e in lock['files']:
            if hashlib.sha256((ROOT/f'data/reference/{folder}'/e['path']).read_bytes()).hexdigest()!=e['sha256']:
                raise ValueError('Source changed: '+e['path'])
    historical=ROOT/'data/reference/lamina/lamina/vision_models/lamina_model_template.py'
    current=ROOT/'data/reference/neurodriver_graded/neurokernel/LPU/NDComponents/MembraneModels/MorrisLecar.py'
    tree=ast.parse(current.read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MorrisLecar')
    required=next(ast.literal_eval(n.value) for n in cls.body if isinstance(n,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='params' for t in n.targets))
    cells=[]
    for n in ast.walk(ast.parse(historical.read_text())):
        if not isinstance(n,ast.Dict):continue
        fields={ast.literal_eval(k):v for k,v in zip(n.keys,n.values) if isinstance(k,ast.Constant)}
        if not isinstance(fields.get('class'),ast.Constant) or fields['class'].value!='MorrisLecar':continue
        cells.append({'name':ast.literal_eval(fields['name']),
                      'missing_required_names':sorted(set(required)-set(fields)),
                      'historical_keys':sorted(fields)})
    report={'scope':'Source interface compatibility audit, not biological validation',
            'current_required_parameters':required,'cells':cells,
            'direct_parameter_compatibility':all(not c['missing_required_names'] for c in cells),
            'automatic_transfer_enabled':False,
            'graded_synapse_equation':'g=min(saturation,slope*max(0,Vpre-threshold)^power)',
            'unresolved':['historical-to-current parameter semantics and naming',
                          'scale/delay and reversal handling outside conductance kernel',
                          'MaleCNS edge counts versus author cartridge scale',
                          'cell-specific biological calibration'],
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [historical,current]}}
    (ROOT/'reports/graded_interface_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'cells':len(cells),'direct_parameter_compatibility':report['direct_parameter_compatibility'],
                      'missing_names':sorted(set(x for c in cells for x in c['missing_required_names']))},indent=2))

if __name__=='__main__':main()
