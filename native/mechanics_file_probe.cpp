// Same-build diagnostic file checkpoint. Not a full experiment checkpoint.
#include <mujoco/mujoco.h>
#include "rocket_vertical.h"
#include "atomic_checkpoint.hpp"
#include <vector>
#include <memory>
#include <fstream>
#include <cstring>
#include <cstdint>
#include <limits>
uint64_t hash_bytes(const void* p,size_t n) {
    uint64_t h=14695981039346656037ULL;auto b=static_cast<const unsigned char*>(p);
    for(size_t i=0;i<n;++i){h^=b[i];h*=1099511628211ULL;}return h;
}
int main(int argc,char**argv) {try {
    // XML, output, stop tick, optional input checkpoint
    if(argc!=4&&argc!=5)return 2;
    size_t used=0;std::string number=argv[3];auto stop=std::stoull(number,&used);
    if(used!=number.size()||stop>10000)return 2;
    char error[2048]{};
    std::unique_ptr<mjModel,decltype(&mj_deleteModel)>m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
    if(!m)throw std::runtime_error(error);
    auto size=mj_sizeModel(m.get());if(size<=0||size>std::numeric_limits<int>::max())return 2;
    std::vector<unsigned char> model(size);mj_saveModel(m.get(),nullptr,model.data(),static_cast<int>(size));
    uint64_t identity=hash_bytes(model.data(),model.size());
    int n=mj_stateSize(m.get(),mjSTATE_INTEGRATION);
    int key=mj_name2id(m.get(),mjOBJ_KEY,"neutral"),j=mj_name2id(m.get(),mjOBJ_JOINT,"control_slide");
    if(key<0||j<0||m->nu<1||m->opt.timestep!=.0001)return 2;
    std::unique_ptr<mjData,decltype(&mj_deleteData)>d(mj_makeData(m.get()),mj_deleteData);if(!d)return 2;
    m->opt.gravity[0]=m->opt.gravity[1]=m->opt.gravity[2]=0;
    mj_resetDataKeyframe(m.get(),d.get(),key);mj_forward(m.get(),d.get());
    fly_rocket::Parameters p{200000.,6.5e10,1000.,20000.,3000.,.3};
    fly_rocket::State initial{0.,2500.,-20.,100.,0.,false};uint64_t tick=0;
    // Header words: magic, version, n, tick, compiled-model hash, payload hash.
    constexpr uint64_t magic=0x314b434548434d46ULL;
    std::vector<double> state(n+6);
    if(argc==5) {
        std::ifstream in(argv[4],std::ios::binary);uint64_t header[6]{};
        if(!in.read(reinterpret_cast<char*>(header),sizeof(header)))throw std::runtime_error("short header");
        if(header[0]!=magic||header[1]!=1||header[2]!=static_cast<uint64_t>(n)||header[3]>stop||header[4]!=identity)
            throw std::runtime_error("checkpoint model/schema/tick mismatch");
        if(!in.read(reinterpret_cast<char*>(state.data()),state.size()*sizeof(double))||in.peek()!=EOF)
            throw std::runtime_error("checkpoint size mismatch");
        // Hash includes tick/model metadata as well as payload.
        uint64_t checksum=hash_bytes(state.data(),state.size()*sizeof(double))^hash_bytes(header,5*sizeof(uint64_t));
        if(checksum!=header[5])throw std::runtime_error("checkpoint checksum mismatch");
        for(double x:state)if(!std::isfinite(x))throw std::runtime_error("nonfinite snapshot");
        tick=header[3];initial={state[n],state[n+1],state[n+2],state[n+3],state[n+4],false};
        if(state[n+5]!=0||std::abs(initial.time-tick*.0001)>1e-10||std::abs(state[0]-initial.time)>1e-10)
            throw std::runtime_error("clock or contact mismatch");
        // Validate rocket state before changing MuJoCo state.
        fly_rocket::VerticalPlant validate(p,initial);
        mj_setState(m.get(),d.get(),state.data(),mjSTATE_INTEGRATION);
    }
    fly_rocket::VerticalPlant rocket(p,initial);
    for(;tick<stop;++tick) {
        auto r=rocket.state();m->opt.gravity[2]=-1000*r.thrust/(1000+r.fuel);
        double throttle=std::clamp(d->qpos[m->jnt_qposadr[j]]/.3,0.,1.);
        d->ctrl[0]=tick>=2000&&tick<4000?2.:0.;
        mj_step(m.get(),d.get());rocket.advance_diagnostic(throttle,.0001);
        for(int i=0;i<mjNWARNING;++i)if(d->warning[i].number)throw std::runtime_error("MuJoCo warning");
    }
    mj_getState(m.get(),d.get(),state.data(),mjSTATE_INTEGRATION);
    auto r=rocket.state();double tail[]={r.time,r.altitude,r.velocity,r.fuel,r.thrust,double(r.contact)};
    std::copy(tail,tail+6,state.begin()+n);
    for(double x:state)if(!std::isfinite(x))throw std::runtime_error("nonfinite output");
    uint64_t header[]={magic,1,static_cast<uint64_t>(n),tick,identity,0};
    header[5]=hash_bytes(state.data(),state.size()*sizeof(double))^hash_bytes(header,5*sizeof(uint64_t));
    AtomicCheckpoint out(argv[2]);out.write(header,sizeof(header));out.write(state.data(),state.size()*sizeof(double));out.commit();
    return 0;
}catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
