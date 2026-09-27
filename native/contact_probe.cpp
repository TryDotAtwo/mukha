#include <mujoco/mujoco.h>
#include <cmath>
#include <cstdio>
#include <memory>

int main(int argc,char**argv){
 if(argc!=3)return 2;
 FILE* out=std::fopen(argv[2],"w"); if(!out)return 1;
 std::fprintf(out,"contact,pulse,tick,time,slider_q,slider_v,normal_force,contacts\n");
 bool passed=true; double displacement[4]={};
 for(int contact=0;contact<2;++contact)for(int pulse=0;pulse<2;++pulse){
  char error[2048]={};
  std::unique_ptr<mjModel,decltype(&mj_deleteModel)>m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
  if(!m){std::fprintf(stderr,"%s\n",error);std::fclose(out);return 1;}
  const int joint=mj_name2id(m.get(),mjOBJ_JOINT,"control_slide");
  const int key=mj_name2id(m.get(),mjOBJ_KEY,"neutral");
  const int pad=mj_name2id(m.get(),mjOBJ_GEOM,"control_pad");
  if(joint<0||key<0||pad<0){std::fclose(out);return 1;}
  for(int a=0;a<m->nu;++a)if(m->actuator_trnid[2*a]==joint){std::fclose(out);return 1;}
  if(!contact)m->opt.disableflags|=mjDSBL_CONTACT;
  std::unique_ptr<mjData,decltype(&mj_deleteData)>d(mj_makeData(m.get()),mj_deleteData);
  mj_resetDataKeyframe(m.get(),d.get(),key);mj_forward(m.get(),d.get());
  double maximum=0,force_max=0;int contacts=0,warnings=0;
  for(int tick=0;tick<10000;++tick){
   d->ctrl[0]=pulse&&tick>=2000&&tick<4000?2.0:0.0;
   mj_step(m.get(),d.get());
   double force=0;int count=0;
   for(int c=0;c<d->ncon;++c)if(d->contact[c].geom[0]==pad||d->contact[c].geom[1]==pad){
    double wrench[6];mj_contactForce(m.get(),d.get(),c,wrench);force+=wrench[0];++count;
   }
   const double q=d->qpos[m->jnt_qposadr[joint]],v=d->qvel[m->jnt_dofadr[joint]];
   for(int j=0;j<m->nq;++j)passed&=std::isfinite(d->qpos[j]);
   for(int j=0;j<m->nv;++j)passed&=std::isfinite(d->qvel[j]);
   maximum=std::fmax(maximum,std::abs(q));force_max=std::fmax(force_max,force);contacts+=count;
   std::fprintf(out,"%d,%d,%d,%.17g,%.17g,%.17g,%.17g,%d\n",contact,pulse,tick+1,d->time,q,v,force,count);
  }
  for(int w=0;w<mjNWARNING;++w)warnings+=d->warning[w].number;
  passed&=warnings==0;
  displacement[2*contact+pulse]=maximum;
  std::printf("{\"contact\":%d,\"pulse\":%d,\"max_slider_mm\":%.17g,\"max_normal_force\":%.17g,\"contact_samples\":%d,\"warnings\":%d}\n",contact,pulse,maximum,force_max,contacts,warnings);
 }
 passed&=displacement[0]<1e-12&&displacement[1]<1e-12&&displacement[3]>displacement[2]+1e-4;
 bool io_ok=std::fflush(out)==0&&!std::ferror(out);io_ok&=std::fclose(out)==0;
 return passed&&io_ok?0:1;
}
