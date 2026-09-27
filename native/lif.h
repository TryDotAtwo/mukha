#pragma once
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif
typedef struct ff_model ff_model;
typedef struct ff_params {
    float dt_ms, rest_mv, reset_mv, threshold_mv, membrane_ms, synapse_ms;
    uint32_t refractory_ticks, delay_ticks;
} ff_params;

/* Incoming CSR: row=post, columns=pre. Signed weights are millivolts.
   Inputs are copied on creation. C++ owns state. Every function catches errors.
   No global mutable model state, no Python callbacks, no implicit resets. */
ff_model* ff_create(uint32_t n, uint64_t edges, const uint64_t* row_ptr,
                    const uint32_t* columns, const float* weights_mv,
                    const uint8_t* sensory_mask, ff_params params);
void ff_destroy(ff_model* model);
int ff_step(ff_model* model, const float* voltage_jump_mv, uint8_t* spikes);
int ff_observe(const ff_model* model, float* voltage_mv, float* synapse_mv);
size_t ff_checkpoint_size(const ff_model* model);
int ff_save(const ff_model* model, uint8_t* buffer, size_t bytes);
int ff_load(ff_model* model, const uint8_t* buffer, size_t bytes);
const char* ff_last_error(void);
#ifdef __cplusplus
}
#endif
