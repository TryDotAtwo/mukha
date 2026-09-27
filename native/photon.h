#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef _WIN32
#define FP_API __declspec(dllexport)
#else
#define FP_API
#endif
#ifdef __cplusplus
extern "C" {
#endif
// Stateful pinned VisTrans phototransduction; no camera calibration or CNS mapping.
// Only one live instance per library is supported (author kernels use CUDA symbols).
// Factory captures the current CUDA device. All calls are serialized internally.
FP_API void* fp_create(uint32_t cells, uint32_t microvilli_each, uint64_t seed,
                       uint32_t launch_blocks);
FP_API void fp_destroy(void* model);
// Explicit episode boundary. Restores baseline molecular/membrane/RNG state.
FP_API int fp_reset(void* model, uint64_t seed);
// Nonnegative finite photons/second per cell. Held constant for ticks * 0.1 ms.
// No reset between calls; molecular, adaptation and RNG state persist.
// Invalid arguments do not modify state. CUDA failures poison the model until reset.
FP_API int fp_advance(void* model, const double* rates, size_t count, uint32_t ticks);
// Endogenous synaptic feedback current in author membrane units (uA/cm^2),
// held until replaced. This is not sensory telemetry. Zero after reset; included
// in checkpoints. Graph conductance/reversal calibration is external and required.
FP_API int fp_set_neural_feedback(void* model, const double* current, size_t count);
// 9 SoA rows: V, sa, si, dra, dri, nov, ns, last input, reserved (zero).
// Diagnostic output only. Output has exactly cells*9 doubles.
FP_API int fp_observe(void* model, double* state, size_t count, uint64_t* tick);
// Trusted checkpoint bytes, bound to build, dimensions, launch config and GPU CC.
// Caller owns the host buffer. The size includes metadata, checksum and all
// persistent GPU state. Raw cuRAND layout is not a portable interchange format.
// Invalid checkpoint/length fails before any model mutation. A CUDA restore
// failure poisons the model. Input/output buffers must not alias the model.
FP_API size_t fp_checkpoint_size(void* model);
FP_API int fp_save(void* model, unsigned char* output, size_t bytes);
FP_API int fp_load(void* model, const unsigned char* input, size_t bytes);
FP_API const char* fp_build_identity(void);
FP_API const char* fp_last_error(void);
#ifdef __cplusplus
}
#endif
