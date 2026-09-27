#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef _WIN32
#define FB_API __declspec(dllexport)
#else
#define FB_API
#endif
#ifdef __cplusplus
extern "C" {
#endif
typedef struct fb_body fb_body;
// One handle owns one model and persistent physical state; calls are not concurrent.
FB_API fb_body* fb_create(const char* xml_path);
FB_API void fb_destroy(fb_body* body);
FB_API const char* fb_error(void);
FB_API size_t fb_controls(const fb_body* body);
FB_API size_t fb_state_size(const fb_body* body);
FB_API int fb_reset(fb_body* body);
// Finite commands within the model's declared bounds; same command held for ticks.
// No allocation and no implicit episode reset. Invalid input leaves state unchanged.
FB_API int fb_advance(fb_body* body,const double* commands,size_t count,uint32_t ticks);
FB_API int fb_state(const fb_body* body,double* values,size_t count);
// In-memory same-model snapshot only, not a portable or authenticated checkpoint.
FB_API int fb_restore(fb_body* body,const double* values,size_t count);
FB_API int fb_control_position(const fb_body* body,double* time,double* position);
// Read a named scalar physical joint, suitable for proprioceptive transduction.
FB_API int fb_joint_position(const fb_body* body,const char* joint,double* position);
// MuJoCo contact solver observation for one named geometry. Force is in model
// units; evaluation time can precede the integrated state time by one step.
// After restore, call advance before reading contact again.
FB_API int fb_contact_normal(const fb_body* body,const char* geom,double* evaluation_time,
                             double* normal_force,uint32_t* contact_count);
// Per-contact world position [0:3], unit normal pointing into queried geom
// [3:6], full force ON queried geom in world coordinates [6:9], and positive
// normal-force magnitude [9]. Ten doubles per row; capacity counts rows.
// A zero-contact call accepts a null sample buffer with zero capacity.
FB_API int fb_contact_points(const fb_body* body,const char* geom,double* samples,
                             size_t capacity,uint32_t* count,double* evaluation_time);
#ifdef __cplusplus
}
#endif
