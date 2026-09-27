#pragma once
#include "lif.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ff_cuda_model ff_cuda_model;
/* Incoming CSR; signed weights in mV. Inputs are copied; GPU memory is C++ owned.
   Capacity bounds recorded ticks per advance, not episode duration.
   Calls on one handle must be serialized. No implicit reset between calls. */
ff_cuda_model* ff_cuda_create(uint32_t n,uint64_t edges,const uint64_t* rows,
    const uint32_t* columns,const float* weights,const uint8_t* sensory,
    ff_params parameters,uint32_t chunk_capacity);
/* Mixed diagnostic: graded-source weight is the steady synaptic-state value at
   unit release; each step adds weight * release * (1-exp(-dt/tau_synapse)).
   Spiking-source weight remains an impulse per event. Mixed checkpoints use v3. */
ff_cuda_model* ff_cuda_create_mixed(uint32_t n,uint64_t edges,const uint64_t* rows,
    const uint32_t* columns,const float* weights,const uint8_t* sensory,
    const uint8_t* graded_mask,float graded_span_mv,ff_params parameters,uint32_t chunk_capacity);
void ff_cuda_destroy(ff_cuda_model* model);
int ff_cuda_advance(ff_cuda_model* model,uint32_t steps,const float* inputs,
    float* voltage_trace,float* synapse_trace,uint8_t* spike_trace);
int ff_cuda_reset(ff_cuda_model* model);
size_t ff_cuda_checkpoint_size(const ff_cuda_model* model);
int ff_cuda_save(ff_cuda_model* model,uint8_t* output,size_t bytes);
int ff_cuda_load(ff_cuda_model* model,const uint8_t* input,size_t bytes);
const char* ff_cuda_probe_error(void);
#ifdef __cplusplus
}
#endif
