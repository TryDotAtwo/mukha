// Same-model, in-memory checkpoint test. No portable checkpoint format claimed.
#include <mujoco/mujoco.h>
#include "rocket_vertical.h"
#include <memory>
#include <vector>
#include <cstdio>
#include <cmath>
#include <algorithm>
int main(int argc,char**argv) {
    if(argc!=2)return 2;
    char error[2048]{};
    std::unique_ptr<mjModel,decltype(&mj_deleteModel)>m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
    if(!m){std::fprintf(stderr,"%s\n",error);return 2;}
    auto make=[&](){return std::unique_ptr<mjData,decltype(&mj_deleteData)>(mj_makeData(m.get()),mj_deleteData);};
    auto a=make(),b=make();if(!a||!b)return 2;
    int key=mj_name2id(m.get(),mjOBJ_KEY,"neutral"),j=mj_name2id(m.get(),mjOBJ_JOINT,"control_slide");
    if(key<0||j<0||m->nu<1||m->opt.timestep!=.0001)return 2;
    m->opt.gravity[0]=m->opt.gravity[1]=m->opt.gravity[2]=0;
    mj_resetDataKeyframe(m.get(),a.get(),key);mj_forward(m.get(),a.get());
    fly_rocket::Parameters p{200000.,6.5e10,1000.,20000.,3000.,.3};
    fly_rocket::VerticalPlant r(p,{0.,2500.,-20.,100.,0.,false});
    auto step=[&](mjData* d,fly_rocket::VerticalPlant& plant,int tick){
        auto start=plant.state();
        m->opt.gravity[2]=-1000*start.thrust/(1000+start.fuel);
        double command=std::clamp(d->qpos[m->jnt_qposadr[j]]/.3,0.,1.);
        d->ctrl[0]=tick>=2000&&tick<4000?2.:0.;
        mj_step(m.get(),d);plant.advance_diagnostic(command,m->opt.timestep);
    };
    for(int tick=0;tick<3000;++tick)step(a.get(),r,tick);
    int n=mj_stateSize(m.get(),mjSTATE_INTEGRATION);
    std::vector<double> saved(n),sa(n),sb(n);
    mj_getState(m.get(),a.get(),saved.data(),mjSTATE_INTEGRATION);
    mj_setState(m.get(),b.get(),saved.data(),mjSTATE_INTEGRATION);
    fly_rocket::VerticalPlant resumed(p,r.state());
    double max_error=0;bool exact=true;
    for(int tick=3000;tick<10000;++tick) {
        step(a.get(),r,tick);step(b.get(),resumed,tick);
        mj_getState(m.get(),a.get(),sa.data(),mjSTATE_INTEGRATION);
        mj_getState(m.get(),b.get(),sb.data(),mjSTATE_INTEGRATION);
        for(int i=0;i<n;++i) {
            if(!std::isfinite(sa[i])||!std::isfinite(sb[i]))return 1;
            exact=exact&&sa[i]==sb[i];max_error=std::max(max_error,std::abs(sa[i]-sb[i]));
        }
        auto x=r.state(),y=resumed.state();
        exact=exact&&x.time==y.time&&x.altitude==y.altitude&&x.velocity==y.velocity&&
            x.fuel==y.fuel&&x.thrust==y.thrust&&x.contact==y.contact;
        for(int i=0;i<mjNWARNING;++i)if(a->warning[i].number||b->warning[i].number)return 1;
    }
    std::printf("{\"exact\":%s,\"body_state_values\":%d,\"checkpoint_tick\":3000,\"compared_ticks\":7000,\"max_body_error\":%.17g}\n",exact?"true":"false",n,max_error);
    return exact?0:1;
}
