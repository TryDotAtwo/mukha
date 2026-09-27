#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef _WIN32
#define HM_API __declspec(dllexport)
#else
#define HM_API
#endif
typedef struct { double weights[6], recurrent[36], fw0, fwdt, tau[3], adaptation_tau; } hm_parameters;
typedef struct { double duration, odor[2], punishment; int32_t training; } hm_event;
#ifdef __cplusplus
extern "C" {
#endif
// Aggregate reference only. Rows of activity contain six variables per event.
// Parameters use row-major matrices. No allocation occurs in the event loop.
HM_API int hm_simulate(const hm_parameters*,const hm_event*,size_t,double* activity,size_t activity_count);
#ifdef __cplusplus
}
#endif
