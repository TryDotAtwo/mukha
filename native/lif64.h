#pragma once
#include <stdint.h>
typedef struct ff_params64 {
    double dt_ms,rest_mv,reset_mv,threshold_mv,membrane_ms,synapse_ms;
    uint32_t refractory_ticks,delay_ticks;
} ff_params64;
