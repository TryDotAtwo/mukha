"""Compare name-matched PAM output-site proximity to KC->MBON contacts.

Nearest chemical-output sites are anatomical proxies, not dopamine diffusion or
per-synapse teaching assignments. The y5 MBONs are anatomical controls.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/derived/mb_synapse_locations_v1/molab_full'
NODES = ROOT / 'data/derived/malecns_v1_candidates/nodes.feather'
OUT = ROOT / 'reports/malecns_pam_mb_spatial.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    report = json.loads((DATA / 'pam-y4-y5-gl-report.json').read_text(encoding='utf-8'))
    path = DATA / 'pam-y4-y5-gl.parquet'
    assert path.stat().st_size == report['bytes'] and sha(path) == report['sha256']
    assert report['source']['generation'] == '1780494942562468'
    source = json.loads((DATA / 'report-00000-04759.json').read_text(encoding='utf-8'))
    assert source['source']['generation'] == report['source']['generation']
    kc_path = DATA / 'contacts-00000-04759.parquet'
    assert sha(kc_path) == source['sha256']
    nodes = pd.read_feather(NODES, columns=['bodyId', 'class', 'instance'])
    targets = nodes[(nodes['class'] == 'MBON') & nodes.instance.fillna('').str.match(
        r'^MBON(05\(y4>y1y2\)|27\(y5d\)|01\(y5B\x272a\))_[LR]$')]
    assert len(targets) == 6
    pam = pq.read_table(path).to_pandas()
    kc = pq.read_table(kc_path).to_pandas()
    assert len(pam) == report['contacts'] == 81367
    group_of = {int(neuron):name for name, neurons in report['groups'].items()
                for neuron in neurons}
    assert len(group_of) == 108 and set(map(int, pam.body_pre)) <= set(group_of)
    pam['group'] = pam.body_pre.map(group_of)
    results = []
    for roi in ('gL(L)', 'gL(R)'):
        by_group = {}
        for name in report['groups']:
            subset = pam[(pam.primary_post == roi) & (pam.group == name)]
            points = np.unique(subset[['x_pre','y_pre','z_pre']].to_numpy(np.float64), axis=0)
            assert len(points)
            by_group[name] = {'points':points, 'tree':cKDTree(points),
                              'partner_rows':len(subset)}
        balance_count = min(len(by_group['PAM08_y4']['points']),
                            len(by_group['PAM01_y5_control']['points']))
        balanced_trees = []
        for seed in range(10):
            rng = np.random.default_rng(seed)
            balanced_trees.append({name:cKDTree(item['points'][rng.choice(
                len(item['points']),size=balance_count,replace=False)])
                for name,item in by_group.items()
                if name in ('PAM08_y4','PAM01_y5_control')})
        for target in targets.itertuples():
            subset = kc[(kc.primary_post == roi) & (kc.body_post == target.bodyId)]
            if len(subset) < 100:
                continue
            points = subset[['x_post','y_post','z_post']].to_numpy(np.float64)
            distances = {name:item['tree'].query(points, workers=1)[0]
                         for name,item in by_group.items()}
            y4 = distances['PAM08_y4']
            y5 = distances['PAM01_y5_control']
            per_kc = pd.DataFrame({'body_pre':subset.body_pre.to_numpy(),
                                   'y4':y4,'y5':y5}).groupby('body_pre').median()
            balanced_fractions = []
            for trees in balanced_trees:
                d4 = trees['PAM08_y4'].query(points, workers=1)[0]
                d5 = trees['PAM01_y5_control'].query(points, workers=1)[0]
                balanced_fractions.append(float(np.mean(d4 < d5)))
            metric = {'target_body_id':int(target.bodyId), 'target_instance':target.instance,
                      'roi':roi, 'kc_contacts':len(subset),
                      'pam_output_rows':{name:item['partner_rows'] for name,item in by_group.items()},
                      'pam_unique_output_sites':{name:len(item['points']) for name,item in by_group.items()},
                      'nearest_distance_voxels':{
                          name:{'p10':float(np.quantile(d, .1)),
                                'median':float(np.median(d)),
                                'p90':float(np.quantile(d, .9))}
                          for name,d in distances.items()},
                      'fraction_pam08_y4_nearer_than_pam01_y5':float(np.mean(y4 < y5)),
                      'kc_cells_with_contacts':len(per_kc),
                      'fraction_kc_cells_median_y4_nearer':float(np.mean(per_kc.y4 < per_kc.y5)),
                      'equal_site_count_per_group':balance_count,
                      'balanced_site_fraction_y4_nearer_seeds_0_to_9':balanced_fractions,
                      'fraction_equal_distance':float(np.mean(y4 == y5))}
            results.append(metric)
    assert len(results) >= 6, [(v['target_instance'],v['roi']) for v in results]
    record = {'scope':'Nearest known PAM chemical-output site to KC->MBON contact in same broad gL ROI; no release-range model or accepted compartment assignment',
              'source_generation':report['source']['generation'],
              'pam_parquet_sha256':report['sha256'],
              'kc_mbon_parquet_sha256':source['sha256'],
              'coordinate_unit':'published 8-nm voxel indices; distances reported in voxels',
              'targets':results,
              'per_synapse_teaching_signal_assigned':False,
              'plasticity_enabled':False,
              'biological_gate_passed':False}
    OUT.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    for item in results:
        print(item['target_instance'],item['roi'],item['kc_contacts'],
              'frac_y4_nearer',round(item['fraction_pam08_y4_nearer_than_pam01_y5'],3),
              'median_y4',round(item['nearest_distance_voxels']['PAM08_y4']['median'],2),
              'median_y5',round(item['nearest_distance_voxels']['PAM01_y5_control']['median'],2))


if __name__ == '__main__':
    run()
