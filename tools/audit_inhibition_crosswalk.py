"""Exact source-annotation candidates, never an automatically enabled crosswalk."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'data/derived/malecns_v1_candidates/nodes.feather'
n=pd.read_feather(path)
queries={100513:'chief_9A_L1',13157:'chief_9A_L2',14517:'chief_9A_L3',
         165560:'chief_9A_R1',12443:'chief_9A_R2',12804:'chief_9A_R3',
         10093:'BDN2',10107:'web'}
cols=['bodyId','type','mancBodyid','mancType','subclass','entryNerve','matchingNotes']
matches=[]
for key,label in queries.items():
    hits=n.loc[n.mancBodyid.eq(key),cols]
    matches.append(dict(manc_id=key,author_label=label,candidate_count=len(hits),
        candidates=json.loads(hits.to_json(orient='records')),runtime_enabled=False,
        ambiguity='multiple source annotation matches' if len(hits)>1 else 'cross-specimen annotation only'))
conflict=n.loc[n.type.eq('SNpp38'),cols]
report=dict(source_nodes_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    author_commit='e1233f4a987c532c9f1ab42273af21a0a6a50393',
    source_notebooks=['simulation_run_model.ipynb','manc_9A_web_connectivity.ipynb'],
    matches=matches,author_hook_selector='SNpp38',
    malecns_same_name=json.loads(conflict.to_json(orient='records')),
    interpretation='Author MANC v1 selector cannot be copied by name to this MaleCNS release; resolve versioned identity and morphology first',
    approved_mappings=0)
(ROOT/'reports/inhibition_crosswalk_candidates.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(queried_ids=len(queries),candidate_rows=sum(m['candidate_count'] for m in matches),
    ambiguous_ids=[m['manc_id'] for m in matches if m['candidate_count']>1],
    same_name_hook_candidates=len(conflict),same_name_subclasses=conflict.subclass.value_counts().to_dict())))
