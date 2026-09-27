import sys
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from build_connectome import build, select_nodes, locate, sha256


def annotations():
    return pa.table({'bodyId': [100, 10, 30, 50, 80],
                     'status': ['Traced', 'Traced', None, 'Glia', 'Traced'],
                     'superclass': [None, 'cb_intrinsic', ' ol_sensory ', None, None]})


def test_population_retains_unclassified_traced_and_nontraced_sensory():
    nodes, excluded = select_nodes(annotations())
    assert nodes['bodyId'].to_pylist() == [10, 30, 80, 100]
    assert excluded['bodyId'].to_pylist() == [50]
    assert nodes['compact_index'].to_pylist() == [0, 1, 2, 3]


def test_incoming_orientation_duplicates_loops_and_boundary(tmp_path):
    raw = tmp_path/'source.feather'
    feather.write_feather(pa.table({'body_pre': [100, 10, 10, 30, 50, 999, 10],
                                   'body_post': [10, 30, 30, 30, 10, 100, 999],
                                   'weight': [7, 1, 2, 4, 8, 16, 32]}), raw)
    out = tmp_path/'graph'
    r = build(annotations(), raw, out)
    assert (r['nodes'], r['edges'], r['retained_synapse_count_sum']) == (4, 4, 14)
    assert r['all_source_synapse_count_sum'] == 70
    assert r['self_edges_preserved'] == r['duplicate_pair_rows_preserved'] == 1
    assert r['isolated_nodes_preserved'] == 1
    assert np.load(out/'indptr.npy').tolist() == [0, 1, 4, 4, 4]
    assert np.load(out/'indices.npy').tolist() == [3, 0, 0, 1]
    assert np.load(out/'source_rows.npy').tolist() == [0, 1, 2, 3]
    assert np.load(out/'synapse_counts.npy').tolist() == [7, 1, 2, 4]
    # Direct original-edge multiplication, including duplicate pair and self-loop.
    x = np.array([3, 5, 11, 2])
    ptr, col, w = (np.load(out/(s+'.npy')) for s in ['indptr', 'indices', 'synapse_counts'])
    got = [sum(x[col[int(ptr[i]):int(ptr[i+1])]]*w[int(ptr[i]):int(ptr[i+1])]) for i in range(4)]
    assert got == [14, 29, 0, 0]
    assert sum(map(sum, r['source_rows_by_pre_post_category'])) == 7
    assert not (out/'INCOMPLETE').exists()
    for name, entry in r['files'].items():
        assert sha256(out/name) == entry['sha256']
    with pytest.raises(FileExistsError):
        build(annotations(), raw, out)


def test_bad_weight_leaves_incomplete_marker(tmp_path):
    raw = tmp_path/'bad.feather'
    feather.write_feather(pa.table({'body_pre': [10], 'body_post': [30], 'weight': [0]}), raw)
    with pytest.raises(ValueError, match='nonpositive'):
        build(annotations(), raw, tmp_path/'graph')
    assert (tmp_path/'graph/INCOMPLETE').exists()
    assert not (tmp_path/'graph/manifest.json').exists()


def test_duplicate_ids_rejected_and_search_boundaries():
    a = annotations()
    with pytest.raises(ValueError, match='unique'):
        select_nodes(pa.concat_tables([a, a]))
    _, found = locate(np.array([0,10,11,100,101]), np.array([10,100]))
    assert found.tolist() == [False,True,False,True,False]


def test_no_edges_preserves_all_nodes(tmp_path):
    raw = tmp_path/'empty.feather'
    feather.write_feather(pa.table({s: pa.array([], type=pa.int64()) for s in ['body_pre','body_post','weight']}), raw)
    r = build(annotations(), raw, tmp_path/'graph')
    assert r['edges'] == 0 and r['isolated_nodes_preserved'] == 4
