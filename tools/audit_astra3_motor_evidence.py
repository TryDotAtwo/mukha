"""Audit exported motor tables offline; this does not revalidate raw anatomy."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def indexed(rows):
    result = {}
    for row in rows:
        key = row['bodyId']
        require(key not in result, f'duplicate bodyId {key}')
        result[key] = row
    return result


def audit(root, publisher_dir=None):
    hashes = {}

    def read(path):
        data = (root / path).read_bytes()
        hashes[path] = hashlib.sha256(data).hexdigest()
        return data

    def table(path):
        return indexed(csv.DictReader(read(path).decode('utf-8-sig').splitlines()))

    candidates = table('reports/malecns_motor_candidates.csv')
    curated = table('reports/curated_motor_targets.csv')
    predicted = table('reports/malecns_manc_motor_targets.csv')
    lock = json.loads(read('reports/curated_motor_resolution.json'))
    join_lock = json.loads(read('reports/motor_target_join.json'))
    require(hashes['reports/malecns_motor_candidates.csv'] == lock['candidate_sha256'], 'candidate hash mismatch')
    require(hashes['reports/curated_motor_targets.csv'] == lock['output_sha256'], 'curated hash mismatch')
    require(hashes['reports/malecns_manc_motor_targets.csv'] == join_lock['joined_table_sha256'], 'predicted table hash mismatch')
    require(len(candidates) == 815 and len(curated) == 381, 'population size changed')
    require(set(curated) == set(predicted), 'join population mismatch')
    for body, row in curated.items():
        require(body in candidates, f'missing candidate {body}')
        for field in ('graph_index', 'mancGroup', 'mancBodyid', 'somaSide', 'rootSide'):
            require(row[field] == candidates[body][field] == predicted[body][field], f'{body}: inconsistent {field}')
        for field in ('approved_joint', 'approved_torque_sign', 'approved_gain', 'mechanical_evidence'):
            require(row[field] == candidates[body][field] == predicted[body][field] == '', f'{body}: unexpected approval {field}')
    groups = {}
    for group in ('11657', '11706'):
        members = []
        for body, row in curated.items():
            if row['mancGroup'] != group + '.0':
                continue
            require(row['curated_target'] == 'Ti extensor' and row['rootSide'] == '', 'target or laterality changed')
            members.append({k: row[k] for k in ('bodyId', 'graph_index', 'somaSide', 'rootSide', 'mancBodyid')})
        groups[group] = sorted(members, key=lambda r: int(r['bodyId']))
    require({r['bodyId'] for r in groups['11657']} == {'804257', '815344'}, 'group 11657 membership changed')
    require({r['bodyId'] for r in groups['11706']} == {'800636', '815678'}, 'group 11706 membership changed')
    require(predicted['815344']['exact_id_match'] == 'False', '815344 predicted lookup changed')
    require(predicted['815678']['manc_target'] == 'Tergotr.', '815678 predicted target changed')
    draft = json.loads(read('configs/knee_interface_draft.json'))
    require(draft['curated_table_sha256'] == hashes['reports/curated_motor_targets.csv'], 'draft table identity mismatch')
    draft_ids = set()
    for entry in draft['entries']:
        body = str(entry['body_id'])
        require(body not in draft_ids, f'duplicate draft bodyId {body}')
        draft_ids.add(body)
        require(body in curated, f'unknown draft bodyId {body}')
        row = curated[body]
        require(entry['graph_index'] == int(row['graph_index']), f'{body}: draft graph_index mismatch')
        require(entry['curated_manc_group'] == int(float(row['mancGroup'])), f'{body}: draft curated group mismatch')
        require(entry['muscle_annotation'] == row['curated_target'], f'{body}: draft muscle mismatch')
        require(entry['enabled'] is False and entry['gain'] is None and entry['activation_time_constant_ms'] is None, 'draft has active or calibrated entries')
    require(len(draft_ids) == 24, 'draft population changed')
    require({str(e['body_id']) for e in draft['entries']} >= {'800636', '804257', '815344', '815678'}, 'draft omits a group member')
    publisher_check = None
    if publisher_dir is not None:
        sources = {}
        for name, digest in [('supp3.csv', lock['source_sha256']), ('supp6.csv', lock['serial_source_sha256'])]:
            data = (publisher_dir / name).read_bytes()
            require(hashlib.sha256(data).hexdigest() == digest, f'{name}: publisher hash mismatch')
            sources[name] = list(csv.DictReader(data.decode('utf-8-sig').splitlines()))
        source3 = {str(int(float(r['bodyid']))): r for r in sources['supp3.csv']}
        require('10256' not in source3 and source3['22126']['target'] == 'Tergotr.', 'publisher predicted-ID result differs')
        for group, expected_ids, serial in [('11657', {'11657', '13115'}, '10347'), ('11706', {'12704', '11706'}, '10737')]:
            for name, rows in sources.items():
                members = [r for r in rows if str(int(float(r['group']))) == group]
                require({str(int(float(r['bodyid']))) for r in members} == expected_ids, f'{name}: group membership mismatch')
                require(all(r['target'] == 'Ti extensor' for r in members), f'{name}: target mismatch')
                if name == 'supp6.csv':
                    require({r['serial'] for r in members} == {serial}, 'serial group mismatch')
                    require({r['soma_side'] for r in members} == {'LHS', 'RHS'}, 'source soma side mismatch')
        publisher_check = {
            'sha256': {'supp3.csv': lock['source_sha256'], 'supp6.csv': lock['serial_source_sha256']},
            'url_base': 'https://cdn.elifesciences.org/articles/96084/elife-96084-',
            'checks': ['both MANC group memberships and targets', 'serial groups and annotated soma sides', '10256 absent and 22126 target Tergotr.'],
            'does_not_validate': 'MaleCNS raw annotation or individual cross-dataset identity'
        }
    return {
        'schema': 'astra3-exported-motor-evidence-v1',
        'scope': 'Consistency of public exported tables and disabled draft; raw Feather and graph not revalidated. Publisher validation is recorded separately when requested.',
        'input_sha256': hashes,
        'candidate_count': len(candidates), 'leg_count': len(curated),
        'curated_group_members': groups,
        'selected_pair_is_same_curated_group': False,
        'predicted_lookup': {b: {k: predicted[b][k] for k in ('mancBodyid', 'exact_id_match', 'manc_target')} for b in ('815344', '815678')},
        'draft_entries_checked': len(draft['entries']),
        'gate_D_passed': False,
        'unresolved': ['individual cross-dataset identity', 'effector laterality', 'fast/slow motor unit identity', 'spike-to-muscle gain and kinetics', 'aggregation of motor units'],
        'source_validation': 'Historical digests are consistency anchors, not independent evidence of source authenticity.',
        'publisher_source_check': publisher_check
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--publisher-dir', type=Path, help='Optional directory containing publisher supp3.csv and supp6.csv')
    args = parser.parse_args()
    report = json.dumps(audit(args.root, args.publisher_dir), indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')
