#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <stdexcept>
#include <cmath>
#include <cstring>
#include <chrono>
#ifdef FF_FILE_CHECKPOINT
#include "photon_checkpoint.hpp"
#if defined(FF_CHECK_REPLAY) || !defined(FF_ENTITY_RNG)
#error File checkpoint requires entity RNG and excludes in-memory replay mode
#endif
#endif
#ifdef FF_SAFE_TRANSDUCTION
#include "phototransduction_safe.cuh"
#else
#include "../build/photoreceptor_author_transduction.cu"
#endif
#undef BLOCK_SIZE
#include "photocurrent_safe.cuh"
#include "../build/photoreceptor_author_hh.cu"
#undef C
#include "../build/photoreceptor_author_adaptation.cu"
void checked(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T> struct Buffer {
    T* p=nullptr;
    Buffer(size_t n){checked(cudaMalloc(&p,n*sizeof(T)));}
    ~Buffer(){cudaFree(p);}
};
template<class T> void upload(T* dst,const T* src,size_t n){checked(cudaMemcpy(dst,src,n*sizeof(T),cudaMemcpyHostToDevice));}
__global__ void initialize_rng(curandStateXORWOW_t* states,int count){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<count)curand_init(19303,i,0,&states[i]);}
#if defined(FF_TRANSDUCTION_BLOCKS) && FF_TRANSDUCTION_BLOCKS > 1 && !defined(FF_ENTITY_RNG)
#error Multi-block diagnostic requires per-microvillus RNG allocation
#endif
#if defined(FF_COMPARE_LAUNCH) && (!defined(FF_CHECK_REPLAY) || !defined(FF_ENTITY_RNG))
#error Launch comparison requires checkpoint test and entity RNG
#endif
int main(int argc,char** argv){try{
    int ticks=argc>=2?std::atoi(argv[1]):1;
    int onset=argc>=3?std::atoi(argv[2]):0;
#ifdef FF_FILE_CHECKPOINT
    if(argc!=5 || ticks<2 || ticks>20000 || onset<0 || onset>=ticks)return 4;
    bool resume=std::strcmp(argv[3],"resume")==0;
    if(!resume && std::strcmp(argv[3],"save")!=0)return 4;
#else
    if(ticks<1 || ticks>20000 || onset<0 || onset>=ticks || argc>3)return 4;
#endif
#ifndef FF_MICROVILLI
#define FF_MICROVILLI 30000
#endif
    #ifndef FF_PHOTORECEPTORS
#define FF_PHOTORECEPTORS 2
#endif
    constexpr int n=FF_PHOTORECEPTORS,m=FF_MICROVILLI;
    static_assert(n>=2 && n<=65535 && m>0 && 1ll*n*m<=2147483647ll,"Population exceeds source index representation");
    constexpr int total=n*m;
#ifdef FF_PROFILE
    size_t free_before=0,total_memory=0;checked(cudaMemGetInfo(&free_before,&total_memory));
#endif
    Buffer<ushort2> x0(total),x1(total),x2(total);
    Buffer<unsigned short> x3(total),owner(total);
    Buffer<int> counts(n),offsets(n),counter(1);
    Buffer<double> state(n*9);
#ifdef FF_ENTITY_RNG
    constexpr int rng_count=total;
#else
    constexpr int rng_count=128;
#endif
    Buffer<curandStateXORWOW_t> random(rng_count);
    std::vector<ushort2> init(total,make_ushort2(50,0));upload(x0.p,init.data(),total);
    checked(cudaMemset(x1.p,0,total*sizeof(ushort2)));checked(cudaMemset(x2.p,0,total*sizeof(ushort2)));
    checked(cudaMemset(x3.p,0,total*sizeof(unsigned short)));
    std::vector<unsigned short> owners(total);for(int i=0;i<total;++i)owners[i]=i/m;
    upload(owner.p,owners.data(),total);
    long long addresses[5]={(long long)x0.p,(long long)x1.p,(long long)x2.p,(long long)x3.p,(long long)owner.p};
    checked(cudaMemcpyToSymbol(d_X,addresses,sizeof(addresses)));
    int a[14]={0,0,1,2,2,1,4,3,4,4,6,5,5,0};
    int b[14]={0,0,2,3,0,0,0,0,0,6,0,0,0,0};
    int c[14]={0,-1,-1,-1,-1,1,1,-1,-1,-2,-1,1,-1,1};
    int d[14]={0,0,1,1,0,0,0,0,0,1,0,0,0,0};
    checked(cudaMemcpyToSymbol(change_ind1,a,sizeof(a)));checked(cudaMemcpyToSymbol(change_ind2,b,sizeof(b)));
    checked(cudaMemcpyToSymbol(change1,c,sizeof(c)));checked(cudaMemcpyToSymbol(change2,d,sizeof(d)));
    std::vector<int> count(n,m),off(n);for(int i=0;i<n;++i)off[i]=i*m;
    upload(counts.p,count.data(),n);upload(offsets.p,off.data(),n);
    std::vector<double> initial(n*9,0),rates(n);
    const double baseline[7]={-81.9925,.2184,.9653,.0117,.9998,.0017,1};
    for(int i=0;i<n;++i){
        for(int j=0;j<7;++j)initial[j*n+i]=baseline[j];
        rates[i]=(i%2)?100000:0;
        initial[7*n+i]=onset>0?0:rates[i];
    }
    upload(state.p,initial.data(),n*9);
    Buffer<double> current(n),feedback(n);checked(cudaMemset(feedback.p,0,n*sizeof(double)));
    initialize_rng<<<(rng_count+127)/128,128>>>(random.p,rng_count);checked(cudaGetLastError());
#ifdef FF_PROFILE
    checked(cudaDeviceSynchronize());
    size_t free_after=0,ignored_total=0;checked(cudaMemGetInfo(&free_after,&ignored_total));
    std::fprintf(stderr,"RESOURCE n=%d microvilli=%d total_microvilli=%d allocated_vram_delta=%zu total_vram=%zu\n",n,m,total,free_before-free_after,total_memory);
    auto loop_start=std::chrono::steady_clock::now();
#endif
    std::puts("tick,dark_mv,light_mv,dark_ns,light_ns");
#if defined(FF_CHECK_REPLAY) || defined(FF_FILE_CHECKPOINT)
    if(ticks<2)return 6;
    struct Piece {void* pointer; size_t bytes;};
    std::vector<Piece> pieces={{x0.p,total*sizeof(ushort2)},{x1.p,total*sizeof(ushort2)},
        {x2.p,total*sizeof(ushort2)},{x3.p,total*sizeof(unsigned short)},
        {state.p,n*9*sizeof(double)},{random.p,rng_count*sizeof(curandStateXORWOW_t)},
        {feedback.p,n*sizeof(double)}};
    size_t bytes=0;for(auto piece:pieces)bytes+=piece.bytes;
#ifdef FF_FILE_CHECKPOINT
    std::vector<unsigned char> checkpoint(bytes);
#else
    std::vector<unsigned char> checkpoint(bytes),first_end(bytes),second_end(bytes);
#endif
    auto copy_state=[&](std::vector<unsigned char>& data,bool restore){
        size_t offset=0;
        for(auto piece:pieces){
            if(restore)checked(cudaMemcpy(piece.pointer,data.data()+offset,piece.bytes,cudaMemcpyHostToDevice));
            else checked(cudaMemcpy(data.data()+offset,piece.pointer,piece.bytes,cudaMemcpyDeviceToHost));
            offset+=piece.bytes;
        }
    };
#ifdef FF_FILE_CHECKPOINT
    const int middle=ticks/2,iterations=ticks;
    if(resume){photon_checkpoint(argv[4],true,checkpoint,n,m,ticks,onset,sizeof(curandStateXORWOW_t));copy_state(checkpoint,true);}
#else
    const int middle=ticks/2,iterations=ticks+(ticks-middle);
#endif
#else
    const int iterations=ticks;
#endif
#ifdef FF_FILE_CHECKPOINT
    const int begin=resume?middle:0;
#else
    const int begin=0;
#endif
    for(int iteration=begin;iteration<iterations;++iteration){
#ifdef FF_FILE_CHECKPOINT
      if(!resume && iteration==middle){copy_state(checkpoint,false);photon_checkpoint(argv[4],false,checkpoint,n,m,ticks,onset,sizeof(curandStateXORWOW_t));}
#endif
      int tick=iteration;
#ifdef FF_CHECK_REPLAY
      if(iteration==middle)copy_state(checkpoint,false);
      if(iteration==ticks){copy_state(first_end,false);copy_state(checkpoint,true);}
      if(iteration>=ticks)tick=middle+iteration-ticks;
#endif
    if(tick==onset)upload(state.p+7*n,rates.data(),n);
    checked(cudaMemset(counter.p,0,sizeof(int)));
#ifndef FF_TRANSDUCTION_BLOCKS
#define FF_TRANSDUCTION_BLOCKS 1
#endif
#ifdef FF_COMPARE_LAUNCH
    const int launch_blocks=iteration<ticks?1:16;
#else
    const int launch_blocks=FF_TRANSDUCTION_BLOCKS;
#endif
    transduction<<<launch_blocks,128>>>(random.p,1e-4f,state.p,state.p+6*n,state.p+7*n,counts.p,total,counter.p);
    checked(cudaGetLastError());checked(cudaDeviceSynchronize());
    sum_current<<<n,256>>>(x2.p,counts.p,offsets.p,state.p,current.p,feedback.p);
    hh<<<(n+31)/32,32>>>(current.p,state.p,state.p+n,state.p+2*n,state.p+3*n,state.p+4*n,state.p+5*n,n,1e-5,10);
    update_ns<<<(n+127)/128,128>>>(state.p+6*n,n,state.p,1e-4);
    checked(cudaGetLastError());checked(cudaMemcpy(initial.data(),state.p,initial.size()*sizeof(double),cudaMemcpyDeviceToHost));
    for(int i=0;i<7*n;++i)if(!std::isfinite(initial[i]))return 2;
    for(int i=n;i<6*n;++i)if(initial[i]<0 || initial[i]>1)return 5;
    std::printf("%d,%.17g,%.17g,%.17g,%.17g\n",tick+1,initial[0],initial[1],initial[6*n],initial[6*n+1]);
    }
#ifdef FF_CHECK_REPLAY
    copy_state(second_end,false);
    if(first_end!=second_end){std::fprintf(stderr,"Full state continuation mismatch\n");return 7;}
    std::fprintf(stderr,"Checkpoint continuation exact: %zu bytes; checkpoint tick %d; final tick %d\n",bytes,middle,ticks);
#endif
#ifdef FF_FILE_CHECKPOINT
    copy_state(checkpoint,false);
    photon_checkpoint((std::string(argv[4])+".final").c_str(),false,checkpoint,n,m,ticks,onset,sizeof(curandStateXORWOW_t));
    std::fprintf(stderr,"File checkpoint %s: final state checksum %llu; bytes %zu\n",resume?"resume":"save",(unsigned long long)photon_checksum(checkpoint),bytes);
#endif
#ifdef FF_PROFILE
    checked(cudaDeviceSynchronize());
    std::fprintf(stderr,"RESOURCE loop_wall_seconds=%.9f ticks=%d\n",std::chrono::duration<double>(std::chrono::steady_clock::now()-loop_start).count(),ticks);
#endif
#ifdef FF_DUMP_POPULATION
    FILE* population=std::fopen("population_state.bin","wb");
    if(!population)return 8;
    bool written=std::fwrite(initial.data(),sizeof(double),initial.size(),population)==initial.size();
    if(std::fclose(population)!=0 || !written)return 8;
#endif
    return 0;
}catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 3;}}
