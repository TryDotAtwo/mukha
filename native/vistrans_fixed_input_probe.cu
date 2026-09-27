// Fixed-input diagnostic using the unchanged native VisTrans reaction kernel.
// This is an experimental distribution oracle, not a production retina.
#include <cuda_runtime.h>
#include <curand_kernel.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <stdexcept>
#include <vector>

#define FF_ENTITY_RNG 1
#include "phototransduction_safe.cuh"

static void checked(cudaError_t error) {
    if(error!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(error));
}

template<class T> struct Buffer {
    T* p=nullptr;
    explicit Buffer(size_t n) { checked(cudaMalloc(&p,n*sizeof(T))); }
    ~Buffer(){ if(p) cudaFree(p); }
    Buffer(const Buffer&)=delete;
    Buffer& operator=(const Buffer&)=delete;
};

__global__ void initialize(ushort2* x0,unsigned short* owner,
                           curandStateXORWOW_t* rng,int total,int m,uint64_t seed) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<total) {
        x0[i]=make_ushort2(50,0);
        owner[i]=i/m;
        curand_init(seed,i,0,rng+i);
    }
}

int main(int argc,char** argv) {
  try {
    if(argc!=6) throw std::runtime_error("usage: probe rows.bin receptors microvilli ticks seed");
    const int n=std::atoi(argv[2]),m=std::atoi(argv[3]),ticks=std::atoi(argv[4]);
    const uint64_t seed=std::strtoull(argv[5],nullptr,10);
    if(n<=0||n>65535||m<=0||ticks<=0||ticks>10000||uint64_t(n)*m>INT32_MAX)
        throw std::runtime_error("dimensions");
    const int total=n*m;
    Buffer<ushort2> x0(total),x1(total),x2(total);
    Buffer<unsigned short> x3(total),owner(total);
    Buffer<curandStateXORWOW_t> rng(total);
    Buffer<double> vm(n),ns(n),rate(n);
    Buffer<int> counts(n),counter(1);
    checked(cudaMemset(x1.p,0,total*sizeof(ushort2)));
    checked(cudaMemset(x2.p,0,total*sizeof(ushort2)));
    checked(cudaMemset(x3.p,0,total*sizeof(unsigned short)));
    initialize<<<(total+127)/128,128>>>(x0.p,owner.p,rng.p,total,m,seed);
    checked(cudaGetLastError());
    long long addresses[5]={(long long)x0.p,(long long)x1.p,(long long)x2.p,
                            (long long)x3.p,(long long)owner.p};
    checked(cudaMemcpyToSymbol(d_X,addresses,sizeof(addresses)));
    int a[14]={0,0,1,2,2,1,4,3,4,4,6,5,5,0};
    int b[14]={0,0,2,3,0,0,0,0,0,6,0,0,0,0};
    int c[14]={0,-1,-1,-1,-1,1,1,-1,-1,-2,-1,1,-1,1};
    int d[14]={0,0,1,1,0,0,0,0,0,1,0,0,0,0};
    checked(cudaMemcpyToSymbol(change_ind1,a,sizeof(a)));
    checked(cudaMemcpyToSymbol(change_ind2,b,sizeof(b)));
    checked(cudaMemcpyToSymbol(change1,c,sizeof(c)));
    checked(cudaMemcpyToSymbol(change2,d,sizeof(d)));
    std::vector<double> host_vm(n,-56.),host_ns(n,1.),host_rate(n,50000.);
    std::vector<int> host_counts(n,m);
    checked(cudaMemcpy(vm.p,host_vm.data(),n*sizeof(double),cudaMemcpyHostToDevice));
    checked(cudaMemcpy(ns.p,host_ns.data(),n*sizeof(double),cudaMemcpyHostToDevice));
    checked(cudaMemcpy(rate.p,host_rate.data(),n*sizeof(double),cudaMemcpyHostToDevice));
    checked(cudaMemcpy(counts.p,host_counts.data(),n*sizeof(int),cudaMemcpyHostToDevice));
    checked(cudaDeviceSynchronize());
    for(int k=0;k<ticks;++k) {
        checked(cudaMemset(counter.p,0,sizeof(int)));
        transduction<<<1024,128>>>(rng.p,1e-4f,vm.p,ns.p,rate.p,
                                    counts.p,total,counter.p);
        checked(cudaGetLastError());
        checked(cudaDeviceSynchronize());
    }
    std::vector<ushort2> h0(total),h1(total),h2(total);
    std::vector<unsigned short> h3(total);
    checked(cudaMemcpy(h0.data(),x0.p,total*sizeof(ushort2),cudaMemcpyDeviceToHost));
    checked(cudaMemcpy(h1.data(),x1.p,total*sizeof(ushort2),cudaMemcpyDeviceToHost));
    checked(cudaMemcpy(h2.data(),x2.p,total*sizeof(ushort2),cudaMemcpyDeviceToHost));
    checked(cudaMemcpy(h3.data(),x3.p,total*sizeof(unsigned short),cudaMemcpyDeviceToHost));
    std::vector<int32_t> rows(size_t(n)*4,0);
    for(int i=0;i<n;++i) for(int j=0;j<m;++j) {
        const int k=i*m+j;
        rows[size_t(i)*4+0]+=h3[k]==0 && h0[k].x==50 && h0[k].y==0 &&
            h1[k].x==0 && h1[k].y==0 && h2[k].x==0 && h2[k].y==0;
        rows[size_t(i)*4+1]+=h3[k];
        rows[size_t(i)*4+2]+=h2[k].x;
        rows[size_t(i)*4+3]+=h2[k].y;
    }
    FILE* f=std::fopen(argv[1],"wb");
    if(!f)throw std::runtime_error("output open");
    const size_t needed=rows.size();
    const size_t written=std::fwrite(rows.data(),sizeof(int32_t),needed,f);
    if(std::fclose(f) || written!=needed)throw std::runtime_error("output write");
    std::printf("FIXED_SOURCE_COMPLETE receptors=%d microvilli=%d ticks=%d seed=%llu\n",
                n,m,ticks,(unsigned long long)seed);
    return 0;
  } catch(const std::exception& error) {
    std::fprintf(stderr,"%s\n",error.what());
    return 1;
  }
}
