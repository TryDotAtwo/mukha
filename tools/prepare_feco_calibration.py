"""Freeze a protocol holdout without using calcium response values to select rows.

Exploratory protocol transfer only: source preprocessing used response clustering.
This is not an independent-animal or raw-data blinded validation.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / 'data/derived/mamiya2018_recordings_v1'
manifest_path = base / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
dest = ROOT / 'data/derived/feco_protocol_partition_v1'
if dest.exists():
    raise FileExistsError('Immutable partition already exists')

# Figure 4 identifies these driver populations and recording regions.
# Branch names do not assign flexion/extension identity to individual clusters.
families = {
    'R73D10': ('claw', {'XBranch': 10, 'YBranch': 10, 'ZBranch': 10}),
    'R64C04': ('club', {'Tip': 14, 'Middle': 11}),
    'R21D12': ('hook', {'Tip': 14, 'YBranch': 9, 'ZBranch': 14}),
}
protocols = {'RampAndHold_FlexFirst': 'calibration',
             'RampAndHold_ExtFirst': 'calibration',
             'Swing_FlexFirst': 'protocol_holdout'}
entries = []
totals = dict(calibration=0, protocol_holdout=0, unassigned_population=0)
for record in manifest['records']:
    stem = Path(record['source_file']).stem
    driver, indicator, region = stem.split('_')
    assert indicator == 'GCaMP6f'
    path = base / (stem + '.npz')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['files'][path.name]
    assert {p['protocol'] for p in record['protocols']} == set(protocols)
    if driver in families:
        family, expected_regions = families[driver]
        expected_flies = expected_regions[region]
    else:
        assert driver == 'InactiveGal4'
        family = None
    for p in record['protocols']:
        role = protocols[p['protocol']] if family else 'unassigned_population'
        if family:
            assert len(p['fly_ids']) == expected_flies, (stem, p['protocol'])
        totals[role] += p['rows']
        entries.append(dict(file=path.name, sha256=manifest['files'][path.name],
                            protocol=p['protocol'], rows=list(range(p['rows'])),
                            population=family, driver=driver, region=region, role=role))
assert sum(totals.values()) == sum(p['rows'] for r in manifest['records'] for p in r['protocols'])
assert len({(e['file'], e['protocol']) for e in entries}) == len(entries)
report = dict(source_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              population_evidence=dict(doi='10.1016/j.neuron.2018.09.009', figure='4',
                url='https://faculty.washington.edu/tuthill/docs/mamiya_2018.pdf'),
              selection_uses_response_values=False, independent_animal_holdout=False,
              raw_preprocessing_independent_of_holdout=False,
              purpose='Exploratory transfer from ramp-and-hold to swing protocols',
              rows_by_role=totals, entries=entries, runtime_enabled=False,
              cluster_functional_identity_assigned=False,
              parameter_fit_performed=False)
dest.mkdir()
(dest / 'manifest.json').write_text(json.dumps(report, indent=2))
(ROOT / 'reports/feco_protocol_partition.json').write_text(json.dumps(report, indent=2))
print(json.dumps(totals))
