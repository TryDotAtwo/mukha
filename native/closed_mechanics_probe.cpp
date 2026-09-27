// Closed radial mechanics diagnostic. No neural controller or rotation.
#include <mujoco/mujoco.h>
#include "rocket_vertical.h"
#include <cstdio>
#include <memory>
#include <cmath>
#include <algorithm>
#include <cstring>
int main(int argc,char**argv) {
    if(argc!=3 && argc!=4)return 2;
    int scale=1;
    if(argc==4) {
        if(!std::strcmp(argv[3],"halfstep"))scale=2;
        else if(!std::strcmp(argv[3],"quarterstep"))scale=4;
        else if(!std::strcmp(argv[3],"eighthstep"))scale=8;
        else if(!std::strcmp(argv[3],"sixteenthstep"))scale=16;
        else if(!std::strcmp(argv[3],"thirtysecondstep"))scale=32;
        else if(!std::strcmp(argv[3],"sixtyfourthstep"))scale=64;
        else return 2;
    }
    FILE* out=std::fopen(argv[2],"w");if(!out)return 2;
    std::fprintf(out,"feedback,contact,pulse,tick,time,q_start_mm,q_end_mm,throttle,altitude_m,velocity_mps,fuel_kg,thrust_n,effective_g_mm_s2,motor_joint_rad\n");
    bool ok=true;
    for(int feedback=0;feedback<2 && ok;++feedback)for(int contact=0;contact<2 && ok;++contact)for(int pulse=0;pulse<2 && ok;++pulse) {
        if(scale>2 && (!contact || !pulse))continue; // refinement of driven pair only
        char error[2048]{};
        std::unique_ptr<mjModel,decltype(&mj_deleteModel)> m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
        if(!m){std::fprintf(stderr,"%s\n",error);ok=false;break;}
        int j=mj_name2id(m.get(),mjOBJ_JOINT,"control_slide"), key=mj_name2id(m.get(),mjOBJ_KEY,"neutral");
        if(j<0 || key<0 || m->nu<1 || std::abs(m->opt.timestep-.0001)>1e-15){ok=false;break;}
        for(int a=0;a<m->nu;++a)if(m->actuator_trnid[2*a]==j){ok=false;break;}
        if(!ok)break;
        if(!contact)m->opt.disableflags|=mjDSBL_CONTACT;
        m->opt.gravity[0]=m->opt.gravity[1]=m->opt.gravity[2]=0;
        m->opt.timestep/=scale;
        const int steps=10000*scale;
        std::unique_ptr<mjData,decltype(&mj_deleteData)>d(mj_makeData(m.get()),mj_deleteData);
        if(!d){ok=false;break;}
        mj_resetDataKeyframe(m.get(),d.get(),key);mj_forward(m.get(),d.get());
        fly_rocket::VerticalPlant rocket({200000.,6.5e10,1000.,20000.,3000.,.3},
                                         {0.,2500.,-20.,100.,0.,false});
        for(int tick=0;tick<steps && ok;++tick) {
            // Both solvers advance from t to t+dt. Rocket gets control at t.
            const double q=d->qpos[m->jnt_qposadr[j]];
            const double throttle=std::clamp(q/.3,0.,1.); // declared 0..0.3 mm travel
            // In a nonrotating co-falling cabin: g_world - a_cabin = -F/m.
            // Uniform gravity at the rocket reference point; mm/s^2 for MuJoCo.
            const auto start=rocket.state();
            const double effective_g=feedback ? -1000*start.thrust/(1000+start.fuel) : 0.;
            m->opt.gravity[2]=effective_g;
            d->ctrl[0]=pulse && tick>=steps/5 && tick<2*steps/5 ? 2. : 0.;
            mj_step(m.get(),d.get());
            rocket.advance_diagnostic(throttle,m->opt.timestep);
            const auto& r=rocket.state();
            ok=std::abs(d->time-r.time)<1e-10 && std::isfinite(r.altitude) && std::isfinite(r.velocity);
            for(int k=0;k<m->nq;++k)ok=ok && std::isfinite(d->qpos[k]);
            for(int k=0;k<m->nv;++k)ok=ok && std::isfinite(d->qvel[k]);
            for(int k=0;k<mjNWARNING;++k)ok=ok && d->warning[k].number==0;
            if(std::fprintf(out,"%d,%d,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",
                feedback,contact,pulse,tick+1,r.time,q,d->qpos[m->jnt_qposadr[j]],throttle,
                r.altitude,r.velocity,r.fuel,r.thrust,effective_g,
                d->qpos[m->jnt_qposadr[m->actuator_trnid[0]]])<0)ok=false;
        }
    }
    if(std::fflush(out) || std::ferror(out))ok=false;
    if(std::fclose(out))ok=false;
    return ok?0:1;
}
