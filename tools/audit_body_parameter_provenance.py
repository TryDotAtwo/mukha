"""Trace diagnostic mechanics to pinned author defaults versus project choices."""
import ast
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

source = Path('data/reference/flygym_2.1.0/src/flygym/compose/fly/base_fly.py')
lock = json.loads(Path('reports/body_reference_sources.json').read_text())
entry = next(e for e in lock['flygym_files'] if Path(e['path']) == source)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source) == entry['sha256']
tree = ast.parse(source.read_text())
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'add_joints')
defaults = {a.arg: ast.literal_eval(v) for a, v in zip(fn.args.kwonlyargs, fn.args.kw_defaults)
            if a.arg in ('stiffness', 'damping', 'armature')}
assert defaults == dict(stiffness=10., damping=.5, armature=1e-6)
model = Path('data/derived/contact_diagnostic/body.xml')
xml = ET.parse(model).getroot()
joints = [j for j in xml.findall('.//worldbody//joint') if j.get('name') != 'control_slide']
for j in joints:
    for key, value in defaults.items():
        assert float(j.get(key)) == value, (j.get('name'), key)
report = dict(flygym_commit=lock['flygym_commit'], author_source_url=entry['source_url'],
    author_default_function_line=fn.lineno, uniform_joint_defaults=defaults,
    matching_joint_count=len(joints),
    provenance=[
        dict(parameters=['joint stiffness', 'joint damping', 'joint armature'],
             origin='Pinned FlyGym BaseFly.add_joints defaults, inherited by NeuroMechFly',
             physiological_calibration_demonstrated=False),
        dict(parameters=['motor force range +/-1', 'motor control range +/-1'],
             origin='Project tools/export_body.py explicit engineering choices',
             physiological_calibration_demonstrated=False),
        dict(parameters=['spike gain 0.1', 'decay 20 ms'],
             origin='Project native/brain_body_probe.cpp diagnostic filter',
             physiological_calibration_demonstrated=False),
        dict(parameters=['slider geometry', 'slider mass', 'slider stiffness', 'slider damping'],
             origin='Project tools/export_contact.py engineering cockpit bench',
             physiological_calibration_demonstrated=False)],
    decision='Retain existing diagnostic baseline. Do not infer biological inability from its failure to contact. No parameter change is made by this audit.',
    calibration_source=dict(doi='10.7554/eLife.56754', local_pdf='data/reference/azevedo2020/article.pdf',
        relevant_pages=[9,10,11,32], dataset_doi='10.5061/dryad.76hdr7stb',
        applicability='Measured tibia FLEXOR motor units; not direct calibration for current active EXTENSOR units or identified MaleCNS IDs',
        unresolved=['motor-unit identity crosswalk', 'force-to-joint-torque geometry', 'passive joint measurements', 'extensor force dynamics']),
    hashes={str(p): sha(p) for p in [source, model, Path('tools/export_body.py'),
        Path('tools/export_contact.py'), Path('native/brain_body_probe.cpp'),
        Path('data/reference/azevedo2020/article.pdf')]})
Path('reports/body_parameter_provenance.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'defaults':defaults, 'matching_joints':len(joints), 'decision':report['decision']}, indent=2))
