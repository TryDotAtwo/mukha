// CUDA kernels and persistent C ABI implementation with a bounded replay wrapper.
#include "lif.h"
#include "lif_coeff.h"
#include <cuda_runtime.h>
#include <cusparse.h>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <memory>
#include <cstring>

#ifdef FF_FP64
#include "lif64.h"
using Real=double;
using NeuralParams=ff_params64;
constexpr cudaDataType REAL_CUDA_TYPE=CUDA_R_64F;
constexpr uint64_t CHECKPOINT_MAGIC=0x3241445543594c46ULL;
#define ff_cuda_model ff_cuda64_model
#define ff_cuda_create ff_cuda64_create
#define ff_cuda_destroy ff_cuda64_destroy
#define ff_cuda_advance ff_cuda64_advance
#define ff_cuda_reset ff_cuda64_reset
#define ff_cuda_save ff_cuda64_save
#define ff_cuda_load ff_cuda64_load
#define ff_cuda_checkpoint_size ff_cuda64_checkpoint_size
#define ff_cuda_probe_error ff_cuda64_probe_error
#define ff_cuda_probe ff_cuda64_probe
#define ff_cuda_create_mixed ff_cuda64_create_mixed
#else
using Real=float;
using NeuralParams=ff_params;
constexpr cudaDataType REAL_CUDA_TYPE=CUDA_R_32F;
constexpr uint64_t CHECKPOINT_MAGIC=0x3141445543594c46ULL;
#endif

#ifdef _WIN32
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT extern "C"
#endif
namespace {
thread_local std::string error;
void check(cudaError_t rc) { if(rc!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(rc)); }
void check(cusparseStatus_t rc) { if(rc!=CUSPARSE_STATUS_SUCCESS) throw std::runtime_error(cusparseGetErrorString(rc)); }
void require(bool ok,const char* msg) { if(!ok) throw std::runtime_error(msg); }
template<class T> struct Buffer {
    T* p=nullptr;
    explicit Buffer(size_t n) { require(n<=SIZE_MAX/sizeof(T),"allocation overflow");check(cudaMalloc(&p,(n?n:1)*sizeof(T))); }
    ~Buffer() { cudaFree(p); }
    Buffer(const Buffer&)=delete;
    Buffer& operator=(const Buffer&)=delete;
    void upload(const T* src,size_t n) { if(n) check(cudaMemcpy(p,src,n*sizeof(T),cudaMemcpyHostToDevice)); }
};
struct Sparse {
    cusparseHandle_t handle=nullptr;
    cusparseSpMatDescr_t matrix=nullptr;
    cusparseDnVecDescr_t x=nullptr,y=nullptr;
    ~Sparse() { if(y) cusparseDestroyDnVec(y);if(x) cusparseDestroyDnVec(x);
        if(matrix) cusparseDestroySpMat(matrix);if(handle) cusparseDestroy(handle); }
};
uint64_t hash_bytes(const void* bytes,size_t length,uint64_t h=14695981039346656037ULL) {
    auto data=static_cast<const uint8_t*>(bytes);
    for(size_t i=0;i<length;++i) { h^=data[i];h*=1099511628211ULL; }
    return h;
}
__global__ void initialize(uint32_t n,Real rest,Real* v,Real* g,uint64_t* next) {
    uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<n) { v[i]=rest;g[i]=0;next[i]=0; }
}
__global__ void integrate(uint32_t n,uint64_t tick,NeuralParams p,Real a,Real b,Real c,
                          Real* v,Real* g,const uint64_t* next,const uint8_t* graded,
                          Real graded_span,Real graded_step_factor,Real* emitted,uint8_t* allowed) {
    uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<n) { bool ok=tick>=next[i];allowed[i]=ok;
        if(ok) { v[i]=p.rest_mv+a*(v[i]-p.rest_mv)+c*g[i];g[i]=b*g[i]; }
        // For a graded cell, w means steady synaptic state at unit release.
        // Integrating dg/dt=(-g+w*r)/tau_s over this step contributes
        // w*r*(1-exp(-dt/tau_s)); spike cells retain impulse-per-event weights.
        if(graded[i]) emitted[i]=ok?graded_step_factor*Real(fmin(1.0,fmax(0.0,double((v[i]-Real(p.rest_mv))/graded_span)))):Real(0);
        else emitted[i]=(ok && v[i]>p.threshold_mv)?1.f:0.f;
    }
}
__global__ void finish(uint32_t n,uint64_t tick,NeuralParams p,const Real* input,
                       const Real* incoming,const Real* fired,const uint8_t* allowed,
                       const uint8_t* sensory,const uint8_t* graded,Real* v,Real* g,uint64_t* next,
                       Real* trace_v,Real* trace_g,uint8_t* trace_s) {
    uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<n) {
        if(allowed[i]) { g[i]+=incoming[i];v[i]+=input[i]; }
        if(!graded[i] && fired[i]!=0) { v[i]=p.reset_mv;g[i]=0;next[i]=tick+(sensory[i]?0:p.refractory_ticks); }
        trace_v[i]=v[i];trace_g[i]=g[i];trace_s[i]=graded[i]?0:uint8_t(fired[i]);
    }
}
}
#include "cuda_state.inc"
