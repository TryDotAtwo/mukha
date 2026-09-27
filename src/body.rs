use std::{ffi::{c_char,c_void,CStr,CString},marker::PhantomData,path::Path,ptr::NonNull,rc::Rc};
extern "C" {
    fn fb_create(path:*const c_char)->*mut c_void;
    fn fb_destroy(body:*mut c_void);
    fn fb_error()->*const c_char;
    fn fb_controls(body:*const c_void)->usize;
    fn fb_advance(body:*mut c_void,u:*const f64,count:usize,ticks:u32)->i32;
    fn fb_control_position(body:*const c_void,time:*mut f64,q:*mut f64)->i32;
    fn fb_contact_normal(body:*const c_void,geom:*const c_char,time:*mut f64,
                         force:*mut f64,count:*mut u32)->i32;
    fn fb_contact_points(body:*const c_void,geom:*const c_char,samples:*mut f64,
                         capacity:usize,count:*mut u32,time:*mut f64)->i32;
}
/// Solver contact observation, with its own evaluation time and model force units.
pub struct ContactObservation { pub evaluation_time:f64, pub normal_force:f64, pub count:u32 }
pub struct ContactPoint { pub position:[f64;3], pub normal_into_geometry:[f64;3],
    pub force_on_geometry_world:[f64;3], pub normal_force:f64 }
fn check(code:i32)->Result<(),String> {
    if code==0 {Ok(())} else {Err(unsafe{CStr::from_ptr(fb_error())}.to_string_lossy().into_owned())}
}
/// Exclusive owner. The model stays native; this handle is neither Send nor Sync.
pub struct Body { ptr:NonNull<c_void>, controls:usize, _thread:PhantomData<Rc<()>> }
impl Body {
    pub fn open(path:&str)->Result<Self,String> {
        let path=CString::new(path).map_err(|e|e.to_string())?;
        let ptr=NonNull::new(unsafe{fb_create(path.as_ptr())}).ok_or_else(||unsafe{CStr::from_ptr(fb_error())}.to_string_lossy().into_owned())?;
        Ok(Self {controls:unsafe{fb_controls(ptr.as_ptr())},ptr,_thread:PhantomData})
    }
    pub fn advance(&mut self,commands:&[f64],ticks:u32)->Result<(),String> {
        if commands.len()!=self.controls{return Err("wrong joint command count".into())}
        check(unsafe{fb_advance(self.ptr.as_ptr(),commands.as_ptr(),commands.len(),ticks)})
    }
    pub fn control_position(&self)->Result<(f64,f64),String> {
        let(mut time,mut q)=(0.,0.);
        check(unsafe{fb_control_position(self.ptr.as_ptr(),&mut time,&mut q)})?;Ok((time,q))
    }
    pub fn contact_normal(&self,geometry:&str)->Result<ContactObservation,String> {
        let name=CString::new(geometry).map_err(|e|e.to_string())?;
        let(mut evaluation_time,mut normal_force,mut count)=(0.,0.,0);
        check(unsafe{fb_contact_normal(self.ptr.as_ptr(),name.as_ptr(),
            &mut evaluation_time,&mut normal_force,&mut count)})?;
        Ok(ContactObservation{evaluation_time,normal_force,count})
    }
    pub fn contact_points(&self,geometry:&str)->Result<(f64,Vec<ContactPoint>),String> {
        let summary=self.contact_normal(geometry)?;
        let name=CString::new(geometry).map_err(|e|e.to_string())?;
        let mut buffer=vec![0.;summary.count as usize*10];
        let(mut count,mut time)=(0u32,0.);
        check(unsafe{fb_contact_points(self.ptr.as_ptr(),name.as_ptr(),buffer.as_mut_ptr(),
            summary.count as usize,&mut count,&mut time)})?;
        if count!=summary.count || time!=summary.evaluation_time {
            return Err("contact state changed during observation".into())
        }
        let points=buffer.chunks_exact(10).map(|x|ContactPoint{
            position:[x[0],x[1],x[2]],normal_into_geometry:[x[3],x[4],x[5]],
            force_on_geometry_world:[x[6],x[7],x[8]],normal_force:x[9]}).collect();
        Ok((time,points))
    }
}
impl Drop for Body {fn drop(&mut self){unsafe{fb_destroy(self.ptr.as_ptr())}}}

pub fn diagnostic(model:&str,output:&Path)->Result<(),String> {
    let mut body=Body::open(model)?;
    let mut commands=vec![0.;body.controls];
    if commands.is_empty(){return Err("no joint drives".into())}
    let mut trace=Vec::with_capacity(100);
    for chunk in 0..100 {
        commands[0]=if (20..40).contains(&chunk){1.}else{0.};
        body.advance(&commands,100)?;
        let(time,q)=body.control_position()?;
        let contact=body.contact_normal("control_pad")?;
        let foot=body.contact_normal("lf_tarsus5")?;
        let(point_time,points)=body.contact_points("lf_tarsus5")?;
        if contact.count!=foot.count ||
            (contact.normal_force-foot.normal_force).abs()>1e-10 ||
            (contact.evaluation_time-foot.evaluation_time).abs()>1e-12 ||
            (point_time-foot.evaluation_time).abs()>1e-12 ||
            points.len()!=foot.count as usize ||
            (points.iter().map(|p|p.normal_force).sum::<f64>()-foot.normal_force).abs()>1e-10 {
            return Err("pad/foot contact observation mismatch".into())
        }
        trace.push(serde_json::json!({"time":time,"slider_mm":q,
            "diagnostic_command":commands[0],
            "contact_evaluation_time":contact.evaluation_time,
            "contact_normal_force_model_units":contact.normal_force,
            "contact_count":contact.count,
            "foot_normal_force_model_units":foot.normal_force,
            "foot_contact_count":foot.count,
            "foot_contact_points":points.iter().map(|p|serde_json::json!({
                "position":p.position,"normal_into_foot":p.normal_into_geometry,
                "force_on_foot_world":p.force_on_geometry_world,
                "normal_force_model_units":p.normal_force})).collect::<Vec<_>>()}));
    }
    let(time,_)=body.control_position()?;
    if (time-1.).abs()>1e-9{return Err("body clock mismatch".into())}
    let report=serde_json::json!({"scope":"Rust/native mechanical diagnostic, no neural controller", "controls":body.controls,"samples":trace});
    std::fs::write(output,serde_json::to_vec_pretty(&report).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    println!("{}",serde_json::json!({"time":time,"controls":body.controls,"samples":100}));Ok(())
}
