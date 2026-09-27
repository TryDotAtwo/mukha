// Live mechanical diagnostic: no neural controller, no rocket-to-body feedback.
#include <mujoco/mujoco.h>
#include "rocket_vertical.h"
#include <cstdio>
#include <memory>
#include <cmath>
#include <algorithm>
int main(int argc,char**argv) {
    if(argc!=3)return 2;
    FILE* out=std::fopen(argv[2],"w");if(!out)return 2;
    std::fprintf(out,"contact,pulse,tick,time,q_start_mm,q_end_mm,throttle,altitude_m,velocity_mps,fuel_kg,thrust_n\n");
    bool ok=true;
    for(int contact=0;contact<2 && ok;++contact)for(int pulse=0;pulse<2 && ok;++pulse) {
        char error[2048]{};
        std::unique_ptr<mjModel,decltype(&mj_deleteModel)> m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
        if(!m){std::fprintf(stderr,"%s\n",error);ok=false;break;}
        int j=mj_name2id(m.get(),mjOBJ_JOINT,"control_slide"), key=mj_name2id(m.get(),mjOBJ_KEY,"neutral");
        if(j<0 || key<0 || m->nu<1 || std::abs(m->opt.timestep-.0001)>1e-15){ok=false;break;}
        for(int a=0;a<m->nu;++a)if(m->actuator_trnid[2*a]==j){ok=false;break;}
        if(!ok)break;
        if(!contact)m->opt.disableflags|=mjDSBL_CONTACT;
        std::unique_ptr<mjData,decltype(&mj_deleteData)>d(mj_makeData(m.get()),mj_deleteData);
        if(!d){ok=false;break;}
        mj_resetDataKeyframe(m.get(),d.get(),key);mj_forward(m.get(),d.get());
        fly_rocket::VerticalPlant rocket({200000.,6.5e10,1000.,20000.,3000.,.3},
                                         {0.,2500.,-20.,100.,0.,false});
        for(int tick=0;tick<10000 && ok;++tick) {
            // Both solvers advance from t to t+dt. Rocket gets control at t.
            const double q=d->qpos[m->jnt_qposadr[j]];
            const double throttle=std::clamp(q/.3,0.,1.); // declared 0..0.3 mm travel
            d->ctrl[0]=pulse && tick>=2000 && tick<4000 ? 2. : 0.;
            mj_step(m.get(),d.get());
            rocket.advance_diagnostic(throttle,m->opt.timestep);
            const auto& r=rocket.state();
            ok=std::abs(d->time-r.time)<1e-10 && std::isfinite(r.altitude) && std::isfinite(r.velocity);
            for(int k=0;k<m->nq;++k)ok=ok && std::isfinite(d->qpos[k]);
            for(int k=0;k<m->nv;++k)ok=ok && std::isfinite(d->qvel[k]);
            for(int k=0;k<mjNWARNING;++k)ok=ok && d->warning[k].number==0;
            if(std::fprintf(out,"%d,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",
                contact,pulse,tick+1,r.time,q,d->qpos[m->jnt_qposadr[j]],throttle,
                r.altitude,r.velocity,r.fuel,r.thrust)<0)ok=false;
        }
    }
    if(std::fflush(out) || std::ferror(out))ok=false;
    if(std::fclose(out))ok=false;
    return ok?0:1;
}
