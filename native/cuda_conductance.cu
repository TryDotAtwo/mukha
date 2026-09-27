// Separate, parameterized conductance-capable whole-graph runtime.
// It does not assign receptor identity or physiological constants to MaleCNS.
#include "cuda_conductance.h"
#include <cuda_runtime.h>
#include <cusparse.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef _WIN32
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT extern "C"
#endif

namespace {
thread_local std::string last_error;
void check(cudaError_t rc) { if(rc!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(rc)); }
void check(cusparseStatus_t rc) { if(rc!=CUSPARSE_STATUS_SUCCESS) throw std::runtime_error(cusparseGetErrorString(rc)); }
void require(bool ok,const char* message) { if(!ok) throw std::invalid_argument(message); }

template<class T> struct Buffer {
    T* data=nullptr;
    explicit Buffer(size_t count) { check(cudaMalloc(&data,std::max(size_t(1),count)*sizeof(T))); }
    ~Buffer() { if(data) cudaFree(data); }
    Buffer(const Buffer&)=delete;
    Buffer& operator=(const Buffer&)=delete;
    void upload(const T* source,size_t count) { if(count) check(cudaMemcpy(data,source,count*sizeof(T),cudaMemcpyHostToDevice)); }
};

__global__ void reset_state(uint32_t n,double rest,double* v,double* ge,double* gi,uint64_t* next) {
    const uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<n) { v[i]=rest;ge[i]=0;gi[i]=0;next[i]=0; }
}

__global__ void integrate(uint32_t n,uint64_t tick,fc_params p,double synapse_decay,
                          double* v,double* ge,double* gi,const uint64_t* next,
                          double* emitted,uint8_t* allowed) {
    const uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=n) return;
    const bool active=tick>=next[i];
    allowed[i]=active;
    if(active) {
        const double total=1.0+ge[i]+gi[i];
        const double equilibrium=(p.rest_mv+ge[i]*p.reversal_exc_mv+gi[i]*p.reversal_inh_mv)/total;
        v[i]=equilibrium+(v[i]-equilibrium)*exp(-p.dt_ms*total/p.membrane_ms);
    }
    ge[i]*=synapse_decay;
    gi[i]*=synapse_decay;
    emitted[i]=(active && v[i]>p.threshold_mv)?1.0:0.0;
}

__global__ void finish(uint32_t n,uint64_t tick,fc_params p,
                       const double* direct,const double* incoming_e,const double* incoming_i,
                       const double* emitted,const uint8_t* sensory,const uint8_t* allowed,
                       double* v,double* ge,double* gi,uint64_t* next,
                       double* trace_v,double* trace_e,double* trace_i,uint8_t* trace_spikes) {
    const uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=n) return;
    // Conductance decays and accumulates during refractory periods too.
    ge[i]+=incoming_e[i];
    gi[i]+=incoming_i[i];
    if(allowed[i]) v[i]+=direct[i];
    if(emitted[i]!=0.0) { v[i]=p.reset_mv;next[i]=tick+(sensory[i]?0:p.refractory_ticks); }
    trace_v[i]=v[i];trace_e[i]=ge[i];trace_i[i]=gi[i];
    trace_spikes[i]=uint8_t(emitted[i]);
}
}

struct fc_model {
    uint32_t n,cap;
    uint64_t edges,tick=0;
    fc_params p;
    double synapse_decay;
    Buffer<uint64_t> row,col,next;
    Buffer<uint8_t> sensory,allowed,trace_spikes;
    Buffer<double> we,wi,v,ge,gi,ring,in_e,in_i,direct,trace_v,trace_e,trace_i;
    cusparseHandle_t sparse=nullptr;
    cusparseSpMatDescr_t mat_e=nullptr,mat_i=nullptr;
    cusparseDnVecDescr_t x=nullptr,y_e=nullptr,y_i=nullptr;
    std::unique_ptr<Buffer<uint8_t>> scratch;
    fc_model(uint32_t count,uint64_t edge_count,const uint64_t* indptr,const uint32_t* indices,
             const double* excitatory,const double* inhibitory,const uint8_t* sense,
             fc_params params,uint32_t capacity):
        n(count),cap(capacity),edges(edge_count),p(params),
        synapse_decay(std::exp(-params.dt_ms/params.synapse_ms)),
        row(size_t(count)+1),col(edge_count),next(count),
        sensory(count),allowed(count),trace_spikes(size_t(count)*capacity),
        we(edge_count),wi(edge_count),v(count),ge(count),gi(count),
        ring(size_t(count)*(params.delay_ticks+1)),in_e(count),in_i(count),
        direct(size_t(count)*capacity),trace_v(size_t(count)*capacity),
        trace_e(size_t(count)*capacity),trace_i(size_t(count)*capacity) {
        std::vector<uint64_t> wide(edges);
        for(uint64_t i=0;i<edges;++i) wide[i]=indices[i];
        row.upload(indptr,size_t(n)+1);col.upload(wide.data(),edges);
        we.upload(excitatory,edges);wi.upload(inhibitory,edges);sensory.upload(sense,n);
        check(cusparseCreate(&sparse));
        check(cusparseCreateCsr(&mat_e,n,n,edges,row.data,col.data,we.data,
              CUSPARSE_INDEX_64I,CUSPARSE_INDEX_64I,CUSPARSE_INDEX_BASE_ZERO,CUDA_R_64F));
        check(cusparseCreateCsr(&mat_i,n,n,edges,row.data,col.data,wi.data,
              CUSPARSE_INDEX_64I,CUSPARSE_INDEX_64I,CUSPARSE_INDEX_BASE_ZERO,CUDA_R_64F));
        check(cusparseCreateDnVec(&x,n,ring.data,CUDA_R_64F));
        check(cusparseCreateDnVec(&y_e,n,in_e.data,CUDA_R_64F));
        check(cusparseCreateDnVec(&y_i,n,in_i.data,CUDA_R_64F));
        const double alpha=1,beta=0;
        size_t se=0,si=0;
        check(cusparseSpMV_bufferSize(sparse,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,
              mat_e,x,&beta,y_e,CUDA_R_64F,CUSPARSE_SPMV_CSR_ALG2,&se));
        check(cusparseSpMV_bufferSize(sparse,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,
              mat_i,x,&beta,y_i,CUDA_R_64F,CUSPARSE_SPMV_CSR_ALG2,&si));
        scratch=std::make_unique<Buffer<uint8_t>>(std::max(se,si));
        reset();
    }
    ~fc_model() {
        if(y_i) cusparseDestroyDnVec(y_i);
        if(y_e) cusparseDestroyDnVec(y_e);
        if(x) cusparseDestroyDnVec(x);
        if(mat_i) cusparseDestroySpMat(mat_i);
        if(mat_e) cusparseDestroySpMat(mat_e);
        if(sparse) cusparseDestroy(sparse);
    }
    void reset() {
        check(cudaMemset(ring.data,0,size_t(n)*(p.delay_ticks+1)*sizeof(double)));
        check(cudaMemset(in_e.data,0,size_t(n)*sizeof(double)));
        check(cudaMemset(in_i.data,0,size_t(n)*sizeof(double)));
        reset_state<<<(n+255)/256,256>>>(n,p.rest_mv,v.data,ge.data,gi.data,next.data);
        check(cudaGetLastError());check(cudaDeviceSynchronize());
        tick=0;
    }
    void advance(uint32_t ticks,const double* input,double* output_v,double* output_e,
                 double* output_i,uint8_t* output_spikes) {
        require(ticks>0 && ticks<=cap,"invalid tick count");
        for(size_t i=0;i<size_t(n)*ticks;++i) require(std::isfinite(input[i]),"nonfinite direct drive");
        direct.upload(input,size_t(n)*ticks);
        const double alpha=1,beta=0;
        for(uint32_t step=0;step<ticks;++step,++tick) {
            double* fired=ring.data+(tick%(p.delay_ticks+1))*n;
            double* delayed=ring.data+((tick+1)%(p.delay_ticks+1))*n;
            integrate<<<(n+255)/256,256>>>(n,tick,p,synapse_decay,v.data,ge.data,gi.data,
                                           next.data,fired,allowed.data);
            check(cudaGetLastError());
            check(cusparseDnVecSetValues(x,delayed));
            check(cusparseSpMV(sparse,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,
                  mat_e,x,&beta,y_e,CUDA_R_64F,CUSPARSE_SPMV_CSR_ALG2,scratch->data));
            check(cusparseSpMV(sparse,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,
                  mat_i,x,&beta,y_i,CUDA_R_64F,CUSPARSE_SPMV_CSR_ALG2,scratch->data));
            const size_t offset=size_t(step)*n;
            finish<<<(n+255)/256,256>>>(n,tick,p,direct.data+offset,in_e.data,in_i.data,
                                        fired,sensory.data,allowed.data,v.data,ge.data,gi.data,next.data,
                                        trace_v.data+offset,trace_e.data+offset,trace_i.data+offset,
                                        trace_spikes.data+offset);
            check(cudaGetLastError());
        }
        check(cudaDeviceSynchronize());
        const size_t total=size_t(n)*ticks;
        check(cudaMemcpy(output_v,trace_v.data,total*sizeof(double),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(output_e,trace_e.data,total*sizeof(double),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(output_i,trace_i.data,total*sizeof(double),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(output_spikes,trace_spikes.data,total,cudaMemcpyDeviceToHost));
    }
};

EXPORT fc_model* fc_create(uint32_t n,uint64_t edges,const uint64_t* row,const uint32_t* col,
                           const double* excitatory,const double* inhibitory,const uint8_t* sensory,
                           fc_params p,uint32_t capacity) {
    try {
        require(n && capacity && row && sensory,"invalid graph dimensions or pointers");
        require(!edges || (col && excitatory && inhibitory),"null edge arrays");
        require(std::isfinite(p.dt_ms) && p.dt_ms>0 && std::isfinite(p.membrane_ms) && p.membrane_ms>0
                && std::isfinite(p.synapse_ms) && p.synapse_ms>0,"invalid time constants");
        require(std::isfinite(p.rest_mv) && std::isfinite(p.reset_mv) &&
                std::isfinite(p.threshold_mv) && std::isfinite(p.reversal_exc_mv) &&
                std::isfinite(p.reversal_inh_mv),"nonfinite voltage parameter");
        require(p.delay_ticks>=1 && p.delay_ticks<100000 && p.refractory_ticks<100000,
                "invalid delay or refractory period");
        require(row[0]==0 && row[n]==edges,"invalid CSR endpoints");
        for(uint32_t i=0;i<n;++i) require(row[i]<=row[i+1],"nonmonotonic CSR");
        for(uint64_t i=0;i<edges;++i) require(col[i]<n && std::isfinite(excitatory[i]) &&
             std::isfinite(inhibitory[i]) && excitatory[i]>=0 && inhibitory[i]>=0,
             "invalid edge index or conductance");
        auto model=std::make_unique<fc_model>(n,edges,row,col,excitatory,inhibitory,sensory,p,capacity);
        last_error.clear();return model.release();
    } catch(const std::exception& e) { last_error=e.what();return nullptr; }
}
EXPORT int fc_advance(fc_model* model,uint32_t ticks,const double* direct,double* voltage,
                      double* excitatory,double* inhibitory,uint8_t* spikes) {
    try {
        require(model && direct && voltage && excitatory && inhibitory && spikes,"null model or output");
        model->advance(ticks,direct,voltage,excitatory,inhibitory,spikes);
        last_error.clear();return 0;
    } catch(const std::exception& e) { last_error=e.what();return -1; }
}
EXPORT int fc_reset(fc_model* model) {
    try {
        require(model,"null model");model->reset();last_error.clear();return 0;
    } catch(const std::exception& e) { last_error=e.what();return -1; }
}
EXPORT void fc_destroy(fc_model* model) { delete model; }
EXPORT const char* fc_error(void) { return last_error.c_str(); }
