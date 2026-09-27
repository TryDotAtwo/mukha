#include "photon.h"
#include <cuda_runtime.h>
#include <cmath>
#include <climits>
#include <cfloat>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>
#include <algorithm>
#include <array>
#include <cstring>
#include "../build/photon_build_id.h"
#define FF_ENTITY_RNG 1
#include "phototransduction_safe.cuh"
#undef BLOCK_SIZE
#include "photocurrent_safe.cuh"
#include "../build/photoreceptor_author_hh.cu"
#undef C
#include "../build/photoreceptor_author_adaptation.cu"

namespace {
static_assert(sizeof(FP_BUILD_ID)==65,"Expected SHA-256 build fingerprint");
constexpr size_t snapshot_words=16, snapshot_header_bytes=16*8+64;
constexpr uint64_t snapshot_magic=0x32504e534e435046ull;
// FNV-1a includes metadata and payload, excluding only its own checksum field.
// Accidental corruption detection, not authentication of hostile input.
uint64_t checksum(const unsigned char* bytes,size_t n) {
    uint64_t value=14695981039346656037ull;
    for(size_t i=0;i<n;++i) if(i<11*8 || i>=12*8) { value^=bytes[i]; value*=1099511628211ull; }
    return value;
}
void check(cudaError_t e) { if(e!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(e)); }
template<class T> struct DeviceArray {
    T* p=nullptr;
    explicit DeviceArray(size_t n) { check(cudaMalloc(&p,n*sizeof(T))); }
    ~DeviceArray() { if(p) cudaFree(p); }
    DeviceArray(const DeviceArray&)=delete;
    DeviceArray& operator=(const DeviceArray&)=delete;
};
template<class T> void upload(T* to,const T* from,size_t n) {
    check(cudaMemcpy(to,from,n*sizeof(T),cudaMemcpyHostToDevice));
}
__global__ void reset_microvilli(ushort2* x0,unsigned short* owner,
                                curandStateXORWOW_t* rng,int total,int m,
                                unsigned long long seed) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<total) { x0[i]=make_ushort2(50,0); owner[i]=i/m; curand_init(seed,i,0,rng+i); }
}
struct Model {
    int n,m,total,device,blocks,compute_capability=0;
    uint64_t tick=0,episode_seed=0;
    bool healthy=false;
    DeviceArray<ushort2> x0,x1,x2;
    DeviceArray<unsigned short> x3,owner;
    DeviceArray<int> counts,offsets,counter;
    DeviceArray<double> state,current,feedback;
    DeviceArray<curandStateXORWOW_t> rng;
    std::vector<double> host;
    Model(int n_,int m_,int device_,int blocks_,uint64_t seed)
        : n(n_),m(m_),total(n_*m_),device(device_),blocks(blocks_),
          x0(total),x1(total),x2(total),x3(total),owner(total),
          counts(n),offsets(n),counter(1),state(9*n),current(n),feedback(n),rng(total),host(9*n) {
        cudaDeviceProp properties{}; check(cudaGetDeviceProperties(&properties,device));
        compute_capability=100*properties.major+properties.minor;
        long long addresses[5]={(long long)x0.p,(long long)x1.p,(long long)x2.p,
                                (long long)x3.p,(long long)owner.p};
        check(cudaMemcpyToSymbol(d_X,addresses,sizeof(addresses)));
        int a[14]={0,0,1,2,2,1,4,3,4,4,6,5,5,0};
        int b[14]={0,0,2,3,0,0,0,0,0,6,0,0,0,0};
        int c[14]={0,-1,-1,-1,-1,1,1,-1,-1,-2,-1,1,-1,1};
        int d[14]={0,0,1,1,0,0,0,0,0,1,0,0,0,0};
        check(cudaMemcpyToSymbol(change_ind1,a,sizeof(a)));
        check(cudaMemcpyToSymbol(change_ind2,b,sizeof(b)));
        check(cudaMemcpyToSymbol(change1,c,sizeof(c)));
        check(cudaMemcpyToSymbol(change2,d,sizeof(d)));
        std::vector<int> count(n,m),off(n);
        for(int i=0;i<n;++i) off[i]=i*m;
        upload(counts.p,count.data(),n); upload(offsets.p,off.data(),n);
        reset(seed);
    }
    void reset(uint64_t seed) {
        healthy=false;
        check(cudaSetDevice(device));
        // Make opaque RNG padding deterministic as well as the initialized fields.
        check(cudaMemset(rng.p,0,size_t(total)*sizeof(curandStateXORWOW_t)));
        reset_microvilli<<<(total+127ll)/128,128>>>(x0.p,owner.p,rng.p,total,m,seed);
        check(cudaGetLastError());
        check(cudaMemset(x1.p,0,total*sizeof(ushort2)));
        check(cudaMemset(x2.p,0,total*sizeof(ushort2)));
        check(cudaMemset(x3.p,0,total*sizeof(unsigned short)));
        check(cudaMemset(feedback.p,0,n*sizeof(double)));
        check(cudaMemset(current.p,0,n*sizeof(double)));
        check(cudaMemset(counter.p,0,sizeof(int)));
        std::fill(host.begin(),host.end(),0.);
        const double baseline[7]={-81.9925,.2184,.9653,.0117,.9998,.0017,1};
        for(int j=0;j<7;++j) for(int i=0;i<n;++i) host[j*n+i]=baseline[j];
        upload(state.p,host.data(),host.size());
        check(cudaDeviceSynchronize());
        tick=0; episode_seed=seed; healthy=true;
    }
    void advance(const double* rates,uint32_t ticks) {
        healthy=false;
        check(cudaSetDevice(device));
        upload(state.p+7*n,rates,n);
        for(uint32_t step=0;step<ticks;++step) {
            check(cudaMemset(counter.p,0,sizeof(int)));
            transduction<<<blocks,128>>>(rng.p,1e-4f,state.p,state.p+6*n,state.p+7*n,
                                          counts.p,total,counter.p);
            check(cudaGetLastError()); check(cudaDeviceSynchronize());
            sum_current<<<n,256>>>(x2.p,counts.p,offsets.p,state.p,current.p,feedback.p);
            check(cudaGetLastError());
            hh<<<(n+31)/32,32>>>(current.p,state.p,state.p+n,state.p+2*n,state.p+3*n,
                                state.p+4*n,state.p+5*n,n,1e-5,10);
            check(cudaGetLastError());
            update_ns<<<(n+127)/128,128>>>(state.p+6*n,n,state.p,1e-4);
            check(cudaGetLastError());
            check(cudaMemcpy(host.data(),state.p,host.size()*sizeof(double),cudaMemcpyDeviceToHost));
            for(int i=0;i<7*n;++i) if(!std::isfinite(host[i]))
                throw std::runtime_error("Nonfinite photoreceptor state");
            for(int i=n;i<6*n;++i) if(host[i]<0 || host[i]>1)
                throw std::runtime_error("Photoreceptor gate outside [0,1]");
            ++tick;
        }
        healthy=true;
    }
    void set_feedback(const double* input,size_t count) {
        if(!input || count!=size_t(n)) throw std::invalid_argument("Feedback population size mismatch");
        for(size_t i=0;i<count;++i) if(!std::isfinite(input[i]))
            throw std::invalid_argument("Feedback current must be finite");
        healthy=false;
        check(cudaSetDevice(device));
        upload(feedback.p,input,count);
        healthy=true;
    }
    struct Piece { void* pointer; size_t bytes; };
    std::array<Piece,7> pieces() const {
        return {{{x0.p,size_t(total)*sizeof(ushort2)},
                 {x1.p,size_t(total)*sizeof(ushort2)},
                 {x2.p,size_t(total)*sizeof(ushort2)},
                 {x3.p,size_t(total)*sizeof(unsigned short)},
                 {state.p,size_t(n)*9*sizeof(double)},
                 {rng.p,size_t(total)*sizeof(curandStateXORWOW_t)},
                 {feedback.p,size_t(n)*sizeof(double)}}};
    }
    size_t checkpoint_size() const {
        size_t bytes=snapshot_header_bytes;
        for(const auto& piece:pieces()) bytes+=piece.bytes;
        return bytes;
    }
    void save(unsigned char* output,size_t bytes) {
        if(!output || bytes!=checkpoint_size()) throw std::invalid_argument("Checkpoint output size mismatch");
        std::array<uint64_t,snapshot_words> header={snapshot_magic,1,uint64_t(n),uint64_t(m),
            uint64_t(blocks),sizeof(curandStateXORWOW_t),CUDART_VERSION,uint64_t(compute_capability),
            tick,episode_seed,bytes-snapshot_header_bytes,0,snapshot_header_bytes,0,0,0};
        std::memcpy(output,header.data(),sizeof(header));
        std::memcpy(output+sizeof(header),FP_BUILD_ID,64);
        try {
            check(cudaSetDevice(device));
            size_t offset=snapshot_header_bytes;
            for(const auto& piece:pieces()) {
                check(cudaMemcpy(output+offset,piece.pointer,piece.bytes,cudaMemcpyDeviceToHost));
                offset+=piece.bytes;
            }
        } catch(...) { healthy=false; throw; }
        header[11]=checksum(output,bytes);
        std::memcpy(output+11*8,&header[11],8);
    }
    void load(const unsigned char* input,size_t bytes) {
        if(!input || bytes!=checkpoint_size()) throw std::invalid_argument("Checkpoint input size mismatch");
        std::array<uint64_t,snapshot_words> header{};
        std::memcpy(header.data(),input,sizeof(header));
        if(header[0]!=snapshot_magic || header[1]!=1 || header[2]!=uint64_t(n) ||
           header[3]!=uint64_t(m) || header[4]!=uint64_t(blocks) ||
           header[5]!=sizeof(curandStateXORWOW_t) || header[6]!=CUDART_VERSION ||
           header[7]!=uint64_t(compute_capability) || header[10]!=bytes-snapshot_header_bytes ||
           header[12]!=snapshot_header_bytes || header[13] || header[14] || header[15] ||
           std::memcmp(input+sizeof(header),FP_BUILD_ID,64)!=0)
            throw std::invalid_argument("Checkpoint build/configuration mismatch");
        if(checksum(input,bytes)!=header[11]) throw std::invalid_argument("Checkpoint checksum mismatch");
        // Validate floating observations before touching either host cache or GPU.
        const size_t state_offset=snapshot_header_bytes+size_t(total)*14;
        for(int i=0;i<9*n;++i) {
            double value; std::memcpy(&value,input+state_offset+size_t(i)*8,8);
            if(!std::isfinite(value) || (i>=n && i<6*n && (value<0 || value>1)) ||
               (i>=7*n && i<8*n && (value<0 || value/m>FLT_MAX)))
                throw std::invalid_argument("Checkpoint contains invalid receptor state");
        }
        for(int i=0;i<n;++i) {
            double value; std::memcpy(&value,input+bytes-size_t(n)*8+size_t(i)*8,8);
            if(!std::isfinite(value)) throw std::invalid_argument("Checkpoint contains invalid feedback");
        }
        healthy=false;
        check(cudaSetDevice(device));
        size_t offset=snapshot_header_bytes;
        for(const auto& piece:pieces()) {
            check(cudaMemcpy(piece.pointer,input+offset,piece.bytes,cudaMemcpyHostToDevice));
            offset+=piece.bytes;
        }
        // Scratch arrays are overwritten before use; fixed owner/count/offset
        // arrays are derived from the checked dimensions during construction.
        check(cudaMemset(counter.p,0,sizeof(int)));
        check(cudaMemset(current.p,0,size_t(n)*sizeof(double)));
        check(cudaDeviceSynchronize());
        std::memcpy(host.data(),input+state_offset,host.size()*sizeof(double));
        tick=header[8]; episode_seed=header[9]; healthy=true;
    }
};
std::mutex api_mutex;
Model* live=nullptr;
thread_local std::string error;
Model& validate(void* raw,bool require_healthy=true) {
    if(!raw || raw!=live) throw std::invalid_argument("Invalid photoreceptor handle");
    if(require_healthy && !live->healthy) throw std::runtime_error("Model needs reset after execution failure");
    return *live;
}
}
extern "C" {
void* fp_create(uint32_t n,uint32_t m,uint64_t seed,uint32_t blocks) {
    std::lock_guard<std::mutex> lock(api_mutex); error.clear();
    try {
        if(live) throw std::runtime_error("Only one photoreceptor instance is supported");
        // Queue atomics take one terminal claim per warp as well as live claims.
        // Reserve headroom so start+lane and the final counter cannot overflow.
        if(!n || n>65535 || !m || !blocks || blocks>65535 ||
           uint64_t(n)*m+uint64_t(blocks)*128+64>INT_MAX)
            throw std::invalid_argument("Invalid population or launch dimensions");
        int device; check(cudaGetDevice(&device));
        live=new Model(n,m,device,blocks,seed); return live;
    } catch(const std::exception& e) { error=e.what(); return nullptr; }
}
void fp_destroy(void* raw) {
    std::lock_guard<std::mutex> lock(api_mutex);
    if(raw && raw==live) { cudaSetDevice(live->device); delete live; live=nullptr; }
}
int fp_reset(void* raw,uint64_t seed) {
    std::lock_guard<std::mutex> lock(api_mutex); error.clear();
    try { validate(raw,false).reset(seed); return 0; }
    catch(const std::exception& e) { error=e.what(); return -1; }
}
int fp_advance(void* raw,const double* rates,size_t count,uint32_t ticks) {
    std::lock_guard<std::mutex> lock(api_mutex); error.clear();
    try {
        Model& model=validate(raw);
        if(!rates || count!=size_t(model.n) || !ticks || ticks>10000 ||
           model.tick>UINT64_MAX-ticks) throw std::invalid_argument("Invalid input shape or tick count");
        for(size_t i=0;i<count;++i)
            if(!std::isfinite(rates[i]) || rates[i]<0 || rates[i]/model.m>FLT_MAX)
                throw std::invalid_argument("Photon rates must be finite, nonnegative and representable");
        model.advance(rates,ticks); return 0;
    } catch(const std::exception& e) { error=e.what(); return -1; }
}
int fp_observe(void* raw,double* state,size_t count,uint64_t* tick) {
    std::lock_guard<std::mutex> lock(api_mutex); error.clear();
    try {
        Model& model=validate(raw);
        if(!state || !tick || count!=model.host.size()) throw std::invalid_argument("Invalid observation buffers");
        std::copy(model.host.begin(),model.host.end(),state); *tick=model.tick; return 0;
    } catch(const std::exception& e) { error=e.what(); return -1; }
}
int fp_set_neural_feedback(void* raw,const double* current,size_t count) {
    std::lock_guard<std::mutex> lock(api_mutex); error.clear();
    try { validate(raw).set_feedback(current,count); return 0; }
    catch(const std::exception& e) { error=e.what(); return -1; }
}
size_t fp_checkpoint_size(void* raw) {
    std::lock_guard<std::mutex> lock(api_mutex); error.clear();
    try { return validate(raw).checkpoint_size(); }
    catch(const std::exception& e) { error=e.what(); return 0; }
}
int fp_save(void* raw,unsigned char* output,size_t bytes) {
    std::lock_guard<std::mutex> lock(api_mutex); error.clear();
    try { validate(raw).save(output,bytes); return 0; }
    catch(const std::exception& e) { error=e.what(); return -1; }
}
int fp_load(void* raw,const unsigned char* input,size_t bytes) {
    std::lock_guard<std::mutex> lock(api_mutex); error.clear();
    try { validate(raw).load(input,bytes); return 0; }
    catch(const std::exception& e) { error=e.what(); return -1; }
}
const char* fp_build_identity() { return FP_BUILD_ID; }
const char* fp_last_error() { return error.c_str(); }
}
