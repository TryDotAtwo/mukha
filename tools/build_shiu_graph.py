"""Prepare the complete author's graph for biological replication; no MaleCNS transfer."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''): h.update(block)
    return h.hexdigest()


def main():
    lock = json.loads((ROOT/'reports/shiu_reference_sources.json').read_text())
    paths = {}
    for record in lock['files']:
        path = ROOT/record['path']
        if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
            raise ValueError('Source lock mismatch: '+path.name)
        paths[path.name] = path
    nodes = pd.read_csv(paths['2023_03_23_completeness_630_final.csv'],index_col=0)
    edges = pd.read_parquet(paths['2023_03_23_connectivity_630_final.parquet'])
    ids = nodes.index.to_numpy(dtype=np.int64)
    if len(np.unique(ids)) != len(ids): raise ValueError('Duplicate source neuron ID')
    pre,post = [edges[k].to_numpy() for k in ('Presynaptic_Index','Postsynaptic_Index')]
    if pre.min()<0 or post.min()<0 or pre.max()>=len(ids) or post.max()>=len(ids):
        raise ValueError('Source index outside population')
    if not (np.array_equal(ids[pre],edges.Presynaptic_ID) and np.array_equal(ids[post],edges.Postsynaptic_ID)):
        raise ValueError('Author IDs and indices disagree')
    signed = edges['Excitatory x Connectivity'].to_numpy()
    if not np.array_equal(signed,edges.Connectivity.to_numpy()*edges.Excitatory.to_numpy()):
        raise ValueError('Signed author weights disagree with component columns')
    out = ROOT/'data/derived/shiu_2024'
    out.mkdir(parents=True,exist_ok=False)
    (out/'INCOMPLETE').write_text('Graph under construction\n')
    # Stable source row is retained even if multiple rows share one pair.
    order = np.lexsort((np.arange(len(edges)),pre,post))
    row = np.r_[0,np.cumsum(np.bincount(post,minlength=len(ids)))].astype(np.uint64)
    for name,array in (
        ('body_ids',ids),('indptr',row),('indices',pre[order].astype(np.uint32)),
        ('signed_synapse_counts',signed[order]),('source_rows',order.astype(np.uint64)),
        ('weights_mv',(signed[order]*0.275).astype(np.float32))):
        np.save(out/(name+'.npy'),array)
    duplicate_rows = int(np.count_nonzero((pre[order[1:]]==pre[order[:-1]]) & (post[order[1:]]==post[order[:-1]])))
    report = dict(format='flyrocket.shiu-author-csr.v1',repository=lock['repository'],commit=lock['commit'],
                  nodes=len(ids),edges=len(edges),orientation='row=post; columns=pre',
                  signed_weight_rule='original signed synapse count * 0.275 mV',
                  duplicate_pair_rows=duplicate_rows,source_rows_preserved=True,
                  source_lock_sha256=digest(ROOT/'reports/shiu_reference_sources.json'),
                  files={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(out.glob('*.npy'))},
                  scope='original author graph only; biological experiments not yet run; no MaleCNS sign assignment')
    text = json.dumps(report,indent=2)+'\n'
    (out/'manifest.json').write_text(text)
    (out/'INCOMPLETE').unlink()
    (ROOT/'reports/shiu_runtime_graph.json').write_text(text)
    print(json.dumps({k:report[k] for k in ('nodes','edges','duplicate_pair_rows','scope')}))


if __name__ == '__main__': main()
