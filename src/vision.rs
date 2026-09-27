//! Pixel sampling only; no MaleCNS registration or receptor dynamics.
use std::{ffi::c_void, marker::PhantomData, ptr::NonNull, rc::Rc};

extern "C" {
    fn fv_create(rays: *const f64, count: usize, width: u32, height: u32) -> *mut c_void;
    fn fv_destroy(handle: *mut c_void);
    fn fv_sample(handle: *const c_void, rgb: *const f32, count: usize,
                 output: *mut f32, output_count: usize) -> i32;
    fn fv_sample_oriented(handle: *const c_void, rgb: *const f32, count: usize,
                          rotation_row_major: *const f64, output: *mut f32,
                          output_count: usize) -> i32;
}

pub struct Retina {
    handle: NonNull<c_void>,
    image_len: usize,
    output_len: usize,
    _exclusive: PhantomData<Rc<()>>,
}
impl Retina {
    pub fn new(rays: &[[f64; 3]], width: u32, height: u32) -> Result<Self, String> {
        let image_len = (width as usize).checked_mul(height as usize)
            .and_then(|n| n.checked_mul(3)).ok_or("Image dimensions overflow")?;
        let output_len = rays.len().checked_mul(3).ok_or("Ray count overflow")?;
        // C++ copies ray lookup data; it does not retain the Rust slice.
        let raw = unsafe { fv_create(rays.as_ptr().cast(), rays.len(), width, height) };
        let handle = NonNull::new(raw).ok_or("Invalid rays/dimensions or allocation failure")?;
        Ok(Self { handle, image_len, output_len, _exclusive: PhantomData })
    }
    pub fn sample(&mut self, rgb: &[f32], output: &mut [f32]) -> Result<(), String> {
        if rgb.len() != self.image_len || output.len() != self.output_len {
            return Err("Image/output dimensions disagree with ray map".into());
        }
        // Rust borrows guarantee distinct live input/output buffers.
        let status = unsafe { fv_sample(self.handle.as_ptr(), rgb.as_ptr(), rgb.len(),
                                         output.as_mut_ptr(), output.len()) };
        if status == 0 { Ok(()) } else { Err(format!("Native image sampling failed: {status}")) }
    }
    pub fn sample_oriented(&mut self, rgb: &[f32], local_to_world: &[[f64; 3]; 3],
                           output: &mut [f32]) -> Result<(), String> {
        if rgb.len() != self.image_len || output.len() != self.output_len {
            return Err("Image/output dimensions disagree with ray map".into());
        }
        let status = unsafe { fv_sample_oriented(self.handle.as_ptr(), rgb.as_ptr(), rgb.len(),
                                                 local_to_world.as_ptr().cast(),
                                                 output.as_mut_ptr(), output.len()) };
        if status == 0 { Ok(()) } else { Err(format!("Native oriented image sampling failed: {status}")) }
    }
}
impl Drop for Retina {
    fn drop(&mut self) { unsafe { fv_destroy(self.handle.as_ptr()) } }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn owns_lookup_and_rejects_invalid_input_without_output_mutation() {
        let mut retina = {
            let rays = vec![[1., 0., 0.], [0., 0., 1.]];
            Retina::new(&rays, 8, 4).unwrap()
        };
        let pixels = vec![2.; 8*4*3];
        let mut output = vec![-1.; 6];
        retina.sample(&pixels, &mut output).unwrap();
        assert_eq!(output, vec![2.; 6]);
        assert!(retina.sample(&pixels[..10], &mut output).is_err());
        let mut bad = pixels.clone(); bad[0] = f32::NAN;
        assert!(retina.sample(&bad, &mut output).is_err());
        assert_eq!(output, vec![2.; 6]);
        retina.sample(&pixels, &mut output).unwrap();
        assert!(Retina::new(&[[0.; 3]], 8, 4).is_err());
    }
    #[test]
    fn oriented_sample_follows_head_yaw_and_rejects_reflection() {
        let mut retina = Retina::new(&[[1., 0., 0.]], 8, 4).unwrap();
        let mut pixels = vec![0.; 8 * 4 * 3];
        for y in 0..4 { for x in 0..8 { pixels[(y * 8 + x) * 3] = x as f32; } }
        let mut output = vec![-1.; 3];
        let identity = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]];
        retina.sample_oriented(&pixels, &identity, &mut output).unwrap();
        let center = output[0];
        let yaw = [[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]];
        retina.sample_oriented(&pixels, &yaw, &mut output).unwrap();
        assert!(output[0] > center);
        let frozen = output.clone();
        let reflection = [[-1., 0., 0.], [0., 1., 0.], [0., 0., 1.]];
        assert!(retina.sample_oriented(&pixels, &reflection, &mut output).is_err());
        assert_eq!(output, frozen);
    }
}
