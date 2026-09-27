// Diagnostic driver for the unchanged, separately hash-pinned author kernel.
#include <cuda_runtime.h>
#include <cstdio>
#include <cmath>
#include "../build/photoreceptor_author_hh.cu"
#undef C
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    constexpr int n=4, ticks=10000;
    double host[7*n]{};
    const double initial[6]={-81.9925,.2184,.9653,.0117,.9998,.0017};
    for(int s=0;s<6;++s)for(int j=0;j<n;++j)host[(s+1)*n+j]=initial[s];
    double* device=nullptr;
    auto check=[](cudaError_t e){if(e!=cudaSuccess){std::fprintf(stderr,"%s\n",cudaGetErrorString(e));return false;}return true;};
    if(!check(cudaMalloc(&device,sizeof(host))))return 3;
    FILE* out=std::fopen(argv[1],"wb");
    if(!out){cudaFree(device);return 4;}
    bool ok=check(cudaMemcpy(device,host,sizeof(host),cudaMemcpyHostToDevice));
    for(int t=0;t<ticks && ok;++t){
        host[0]=0;host[1]=10;host[2]=100;host[3]=(t>=2000 && t<4000)?100:0;
        ok=check(cudaMemcpy(device,host,n*sizeof(double),cudaMemcpyHostToDevice));
        if(!ok)break;
        hh<<<1,32>>>(device,device+n,device+2*n,device+3*n,device+4*n,device+5*n,device+6*n,n,1e-5,10);
        ok=check(cudaGetLastError()) && check(cudaMemcpy(host+n,device+n,6*n*sizeof(double),cudaMemcpyDeviceToHost));
        for(int j=n;j<7*n;++j)if(!std::isfinite(host[j]))ok=false;
        if(ok && std::fwrite(host+n,sizeof(double),6*n,out)!=6*n)ok=false;
    }
    if(std::fclose(out))ok=false;
    if(!check(cudaFree(device)))ok=false;
    if(ok)std::puts("10000 ticks, 4 current protocols, 6 state variables; GPU run complete");
    return ok?0:5;
}
