use serde::{Deserialize, Serialize};
use sha2::{Digest,Sha256};
use std::{env,ffi::{c_char,CStr},fs,io::Read,path::Path};
mod landing;
#[cfg(feature="vision")]
mod vision;
#[cfg(feature="photon")]
mod photon;
#[cfg(feature="photon")]
mod checkpoint_file;
#[cfg(all(feature="vision",feature="photon"))]
mod visual_input;
#[cfg(feature="body")]
mod body;
#[cfg(feature="cuda")]
mod cuda;
#[cfg(feature="cuda")]
mod pilot;

#[repr(C)]
#[derive(Clone,Copy)]
struct Params { dt:f32,rest:f32,reset:f32,threshold:f32,membrane:f32,synapse:f32,refractory:u32,delay:u32 }
impl Default for Params { fn default()->Self { Self{dt:0.1,rest:-52.,reset:-52.,threshold:-45.,membrane:20.,synapse:5.,refractory:22,delay:18} } }
extern "C" {
    fn ff_create(n:u32,e:u64,row:*const u64,col:*const u32,w:*const f32,sensory:*const u8,p:Params)->*mut std::ffi::c_void;
    fn ff_destroy(m:*mut std::ffi::c_void);
    fn ff_step(m:*mut std::ffi::c_void,x:*const f32,s:*mut u8)->i32;
    fn ff_observe(m:*const std::ffi::c_void,v:*mut f32,g:*mut f32)->i32;
    fn ff_checkpoint_size(m:*const std::ffi::c_void)->usize;
    fn ff_save(m:*const std::ffi::c_void,b:*mut u8,n:usize)->i32;
    fn ff_load(m:*mut std::ffi::c_void,b:*const u8,n:usize)->i32;
    fn ff_last_error()->*const c_char;
}
fn native_error()->String { unsafe { CStr::from_ptr(ff_last_error()).to_string_lossy().into_owned() } }
struct Model(*mut std::ffi::c_void);
impl Drop for Model { fn drop(&mut self) { unsafe{ff_destroy(self.0)} } }

#[cfg(test)]
mod numerical_tests {
    use super::*;

    #[test]
    fn near_equal_tau_preserves_synaptic_voltage_coupling() {
        let row=[0u64,0,1];let col=[0u32];let weight=[1.0f32];let sensory=[1u8,0];
        let p=Params{dt:0.1,rest:-60.,reset:-60.,threshold:-53.,membrane:20.,
                     synapse:f32::from_bits(20f32.to_bits()+1),refractory:0,delay:0};
        let m=Model(unsafe{ff_create(2,1,row.as_ptr(),col.as_ptr(),weight.as_ptr(),sensory.as_ptr(),p)});
        assert!(!m.0.is_null(),"{}",native_error());
        let mut spikes=[0u8;2];
        for drive in [[10.0f32,0.],[0.,0.],[0.,0.]] {
            assert_eq!(unsafe{ff_step(m.0,drive.as_ptr(),spikes.as_mut_ptr())},0,"{}",native_error());
        }
        let mut voltage=[0f32;2];let mut conductance=[0f32;2];
        assert_eq!(unsafe{ff_observe(m.0,voltage.as_mut_ptr(),conductance.as_mut_ptr())},0);
        let expected=0.1f64/20.0*(-0.1f64/20.0).exp();
        assert!(((voltage[1]+60.) as f64-expected).abs()<2e-6,
                "observed={} expected={}",voltage[1]+60.,expected);
    }
}
#[derive(Deserialize)]
struct Fixture { n:usize,pre:Vec<usize>,post:Vec<usize>,weights_mv:Vec<f32>,sensory:Vec<usize>,stimuli:Vec<Vec<f32>> }
#[derive(Serialize)]
struct Trace { backend:&'static str,v:Vec<Vec<f32>>,g:Vec<Vec<f32>>,spikes:Vec<Vec<u8>>,checkpoint_continuation_exact:bool,corrupt_checkpoint_rejected:bool }

fn simulate(input:&Path,output:&Path)->Result<(),String> {
    let f:Fixture=serde_json::from_slice(&fs::read(input).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    if f.n==0||f.n>u32::MAX as usize||f.pre.len()!=f.post.len()||f.pre.len()!=f.weights_mv.len()||
       f.pre.iter().chain(&f.post).chain(&f.sensory).any(|&i|i>=f.n)||f.stimuli.iter().any(|x|x.len()!=f.n) {
        return Err("invalid fixture dimensions".into())
    }
    let mut order:Vec<usize>=(0..f.pre.len()).collect();order.sort_by_key(|&i|(f.post[i],f.pre[i],i));
    let mut row=vec![0u64;f.n+1];
    for &p in &f.post { row[p+1]+=1; } for i in 0..f.n { row[i+1]+=row[i]; }
    let col:Vec<u32>=order.iter().map(|&i|f.pre[i] as u32).collect();
    let w:Vec<f32>=order.iter().map(|&i|f.weights_mv[i]).collect();
    let mut sensory=vec![0u8;f.n]; for i in f.sensory { sensory[i]=1; }
    let m=Model(unsafe{ff_create(f.n as u32,w.len() as u64,row.as_ptr(),col.as_ptr(),w.as_ptr(),sensory.as_ptr(),Params::default())});
    if m.0.is_null() { return Err(native_error()) }
    let mut trace=Trace{backend:"native-cpu-fp32",v:vec![],g:vec![],spikes:vec![],checkpoint_continuation_exact:false,corrupt_checkpoint_rejected:false};
    let halfway=f.stimuli.len()/2;
    let mut checkpoint=vec![0u8;unsafe{ff_checkpoint_size(m.0)}];
    for (i,x) in f.stimuli.iter().enumerate() {
        if i==halfway && unsafe{ff_save(m.0,checkpoint.as_mut_ptr(),checkpoint.len())}!=0 { return Err(native_error()) }
        let mut s=vec![0u8;f.n];let mut v=vec![0f32;f.n];let mut g=vec![0f32;f.n];
        if unsafe{ff_step(m.0,x.as_ptr(),s.as_mut_ptr())}!=0||unsafe{ff_observe(m.0,v.as_mut_ptr(),g.as_mut_ptr())}!=0 { return Err(native_error()) }
        trace.v.push(v);trace.g.push(g);trace.spikes.push(s);
    }
    if !f.stimuli.is_empty() {
        if unsafe{ff_load(m.0,checkpoint.as_ptr(),checkpoint.len())}!=0 { return Err(native_error()) }
        let mut exact=true;
        for (i,x) in f.stimuli.iter().enumerate().skip(halfway) {
            let mut s=vec![0u8;f.n];let mut v=vec![0f32;f.n];let mut g=vec![0f32;f.n];
            if unsafe{ff_step(m.0,x.as_ptr(),s.as_mut_ptr())}!=0||unsafe{ff_observe(m.0,v.as_mut_ptr(),g.as_mut_ptr())}!=0 { return Err(native_error()) }
            exact &= s==trace.spikes[i] && v==trace.v[i] && g==trace.g[i];
        }
        trace.checkpoint_continuation_exact=exact;
        let last=checkpoint.len()-1;checkpoint[last]^=1;
        trace.corrupt_checkpoint_rejected=unsafe{ff_load(m.0,checkpoint.as_ptr(),checkpoint.len())}!=0;
    }
    fs::write(output,serde_json::to_vec(&trace).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    println!("{}",serde_json::json!({"backend":trace.backend,"ticks":trace.v.len(),"checkpoint_continuation_exact":trace.checkpoint_continuation_exact,"corrupt_checkpoint_rejected":trace.corrupt_checkpoint_rejected}));
    if !trace.checkpoint_continuation_exact || !trace.corrupt_checkpoint_rejected {return Err("checkpoint verification failed".into())}
    Ok(())
}
fn verify(dir:&Path)->Result<(),String> {
    if dir.join("INCOMPLETE").exists() { return Err("incomplete graph".into()) }
    let m:serde_json::Value=serde_json::from_slice(&fs::read(dir.join("manifest.json")).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    if m["format"]!="flyrocket.incoming-csr.v1"||m["orientation"]!="row=postsynaptic; indices=presynaptic" { return Err("unsupported graph contract".into()) }
    let files=m["files"].as_object().ok_or("missing file hashes")?;
    for required in ["body_ids.npy","indptr.npy","indices.npy","synapse_counts.npy","source_rows.npy","nodes.feather"] {
        if !files.contains_key(required) {return Err(format!("missing required file {required}"))}
    }
    for (name,entry) in files {
        if name.contains(['/', '\\'])||name==".." {return Err("invalid manifest filename".into())}
        let mut f=fs::File::open(dir.join(name)).map_err(|e|e.to_string())?;
        if Some(f.metadata().map_err(|e|e.to_string())?.len())!=entry["bytes"].as_u64() { return Err(format!("size mismatch: {name}")) }
        let mut hash=Sha256::new();let mut buf=vec![0u8;1<<20];
        loop {let n=f.read(&mut buf).map_err(|e|e.to_string())?;if n==0 {break} hash.update(&buf[..n]);}
        if format!("{:x}",hash.finalize())!=entry["sha256"].as_str().unwrap_or("") {return Err(format!("hash mismatch: {name}"))}
    }
    println!("{}",serde_json::json!({"verified_files":files.len(),"nodes":m["nodes"],"edges":m["edges"],"scope":"artifact integrity; no physiological signs assigned"}));Ok(())
}
fn main() {
    let args:Vec<String>=env::args().collect();
    let result=match args.get(1).map(|s|s.as_str()) {
        Some("verify-graph") if args.len()==3=>verify(Path::new(&args[2])),
        Some("fixture") if args.len()==4=>simulate(Path::new(&args[2]),Path::new(&args[3])),
        Some("assess-landing") if args.len()==4=>landing::run(Path::new(&args[2]),Path::new(&args[3])),
        Some("assess-landing-series") if args.len()==4=>landing::run_series(Path::new(&args[2]),Path::new(&args[3])),
        #[cfg(all(feature="vision",feature="photon"))]
        Some("visual-fixture") if args.len()==4=>visual_input::run_fixture(Path::new(&args[2]),Path::new(&args[3])),
        #[cfg(all(feature="vision",feature="photon"))]
        Some("visual-resume") if args.len()==5=>visual_input::resume_fixture(Path::new(&args[2]),Path::new(&args[3]),Path::new(&args[4])),
        #[cfg(feature="body")]
        Some("body-diagnostic") if args.len()==4=>body::diagnostic(&args[2],Path::new(&args[3])),
        #[cfg(feature="cuda")]
        Some("cuda-fixture") if args.len()==4=>cuda::simulate(Path::new(&args[2]),Path::new(&args[3])),
        #[cfg(feature="cuda")]
        Some("shiu-pilot") if args.len()==5=>pilot::run(Path::new(&args[2]),Path::new(&args[3]),Path::new(&args[4])),
        _=>Err("usage: faithful-fly verify-graph DIR | fixture INPUT.json OUTPUT.json".into()),
    };
    if let Err(e)=result {eprintln!("{e}");std::process::exit(1)}
}
