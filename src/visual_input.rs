//! Image-only native input path. Current RGB-to-photon calibration is explicitly
//! an engineering assumption; this module supplies no MaleCNS anatomical mapping.
use crate::{photon::{self,Photoreceptors},vision::Retina};
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};
use std::{fs,path::Path};

#[derive(Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AssumedOptics {
    pub width:u32,
    pub height:u32,
    pub rays:Vec<[f64;3]>,
    /// Explicit engineering coefficients: photons/second per linear RGB unit.
    /// No default luminance rule and no implicit R7/R8 channel assignment.
    pub rgb_to_photons:Vec<[f64;3]>,
    pub assumption_note:String,
}
pub struct VisualInput {
    retina:Retina,
    receptors:Photoreceptors,
    coefficients:Vec<[f64;3]>,
    samples:Vec<f32>,
    rates:Vec<f64>,
    identity:[u8;32],
    frames:u64,
}
impl VisualInput {
    pub fn new(config:&AssumedOptics,microvilli:u32,seed:u64,blocks:u32)->Result<Self,String> {
        let n=config.rays.len();
        if n==0 || n>65535 || config.rgb_to_photons.len()!=n || config.assumption_note.trim().is_empty() ||
           config.rgb_to_photons.iter().flatten().any(|v| !v.is_finite() || *v<0.) {
            return Err("Each ray requires explicit nonnegative photon coefficients and an assumption note".into());
        }
        let retina=Retina::new(&config.rays,config.width,config.height)?;
        let mut hash=Sha256::new();
        hash.update(serde_json::to_vec(config).map_err(|e|e.to_string())?);
        hash.update(photon::build_identity());
        hash.update(include_bytes!("visual_input.rs"));
        hash.update(include_bytes!("vision.rs"));
        hash.update(include_bytes!("photon.rs"));
        hash.update(include_bytes!("../native/retina.cpp"));
        hash.update(include_bytes!("../native/retina.h"));
        let receptors=Photoreceptors::new(n as u32,microvilli,seed,blocks)?;
        Ok(Self { retina,receptors,coefficients:config.rgb_to_photons.clone(),
            samples:vec![0.;3*n],rates:vec![0.;n],identity:hash.finalize().into(),frames:0 })
    }
    pub fn advance_image(&mut self,rgb:&[f32],ticks:u32)->Result<(),String> {
        self.advance_image_with_pose(rgb,None,ticks)
    }
    pub fn advance_image_with_pose(&mut self,rgb:&[f32],local_to_world:Option<&[[f64;3];3]>,ticks:u32)->Result<(),String> {
        let next=self.frames.checked_add(1).ok_or("Image sequence counter overflow")?;
        match local_to_world {
            Some(rotation)=>self.retina.sample_oriented(rgb,rotation,&mut self.samples)?,
            None=>self.retina.sample(rgb,&mut self.samples)?,
        }
        for (i,coeff) in self.coefficients.iter().enumerate() {
            let rate=(0..3).map(|c|f64::from(self.samples[3*i+c])*coeff[c]).sum::<f64>();
            if !rate.is_finite() { return Err("RGB-to-photon conversion overflow".into()); }
            self.rates[i]=rate;
        }
        self.receptors.advance(&self.rates,ticks)?;
        self.frames=next;
        Ok(())
    }
    pub fn observe(&mut self,state:&mut [f64])->Result<u64,String> { self.receptors.observe(state) }
    pub fn frames(&self)->u64 { self.frames }
    pub fn identity_hex(&self)->String { self.identity.iter().map(|v|format!("{v:02x}")).collect() }
    pub fn snapshot(&mut self)->Result<Vec<u8>,String> {
        let payload=self.receptors.snapshot_size()?;
        let size=payload.checked_add(96).ok_or("Visual checkpoint size overflow")?;
        let mut bytes=Vec::new();bytes.try_reserve_exact(size).map_err(|e|e.to_string())?;
        bytes.resize(size,0);
        bytes[..8].copy_from_slice(b"FFVIS001");
        bytes[8..16].copy_from_slice(&1u64.to_le_bytes());
        bytes[16..48].copy_from_slice(&self.identity);
        bytes[48..56].copy_from_slice(&self.frames.to_le_bytes());
        bytes[56..64].copy_from_slice(&(payload as u64).to_le_bytes());
        self.receptors.snapshot_into(&mut bytes[96..])?;
        let mut hash=Sha256::new();hash.update(&bytes[..64]);hash.update(&bytes[96..]);
        bytes[64..96].copy_from_slice(&hash.finalize());
        Ok(bytes)
    }
    pub fn restore(&mut self,bytes:&[u8])->Result<(),String> {
        let payload=self.receptors.snapshot_size()?;
        if bytes.len()!=96+payload || &bytes[..8]!=b"FFVIS001" ||
           bytes[8..16]!=1u64.to_le_bytes() || bytes[16..48]!=self.identity ||
           bytes[56..64]!=(payload as u64).to_le_bytes() {
            return Err("Visual checkpoint length, version or optical configuration mismatch".into());
        }
        let mut hash=Sha256::new();hash.update(&bytes[..64]);hash.update(&bytes[96..]);
        if bytes[64..96]!=hash.finalize()[..] { return Err("Visual checkpoint checksum mismatch".into()); }
        let frames=u64::from_le_bytes(bytes[48..56].try_into().unwrap());
        self.receptors.restore(&bytes[96..])?;
        self.frames=frames;
        // samples/rates are scratch; both are overwritten before any advance.
        Ok(())
    }
    pub fn load_file(&mut self,path:&Path)->Result<(),String> {
        let size=self.receptors.snapshot_size()?.checked_add(96).ok_or("Checkpoint size overflow")?;
        let bytes=crate::checkpoint_file::read_exact_size(path,size).map_err(|e|e.to_string())?;
        self.restore(&bytes)
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Frame { ticks:u32,rgb:Vec<f32>,#[serde(default)] local_to_world:Option<[[f64;3];3]> }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Fixture { optics:AssumedOptics,microvilli:u32,seed:u64,blocks:u32,frames:Vec<Frame> }
pub fn run_fixture(input:&Path,output:&Path)->Result<(),String> {
    let source=fs::read(input).map_err(|e|e.to_string())?;
    let fixture:Fixture=serde_json::from_slice(&source).map_err(|e|e.to_string())?;
    if fixture.frames.is_empty() { return Err("At least one recorded image is required".into()); }
    let mut model=VisualInput::new(&fixture.optics,fixture.microvilli,fixture.seed,fixture.blocks)?;
    let midpoint=fixture.frames.len()/2;
    let mut checkpoint=Vec::new();let mut records=Vec::new();
    let mut state=vec![0.;fixture.optics.rays.len()*9];
    for (i,frame) in fixture.frames.iter().enumerate() {
        if i==midpoint { checkpoint=model.snapshot()?; }
        model.advance_image_with_pose(&frame.rgb,frame.local_to_world.as_ref(),frame.ticks)?;
        let tick=model.observe(&mut state)?;
        let mut hash=Sha256::new();for value in &frame.rgb { hash.update(value.to_le_bytes()); }
        records.push(serde_json::json!({"frame":model.frames(),"tick":tick,
            "rgb_f32le_sha256":format!("{:x}",hash.finalize()),
            "local_to_world":frame.local_to_world,"state_soa":state}));
    }
    let expected=model.snapshot()?;
    model.restore(&checkpoint)?;
    for frame in &fixture.frames[midpoint..] { model.advance_image_with_pose(&frame.rgb,frame.local_to_world.as_ref(),frame.ticks)?; }
    if model.snapshot()?!=expected { return Err("Image-driven full-state continuation mismatch".into()); }
    let checkpoint_hash=format!("{:x}",Sha256::digest(&checkpoint));
    // Content-addressed checkpoint first, manifest last: a failed report write
    // cannot replace a checkpoint referenced by the previous report.
    let checkpoint_path=output.with_extension(format!("{checkpoint_hash}.visual-checkpoint"));
    crate::checkpoint_file::write_atomic(&checkpoint_path,&checkpoint).map_err(|e|e.to_string())?;
    let report=serde_json::json!({"passed":true,
        "scope":"Image -> point sampler -> assumed RGB photon coefficients -> native receptor dynamics. No MaleCNS registration or CNS/body coupling.",
        "input_sha256":format!("{:x}",Sha256::digest(&source)),"optics":fixture.optics,
        "configuration_identity":model.identity_hex(),"native_photon_build_identity":photon::build_identity(),
        "checkpoint_frame":midpoint,"checkpoint_sha256":checkpoint_hash,
        "checkpoint_file":checkpoint_path.file_name().unwrap().to_string_lossy(),
        "final_snapshot_sha256":format!("{:x}",Sha256::digest(&expected)),
        "full_state_continuation_exact":true,"frames":records});
    crate::checkpoint_file::write_atomic(output,&serde_json::to_vec_pretty(&report).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    println!("Verified {} image frames and exact state continuation; engineering calibration only.",records.len());
    Ok(())
}
pub fn resume_fixture(input:&Path,checkpoint:&Path,output:&Path)->Result<(),String> {
    let source=fs::read(input).map_err(|e|e.to_string())?;
    let fixture:Fixture=serde_json::from_slice(&source).map_err(|e|e.to_string())?;
    let mut model=VisualInput::new(&fixture.optics,fixture.microvilli,fixture.seed,fixture.blocks)?;
    model.load_file(checkpoint)?;
    let start=usize::try_from(model.frames()).map_err(|e|e.to_string())?;
    if start>fixture.frames.len() { return Err("Checkpoint frame exceeds supplied image sequence".into()); }
    for frame in &fixture.frames[start..] { model.advance_image_with_pose(&frame.rgb,frame.local_to_world.as_ref(),frame.ticks)?; }
    let mut state=vec![0.;fixture.optics.rays.len()*9];let tick=model.observe(&mut state)?;
    let snapshot=model.snapshot()?;
    let report=serde_json::json!({"scope":"Fresh process continuation of engineering-calibrated image fixture; not biological validation",
        "input_sha256":format!("{:x}",Sha256::digest(&source)),"configuration_identity":model.identity_hex(),
        "restored_frame":start,"final_frame":model.frames(),"tick":tick,"state_soa":state,
        "final_snapshot_sha256":format!("{:x}",Sha256::digest(&snapshot))});
    crate::checkpoint_file::write_atomic(output,&serde_json::to_vec_pretty(&report).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    println!("Restored frame {start}; processed {} further images.",fixture.frames.len()-start);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn config()->AssumedOptics { AssumedOptics {width:8,height:4,
        rays:vec![[1.,0.,0.],[-1.,0.,0.]],rgb_to_photons:vec![[100000.,0.,0.];2],
        assumption_note:"Synthetic red stimulus: 1 linear unit means 100000 photons/s; not R7/R8 spectral calibration".into()} }
    fn front()->Vec<f32> {
        let mut image=vec![0.;8*4*3];
        for y in 0..4 { for x in [3,4] { image[(y*8+x)*3]=1.; } }
        image
    }
    #[test]
    fn pixels_drive_rates_and_checkpoint_binds_optics() {
        let _guard=photon::TEST_LOCK.lock().unwrap();
        let config=config();let dark=vec![0.;8*4*3];let bright=front();
        let mut model=VisualInput::new(&config,30000,19303,16).unwrap();
        let mut state=vec![0.;18];
        model.advance_image(&bright,500).unwrap();
        assert_eq!(model.observe(&mut state).unwrap(),500);
        assert_eq!(&state[14..16],&[100000.,0.]);
        assert!(state[0]>state[1]+1.);
        let saved=model.snapshot().unwrap();
        let mut bad=bright.clone();bad[0]=f32::NAN;
        assert!(model.advance_image(&bad,1).is_err());
        assert!(model.advance_image(&bright[..5],1).is_err());
        assert_eq!(model.snapshot().unwrap(),saved);
        model.advance_image(&dark,500).unwrap();
        let expected=model.snapshot().unwrap();
        model.restore(&saved).unwrap();model.advance_image(&dark,500).unwrap();
        assert_eq!(model.snapshot().unwrap(),expected);
        let mut corrupt=saved.clone();corrupt[48]^=1;
        assert!(model.restore(&corrupt).is_err());
        assert_eq!(model.snapshot().unwrap(),expected);
        drop(model);
        let mut model=VisualInput::new(&config,30000,19303,16).unwrap();
        model.advance_image(&dark,500).unwrap();
        model.observe(&mut state).unwrap();assert_eq!(state[0],state[1]);
        drop(model);
        let mut changed=config.clone();changed.rgb_to_photons[0][0]*=2.;
        let mut model=VisualInput::new(&changed,30000,19303,16).unwrap();
        let before=model.snapshot().unwrap();
        assert!(model.restore(&saved).is_err());
        assert_eq!(model.snapshot().unwrap(),before);
    }
}
