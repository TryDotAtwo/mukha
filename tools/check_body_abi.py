"""Exercise persistent body C ABI, not biological motor mapping."""
import ctypes as c
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    runtime=os.add_dll_directory(str(ROOT/'data/reference/mujoco_3.9.0/bin'))
    dll=c.CDLL(str(ROOT/'build/fly_body.dll'))
    ptr=c.c_void_p;dp=c.POINTER(c.c_double);size=c.c_size_t
    signatures={'fb_create':([c.c_char_p],ptr),'fb_destroy':([ptr],None),
        'fb_controls':([ptr],size),'fb_state_size':([ptr],size),'fb_error':([],c.c_char_p),
        'fb_reset':([ptr],c.c_int),'fb_advance':([ptr,dp,size,c.c_uint32],c.c_int),
        'fb_state':([ptr,dp,size],c.c_int),'fb_restore':([ptr,dp,size],c.c_int),
        'fb_control_position':([ptr,dp,dp],c.c_int),
        'fb_contact_normal':([ptr,c.c_char_p,dp,dp,c.POINTER(c.c_uint32)],c.c_int),
        'fb_contact_points':([ptr,c.c_char_p,dp,size,c.POINTER(c.c_uint32),dp],c.c_int)}
    for name,(args,result) in signatures.items():
        fn=getattr(dll,name);fn.argtypes=args;fn.restype=result
    def ok(code):
        if code:raise RuntimeError(dll.fb_error().decode())
    handles=[]
    def new():
        p=dll.fb_create(b'data/derived/contact_diagnostic/body.xml')
        if not p:raise RuntimeError(dll.fb_error().decode())
        handles.append(p);return p
    def state(p):
        a=(c.c_double*dll.fb_state_size(p))();ok(dll.fb_state(p,a,len(a)));return a
    def advance(p,value,ticks):
        a=(c.c_double*dll.fb_controls(p))();a[0]=value
        ok(dll.fb_advance(p,a,len(a),ticks))
    def contact(p,name=b'control_pad'):
        t,f,n=c.c_double(),c.c_double(),c.c_uint32()
        ok(dll.fb_contact_normal(p,name,c.byref(t),c.byref(f),c.byref(n)))
        return t.value,f.value,n.value
    def points(p,name=b'lf_tarsus5',capacity=8):
        t,n=c.c_double(),c.c_uint32()
        buffer=(c.c_double*(capacity*10))()
        code=dll.fb_contact_points(p,name,buffer,capacity,c.byref(n),c.byref(t))
        if code:return code,None
        return code,(t.value,[tuple(buffer[i*10:i*10+10]) for i in range(n.value)])
    try:
        a,b=new(),new()
        advance(a,0,2000);advance(b,0,2000)
        advance(a,1,1200)
        for _ in range(12):advance(b,1,100)
        checks={'chunk_equivalence':bytes(state(a))==bytes(state(b))}
        snapshot=state(a);fresh=new();ok(dll.fb_restore(fresh,snapshot,len(snapshot)))
        advance(a,1,800);advance(fresh,1,800)
        advance(a,0,1000);advance(fresh,0,1000)
        checks['fresh_restore_exact']=bytes(state(a))==bytes(state(fresh))
        before=bytes(state(a));u=(c.c_double*dll.fb_controls(a))();u[0]=2
        checks['out_of_bounds_rejected']=dll.fb_advance(a,u,len(u),1)!=0
        u[0]=float('nan');checks['nan_rejected']=dll.fb_advance(a,u,len(u),1)!=0
        u[0]=0;checks['wrong_count_rejected']=dll.fb_advance(a,u,len(u)-1,1)!=0
        checks['invalid_input_unchanged']=before==bytes(state(a))
        bad=state(a);bad[0]=float('nan')
        checks['bad_snapshot_rejected']=dll.fb_restore(a,bad,len(bad))!=0
        checks['bad_snapshot_unchanged']=before==bytes(state(a))
        ok(dll.fb_reset(a));initial=new()
        checks['reset_exact']=bytes(state(a))==bytes(state(initial))
        observation=new()
        advance(observation,0,2000)
        quiet=contact(observation)
        quiet_points=points(observation)
        advance(observation,1,1200)
        driven=contact(observation)
        driven_points=points(observation)
        pad_points=points(observation,b'control_pad')
        time,q=c.c_double(),c.c_double()
        ok(dll.fb_control_position(observation,c.byref(time),c.byref(q)))
        checks['contact_observation_pulse']=quiet[2]==0 and driven[2]>0 and driven[1]>0
        checks['contact_evaluation_time']=0<time.value-driven[0]<0.001
        checks['quiet_contact_points_empty']=quiet_points[0]==0 and quiet_points[1][1]==[]
        checks['spatial_contact_matches_force']=(driven_points[0]==0 and
            abs(driven_points[1][0]-driven[0])<1e-12 and
            len(driven_points[1][1])==driven[2] and
            abs(sum(x[9] for x in driven_points[1][1])-driven[1])<1e-12 and
            all(__import__('math').isfinite(v) for x in driven_points[1][1] for v in x))
        checks['paired_contact_forces_opposite']=(pad_points[0]==0 and
            len(pad_points[1][1])==len(driven_points[1][1]) and
            all(max(abs(x[k]-y[k]) for k in range(3))<1e-12 and
                max(abs(x[k]+y[k]) for k in range(3,9))<1e-12 and
                abs(x[9]-y[9])<1e-12
                for x,y in zip(driven_points[1][1],pad_points[1][1])))
        checks['normal_force_projection']=(driven_points[0]==0 and
            all(abs(sum(x[3+k]*x[6+k] for k in range(3))-x[9])<1e-12 and
                abs(sum(x[3+k]*x[3+k] for k in range(3))-1)<1e-12
                for x in driven_points[1][1]))
        checks['contact_capacity_rejected']=points(observation,capacity=0)[0]!=0
        checks['unknown_contact_geom_rejected']=dll.fb_contact_normal(
            observation,b'absent_geometry',c.byref(time),c.byref(q),c.byref(c.c_uint32()))!=0
        saved=state(observation)
        ok(dll.fb_restore(observation,saved,len(saved)))
        checks['restored_contact_cache_invalid']=dll.fb_contact_normal(
            observation,b'control_pad',c.byref(time),c.byref(q),c.byref(c.c_uint32()))!=0
        checks['restored_contact_points_invalid']=points(observation)[0]!=0
        advance(observation,0,1)
        checks['post_restore_contact_available']=contact(observation)[0]>=0
        report={'scope':'Persistent native body ABI, same-model in-memory snapshots only',
            'checks':checks,'contact_quiet':quiet,'contact_driven':driven,
            'foot_contact_points':driven_points[1],
            'passed':all(checks.values()),
            'library_sha256':sha(ROOT/'build/fly_body.dll'),
            'model_sha256':sha(ROOT/'data/derived/contact_diagnostic/body.xml'),
            'runtime_sha256':sha(ROOT/'data/reference/mujoco_3.9.0/bin/mujoco.dll')}
        (ROOT/'reports/body_abi.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
        if not report['passed']:raise SystemExit(1)
    finally:
        for p in handles:dll.fb_destroy(p)
        runtime.close()

if __name__=='__main__':main()
