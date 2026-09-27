//! Native receptor physiology only; photon calibration and MaleCNS wiring are separate.
use std::{ffi::{c_char,c_void,CStr},marker::PhantomData,ptr::NonNull,rc::Rc};
extern "C" {
    fn fp_create(cells:u32,microvilli:u32,seed:u64,blocks:u32)->*mut c_void;
    fn fp_destroy(handle:*mut c_void);
    fn fp_reset(handle:*mut c_void,seed:u64)->i32;
    fn fp_advance(handle:*mut c_void,rates:*const f64,count:usize,ticks:u32)->i32;
    fn fp_set_neural_feedback(handle:*mut c_void,current:*const f64,count:usize)->i32;
    fn fp_observe(handle:*mut c_void,state:*mut f64,count:usize,tick:*mut u64)->i32;
    fn fp_checkpoint_size(handle:*mut c_void)->usize;
    fn fp_save(handle:*mut c_void,output:*mut u8,bytes:usize)->i32;
    fn fp_load(handle:*mut c_void,input:*const u8,bytes:usize)->i32;
    fn fp_build_identity()->*const c_char;
    fn fp_last_error()->*const c_char;
}
fn error()->String { unsafe { CStr::from_ptr(fp_last_error()).to_string_lossy().into_owned() } }
pub fn build_identity()->String { unsafe { CStr::from_ptr(fp_build_identity()).to_string_lossy().into_owned() } }
#[cfg(test)]
pub(crate) static TEST_LOCK:std::sync::Mutex<()>=std::sync::Mutex::new(());
pub struct Photoreceptors {
    handle:NonNull<c_void>,
    cells:usize,
    _exclusive:PhantomData<Rc<()>>,
}
impl Photoreceptors {
    pub fn new(cells:u32,microvilli:u32,seed:u64,blocks:u32)->Result<Self,String> {
        let handle=NonNull::new(unsafe { fp_create(cells,microvilli,seed,blocks) }).ok_or_else(error)?;
        Ok(Self { handle,cells:cells as usize,_exclusive:PhantomData })
    }
    pub fn reset(&mut self,seed:u64)->Result<(),String> {
        if unsafe { fp_reset(self.handle.as_ptr(),seed) }==0 { Ok(()) } else { Err(error()) }
    }
    pub fn advance(&mut self,rates:&[f64],ticks:u32)->Result<(),String> {
        if rates.len()!=self.cells { return Err("Photon input length differs from population".into()); }
        if unsafe { fp_advance(self.handle.as_ptr(),rates.as_ptr(),rates.len(),ticks) }==0 {
            Ok(())
        } else { Err(error()) }
    }
    pub fn set_neural_feedback(&mut self,current:&[f64])->Result<(),String> {
        if current.len()!=self.cells { return Err("Neural feedback length differs from receptor population".into()); }
        if unsafe { fp_set_neural_feedback(self.handle.as_ptr(),current.as_ptr(),current.len()) }==0 {
            Ok(())
        } else { Err(error()) }
    }
    pub fn observe(&mut self,state:&mut [f64])->Result<u64,String> {
        if state.len()!=9*self.cells { return Err("Observation must contain 9 rows per cell".into()); }
        let mut tick=0;
        if unsafe { fp_observe(self.handle.as_ptr(),state.as_mut_ptr(),state.len(),&mut tick) }==0 {
            Ok(tick)
        } else { Err(error()) }
    }
    pub fn snapshot(&mut self)->Result<Vec<u8>,String> {
        let size=self.snapshot_size()?;
        let mut bytes=Vec::new();
        bytes.try_reserve_exact(size).map_err(|e|e.to_string())?;
        bytes.resize(size,0);
        self.snapshot_into(&mut bytes)?;
        Ok(bytes)
    }
    pub(crate) fn snapshot_size(&mut self)->Result<usize,String> {
        let size=unsafe { fp_checkpoint_size(self.handle.as_ptr()) };
        if size==0 { Err(error()) } else { Ok(size) }
    }
    pub(crate) fn snapshot_into(&mut self,bytes:&mut [u8])->Result<(),String> {
        if unsafe { fp_save(self.handle.as_ptr(),bytes.as_mut_ptr(),bytes.len()) }==0 {
            Ok(())
        } else { Err(error()) }
    }
    pub fn restore(&mut self,bytes:&[u8])->Result<(),String> {
        if unsafe { fp_load(self.handle.as_ptr(),bytes.as_ptr(),bytes.len()) }==0 {
            Ok(())
        } else { Err(error()) }
    }
    pub fn save_file(&mut self,path:&std::path::Path)->Result<(),String> {
        let bytes=self.snapshot()?;
        crate::checkpoint_file::write_atomic(path,&bytes).map_err(|e|e.to_string())
    }
    pub fn load_file(&mut self,path:&std::path::Path)->Result<(),String> {
        let size=unsafe { fp_checkpoint_size(self.handle.as_ptr()) };
        if size==0 { return Err(error()); }
        let bytes=crate::checkpoint_file::read_exact_size(path,size).map_err(|e|e.to_string())?;
        self.restore(&bytes)
    }
}
impl Drop for Photoreceptors {
    fn drop(&mut self) { unsafe { fp_destroy(self.handle.as_ptr()) } }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn owns_persistent_state_and_resets_only_explicitly() {
        let _guard=TEST_LOCK.lock().unwrap();
        let mut p=Photoreceptors::new(2,30000,19303,16).unwrap();
        assert!(Photoreceptors::new(2,30000,19303,16).is_err());
        let mut first=vec![0.;18];
        assert_eq!(p.observe(&mut first).unwrap(),0);
        p.advance(&[0.,100000.],20).unwrap();
        let mut split=vec![0.;18];
        assert_eq!(p.observe(&mut split).unwrap(),20);
        assert!(p.advance(&[f64::NAN,100000.],1).is_err());
        assert!(p.advance(&[1.],1).is_err());
        let mut unchanged=vec![0.;18];
        assert_eq!(p.observe(&mut unchanged).unwrap(),20);
        assert_eq!(split,unchanged);
        p.advance(&[0.,100000.],30).unwrap();
        assert_eq!(p.observe(&mut split).unwrap(),50);
        p.reset(19303).unwrap();
        assert_eq!(p.observe(&mut unchanged).unwrap(),0);
        assert_eq!(first,unchanged);
        p.advance(&[0.,100000.],50).unwrap();
        assert_eq!(p.observe(&mut unchanged).unwrap(),50);
        assert_eq!(split,unchanged);
        let checkpoint=p.snapshot().unwrap();
        p.set_neural_feedback(&[0.5,-0.5]).unwrap();
        let with_feedback=p.snapshot().unwrap();
        assert_ne!(with_feedback,checkpoint);
        assert!(p.set_neural_feedback(&[f64::NAN,0.]).is_err());
        assert_eq!(p.snapshot().unwrap(),with_feedback);
        p.restore(&checkpoint).unwrap();
        p.advance(&[100000.,0.],200).unwrap();
        let terminal=p.snapshot().unwrap();
        p.reset(999).unwrap();
        p.restore(&checkpoint).unwrap();
        assert_eq!(p.snapshot().unwrap(),checkpoint);
        p.advance(&[100000.,0.],200).unwrap();
        assert_eq!(p.snapshot().unwrap(),terminal);
        let mut corrupt=checkpoint.clone();
        corrupt[64]^=1; // Tick metadata is included in corruption detection.
        assert!(p.restore(&corrupt).is_err());
        assert_eq!(p.snapshot().unwrap(),terminal);
        assert!(p.restore(&checkpoint[..checkpoint.len()-1]).is_err());
        assert_eq!(p.snapshot().unwrap(),terminal);
        let path=std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("build").join("photon-rust-checkpoint.bin");
        p.save_file(&path).unwrap();
        p.reset(42).unwrap();
        p.load_file(&path).unwrap();
        assert_eq!(p.snapshot().unwrap(),terminal);
        drop(p);
        assert!(Photoreceptors::new(2,30000,19303,16).is_ok());
    }
}
