#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef _WIN32
#define FV_API __declspec(dllexport)
#else
#define FV_API
#endif
#ifdef __cplusplus
extern "C" {
#endif
// Engineering image sampling only; no receptor physiology or neural mapping.
// Rays: unit vectors, xyz = forward,left,up in panorama coordinates.
// Panorama: tightly packed linear RGB32F, top=north; longitude increases leftward
// from -pi at the left boundary to +pi at the right boundary, forward at center.
// Pixel centers: lon=2*pi*((x+.5)/width-.5), lat=pi*(.5-(y+.5)/height).
// Horizontal wrap, vertical clamp. Point sampling with bilinear interpolation.
// Returns null on invalid dimensions/rays or allocation failure.
FV_API void* fv_create(const double* rays_xyz, size_t ray_count, uint32_t width, uint32_t height);
FV_API void fv_destroy(void* handle);
// Disjoint buffers required. Inputs finite and nonnegative. No allocation in sample.
// Error leaves output unchanged. Counts are scalar float elements, not pixels.
FV_API int fv_sample(const void* handle, const float* rgb, size_t rgb_count,
                     float* output, size_t output_count);
// Rotate body-local rays into world panorama coordinates for one stateless sample.
// rotation_row_major is an orthonormal, right-handed 3x3 local-to-world matrix.
// Invalid input leaves output unchanged. The handle and receptor state are unchanged.
FV_API int fv_sample_oriented(const void* handle, const float* rgb, size_t rgb_count,
                              const double* rotation_row_major,
                              float* output, size_t output_count);
#ifdef __cplusplus
}
#endif
