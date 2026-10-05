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
#include <cstring>
#include <limits>

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
    std::vector<T> download(size_t count) const {
        std::vector<T> result(count);
        if(count) check(cudaMemcpy(result.data(),data,count*sizeof(T),cudaMemcpyDeviceToHost));
        return result;
    }
};

__global__ void reset_state(uint32_t n,double rest,double* v,double* ge,double* gi,uint64_t* next) {
    const uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<n) { v[i]=rest;ge[i]=0;gi[i]=0;next[i]=0; }
}

__global__ void integrate(uint32_t n,uint64_t tick,fc_params p,double synapse_decay,
                          double* v,double* ge,double* gi,const uint64_t* next,
                          double* emitted,uint8_t* allowed,uint32_t* numerical_error) {
    const uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=n) return;
    const bool active=tick>=next[i];
    allowed[i]=active;
    if(!isfinite(v[i]) || !isfinite(ge[i]) || !isfinite(gi[i])) {
        atomicExch(numerical_error,1u);allowed[i]=0;emitted[i]=0.0;return;
    }
    if(active) {
        const double total=1.0+ge[i]+gi[i];
        const double equilibrium=(p.rest_mv+ge[i]*p.reversal_exc_mv+gi[i]*p.reversal_inh_mv)/total;
        v[i]=equilibrium+(v[i]-equilibrium)*exp(-p.dt_ms*total/p.membrane_ms);
        if(!isfinite(total) || !isfinite(equilibrium) || !isfinite(v[i])) {
            atomicExch(numerical_error,1u);allowed[i]=0;emitted[i]=0.0;return;
        }
    }
    ge[i]*=synapse_decay;
    gi[i]*=synapse_decay;
    emitted[i]=(active && v[i]>p.threshold_mv)?1.0:0.0;
}

// Deterministic per-edge depletion candidate. Parameters are supplied explicitly;
// this mechanism does not assign physiological release probabilities to a graph.
__global__ void release_incoming(uint32_t n, const uint64_t* row, const uint64_t* col,
    const double* delayed, const double* we, const double* wi,
    const double* utilization, const double* recovery_decay, const double* efficacy,
    double* resource, double* incoming_e, double* incoming_i) {
    const uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=n) return;
    double e=0.0, inh=0.0;
    for(uint64_t k=row[i];k<row[i+1];++k) {
        double available=1.0-(1.0-resource[k])*recovery_decay[k];
        const double released=utilization[k]*available*delayed[col[k]];
        resource[k]=available-released;
        e+=we[k]*efficacy[k]*released;
        inh+=wi[k]*efficacy[k]*released;
    }
    incoming_e[i]=e; incoming_i[i]=inh;
}

__global__ void finish(uint32_t n,uint64_t tick,fc_params p,
                       const double* direct,const double* incoming_e,const double* incoming_i,
                       const double* emitted,const uint8_t* sensory,const uint8_t* allowed,
                       double* v,double* ge,double* gi,uint64_t* next,
                       double* trace_v,double* trace_e,double* trace_i,uint8_t* trace_spikes,
                       uint32_t* numerical_error) {
    const uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=n) return;
    // Conductance decays and accumulates during refractory periods too.
    ge[i]+=incoming_e[i];
    gi[i]+=incoming_i[i];
    if(allowed[i]) v[i]+=direct[i];
    // Reject transient overflow before spike reset can conceal it.
    if(!isfinite(v[i]) || !isfinite(ge[i]) || !isfinite(gi[i])) {
        atomicExch(numerical_error,1u);return;
    }
    if(emitted[i]!=0.0) { v[i]=p.reset_mv;next[i]=tick+(sensory[i]?0:p.refractory_ticks); }
    trace_v[i]=v[i];trace_e[i]=ge[i];trace_i[i]=gi[i];
    trace_spikes[i]=uint8_t(emitted[i]);
}
}

namespace {
template<class T> void append(std::vector<uint8_t>& out,const T* values,size_t count) {
    if(!count) return;
    const auto* p=reinterpret_cast<const uint8_t*>(values);
    out.insert(out.end(),p,p+count*sizeof(T));
}
template<class T> void append_vector(std::vector<uint8_t>& out,const std::vector<T>& v) {
    append(out,v.data(),v.size());
}
uint64_t payload_checksum(const uint8_t* data,size_t size) {
    // Noncryptographic transport corruption detector. HF SHA-256 is authoritative.
    uint64_t value=14695981039346656037ull;
    for(size_t i=0;i<size;++i) { value^=data[i];value*=1099511628211ull; }
    return value;
}
template<class T> std::vector<T> consume(const uint8_t*& at,size_t count) {
    std::vector<T> result(count);
    if(count) std::memcpy(result.data(),at,count*sizeof(T));
    at+=count*sizeof(T);return result;
}
}

struct fc_model {
    uint32_t n,cap;
    uint64_t edges,tick=0;
    fc_params p;
    double synapse_decay;
    bool invalid_state=true;
    Buffer<uint32_t> numerical_error;
    Buffer<uint64_t> row,col,next;
    Buffer<uint8_t> sensory,allowed,trace_spikes;
    Buffer<double> we,wi,v,ge,gi,ring,in_e,in_i,direct,trace_v,trace_e,trace_i;
    cusparseHandle_t sparse=nullptr;
    cusparseSpMatDescr_t mat_e=nullptr,mat_i=nullptr;
    cusparseDnVecDescr_t x=nullptr,y_e=nullptr,y_i=nullptr;
    std::unique_ptr<Buffer<uint8_t>> scratch;
    std::unique_ptr<Buffer<double>> release_u, release_decay, release_eff, release_resource;
    fc_model(uint32_t count,uint64_t edge_count,const uint64_t* indptr,const uint32_t* indices,
             const double* excitatory,const double* inhibitory,const uint8_t* sense,
             fc_params params,uint32_t capacity):
        n(count),cap(capacity),edges(edge_count),p(params),
        synapse_decay(std::exp(-params.dt_ms/params.synapse_ms)),
        numerical_error(1),
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
        invalid_state=true;
        check(cudaMemset(numerical_error.data,0,sizeof(uint32_t)));
        check(cudaMemset(ring.data,0,size_t(n)*(p.delay_ticks+1)*sizeof(double)));
        check(cudaMemset(in_e.data,0,size_t(n)*sizeof(double)));
        check(cudaMemset(in_i.data,0,size_t(n)*sizeof(double)));
        reset_state<<<(n+255)/256,256>>>(n,p.rest_mv,v.data,ge.data,gi.data,next.data);
        check(cudaGetLastError());check(cudaDeviceSynchronize());
        if(release_resource) {
            std::vector<double> initial(edges,1.0);
            release_resource->upload(initial.data(),edges);
        }
        tick=0;invalid_state=false;
    }
    std::vector<uint8_t> configuration_identity() const {
        std::vector<uint8_t> out;
        const uint64_t magic=0x4643525354415431ull;
        const uint32_t version=1,endian=0x01020304,release=release_resource?1:0;
        append(out,&magic,1);append(out,&version,1);append(out,&endian,1);
        append(out,&n,1);append(out,&edges,1);append(out,&release,1);
        const double params[]={p.dt_ms,p.rest_mv,p.reset_mv,p.threshold_mv,p.membrane_ms,
            p.synapse_ms,p.reversal_exc_mv,p.reversal_inh_mv};
        append(out,params,8);append(out,&p.refractory_ticks,1);append(out,&p.delay_ticks,1);
        append_vector(out,row.download(size_t(n)+1));append_vector(out,col.download(edges));
        append_vector(out,we.download(edges));append_vector(out,wi.download(edges));
        append_vector(out,sensory.download(n));
        if(release) {
            append_vector(out,release_u->download(edges));
            append_vector(out,release_decay->download(edges));
            append_vector(out,release_eff->download(edges));
        }
        return out;
    }
    uint64_t state_bytes() const {
        // Configuration plus mutable state, with fixed-width length/tick/checksum.
        const uint64_t config=104+8*(uint64_t(n)+1)+24*edges+n+(release_resource?24*edges:0);
        return 8+config+8+32*uint64_t(n)+8*uint64_t(n)*(p.delay_ticks+1)
            +(release_resource?8*edges:0)+8;
    }
    std::vector<uint8_t> save_state() const {
        require(!invalid_state,"cannot save invalid model");check(cudaDeviceSynchronize());
        auto identity=configuration_identity();const uint64_t length=identity.size();
        std::vector<uint8_t> out;append(out,&length,1);append_vector(out,identity);append(out,&tick,1);
        append_vector(out,v.download(n));append_vector(out,ge.download(n));
        append_vector(out,gi.download(n));append_vector(out,next.download(n));
        append_vector(out,ring.download(size_t(n)*(p.delay_ticks+1)));
        if(release_resource) append_vector(out,release_resource->download(edges));
        const uint64_t checksum=payload_checksum(out.data(),out.size());append(out,&checksum,1);
        require(out.size()==state_bytes(),"checkpoint size accounting failed");return out;
    }
    void load_state(const uint8_t* bytes,uint64_t size) {
        require(!invalid_state,"reset invalid model before checkpoint restore");
        require(size==state_bytes(),"checkpoint byte count mismatch");
        uint64_t stored=0;std::memcpy(&stored,bytes+size-8,8);
        require(stored==payload_checksum(bytes,size-8),"checkpoint checksum mismatch");
        auto identity=configuration_identity();uint64_t length=0;std::memcpy(&length,bytes,8);
        require(length==identity.size(),"checkpoint identity length mismatch");
        require(std::memcmp(bytes+8,identity.data(),identity.size())==0,
            "checkpoint graph, parameters or numerical semantics mismatch");
        const uint8_t* at=bytes+8+identity.size();
        const uint64_t restored_tick=consume<uint64_t>(at,1)[0];
        auto rv=consume<double>(at,n),re=consume<double>(at,n),ri=consume<double>(at,n);
        auto rn=consume<uint64_t>(at,n);auto rr=consume<double>(at,size_t(n)*(p.delay_ticks+1));
        std::vector<double> resource;
        if(release_resource) resource=consume<double>(at,edges);
        for(uint32_t i=0;i<n;++i) require(std::isfinite(rv[i]) && std::isfinite(re[i]) &&
            std::isfinite(ri[i]) && re[i]>=0 && ri[i]>=0,"invalid checkpoint neural state");
        for(double value:rr) require(value==0.0 || value==1.0,"invalid checkpoint delay ring");
        for(double value:resource) require(std::isfinite(value) && value>=0 && value<=1,
            "invalid checkpoint release resource");
        // Validate every host byte before mutation. Device failures invalidate the handle.
        invalid_state=true;
        v.upload(rv.data(),n);ge.upload(re.data(),n);gi.upload(ri.data(),n);
        next.upload(rn.data(),n);ring.upload(rr.data(),rr.size());
        if(release_resource) release_resource->upload(resource.data(),edges);
        check(cudaMemset(numerical_error.data,0,sizeof(uint32_t)));
        check(cudaDeviceSynchronize());tick=restored_tick;invalid_state=false;
    }
    void configure_release(const double* u,const double* recovery_ms,const double* efficacy) {
        require(!invalid_state && tick==0,"configure release only on valid reset state");
        require(u && recovery_ms && efficacy,"null release parameters");
        std::vector<double> decay(edges), initial(edges,1.0);
        for(uint64_t k=0;k<edges;++k) {
            require(std::isfinite(u[k]) && u[k]>=0.0 && u[k]<=1.0,
                    "release utilization outside [0,1]");
            require(std::isfinite(recovery_ms[k]) && recovery_ms[k]>0.0,
                    "invalid release recovery time");
            require(std::isfinite(efficacy[k]) && efficacy[k]>=0.0,
                    "invalid postsynaptic efficacy");
            decay[k]=std::exp(-p.dt_ms/recovery_ms[k]);
        }
        auto nu=std::make_unique<Buffer<double>>(edges);
        auto nd=std::make_unique<Buffer<double>>(edges);
        auto ne=std::make_unique<Buffer<double>>(edges);
        auto nr=std::make_unique<Buffer<double>>(edges);
        nu->upload(u,edges);nd->upload(decay.data(),edges);
        ne->upload(efficacy,edges);nr->upload(initial.data(),edges);
        release_u=std::move(nu);release_decay=std::move(nd);
        release_eff=std::move(ne);release_resource=std::move(nr);
    }
    void advance(uint32_t ticks,const double* input,double* output_v,double* output_e,
                 double* output_i,uint8_t* output_spikes) {
        require(!invalid_state,"model state invalid; explicit reset required");
        require(ticks>0 && ticks<=cap,"invalid tick count");
        require(tick<=std::numeric_limits<uint64_t>::max()-ticks-p.refractory_ticks,
            "tick clock overflow");
        for(size_t i=0;i<size_t(n)*ticks;++i) require(std::isfinite(input[i]),"nonfinite direct drive");
        // Any runtime failure after mutation requires an explicit reset.
        invalid_state=true;
        direct.upload(input,size_t(n)*ticks);
        const double alpha=1,beta=0;
        for(uint32_t step=0;step<ticks;++step,++tick) {
            double* fired=ring.data+(tick%(p.delay_ticks+1))*n;
            double* delayed=ring.data+((tick+1)%(p.delay_ticks+1))*n;
            integrate<<<(n+255)/256,256>>>(n,tick,p,synapse_decay,v.data,ge.data,gi.data,
                                           next.data,fired,allowed.data,numerical_error.data);
            check(cudaGetLastError());
            if(release_resource) {
                release_incoming<<<(n+255)/256,256>>>(n,row.data,col.data,delayed,
                    we.data,wi.data,release_u->data,release_decay->data,release_eff->data,
                    release_resource->data,in_e.data,in_i.data);
                check(cudaGetLastError());
            } else {
            check(cusparseDnVecSetValues(x,delayed));
            check(cusparseSpMV(sparse,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,
                  mat_e,x,&beta,y_e,CUDA_R_64F,CUSPARSE_SPMV_CSR_ALG2,scratch->data));
            check(cusparseSpMV(sparse,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,
                  mat_i,x,&beta,y_i,CUDA_R_64F,CUSPARSE_SPMV_CSR_ALG2,scratch->data));
            }
            const size_t offset=size_t(step)*n;
            finish<<<(n+255)/256,256>>>(n,tick,p,direct.data+offset,in_e.data,in_i.data,
                                        fired,sensory.data,allowed.data,v.data,ge.data,gi.data,next.data,
                                        trace_v.data+offset,trace_e.data+offset,trace_i.data+offset,
                                        trace_spikes.data+offset,numerical_error.data);
            check(cudaGetLastError());
        }
        check(cudaDeviceSynchronize());
        uint32_t error=0;
        check(cudaMemcpy(&error,numerical_error.data,sizeof(error),cudaMemcpyDeviceToHost));
        require(error==0,"nonfinite neural state; explicit reset required");
        const size_t total=size_t(n)*ticks;
        check(cudaMemcpy(output_v,trace_v.data,total*sizeof(double),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(output_e,trace_e.data,total*sizeof(double),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(output_i,trace_i.data,total*sizeof(double),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(output_spikes,trace_spikes.data,total,cudaMemcpyDeviceToHost));
        invalid_state=false;
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

EXPORT int fc_configure_release(fc_model* model,const double* utilization,
    const double* recovery_ms,const double* efficacy) {
    try {
        require(model,"null model");
        model->configure_release(utilization,recovery_ms,efficacy);
        last_error.clear();return 0;
    } catch(const std::exception& e) { last_error=e.what();return -1; }
}

EXPORT uint64_t fc_state_bytes(fc_model* model) {
    try { require(model,"null model");last_error.clear();return model->state_bytes(); }
    catch(const std::exception& e) { last_error=e.what();return 0; }
}
EXPORT int fc_save_state(fc_model* model,uint8_t* bytes,uint64_t size) {
    try {
        require(model && bytes,"null checkpoint output");require(size==model->state_bytes(),"checkpoint output size mismatch");
        auto state=model->save_state();std::memcpy(bytes,state.data(),state.size());last_error.clear();return 0;
    } catch(const std::exception& e) { last_error=e.what();return -1; }
}
EXPORT int fc_load_state(fc_model* model,const uint8_t* bytes,uint64_t size) {
    try { require(model && bytes,"null checkpoint input");model->load_state(bytes,size);last_error.clear();return 0; }
    catch(const std::exception& e) { last_error=e.what();return -1; }
}
