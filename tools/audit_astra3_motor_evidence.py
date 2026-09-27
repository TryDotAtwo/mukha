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


def audit(root):
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
    for entry in draft['entries']:
        require(entry['enabled'] is False and entry['gain'] is None and entry['activation_time_constant_ms'] is None, 'draft has active or calibrated entries')
    require({str(e['body_id']) for e in draft['entries']} >= {'800636', '804257', '815344', '815678'}, 'draft omits a group member')
    return {
        'schema': 'astra3-exported-motor-evidence-v1',
        'scope': 'Consistency of public exported tables and disabled draft; raw Feather, graph and publisher sources not revalidated',
        'input_sha256': hashes,
        'candidate_count': len(candidates), 'leg_count': len(curated),
        'curated_group_members': groups,
        'selected_pair_is_same_curated_group': False,
        'predicted_lookup': {b: {k: predicted[b][k] for k in ('mancBodyid', 'exact_id_match', 'manc_target')} for b in ('815344', '815678')},
        'draft_entries_checked': len(draft['entries']),
        'gate_D_passed': False,
        'unresolved': ['individual cross-dataset identity', 'effector laterality', 'fast/slow motor unit identity', 'spike-to-muscle gain and kinetics', 'aggregation of motor units'],
        'source_validation': 'Historical digests are consistency anchors, not independent evidence of source authenticity.'
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = json.dumps(audit(args.root), indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')
