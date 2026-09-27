// Experimental population SSA for the pinned VisTrans reactions.
// One receptor per CUDA thread; fixed input only. Not a production retina.
#include <cuda_runtime.h>
#include <curand_kernel.h>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <vector>

static constexpr int SLOTS=16384;
static constexpr int MASK=SLOTS-1;
static constexpr float DT=1e-4f;
static constexpr float LA=0.5f;
static constexpr float EPS=2e-5f;

struct MolecularState { uint16_t x[7]; };

__device__ float concentration(int n) {return n*5.5353e-4f;}
__device__ float calcium(const MolecularState& s,float vm) {
    const float cs=concentration(s.x[5]);
    const float input=s.x[6]*8.f*fmaxf(-vm,0.f);
    const float den=1060.f-120.f*cs+179.0952f*expf(-39.60793f*vm);
    return fmaxf(1.6e-4f,(input*690.9537f+0.0795979f+22.f*cs)/den);
}
__device__ float fn_value(const MolecularState& s,float ns) {
    float t=concentration(s.x[5])*5.55555555f;
    t*=t*t;
    return ns*t/(1.f+t);
}
__device__ float fp_value(float ca) {
    float t=ca*3.3333333333f;
    t*=t;
    return t/(1.f+t);
}
__device__ float compact_rate(const MolecularState& s,float vm,float ns,float lambda) {
    const int a=s.x[0],b=s.x[1],c=s.x[2],d=s.x[3],e=s.x[4],f=s.x[5],g=s.x[6];
    const float ca=calcium(s,vm),fn=fn_value(s,ns);
    float sum=lambda+54198.f*ca*(0.5f-f*5.5353e-4f)+5.5f*f;
    sum+=25.f*(1.f+10.f*fn)*g;
    sum+=4.f*(1.f+37.8f*fn)*e;
    sum+=(1444.f+1598.4f*fn)*d;
    sum+=(3.7f*(1.f+40.f*fn)+7.05f*b)*a;
    sum+=(1560.f-12.6f*d)*c;
    sum+=3.5f*(50-c-b-d);
    sum+=0.015f*(1.f+11.5f*fp_value(ca))*e*(e-1)*(25-g)*0.5f;
    return sum;
}

__device__ int reaction(const MolecularState& s,float vm,float ns,float lambda,float sum,curandStateXORWOW_t* rng) {
    const int a=s.x[0],b=s.x[1],c=s.x[2],d=s.x[3],e=s.x[4],f=s.x[5],g=s.x[6];
    const float ca=calcium(s,vm),fn=fn_value(s,ns);
    float r=curand_uniform(rng)*sum;
    if(r<=EPS)return 0;
#define CHOOSE(ID, WEIGHT) r-=(WEIGHT); if(r<=EPS)return (ID)
    CHOOSE(13,lambda);
    CHOOSE(11,rintf(30.f*1806.6f)*ca*(0.5f-concentration(f)));
    CHOOSE(12,rintf(5.5f*1806.6f)*concentration(f));
    CHOOSE(10,25.f*(1.f+10.f*fn)*g);
    CHOOSE(8,4.f*(1.f+37.8f*fn)*e);
    CHOOSE(7,144.f*(1.f+11.1f*fn)*d);
    CHOOSE(1,3.7f*(1.f+40.f*fn)*a);
    CHOOSE(6,1300.f*d);
    CHOOSE(4,3.f*c*d);
    CHOOSE(3,15.6f*c*(100-d));
    CHOOSE(5,3.5f*(50-c-b-d));
    CHOOSE(2,7.05f*b*a);
    CHOOSE(9,0.015f*(1.f+11.5f*fp_value(ca))*e*(e-1)*(25-g)*0.5f);
#undef CHOOSE
    return 0;
}

__device__ MolecularState apply(MolecularState s,int code) {
    constexpr int first[14]={0,0,1,2,2,1,4,3,4,4,6,5,5,0};
    constexpr int second[14]={0,0,2,3,0,0,0,0,0,6,0,0,0,0};
    constexpr int delta[14]={0,-1,-1,-1,-1,1,1,-1,-1,-2,-1,1,-1,1};
    if(code) {
        s.x[first[code]]+=delta[code];
        if(second[code])++s.x[second[code]];
    }
    return s;
}

__device__ uint32_t hash_state(const MolecularState& s) {
    uint32_t h=2166136261u;
    #pragma unroll
    for(int j=0;j<7;++j)h=(h^s.x[j])*16777619u;
    return h&MASK;
}
__device__ bool same(const MolecularState& a,const MolecularState& b) {
    #pragma unroll
    for(int j=0;j<7;++j)if(a.x[j]!=b.x[j])return false;
    return true;
}
__device__ int find_or_insert(MolecularState* keys,int* counts,const MolecularState& s,int* occupied) {
    int k=hash_state(s);
    int first_tombstone=-1;
    for(int probe=0;probe<SLOTS;++probe) {
        if(counts[k]<0) {
            const int dest=first_tombstone>=0?first_tombstone:k;
            keys[dest]=s;
            counts[dest]=0;
            if(first_tombstone<0)++*occupied;
            return dest;
        }
        if(same(keys[k],s))return k;
        if(counts[k]==0 && first_tombstone<0)first_tombstone=k;
        k=(k+1)&MASK;
    }
    if(first_tombstone>=0) {
        keys[first_tombstone]=s;
        counts[first_tombstone]=0;
        return first_tombstone;
    }
    return -1;
}
__device__ void tree_add(double* tree,int slot,double delta) {
    for(int k=slot+1;k<=SLOTS;k+=k&-k)tree[k]+=delta;
}
__device__ int tree_select(const double* tree,double target) {
    int k=0;
    for(int bit=SLOTS;bit;bit>>=1) {
        const int next=k+bit;
        if(next<=SLOTS && tree[next]<=target) {target-=tree[next];k=next;}
    }
    return k<SLOTS?k:SLOTS-1;
}

// Four output values plus occupied slots, event count and error flag.
__global__ void grouped(MolecularState* all_keys,int* all_counts,double* all_tree,
                        int* rows,int receptors,int microvilli,int ticks,uint64_t seed) {
    const int id=blockIdx.x*blockDim.x+threadIdx.x;
    if(id>=receptors)return;
    MolecularState* keys=all_keys+size_t(id)*SLOTS;
    int* counts=all_counts+size_t(id)*SLOTS;
    double* tree=all_tree+size_t(id)*(SLOTS+1);
    for(int i=0;i<SLOTS;++i)counts[i]=-1;
    for(int i=0;i<=SLOTS;++i)tree[i]=0.;
    MolecularState basal={0,50,0,0,0,0,0};
    int occupied=0;
    const int first=find_or_insert(keys,counts,basal,&occupied);
    counts[first]=microvilli;
    const float vm=-0.056f,ns=1.f,lambda=50000.f/microvilli;
    const double first_weight=microvilli*(LA+compact_rate(basal,vm,ns,lambda));
    tree_add(tree,first,first_weight);
    double total=first_weight;
    curandStateXORWOW_t rng;
    curand_init(seed,id,0,&rng);
    int events=0,error=0;
    for(int tick=0;tick<ticks && !error;++tick) {
        double elapsed=-logf(curand_uniform(&rng))/total;
        while(elapsed<=DT) {
            if(++events>ticks*microvilli*50){error=2;break;}
            // XORWOW's (0,1] draw can equal 1; a tree target must be in [0,total).
            const double target=(1.0-double(curand_uniform(&rng)))*total;
            const int slot=tree_select(tree,target);
            if(counts[slot]<=0){error=3;break;}
            const MolecularState old=keys[slot];
            const float old_rate=compact_rate(old,vm,ns,lambda);
            const int code=reaction(old,vm,ns,lambda,old_rate,&rng);
            if(code) {
                const MolecularState next=apply(old,code);
                const int dest=find_or_insert(keys,counts,next,&occupied);
                if(dest<0){error=1;break;}
                if(dest!=slot) {
                    --counts[slot];++counts[dest];
                    const double before=LA+old_rate;
                    const double after=LA+compact_rate(next,vm,ns,lambda);
                    tree_add(tree,slot,-before);
                    tree_add(tree,dest,after);
                    total=tree[SLOTS];
                }
            }
            elapsed+=-logf(curand_uniform(&rng))/total;
        }
    }
    int basal_count=0,sum0=0,sum5=0,sum6=0,population=0;
    for(int i=0;i<SLOTS;++i)if(counts[i]>0){
        const int n=counts[i];
        if(same(keys[i],basal))basal_count=n;
        sum0+=n*keys[i].x[0];sum5+=n*keys[i].x[5];sum6+=n*keys[i].x[6];
        population+=n;
    }
    if(population!=microvilli && !error)error=4;
    const size_t offset=size_t(id)*7;
    rows[offset]=basal_count;rows[offset+1]=sum0;rows[offset+2]=sum5;
    rows[offset+3]=sum6;rows[offset+4]=occupied;rows[offset+5]=events;rows[offset+6]=error;
}

static void checked(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
int main(int argc,char** argv) {
  try {
    if(argc!=6)throw std::runtime_error("usage: output.bin receptors microvilli ticks seed");
    const int n=std::atoi(argv[2]),m=std::atoi(argv[3]),ticks=std::atoi(argv[4]);
    const uint64_t seed=std::strtoull(argv[5],nullptr,10);
    if(n<1||n>3377||m<1||m>30000||ticks<1||ticks>10000)throw std::runtime_error("dimensions");
    MolecularState* keys=nullptr;int* counts=nullptr;double* tree=nullptr;int* output=nullptr;
    checked(cudaMalloc(&keys,size_t(n)*SLOTS*sizeof(MolecularState)));
    checked(cudaMalloc(&counts,size_t(n)*SLOTS*sizeof(int)));
    checked(cudaMalloc(&tree,size_t(n)*(SLOTS+1)*sizeof(double)));
    checked(cudaMalloc(&output,size_t(n)*7*sizeof(int)));
    cudaEvent_t start,stop;checked(cudaEventCreate(&start));checked(cudaEventCreate(&stop));
    checked(cudaEventRecord(start));
    grouped<<<(n+31)/32,32>>>(keys,counts,tree,output,n,m,ticks,seed);
    checked(cudaGetLastError());checked(cudaEventRecord(stop));checked(cudaEventSynchronize(stop));
    float milliseconds=0;checked(cudaEventElapsedTime(&milliseconds,start,stop));
    std::vector<int> host(size_t(n)*7);
    checked(cudaMemcpy(host.data(),output,host.size()*sizeof(int),cudaMemcpyDeviceToHost));
    int failures=0,max_occupied=0,max_events=0;
    for(int i=0;i<n;++i){failures+=host[size_t(i)*7+6]!=0;
        if(host[size_t(i)*7+4]>max_occupied)max_occupied=host[size_t(i)*7+4];
        if(host[size_t(i)*7+5]>max_events)max_events=host[size_t(i)*7+5];}
    FILE* f=std::fopen(argv[1],"wb");if(!f)throw std::runtime_error("output open");
    const size_t written=std::fwrite(host.data(),sizeof(int),host.size(),f);
    if(std::fclose(f)||written!=host.size())throw std::runtime_error("output write");
    std::printf("GROUPED_GPU receptors=%d microvilli=%d ticks=%d ms=%.6f failures=%d max_occupied=%d max_events=%d\n",n,m,ticks,milliseconds,failures,max_occupied,max_events);
    checked(cudaEventDestroy(start));checked(cudaEventDestroy(stop));
    checked(cudaFree(keys));checked(cudaFree(counts));checked(cudaFree(tree));checked(cudaFree(output));
    return failures?2:0;
  } catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
