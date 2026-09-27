//! Bounded full-author-graph pilot. Not MaleCNS transfer or learned control.
use crate::cuda::{CudaModel,Real};
use serde::Deserialize;
use sha2::{Digest,Sha256};
use std::{fs,io::{BufWriter,Write},path::Path,time::Instant};

#[derive(Deserialize)]
struct Event {tick:usize,neuron:usize}
#[derive(Deserialize)]
struct Protocol {steps:usize,dt_ms:f64,voltage_jump_mv:Real,sensory:Vec<usize>,target_index:usize,
    graph_manifest_sha256:String,events:Vec<Event>,max_wall_seconds:u64}
fn sha(bytes:&[u8])->String {format!("{:x}",Sha256::digest(bytes))}
fn payload(bytes:&[u8],dtype:&str,count:usize,width:usize)->Result<usize,String> {
    if bytes.len()<10 || &bytes[..6]!=b"\x93NUMPY" {return Err("invalid NPY magic".into())}
    let (start,length)=match bytes[6] {
        1=>(10,u16::from_le_bytes([bytes[8],bytes[9]]) as usize),
        2 if bytes.len()>=12=>(12,u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize),
        _=>return Err("unsupported NPY version".into())
    };
    let end=start+length;
    let expected=count.checked_mul(width).and_then(|x|x.checked_add(end)).ok_or("NPY size overflow")?;
    if bytes.len()!=expected {return Err("NPY size mismatch".into())}
    let header=std::str::from_utf8(&bytes[start..end]).map_err(|e|e.to_string())?;
    if !header.contains(&format!("'descr': '{dtype}'")) || !header.contains("'fortran_order': False") ||
        !header.contains(&format!("'shape': ({count},)")) {return Err("unsupported NPY dtype/layout/shape".into())}
    Ok(end)
}

pub fn run(graph:&Path,protocol_path:&Path,output:&Path)->Result<(),String> {
    let started=Instant::now();
    let protocol_bytes=fs::read(protocol_path).map_err(|e|e.to_string())?;
    let p:Protocol=serde_json::from_slice(&protocol_bytes).map_err(|e|e.to_string())?;
    let manifest_bytes=fs::read(graph.join("manifest.json")).map_err(|e|e.to_string())?;
    if graph.join("INCOMPLETE").exists() || sha(&manifest_bytes)!=p.graph_manifest_sha256 {return Err("graph/protocol provenance mismatch".into())}
    let manifest:serde_json::Value=serde_json::from_slice(&manifest_bytes).map_err(|e|e.to_string())?;
    if manifest["format"]!="flyrocket.shiu-author-csr.v1" || manifest["orientation"]!="row=post; columns=pre" ||
        manifest["duplicate_pair_rows"]!=0 {return Err("unsupported author graph".into())}
    let n=manifest["nodes"].as_u64().ok_or("missing node count")? as usize;
    let e=manifest["edges"].as_u64().ok_or("missing edge count")? as usize;
    if n==0 || n>i32::MAX as usize || p.dt_ms!=0.1 || p.steps==0 || p.steps>10000 || p.max_wall_seconds>1800 ||
        p.max_wall_seconds==0 || p.target_index>=n || p.sensory.iter().any(|&i|i>=n) ||
        !p.voltage_jump_mv.is_finite() {return Err("unsupported bounded pilot protocol".into())}
    let files=manifest["files"].as_object().ok_or("missing files")?;
    for (name,record) in files {
        if name.contains(['/', '\\']) || name==".." {return Err("invalid graph filename".into())}
        let bytes=fs::read(graph.join(name)).map_err(|e|e.to_string())?;
        if record["bytes"].as_u64()!=Some(bytes.len() as u64) || record["sha256"].as_str()!=Some(sha(&bytes).as_str()) {
            return Err(format!("graph artifact mismatch: {name}"))
        }
    }
    let load=|name:&str,dtype:&str,count:usize,width:usize|->Result<Vec<u8>,String> {
        if !files.contains_key(name) {return Err(format!("missing {name}"))}
        let bytes=fs::read(graph.join(name)).map_err(|e|e.to_string())?;
        let offset=payload(&bytes,dtype,count,width)?;Ok(bytes[offset..].to_vec())
    };
    let row:Vec<u64>=load("indptr.npy","<u8",n+1,8)?.chunks_exact(8).map(|x|u64::from_le_bytes(x.try_into().unwrap())).collect();
    let col:Vec<u32>=load("indices.npy","<u4",e,4)?.chunks_exact(4).map(|x|u32::from_le_bytes(x.try_into().unwrap())).collect();
    #[cfg(not(feature="cuda64"))]
    let weights:Vec<Real>=load("weights_mv.npy","<f4",e,4)?.chunks_exact(4).map(|x|f32::from_le_bytes(x.try_into().unwrap())).collect();
    #[cfg(feature="cuda64")]
    let weights:Vec<Real>=load("signed_synapse_counts.npy","<i8",e,8)?.chunks_exact(8).map(|x|i64::from_le_bytes(x.try_into().unwrap()) as f64*0.275).collect();
    let mut sense=vec![0u8;n];for &i in &p.sensory {sense[i]=1}
    if p.events.iter().any(|ev|ev.tick>=p.steps||ev.neuron>=n||sense[ev.neuron]==0) ||
        p.events.windows(2).any(|w|w[0].tick>w[1].tick) {return Err("invalid stimulus events".into())}
    const CAP:usize=32;
    let mut model=CudaModel::new(n,&row,&col,&weights,&sense,CAP)?;
    let setup_seconds=started.elapsed().as_secs_f64();
    let spike_path=output.with_extension("spikes.bin");
    let mut spike_file=BufWriter::new(fs::OpenOptions::new().write(true).create_new(true).open(&spike_path).map_err(|e|e.to_string())?);
    // Each event is (tick:u32 LE, neuron_index:u32 LE); no event dropping.
    let mut input=vec![0 as Real;n*CAP];let mut event_cursor=0;let mut done=0;
    let mut spike_count=0u64;let mut target_spike_ticks=vec![];let mut target_voltage=vec![];
    let mut chunk_seconds=vec![];
    while done<p.steps && started.elapsed().as_secs()<p.max_wall_seconds {
        let steps=CAP.min(p.steps-done);input[..steps*n].fill(0.);
        while event_cursor<p.events.len() && p.events[event_cursor].tick<done+steps {
            let ev=&p.events[event_cursor];input[(ev.tick-done)*n+ev.neuron]+=p.voltage_jump_mv;event_cursor+=1;
        }
        let chunk_start=Instant::now();
        let (v,_g,s)=model.advance(&input[..steps*n])?;
        for step in 0..steps {
            target_voltage.push(v[step*n+p.target_index]);
            for (i,&fired) in s[step*n..(step+1)*n].iter().enumerate() {
                if fired!=0 {
                    spike_file.write_all(&((done+step) as u32).to_le_bytes()).map_err(|e|e.to_string())?;
                    spike_file.write_all(&(i as u32).to_le_bytes()).map_err(|e|e.to_string())?;
                    spike_count+=1;
                    if i==p.target_index {target_spike_ticks.push(done+step)}
                }
            }
        }
        done+=steps;chunk_seconds.push(chunk_start.elapsed().as_secs_f64());
        if done%1024==0 {println!("{}",serde_json::json!({"completed_ticks":done,"network_spikes":spike_count}));}
    }
    spike_file.flush().map_err(|e|e.to_string())?;drop(spike_file);
    let snapshot=model.save()?;
    fs::write(output.with_extension("checkpoint"),&snapshot).map_err(|e|e.to_string())?;
    let report=serde_json::json!({"backend":if cfg!(feature="cuda64"){"rust-native-cuda-cusparse-fp64"}else{"rust-native-cuda-cusparse-fp32"},"nodes":n,"edges":e,
        "completed_ticks":done,"requested_ticks":p.steps,"simulation_ms":done as f64*p.dt_ms,
        "network_spikes":spike_count,"target_spike_ticks":target_spike_ticks,"target_voltage_mv":target_voltage,
        "setup_seconds":setup_seconds,"wall_seconds":started.elapsed().as_secs_f64(),"chunk_seconds":chunk_seconds,
        "protocol_sha256":sha(&protocol_bytes),"graph_manifest_sha256":p.graph_manifest_sha256,
        "checkpoint_sha256":sha(&snapshot),"spike_format":"repeated tick:u32le, neuron_index:u32le",
        "complete":done==p.steps,"scope":"original Shiu graph single-seed pilot; no biological validation or MaleCNS transfer claimed"});
    fs::write(output,serde_json::to_vec_pretty(&report).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    println!("{}",serde_json::json!({"complete":done==p.steps,"network_spikes":spike_count,"target_spikes":target_spike_ticks.len(),"wall_seconds":started.elapsed().as_secs_f64()}));
    if done!=p.steps {return Err("pilot wall-time budget reached; partial output preserved".into())}
    Ok(())
}
