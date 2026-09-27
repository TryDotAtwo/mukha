"""Generate a self-contained Molab foreground scan cell with public IDs only."""
import base64
import json
from pathlib import Path
import zlib

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
nodes = pd.read_feather(ROOT / 'data/derived/malecns_v1_candidates/nodes.feather',
                        columns=['bodyId', 'class'])
groups = {name: sorted(map(int, nodes.loc[nodes['class'].eq(name), 'bodyId']))
          for name in ('Kenyon_Cell', 'MBON')}
assert len(groups['Kenyon_Cell']) == 4064 and len(groups['MBON']) == 97
payload = base64.b64encode(zlib.compress(json.dumps(groups).encode(), 9)).decode()
template = r'''
def _scan_mb_contacts(_start=0, _stop=100):
    import base64, hashlib, json, time, zlib
    from pathlib import Path
    import fsspec
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    import requests

    _groups = json.loads(zlib.decompress(base64.b64decode("PAYLOAD")))
    _url = ('https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/'
            'flat-connectome/syn-partners-male-cns-v1.0-minconf-0.5.feather')
    _head = requests.head(_url, timeout=30)
    _head.raise_for_status()
    _generation = _head.headers['x-goog-generation']
    _pinned_url = _url + '?generation=' + _generation
    _pinned_head = requests.head(_pinned_url, timeout=30)
    _pinned_head.raise_for_status()
    assert _pinned_head.headers['x-goog-generation'] == _generation
    assert _pinned_head.headers['ETag'] == _head.headers['ETag']
    _identity = {'url':_url,'pinned_url':_pinned_url,'generation':_generation,
                 'content_length':int(_pinned_head.headers['Content-Length']),
                 'etag':_pinned_head.headers['ETag'],
                 'x_goog_hash':_pinned_head.headers.get('x-goog-hash')}
    assert _identity['content_length'] == 6777179098
    _folder = Path('/marimo/mb-synapse-scan')
    _folder.mkdir(exist_ok=True)
    _out = _folder / f'contacts-{_start:05d}-{_stop:05d}.parquet'
    _report = _folder / f'report-{_start:05d}-{_stop:05d}.json'
    assert not _out.exists() and not _report.exists(), 'Existing output requires inspection'
    _kc = pa.array(_groups['Kenyon_Cell'], type=pa.int64())
    _mbon = pa.array(_groups['MBON'], type=pa.int64())
    _begin = time.monotonic()
    _total = 0
    _writer = None
    try:
        with fsspec.open(_pinned_url,'rb',block_size=16 << 20) as _stream:
            _reader = pa.ipc.open_file(_stream)
            assert _reader.num_record_batches == 4759
            assert 0 <= _start < _stop <= _reader.num_record_batches
            for _index in range(_start,_stop):
                _batch = _reader.get_batch(_index)
                _mask = pc.and_(pc.is_in(_batch.column('body_pre'),value_set=_kc),
                                pc.is_in(_batch.column('body_post'),value_set=_mbon))
                _subset = pa.Table.from_batches([_batch]).filter(_mask)
                if _subset.num_rows:
                    if _writer is None:
                        _writer = pq.ParquetWriter(_out, _subset.schema, compression='zstd')
                    _writer.write_table(_subset)
                _total += _subset.num_rows
                if (_index+1) % 20 == 0 or _index+1 == _stop:
                    print('MB_SCAN_PROGRESS',json.dumps({'batch':_index+1,'stop':_stop,
                          'contacts':_total,'elapsed_s':round(time.monotonic()-_begin,2)}),flush=True)
    finally:
        if _writer is not None:
            _writer.close()
    assert _writer is not None, 'No KC-MBON contacts found'
    with _out.open('rb') as _file:
        _hash=hashlib.file_digest(_file,'sha256').hexdigest()
    _record={'source':_identity,'start_batch':_start,'stop_batch':_stop,
             'contacts':_total,'parquet':str(_out),'bytes':_out.stat().st_size,
             'sha256':_hash,'elapsed_s':time.monotonic()-_begin,
             'scope':'Anatomical KC-MBON contact coordinates; no plasticity claim'}
    _report.write_text(json.dumps(_record,indent=2))
    print('MB_SCAN_COMPLETE',json.dumps(_record),flush=True)

_scan_mb_contacts(START, STOP)
'''
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--start', type=int, default=0)
parser.add_argument('--stop', type=int, default=100)
parser.add_argument('--output', type=Path, default=ROOT/'build/molab_mb_scan.py')
args = parser.parse_args()
assert 0 <= args.start < args.stop <= 4759
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(template.replace('PAYLOAD', payload).replace('START', str(args.start))
                       .replace('STOP', str(args.stop)), encoding='utf-8')
print(args.output, args.output.stat().st_size)
