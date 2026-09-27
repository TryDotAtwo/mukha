// Diagnostic single connection per cell, not a MaleCNS circuit.
#include <cuda_runtime.h>
#include <cstdio>
#include <cmath>
#include "../build/morris_author.cu"
int main(int argc,char** argv){
    if(argc!=3)return 2;
    FILE* input=std::fopen(argv[1],"rb");if(!input)return 2;
    constexpr int count=4;
    double host[16*count]{};
    const double params[12]={-1,15,-5,10,.0025,.02,-50,10,-70,.5,1.1,2};
    for(int k=0;k<12;++k)for(int i=0;i<count;++i)host[(k+1)*count+i]=params[k];
    for(int i=0;i<count;++i){host[13*count+i]=-50;host[14*count+i]=.5;}
    double* d=nullptr;FILE* out=std::fopen(argv[2],"wb");if(!out)return 3;
    auto check=[](cudaError_t e){if(e!=cudaSuccess)std::fprintf(stderr,"%s\n",cudaGetErrorString(e));return e==cudaSuccess;};
    bool ok=check(cudaMalloc(&d,sizeof(host)));
    if(ok)ok=check(cudaMemcpy(d,host,sizeof(host),cudaMemcpyHostToDevice));
    double history[11][2];for(auto& row:history)for(double& value:row)value=-81.9925;
    for(int t=0;t<20000 && ok;++t){
        double presynaptic[2];
        if(std::fread(presynaptic,sizeof(double),2,input)!=2){ok=false;break;}
        history[t%11][0]=presynaptic[0];history[t%11][1]=presynaptic[1];
        for(int i=0;i<4;++i){
            const int delay=i==3?0:10;
            double pre=t>=delay?history[(t-delay)%11][i==0?0:1]:-81.9925;
            double g=i==2?0:std::fmin(.032,.0008*std::fmax(0.,pre+80));
            host[i]=g*(-80-host[52+i]);
        }
        ok=check(cudaMemcpy(d,host,count*sizeof(double),cudaMemcpyHostToDevice));
        if(!ok)break;
        update<<<1,32>>>(count,1e-5,10,d,d+4,d+8,d+12,d+16,d+20,d+24,d+28,d+32,d+36,d+40,d+44,d+48,d+52,d+56,d+60);
        ok=check(cudaGetLastError()) && check(cudaMemcpy(host+52,d+52,8*sizeof(double),cudaMemcpyDeviceToHost));
        for(int j=52;j<60;++j)if(!std::isfinite(host[j]))ok=false;
        if(ok && std::fwrite(host+52,sizeof(double),8,out)!=8)ok=false;
    }
    if(std::fgetc(input)!=EOF)ok=false;
    std::fclose(input);
    if(std::fclose(out))ok=false;
    if(d && !check(cudaFree(d)))ok=false;
    return ok?0:4;
}
