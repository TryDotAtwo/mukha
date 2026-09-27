"""Compare native panorama sampling against independent Torch grid_sample."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F

ROOT=Path(__file__).resolve().parents[1]
P=C.POINTER(C.c_float)
D=C.POINTER(C.c_double)

def main():
    path=ROOT/'data/derived/optical_reference/rays.csv'
    source=json.loads((ROOT/'reports/optical_reference_export.json').read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest()!=source['rays_sha256']:
        raise ValueError('Ray source changed')
    table=np.genfromtxt(path,delimiter=',',names=True,dtype=None,encoding='utf8')
    rays=np.column_stack([table[k] for k in ('ray_forward','ray_left','ray_up')])
    rays=np.ascontiguousarray(np.vstack([rays, [[1,0,0],[-1,0,0],[-1,-0.,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]]]),dtype=np.float64)
    lib=C.CDLL(str(ROOT/'build/retina.dll'))
    lib.fv_create.argtypes=[D,C.c_size_t,C.c_uint32,C.c_uint32];lib.fv_create.restype=C.c_void_p
    lib.fv_destroy.argtypes=[C.c_void_p]
    lib.fv_sample.argtypes=[C.c_void_p,P,C.c_size_t,P,C.c_size_t];lib.fv_sample.restype=C.c_int
    rng=np.random.default_rng(93851)
    errors=[]
    for h,w in [(2,2),(17,32),(128,256)]:
        handle=lib.fv_create(rays.ctypes.data_as(D),len(rays),w,h)
        if not handle:raise AssertionError('Create failed')
        try:
            for mode in ('constant','random'):
                pixels=(np.full((h,w,3),[.25,.5,2.],np.float32) if mode=='constant'
                        else rng.random((h,w,3),dtype=np.float32)*4)
                out=np.zeros((len(rays),3),np.float32)
                def sample(image=pixels,target=out,count=None):
                    return lib.fv_sample(handle,image.ctypes.data_as(P),image.size if count is None else count,target.ctypes.data_as(P),target.size)
                assert sample()==0
                # Wrap one column on each side; Torch performs interpolation and vertical clamping.
                image=torch.from_numpy(pixels).permute(2,0,1).unsqueeze(0).double()
                image=torch.cat([image[:,:,:,-1:],image,image[:,:,:,:1]],dim=3)
                longitude=np.arctan2(rays[:,1],rays[:,0])
                latitude=np.arctan2(rays[:,2],np.hypot(rays[:,0],rays[:,1]))
                grid=np.column_stack([2*((longitude/(2*np.pi)+.5)*w+1)/(w+2)-1,-2*latitude/np.pi])
                expected=F.grid_sample(image,torch.from_numpy(grid.reshape(1,1,-1,2)),align_corners=False,padding_mode='border').squeeze().T.numpy()
                error=float(np.max(np.abs(out-expected)))
                assert error<3e-7,(h,w,mode,error)
                if mode=='constant':assert np.array_equal(out,np.broadcast_to([.25,.5,2.],out.shape))
                errors.append({'height':h,'width':w,'image':mode,'max_error':error})
                before=out.copy()
                for bad in (float('nan'),float('inf'),-1.):
                    invalid=pixels.copy();invalid[-1,-1,-1]=bad
                    assert sample(image=invalid)!=0
                    assert np.array_equal(before,out)
                assert sample(count=pixels.size-1)!=0 and np.array_equal(before,out)
                assert lib.fv_sample(handle,pixels.ctypes.data_as(P),pixels.size,pixels.ctypes.data_as(P),out.size)!=0
        finally:lib.fv_destroy(handle)
    bad=rays.copy();bad[0]=0
    assert not lib.fv_create(bad.ctypes.data_as(D),len(bad),32,16)
    bad[0]=[float('nan'),0,0]
    assert not lib.fv_create(bad.ctypes.data_as(D),len(bad),32,16)
    # Analytic axis test: channel 0 is column index, channel 1 row index.
    axes=np.ascontiguousarray([[1,0,0],[0,1,0],[0,-1,0],[-1,0,0],[0,0,1],[0,0,-1]],dtype=np.float64)
    handle=lib.fv_create(axes.ctypes.data_as(D),len(axes),8,4)
    assert handle
    try:
        yy,xx=np.mgrid[:4,:8]
        pixels=np.ascontiguousarray(np.stack([xx,yy,np.ones_like(xx)],axis=-1),dtype=np.float32)
        out=np.zeros((6,3),np.float32)
        assert lib.fv_sample(handle,pixels.ctypes.data_as(P),pixels.size,out.ctypes.data_as(P),out.size)==0
        expected=np.array([[3.5,1.5,1],[5.5,1.5,1],[1.5,1.5,1],[3.5,1.5,1],[3.5,0,1],[3.5,3,1]])
        assert np.array_equal(out,expected),(out,expected)
    finally:lib.fv_destroy(handle)
    report={'scope':'Native engineering image sampler; not phototransduction or neural input',
            'passed':True,'rays':len(rays),'comparisons':errors,'device':'CPU',
            'ray_source_sha256':source['rays_sha256'],
            'dll_sha256':hashlib.sha256((ROOT/'build/retina.dll').read_bytes()).hexdigest(),
            'checks':['analytic axis and seam orientation','constant radiance','Torch random-image oracle','seam and poles',
                      'invalid image leaves output unchanged','overlap rejection','nonunit and NaN ray rejection']}
    (ROOT/'reports/retina_native.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
