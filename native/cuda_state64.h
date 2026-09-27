#pragma once
#include <stddef.h>
#include "lif64.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ff_cuda64_model ff_cuda64_model;
/* Separate FP64 ABI: parameters, weights, inputs and state outputs are doubles. */
ff_cuda64_model* ff_cuda64_create(uint32_t n,uint64_t edges,const uint64_t* rows,
    const uint32_t* columns,const double* weights,const uint8_t* sensory,
    ff_params64 parameters,uint32_t chunk_capacity);
/* Mixed diagnostic: graded-source weight is the steady synaptic-state value at
   unit release; each step adds weight * release * (1-exp(-dt/tau_synapse)).
   Spiking-source weight remains an impulse per event. Mixed checkpoints use v3. */
ff_cuda64_model* ff_cuda64_create_mixed(uint32_t n,uint64_t edges,const uint64_t* rows,
    const uint32_t* columns,const double* weights,const uint8_t* sensory,
    const uint8_t* graded_mask,double graded_span_mv,ff_params64 parameters,uint32_t chunk_capacity);
void ff_cuda64_destroy(ff_cuda64_model* model);
int ff_cuda64_advance(ff_cuda64_model* model,uint32_t steps,const double* inputs,
    double* voltage_trace,double* synapse_trace,uint8_t* spike_trace);
int ff_cuda64_reset(ff_cuda64_model* model);
size_t ff_cuda64_checkpoint_size(const ff_cuda64_model* model);
int ff_cuda64_save(ff_cuda64_model* model,uint8_t* output,size_t bytes);
int ff_cuda64_load(ff_cuda64_model* model,const uint8_t* input,size_t bytes);
const char* ff_cuda64_probe_error(void);
#ifdef __cplusplus
}
#endif
