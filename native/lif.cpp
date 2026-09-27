#include "lif.h"
#include "lif_coeff.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
namespace {
thread_local std::string error;
uint64_t hash_bytes(const void* data, size_t n, uint64_t h=14695981039346656037ULL) {
    auto p=static_cast<const uint8_t*>(data);
    for(size_t i=0;i<n;++i) { h^=p[i]; h*=1099511628211ULL; }
    return h;
}
void require(bool ok, const char* message) { if(!ok) throw std::runtime_error(message); }
}

struct ff_model {
    uint32_t n;
    uint64_t edges, tick=0, identity;
    ff_params p;
    float a,b,c;
    std::vector<uint64_t> row, next_allowed;
    std::vector<uint32_t> col;
    std::vector<float> weight,v,g;
    std::vector<uint8_t> sensory, ring, fired, allowed;
    size_t ring_rows;
    ff_model(uint32_t count,uint64_t e,const uint64_t* r,const uint32_t* columns,
             const float* w,const uint8_t* sense,ff_params params):n(count),edges(e),p(params) {
        require(n>0 && r && sense && (e==0 || (columns && w)),"invalid graph pointer or size");
        require(std::isfinite(p.dt_ms)&&p.dt_ms>0 && std::isfinite(p.membrane_ms)&&p.membrane_ms>0 &&
                std::isfinite(p.synapse_ms)&&p.synapse_ms>0 && std::isfinite(p.rest_mv)&&
                std::isfinite(p.reset_mv)&&std::isfinite(p.threshold_mv),"invalid neuron parameters");
        require(r[0]==0 && r[n]==e,"invalid CSR offsets");
        for(uint32_t i=0;i<n;++i) require(r[i]<=r[i+1],"nonmonotone CSR");
        for(uint64_t j=0;j<e;++j) require(columns[j]<n && std::isfinite(w[j]),"invalid edge");
        row.assign(r,r+size_t(n)+1);
        if(e) { col.assign(columns,columns+e);weight.assign(w,w+e); }
        sensory.assign(sense,sense+n);
        for(auto s:sensory) require(s<=1,"invalid sensory mask");
        v.assign(n,p.rest_mv);g.assign(n,0);next_allowed.assign(n,0);
        ring_rows=size_t(p.delay_ticks)+1;
        require(ring_rows<=std::numeric_limits<size_t>::max()/n,"delay ring overflow");
        ring.assign(ring_rows*n,0);fired.assign(n,0);allowed.assign(n,0);
        const double aa=std::exp(-double(p.dt_ms)/p.membrane_ms);
        const double bb=std::exp(-double(p.dt_ms)/p.synapse_ms);
        a=float(aa);b=float(bb);
        const auto coupling=lif_coupling(p.dt_ms,p.membrane_ms,p.synapse_ms);
        c=float(coupling.value);
        identity=hash_bytes(&p,sizeof(p));
        identity=hash_bytes(row.data(),row.size()*sizeof(uint64_t),identity);
        identity=hash_bytes(col.data(),col.size()*sizeof(uint32_t),identity);
        identity=hash_bytes(weight.data(),weight.size()*sizeof(float),identity);
        identity=hash_bytes(sensory.data(),sensory.size(),identity);
        if(coupling.changed_numerics) {
            constexpr char semantics[]="lif-near-equal-tau-expm1-v1";
            identity=hash_bytes(semantics,sizeof(semantics)-1,identity);
        }
    }
    void step(const float* drive,uint8_t* spikes) {
        require(drive&&spikes,"null step array");
        require(tick<std::numeric_limits<uint64_t>::max()-p.refractory_ticks-1,"tick overflow");
        // Validate before mutating any state.
        for(uint32_t i=0;i<n;++i) require(std::isfinite(drive[i]),"nonfinite drive");
        for(uint32_t i=0;i<n;++i) {
            allowed[i]=tick>=next_allowed[i];
            if(allowed[i]) { v[i]=p.rest_mv+a*(v[i]-p.rest_mv)+c*g[i];g[i]=b*g[i]; }
            fired[i]=allowed[i] && v[i]>p.threshold_mv;
        }
        std::copy(fired.begin(),fired.end(),ring.begin()+(tick%ring_rows)*n);
        const auto* delayed=ring.data()+((tick+ring_rows-p.delay_ticks)%ring_rows)*n;
        for(uint32_t i=0;i<n;++i) {
            if(allowed[i]) {
                float incoming=0;
                for(uint64_t j=row[i];j<row[i+1];++j) incoming+=weight[j]*delayed[col[j]];
                g[i]+=incoming;v[i]+=drive[i];
            }
            if(fired[i]) { v[i]=p.reset_mv;g[i]=0;next_allowed[i]=tick+(sensory[i]?0:p.refractory_ticks); }
        }
        std::copy(fired.begin(),fired.end(),spikes);
        ++tick;
    }
    size_t payload_size() const { return size_t(n)*(2*sizeof(float)+sizeof(uint64_t))+ring.size(); }
};

extern "C" ff_model* ff_create(uint32_t n,uint64_t e,const uint64_t* r,const uint32_t* col,
                                const float* w,const uint8_t* sensory,ff_params p) {
    try { error.clear();return new ff_model(n,e,r,col,w,sensory,p); }
    catch(const std::exception& ex) { error=ex.what();return nullptr; }
}
extern "C" void ff_destroy(ff_model* m) { delete m; }
extern "C" const char* ff_last_error() { return error.c_str(); }
extern "C" int ff_step(ff_model* m,const float* x,uint8_t* spikes) {
    try { require(m,"null model");m->step(x,spikes);return 0; }
    catch(const std::exception& ex) { error=ex.what();return -1; }
}
extern "C" int ff_observe(const ff_model* m,float* v,float* g) {
    if(!m||!v||!g) { error="null observation array";return -1; }
    std::copy(m->v.begin(),m->v.end(),v);std::copy(m->g.begin(),m->g.end(),g);return 0;
}
extern "C" size_t ff_checkpoint_size(const ff_model* m) { return m?64+m->payload_size():0; }
extern "C" int ff_save(const ff_model* m,uint8_t* buffer,size_t bytes) {
    try {
        require(m&&buffer&&bytes==ff_checkpoint_size(m),"invalid checkpoint output");
        size_t pos=64;
        auto put=[&](const void* data,size_t size) { std::memcpy(buffer+pos,data,size);pos+=size; };
        put(m->v.data(),m->n*sizeof(float));put(m->g.data(),m->n*sizeof(float));
        put(m->next_allowed.data(),m->n*sizeof(uint64_t));put(m->ring.data(),m->ring.size());
        const uint64_t header[8]={0x3146494c594c4646ULL,1,m->n,m->edges,m->tick,m->identity,
                                 m->payload_size(),hash_bytes(buffer+64,bytes-64)};
        std::memcpy(buffer,header,64);return 0;
    } catch(const std::exception& ex) { error=ex.what();return -1; }
}
extern "C" int ff_load(ff_model* m,const uint8_t* buffer,size_t bytes) {
    try {
        require(m&&buffer&&bytes==ff_checkpoint_size(m),"invalid checkpoint input");
        uint64_t h[8];std::memcpy(h,buffer,64);
        require(h[0]==0x3146494c594c4646ULL&&h[1]==1&&h[2]==m->n&&h[3]==m->edges&&h[5]==m->identity&&
                h[6]==m->payload_size()&&h[7]==hash_bytes(buffer+64,bytes-64),"checkpoint identity/checksum mismatch");
        require(h[4]<std::numeric_limits<uint64_t>::max()-m->p.refractory_ticks-1,"checkpoint tick overflow");
        for(size_t i=0;i<size_t(m->n)*2;++i) {
            float x;std::memcpy(&x,buffer+64+i*sizeof(float),sizeof(float));
            require(std::isfinite(x),"nonfinite checkpoint state");
        }
        size_t pos=64;
        auto get=[&](void* data,size_t size) { std::memcpy(data,buffer+pos,size);pos+=size; };
        get(m->v.data(),m->n*sizeof(float));get(m->g.data(),m->n*sizeof(float));
        get(m->next_allowed.data(),m->n*sizeof(uint64_t));get(m->ring.data(),m->ring.size());
        m->tick=h[4];return 0;
    } catch(const std::exception& ex) { error=ex.what();return -1; }
}
