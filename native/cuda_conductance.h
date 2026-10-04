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
FC_API int fc_reset(fc_model* model);
FC_API void fc_destroy(fc_model* model);
FC_API const char* fc_error(void);

#ifdef __cplusplus
}
#endif
