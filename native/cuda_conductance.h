#pragma once
#include <stdint.h>

#ifdef _WIN32
#define FC_API __declspec(dllexport)
#else
#define FC_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef struct fc_params {
    double dt_ms, rest_mv, reset_mv, threshold_mv;
    double membrane_ms, synapse_ms, reversal_exc_mv, reversal_inh_mv;
    uint32_t refractory_ticks, delay_ticks;
} fc_params;

typedef struct fc_model fc_model;

// CSR rows are postsynaptic, columns presynaptic. Both weight arrays are
// nonnegative dimensionless conductance increments per presynaptic spike.
FC_API fc_model* fc_create(uint32_t neurons, uint64_t edges, const uint64_t* indptr,
                    const uint32_t* indices, const double* excitatory,
                    const double* inhibitory, const uint8_t* sensory,
                    fc_params params, uint32_t chunk_capacity);
// Returns 0 on success, -1 on failure. Nonfinite internal state rejects the
// entire chunk before copying output arrays. Runtime failures invalidate the
// handle until a successful explicit fc_reset; invalid input rejected before
// mutation does not invalidate an otherwise healthy handle. No failed chunk
// may be published as a valid episode/checkpoint.
FC_API int fc_advance(fc_model* model, uint32_t ticks, const double* direct_voltage_jump_mv,
               double* voltage_mv, double* conductance_exc,
               double* conductance_inh, uint8_t* spikes);
// Optional deterministic depletion/recovery candidate, configured only at tick 0.
// Each edge uses release = U * recovered_resource on a delayed source spike;
// conductance increment = original weight * efficacy * release. Recovery is
// exponential between ticks, reset restores resource=1. This is short-term state,
// not learned long-term efficacy. Arrays contain one value per CSR edge.
// No parameters are inferred or biologically admitted by this API.
FC_API int fc_configure_release(fc_model* model, const double* utilization,
    const double* recovery_ms, const double* postsynaptic_efficacy);
// Versioned native-endian state includes exact graph/configuration identity,
// neural state, delay queue and optional per-edge resource. Chunk capacity may
// differ. FNV-1a detects accidental corruption; external SHA-256/HF receipts
// provide artifact integrity. Rejected host data do not mutate the model;
// device failures require explicit reset. No authenticity claim for FNV-1a.
FC_API uint64_t fc_state_bytes(fc_model* model);
FC_API int fc_save_state(fc_model* model,uint8_t* bytes,uint64_t size);
FC_API int fc_load_state(fc_model* model,const uint8_t* bytes,uint64_t size);
FC_API int fc_reset(fc_model* model);
FC_API void fc_destroy(fc_model* model);
FC_API const char* fc_error(void);

#ifdef __cplusplus
}
#endif
