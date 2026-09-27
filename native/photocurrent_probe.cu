#include <cuda_runtime.h>
#include <cstdio>
#include <vector>
#include <stdexcept>
#include <cmath>
#ifdef FF_SAFE_CURRENT
#include "photocurrent_safe.cuh"
#else
#include "../build/photoreceptor_author_current.cu"
#endif
void checked(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T> struct Buffer {
    T* p=nullptr;
    Buffer(size_t n){checked(cudaMalloc(&p,n*sizeof(T)));}
    ~Buffer(){cudaFree(p);}
};
int main(){try{
    constexpr int n=3,m=30000;
    std::vector<ushort2> channels(n*m);
    long long sums[n]{};
    for(int j=0;j<n;++j)for(int i=0;i<m;++i){
        auto value=static_cast<unsigned short>((i*7+j*3)%26);
        channels[j*m+i]=make_ushort2(0,value);sums[j]+=value;
    }
    int count[n]={m,m,m},offset[n]={0,m,2*m};
    double voltage[n]={-80,-40,5},feedback[n]={0,3,-2},actual[n];
    Buffer<ushort2> ch(n*m);Buffer<int> co(n),off(n);Buffer<double> v(n),fb(n),out(n);
    checked(cudaMemcpy(ch.p,channels.data(),channels.size()*sizeof(ushort2),cudaMemcpyHostToDevice));
    checked(cudaMemcpy(co.p,count,sizeof(count),cudaMemcpyHostToDevice));
    checked(cudaMemcpy(off.p,offset,sizeof(offset),cudaMemcpyHostToDevice));
    checked(cudaMemcpy(v.p,voltage,sizeof(voltage),cudaMemcpyHostToDevice));
    checked(cudaMemcpy(fb.p,feedback,sizeof(feedback),cudaMemcpyHostToDevice));
    sum_current<<<n,256>>>(ch.p,co.p,off.p,v.p,out.p,fb.p);
    checked(cudaGetLastError());checked(cudaMemcpy(actual,out.p,sizeof(actual),cudaMemcpyDeviceToHost));
    for(int j=0;j<n;++j){
        double expected=feedback[j]+sums[j]*8*std::fmax(-voltage[j]*.001,0.)/15.7;
        std::printf("case %d channels %lld expected %.17g actual %.17g\n",j,sums[j],expected,actual[j]);
        if(!std::isfinite(actual[j]) || std::abs(actual[j]-expected)>1e-10)return 2;
    }
    return 0;
}catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 3;}}
