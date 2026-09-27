// Real-memory RNG screening only. No VisTrans reaction equations here.
#include <cuda_runtime.h>
#include <curand_kernel.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <vector>

static constexpr int N=3377*30000;
static constexpr int GRID=8192;
static constexpr int BLOCK=256;
static constexpr float EXTRA=0.03f;
static_assert(sizeof(curandStateXORWOW_t)==48);
static_assert(sizeof(uint4)==16);

static void checked(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}

__global__ void initialize(uint4* state_a,uint4* state_b,unsigned short* owner,
                           curandStateXORWOW_t* rng,int n,uint64_t seed) {
    for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x) {
        uint4 value=make_uint4(uint32_t(i),~uint32_t(i),uint32_t(i*3u),1u);
        state_a[i]=value;state_b[i]=value;
        owner[i]=i/30000;
        curand_init(seed,i,0,rng+i);
    }
}

__global__ void xorwow_step(uint4* state,const unsigned short* owner,
                            curandStateXORWOW_t* rng,int n) {
    for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x) {
        curandStateXORWOW_t local=rng[i];
        uint4 value=state[i];
        const float u=curand_uniform(&local);
        value.x+=__float_as_uint(u);
        if(u<EXTRA) {
            value.y+=__float_as_uint(curand_uniform(&local));
            value.z+=__float_as_uint(curand_uniform(&local));
            ++value.w;
        }
        value.w+=owner[i];
        state[i]=value;
        rng[i]=local;
    }
}

__global__ void philox_step(uint4* state,const unsigned short* owner,int n,
                            uint64_t seed,uint64_t tick) {
    const uint2 key=make_uint2(uint32_t(seed),uint32_t(seed>>32));
    for(int i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x) {
        const uint4 counter=make_uint4(uint32_t(i),uint32_t(tick),uint32_t(tick>>32),0);
        const uint4 draws=curand_Philox4x32_10(counter,key);
        const float u=_curand_uniform(draws.x);
        uint4 value=state[i];
        value.x+=__float_as_uint(u);
        if(u<EXTRA) {
            value.y+=__float_as_uint(_curand_uniform(draws.y));
            value.z+=__float_as_uint(_curand_uniform(draws.z));
            ++value.w;
        }
        value.w+=owner[i];
        state[i]=value;
    }
}

__global__ void checksum(const uint4* state,uint64_t* partial,int n) {
    __shared__ uint64_t sums[BLOCK];
    const int tid=threadIdx.x;
    uint64_t value=0;
    for(int i=blockIdx.x*blockDim.x+tid;i<n;i+=gridDim.x*blockDim.x) {
        const uint4 x=state[i];
        value+=uint64_t(x.x)+x.y+x.z+x.w;
    }
    sums[tid]=value;__syncthreads();
    for(int step=BLOCK/2;step;step>>=1) {
        if(tid<step)sums[tid]+=sums[tid+step];
        __syncthreads();
    }
    if(!tid)partial[blockIdx.x]=sums[0];
}

static double median(std::vector<float> values) {
    std::sort(values.begin(),values.end());
    return values[values.size()/2];
}

int main(int argc,char** argv) {
 try {
    if(argc!=2)throw std::runtime_error("usage: seed");
    const uint64_t seed=std::strtoull(argv[1],nullptr,10);
    uint4 *a=nullptr,*b=nullptr;
    unsigned short* owner=nullptr;
    curandStateXORWOW_t* rng=nullptr;
    uint64_t* partial=nullptr;
    checked(cudaMalloc(&a,size_t(N)*sizeof(uint4)));
    checked(cudaMalloc(&b,size_t(N)*sizeof(uint4)));
    checked(cudaMalloc(&owner,size_t(N)*sizeof(unsigned short)));
    checked(cudaMalloc(&rng,size_t(N)*sizeof(curandStateXORWOW_t)));
    checked(cudaMalloc(&partial,GRID*sizeof(uint64_t)));
    initialize<<<GRID,BLOCK>>>(a,b,owner,rng,N,seed);
    checked(cudaGetLastError());checked(cudaDeviceSynchronize());
    uint64_t tick=0;
    for(int i=0;i<10;++i) {
        xorwow_step<<<GRID,BLOCK>>>(a,owner,rng,N);
        philox_step<<<GRID,BLOCK>>>(b,owner,N,seed,tick++);
    }
    checked(cudaGetLastError());checked(cudaDeviceSynchronize());
    cudaEvent_t start,stop;
    checked(cudaEventCreate(&start));checked(cudaEventCreate(&stop));
    std::vector<float> xor_times,philox_times;
    for(int rep=0;rep<3;++rep) {
        for(int order=0;order<2;++order) {
            const bool philox=(rep+order)%2!=0;
            checked(cudaEventRecord(start));
            for(int step=0;step<100;++step) {
                if(philox)philox_step<<<GRID,BLOCK>>>(b,owner,N,seed,tick++);
                else xorwow_step<<<GRID,BLOCK>>>(a,owner,rng,N);
            }
            checked(cudaGetLastError());
            checked(cudaEventRecord(stop));checked(cudaEventSynchronize(stop));
            float ms=0;checked(cudaEventElapsedTime(&ms,start,stop));
            (philox?philox_times:xor_times).push_back(ms);
            std::printf("RNG_SCREEN_RUN method=%s rep=%d ms=%.6f\n",philox?"philox":"xorwow",rep,ms);
        }
    }
    auto sum_state=[&](const uint4* state) {
        checksum<<<GRID,BLOCK>>>(state,partial,N);
        checked(cudaGetLastError());
        std::vector<uint64_t> host(GRID);
        checked(cudaMemcpy(host.data(),partial,GRID*sizeof(uint64_t),cudaMemcpyDeviceToHost));
        uint64_t total=0;for(uint64_t v:host)total+=v;
        return total;
    };
    const uint64_t xa=sum_state(a),pb=sum_state(b);
    std::printf("RNG_SCREEN_RESULT n=%d ticks=100 repeats=3 xorwow_median_ms=%.6f philox_median_ms=%.6f xorwow_checksum=%llu philox_checksum=%llu\n",
                N,median(xor_times),median(philox_times),
                (unsigned long long)xa,(unsigned long long)pb);
    checked(cudaEventDestroy(start));checked(cudaEventDestroy(stop));
    checked(cudaFree(a));checked(cudaFree(b));checked(cudaFree(owner));
    checked(cudaFree(rng));checked(cudaFree(partial));
    if(!xa||!pb)throw std::runtime_error("zero checksum");
    return 0;
 } catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
