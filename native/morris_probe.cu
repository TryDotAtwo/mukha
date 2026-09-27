#include <cuda_runtime.h>
#include <cstdio>
#include <cmath>
#include "../build/morris_author.cu"
int main(int argc,char** argv){
    if(argc!=2)return 2;
    constexpr int count=4;
    double host[16*count]{};
    const double params[12]={-1,15,-5,10,.0025,.02,-50,10,-70,.5,1.1,2};
    for(int k=0;k<12;++k)for(int i=0;i<count;++i)host[(k+1)*count+i]=params[k];
    for(int i=0;i<count;++i){host[13*count+i]=-50;host[14*count+i]=.5;}
    double* d=nullptr;FILE* out=std::fopen(argv[1],"wb");if(!out)return 3;
    auto check=[](cudaError_t e){if(e!=cudaSuccess)std::fprintf(stderr,"%s\n",cudaGetErrorString(e));return e==cudaSuccess;};
    bool ok=check(cudaMalloc(&d,sizeof(host)));
    if(ok)ok=check(cudaMemcpy(d,host,sizeof(host),cudaMemcpyHostToDevice));
    for(int t=0;t<10000 && ok;++t){
        host[0]=0;host[1]=-.48;host[2]=.48;host[3]=(t>=2000 && t<4000)?-.96:0;
        ok=check(cudaMemcpy(d,host,count*sizeof(double),cudaMemcpyHostToDevice));
        if(!ok)break;
        update<<<1,32>>>(count,1e-5,10,d,d+4,d+8,d+12,d+16,d+20,d+24,d+28,d+32,d+36,d+40,d+44,d+48,d+52,d+56,d+60);
        ok=check(cudaGetLastError()) && check(cudaMemcpy(host+52,d+52,8*sizeof(double),cudaMemcpyDeviceToHost));
        for(int j=52;j<60;++j)if(!std::isfinite(host[j]))ok=false;
        if(ok && std::fwrite(host+52,sizeof(double),8,out)!=8)ok=false;
    }
    if(std::fclose(out))ok=false;
    if(d && !check(cudaFree(d)))ok=false;
    return ok?0:4;
}
