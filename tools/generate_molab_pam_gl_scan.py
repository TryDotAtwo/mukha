"""Generate a foreground Molab scan of name-matched PAM output sites in gL."""
import base64
import json
from pathlib import Path
import zlib

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
nodes = pd.read_feather(ROOT / 'data/derived/malecns_v1_candidates/nodes.feather',
                        columns=['bodyId', 'class', 'instance'])
dan = nodes[nodes['class'].eq('DAN')]
groups = {
    'PAM08_y4': sorted(map(int, dan.loc[dan.instance.str.fullmatch(r'PAM08\(y4\)_[LR]', na=False), 'bodyId'])),
    'PAM07_y4_y1y2': sorted(map(int, dan.loc[dan.instance.str.fullmatch(r'PAM07\(y4<y1y2\)_[LR]', na=False), 'bodyId'])),
    'PAM01_y5_control': sorted(map(int, dan.loc[dan.instance.str.fullmatch(r'PAM01\(y5\)_[LR]', na=False), 'bodyId'])),
}
assert [len(v) for v in groups.values()] == [50, 14, 44]
payload = base64.b64encode(zlib.compress(json.dumps(groups).encode(), 9)).decode()
template = r'''
def _scan_pam_gl():
    import base64, hashlib, json, time, zlib
    from collections import Counter
    from pathlib import Path
    import fsspec
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    import requests

    _groups = json.loads(zlib.decompress(base64.b64decode("PAYLOAD")))
    _ids = sorted(set().union(*(set(v) for v in _groups.values())))
    assert len(_ids) == 108
    _url = ('https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/'
            'flat-connectome/syn-partners-male-cns-v1.0-minconf-0.5.feather')
    _generation = '1780494942562468'
    _pinned_url = _url + '?generation=' + _generation
    _head = requests.head(_pinned_url, timeout=30)
    _head.raise_for_status()
    assert _head.headers['x-goog-generation'] == _generation
    assert int(_head.headers['Content-Length']) == 6777179098
    _folder = Path('/marimo/mb-synapse-scan')
    _folder.mkdir(exist_ok=True)
    _out = _folder / 'pam-y4-y5-gl.parquet'
    _report = _folder / 'pam-y4-y5-gl-report.json'
    assert not _out.exists() and not _report.exists(), 'Existing output requires inspection'
    _id_array = pa.array(_ids, type=pa.int64())
    _roi_array = pa.array(['gL(L)', 'gL(R)'])
    _begin = time.monotonic()
    _total = 0
    _writer = None
    try:
        with fsspec.open(_pinned_url, 'rb', block_size=16 << 20) as _stream:
            _reader = pa.ipc.open_file(_stream)
            assert _reader.num_record_batches == 4759
            for _index in range(_reader.num_record_batches):
                _batch = _reader.get_batch(_index)
                _mask = pc.and_(pc.is_in(_batch.column('body_pre'), value_set=_id_array),
                                pc.is_in(_batch.column('primary_post'), value_set=_roi_array))
                _subset = pa.Table.from_batches([_batch]).filter(_mask)
                if _subset.num_rows:
                    if _writer is None:
                        _writer = pq.ParquetWriter(_out, _subset.schema, compression='zstd')
                    _writer.write_table(_subset)
                _total += _subset.num_rows
                if (_index+1) % 20 == 0 or _index+1 == _reader.num_record_batches:
                    print('PAM_GL_SCAN_PROGRESS',json.dumps({'batch':_index+1,
                          'contacts':_total,'elapsed_s':round(time.monotonic()-_begin,2)}),flush=True)
    finally:
        if _writer is not None:
            _writer.close()
    assert _writer is not None
    with _out.open('rb') as _file:
        _hash = hashlib.file_digest(_file, 'sha256').hexdigest()
    _record = {'source':{'pinned_url':_pinned_url,'generation':_generation,
                         'etag':_head.headers['ETag'],
                         'x_goog_hash':_head.headers.get('x-goog-hash')},
               'groups':_groups,'roi_filter':['gL(L)','gL(R)'],
               'batches':4759,'contacts':_total,'bytes':_out.stat().st_size,
               'sha256':_hash,'elapsed_s':time.monotonic()-_begin,
               'scope':'Name-matched DAN chemical-output sites in broad gamma lobe; not dopamine release range'}
    _report.write_text(json.dumps(_record,indent=2))
    print('PAM_GL_SCAN_COMPLETE',json.dumps(_record),flush=True)

_scan_pam_gl()
'''
out = ROOT / 'build/molab_pam_gl_scan.py'
out.parent.mkdir(exist_ok=True)
out.write_text(template.replace('PAYLOAD', payload), encoding='utf-8')
print(out, out.stat().st_size)
