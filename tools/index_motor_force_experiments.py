"""Index author-selected force trials, preserving missing archive coverage."""
import hashlib
import json
from pathlib import Path
import re

source = Path('data/reference/azevedo2020/code/Dataset3_SlowInterFast_ForcePerSpike.m')
inventory = Path('reports/azevedo2020_file_inventory.json')
files = json.loads(inventory.read_text())['files']
archives = {f['path']: f for f in files}
pattern = re.compile(r"^T_(fastinter|slow)\{[^}]+\}\s*=\s*\{\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'empty',\s*\[([^]]*)\],\s*\[([^]]*)\]\s*\};")
def trials(expression):
    values = []
    for token in re.split(r'[,\s]+', expression.strip()):
        endpoints = [int(x) for x in token.split(':')]
        if len(endpoints) == 1:
            values += endpoints
        else:
            assert len(endpoints) == 2 and endpoints[0] <= endpoints[1]
            values.extend(range(endpoints[0], endpoints[1]+1))
    assert len(values) == len(set(values))
    return values
rows = []
for line_number, line in enumerate(source.read_text().splitlines(), 1):
    if line.lstrip().startswith('%'):
        continue
    match = pattern.match(line)
    if not match:
        assert not line.startswith(('T_fastinter{', 'T_slow{')), 'Unparsed author assignment'
        continue
    _, cell, genotype, label, protocol, positions, trial_expr = match.groups()
    archive = archives.get(cell+'.zip')
    rows.append(dict(source_line=line_number, cell_id=cell, genotype=genotype,
        motor_unit_label=label, protocol=protocol,
        positions_author_units=[int(x) for x in positions.split()],
        trial_numbers=trials(trial_expr), archive=archive,
        coverage='exact cell-named archive listed' if archive else 'not listed as a cell-named archive; bundled coverage unknown'))
assert len(rows) == 23
counts = {label:sum(r['motor_unit_label'] == label for r in rows) for label in ('fast','intermediate','slow')}
smallest = {label:min((r for r in rows if r['motor_unit_label']==label and r['archive']),
    key=lambda r:r['archive']['size'])['cell_id'] for label in counts}
report = dict(scope='Author force-per-spike experiment index, not downloaded recordings or a calibration fit',
    experiments=rows, counts=counts,
    exact_archive_matches=sum(r['archive'] is not None for r in rows),
    smallest_listed_archive_per_class=smallest,
    selection_policy='Smallest exact archive per motor-unit class for format pilot only; no biological result used for selection. Calibration/validation split not yet assigned.',
    total_dataset_bytes=sum(f['size'] for f in files),
    raw_recordings_downloaded=False,
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source, inventory]})
Path('reports/motor_force_experiment_index.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('experiments','hashes')},indent=2))
