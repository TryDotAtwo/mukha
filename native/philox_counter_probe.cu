// Compile-only/runtime mapping oracle, not a retina kernel.
#include <cuda_runtime.h>
#include <curand_kernel.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>

struct Output {uint4 raw;uint4 uniform_bits;};

__global__ void vector(Output* out,uint64_t seed,uint32_t id,uint64_t tick,uint32_t block) {
    const uint4 ctr=make_uint4(id,uint32_t(tick),uint32_t(tick>>32),block);
    const uint2 key=make_uint2(uint32_t(seed),uint32_t(seed>>32));
    Output value{};
    value.raw=curand_Philox4x32_10(ctr,key);
    value.uniform_bits=make_uint4(__float_as_uint(_curand_uniform(value.raw.x)),
                                  __float_as_uint(_curand_uniform(value.raw.y)),
                                  __float_as_uint(_curand_uniform(value.raw.z)),
                                  __float_as_uint(_curand_uniform(value.raw.w)));
    *out=value;
}

static void checked(cudaError_t e) {if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
int main(int argc,char** argv) {
 try {
    if(argc!=5)throw std::runtime_error("usage: seed id tick block");
    const uint64_t seed=std::strtoull(argv[1],nullptr,10);
    const uint64_t id64=std::strtoull(argv[2],nullptr,10);
    const uint64_t tick=std::strtoull(argv[3],nullptr,10);
    const uint64_t block64=std::strtoull(argv[4],nullptr,10);
    if(id64>UINT32_MAX||block64>UINT32_MAX)throw std::runtime_error("range");
    Output* output=nullptr;
    checked(cudaMalloc(&output,sizeof(Output)));
    vector<<<1,1>>>(output,seed,uint32_t(id64),tick,uint32_t(block64));
    checked(cudaGetLastError());
    Output host{};checked(cudaMemcpy(&host,output,sizeof(host),cudaMemcpyDeviceToHost));
    std::printf("%u %u %u %u %u %u %u %u\n",
                host.raw.x,host.raw.y,host.raw.z,host.raw.w,
                host.uniform_bits.x,host.uniform_bits.y,host.uniform_bits.z,host.uniform_bits.w);
    checked(cudaFree(output));
    return 0;
 } catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
