"""Lossless numerical import of author FeCO calcium/angle recordings."""
import hashlib,io,json,zipfile
from pathlib import Path
import numpy as np
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[1]
archive=ROOT/'data/reference/mamiya2018/data.zip'
source=json.loads((ROOT/'reports/mamiya2018_source.json').read_text())
raw=archive.read_bytes();assert hashlib.sha256(raw).hexdigest()==source['sha256']
dest=ROOT/'data/derived/mamiya2018_recordings_v1'
if dest.exists():raise FileExistsError('Immutable output already exists')
dest.mkdir();(dest/'INCOMPLETE').write_text('unfinished import')
records=[];files={}
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    for name in z.namelist():
        if not name.endswith('.mat'):continue
        payload=z.read(name);data=loadmat(io.BytesIO(payload),simplify_cells=True)
        arrays={}
        for key,value in data.items():
            if key.startswith('__'):continue
            a=np.asarray(value)
            if a.dtype.kind not in 'iuf':raise ValueError(f'Unexpected dtype {name}:{key}')
            arrays[key]=a
        out=dest/(Path(name).stem+'.npz');np.savez_compressed(out,**arrays)
        with np.load(out,allow_pickle=False) as check:
            assert set(check.files)==set(arrays)
            for key,a in arrays.items():
                np.testing.assert_array_equal(check[key],a)
                assert check[key].dtype==a.dtype
        protocols=[]
        for key,response in arrays.items():
            if not key.endswith('_DFF'):continue
            prefix=key[:-4];angle=arrays[prefix+'_Angle']
            fly=arrays[prefix+'_Fly'];cluster=arrays[prefix+'_Cluster']
            assert response.ndim==2 and response.shape==angle.shape
            assert response.shape[0]==fly.size==cluster.size
            assert np.isfinite(fly).all() and np.isfinite(cluster).all()
            assert (fly==np.floor(fly)).all() and (cluster==np.floor(cluster)).all()
            protocols.append(dict(protocol=prefix,rows=response.shape[0],frames=response.shape[1],
                fly_ids=np.unique(fly).astype(int).tolist(),cluster_ids=np.unique(cluster).astype(int).tolist(),
                missing_response_samples=int(np.isnan(response).sum()),
                missing_angle_samples=int(np.isnan(angle).sum()),
                paired_finite_samples=int((np.isfinite(response)&np.isfinite(angle)).sum())))
        records.append(dict(source_file=name,source_member_sha256=hashlib.sha256(payload).hexdigest(),protocols=protocols))
        files[out.name]=hashlib.sha256(out.read_bytes()).hexdigest()
report=dict(source_archive_sha256=source['sha256'],records=records,files=files,
    frames_per_second_from_author_readme=8.01,
    scope='Cluster-level calcium response and measured angle; not spike trains or MaleCNS-cell measurements',
    missing_samples_preserved=True,source_arrays_exact=True,
    limitations=['Pixel-cluster identities derive from response similarity',
                 'Cross-file animal identity has not been verified',
                 'Source angle convention needs body-joint registration',
                 'Calcium observation dynamics and sensory transduction remain unfitted'],
    runtime_enabled=False)
(dest/'manifest.json').write_text(json.dumps(report,indent=2))
(ROOT/'reports/mamiya2018_recordings.json').write_text(json.dumps(report,indent=2))
(dest/'INCOMPLETE').unlink()
print(json.dumps(dict(files=len(files),protocol_tables=sum(len(r['protocols']) for r in records),
    response_rows=sum(p['rows'] for r in records for p in r['protocols']),
    paired_finite_samples=sum(p['paired_finite_samples'] for r in records for p in r['protocols']))))
