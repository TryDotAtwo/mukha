//! Safe ownership and size validation around the native CUDA C ABI.
use serde::{Deserialize,Serialize};
#[cfg(feature="cuda64")]
pub type Real=f64;
#[cfg(not(feature="cuda64"))]
pub type Real=f32;
#[repr(C)]
#[derive(Clone,Copy)]
struct Params {dt:Real,rest:Real,reset:Real,threshold:Real,membrane:Real,synapse:Real,refractory:u32,delay:u32}
impl Default for Params {fn default()->Self {Self{dt:0.1,rest:-52.,reset:-52.,threshold:-45.,membrane:20.,synapse:5.,refractory:22,delay:18}}}
#[derive(Deserialize)]
struct Fixture {n:usize,pre:Vec<usize>,post:Vec<usize>,weights_mv:Vec<Real>,sensory:Vec<usize>,stimuli:Vec<Vec<Real>>}
#[derive(Serialize)]
struct Trace {backend:&'static str,v:Vec<Vec<Real>>,g:Vec<Vec<Real>>,spikes:Vec<Vec<u8>>,checkpoint_continuation_exact:bool,corrupt_checkpoint_rejected:bool}
use sha2::{Digest,Sha256};
use std::{ffi::{c_char,c_void,CStr},fs,path::Path,ptr::NonNull};

extern "C" {
    #[cfg_attr(feature="cuda64",link_name="ff_cuda64_create")]
    fn ff_cuda_create(n:u32,e:u64,row:*const u64,col:*const u32,w:*const Real,sense:*const u8,p:Params,cap:u32)->*mut c_void;
    #[cfg_attr(feature="cuda64",link_name="ff_cuda64_destroy")]
    fn ff_cuda_destroy(m:*mut c_void);
    #[cfg_attr(feature="cuda64",link_name="ff_cuda64_advance")]
    fn ff_cuda_advance(m:*mut c_void,steps:u32,input:*const Real,v:*mut Real,g:*mut Real,spikes:*mut u8)->i32;
    #[cfg_attr(feature="cuda64",link_name="ff_cuda64_checkpoint_size")]
    fn ff_cuda_checkpoint_size(m:*const c_void)->usize;
    #[cfg_attr(feature="cuda64",link_name="ff_cuda64_save")]
    fn ff_cuda_save(m:*mut c_void,b:*mut u8,len:usize)->i32;
    #[cfg_attr(feature="cuda64",link_name="ff_cuda64_load")]
    fn ff_cuda_load(m:*mut c_void,b:*const u8,len:usize)->i32;
    #[cfg_attr(feature="cuda64",link_name="ff_cuda64_probe_error")]
    fn ff_cuda_probe_error()->*const c_char;
}
fn error()->String { unsafe { CStr::from_ptr(ff_cuda_probe_error()).to_string_lossy().into_owned() } }
fn check(rc:i32)->Result<(),String> { if rc==0 {Ok(())}else{Err(error())} }

pub struct CudaModel {
    handle:NonNull<c_void>,
    n:usize,
    capacity:usize,
    voltage:Vec<Real>,
    synapse:Vec<Real>,
    spikes:Vec<u8>,
}
// NonNull deliberately keeps this handle !Send / !Sync. Calls are serialized.
impl Drop for CudaModel { fn drop(&mut self) { unsafe {ff_cuda_destroy(self.handle.as_ptr())} } }
impl CudaModel {
    pub fn new(n:usize,row:&[u64],col:&[u32],weights:&[Real],sense:&[u8],capacity:usize)->Result<Self,String> {
        if n==0 || n>i32::MAX as usize || capacity==0 || capacity>u32::MAX as usize ||
            row.len()!=n+1 || sense.len()!=n || col.len()!=weights.len() || row[0]!=0 ||
            row[n]!=col.len() as u64 || row.windows(2).any(|x|x[0]>x[1]) ||
            col.iter().any(|&x|x as usize>=n) || sense.iter().any(|&x|x>1) ||
            weights.iter().any(|x|!x.is_finite()) {return Err("invalid CUDA model arrays".into())}
        let total=n.checked_mul(capacity).ok_or("CUDA chunk shape overflow")?;
        // Allocate host buffers before native creation, so allocation failure cannot leak a handle.
        let mut voltage=Vec::new();let mut synapse=Vec::new();let mut spikes=Vec::new();
        voltage.try_reserve_exact(total).map_err(|e|e.to_string())?;
        synapse.try_reserve_exact(total).map_err(|e|e.to_string())?;
        spikes.try_reserve_exact(total).map_err(|e|e.to_string())?;
        voltage.resize(total,0.);synapse.resize(total,0.);spikes.resize(total,0);
        let raw=unsafe {ff_cuda_create(n as u32,weights.len() as u64,row.as_ptr(),col.as_ptr(),
            weights.as_ptr(),sense.as_ptr(),Params::default(),capacity as u32)};
        let handle=NonNull::new(raw).ok_or_else(error)?;
        Ok(Self{handle,n,capacity,voltage,synapse,spikes})
    }
    pub fn advance(&mut self,input:&[Real])->Result<(&[Real],&[Real],&[u8]),String> {
        if input.is_empty() || input.len()%self.n!=0 || input.len()/self.n>self.capacity || input.iter().any(|x|!x.is_finite()) {
            return Err("invalid CUDA input shape or value".into())
        }
        check(unsafe {ff_cuda_advance(self.handle.as_ptr(),(input.len()/self.n) as u32,input.as_ptr(),
            self.voltage.as_mut_ptr(),self.synapse.as_mut_ptr(),self.spikes.as_mut_ptr())})?;
        Ok((&self.voltage[..input.len()],&self.synapse[..input.len()],&self.spikes[..input.len()]))
    }
    pub fn save(&mut self)->Result<Vec<u8>,String> {
        let size=unsafe {ff_cuda_checkpoint_size(self.handle.as_ptr())};
        let mut bytes=vec![0u8;size];
        check(unsafe {ff_cuda_save(self.handle.as_ptr(),bytes.as_mut_ptr(),bytes.len())})?;
        Ok(bytes)
    }
    pub fn load(&mut self,bytes:&[u8])->Result<(),String> {
        check(unsafe {ff_cuda_load(self.handle.as_ptr(),bytes.as_ptr(),bytes.len())})
    }
}

pub fn simulate(input:&Path,output:&Path)->Result<(),String> {
    let source=fs::read(input).map_err(|e|e.to_string())?;
    let f:Fixture=serde_json::from_slice(&source).map_err(|e|e.to_string())?;
    if f.n==0 || f.n>i32::MAX as usize || f.stimuli.is_empty() || f.pre.len()!=f.post.len() ||
        f.pre.len()!=f.weights_mv.len() || f.pre.iter().chain(&f.post).chain(&f.sensory).any(|&i|i>=f.n) ||
        f.stimuli.iter().any(|x|x.len()!=f.n) {return Err("invalid fixture dimensions".into())}
    let mut order:Vec<usize>=(0..f.pre.len()).collect();order.sort_by_key(|&i|(f.post[i],f.pre[i],i));
    let mut row=vec![0u64;f.n+1];
    for &p in &f.post {row[p+1]+=1} for i in 0..f.n {row[i+1]+=row[i]}
    let col:Vec<u32>=order.iter().map(|&i|f.pre[i] as u32).collect();
    let w:Vec<Real>=order.iter().map(|&i|f.weights_mv[i]).collect();
    let mut sensory=vec![0u8;f.n];for &i in &f.sensory {sensory[i]=1}
    let mut model=CudaModel::new(f.n,&row,&col,&w,&sensory,37)?;
    let halfway=f.stimuli.len()/2;
    let mut trace=Trace{backend:if cfg!(feature="cuda64"){"rust-native-cuda-fp64"}else{"rust-native-cuda-fp32"},v:vec![],g:vec![],spikes:vec![],
        checkpoint_continuation_exact:false,corrupt_checkpoint_rejected:false};
    let mut checkpoint=vec![];
    for (start,end) in [(0,halfway),(halfway,f.stimuli.len())] {
        if start==halfway {checkpoint=model.save()?;}
        for rows in f.stimuli[start..end].chunks(37) {
            let values:Vec<Real>=rows.iter().flatten().copied().collect();
            let (v,g,s)=model.advance(&values)?;
            trace.v.extend(v.chunks(f.n).map(|x|x.to_vec()));
            trace.g.extend(g.chunks(f.n).map(|x|x.to_vec()));
            trace.spikes.extend(s.chunks(f.n).map(|x|x.to_vec()));
        }
    }
    // Exercise actual filesystem persistence, then restore into a fresh GPU instance.
    let cp_path=output.with_extension("checkpoint");
    fs::write(&cp_path,&checkpoint).map_err(|e|e.to_string())?;
    let persisted=fs::read(&cp_path).map_err(|e|e.to_string())?;
    if checkpoint!=persisted {return Err("checkpoint file differs after write".into())}
    drop(model);
    let mut restored=CudaModel::new(f.n,&row,&col,&w,&sensory,19)?;
    restored.load(&persisted)?;
    let mut exact=true;let mut offset=halfway;
    for rows in f.stimuli[halfway..].chunks(19) {
        let values:Vec<Real>=rows.iter().flatten().copied().collect();
        let (v,g,s)=restored.advance(&values)?;
        for j in 0..rows.len() {
            let range=j*f.n..(j+1)*f.n;
            exact &= v[range.clone()]==trace.v[offset+j] && g[range.clone()]==trace.g[offset+j] && s[range]==trace.spikes[offset+j];
        }
        offset+=rows.len();
    }
    trace.checkpoint_continuation_exact=exact;
    let last=checkpoint.len()-1;checkpoint[last]^=1;
    trace.corrupt_checkpoint_rejected=restored.load(&checkpoint).is_err();
    fs::write(output,serde_json::to_vec(&trace).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    let report=serde_json::json!({"backend":trace.backend,"ticks":trace.v.len(),
        "checkpoint_continuation_exact":exact,"corrupt_checkpoint_rejected":trace.corrupt_checkpoint_rejected,
        "checkpoint_sha256":format!("{:x}",Sha256::digest(&persisted)),
        "fixture_sha256":format!("{:x}",Sha256::digest(&source)),
        "scope":"Rust/CUDA numerical fixture and persisted checkpoint; no full-brain biology"});
    fs::write(output.with_extension("report.json"),serde_json::to_vec_pretty(&report).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    println!("{report}");
    if !exact || !trace.corrupt_checkpoint_rejected {return Err("CUDA persistence verification failed".into())}
    Ok(())
}
