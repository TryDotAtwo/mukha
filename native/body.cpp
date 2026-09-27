#include "body.h"
#include <mujoco/mujoco.h>
#include <algorithm>
#include <cmath>
#include <memory>
#include <new>
#include <string>

struct fb_body {
 std::unique_ptr<mjModel,decltype(&mj_deleteModel)> model{nullptr,mj_deleteModel};
 std::unique_ptr<mjData,decltype(&mj_deleteData)> data{nullptr,mj_deleteData};
 int neutral=-1,control=-1,state_size=0;
 bool healthy=true;
 double contact_eval_time=0;
 bool contact_valid=false;
};
static thread_local std::string last_error;
static int fail(const char* message){last_error=message;return -1;}
extern "C" {
const char* fb_error(){return last_error.c_str();}
fb_body* fb_create(const char* path){
 try{
  if(!path){fail("null path");return nullptr;}
  auto b=std::make_unique<fb_body>();char error[2048]={};
  b->model.reset(mj_loadXML(path,nullptr,error,sizeof(error)));
  if(!b->model){last_error=error;return nullptr;}
  auto m=b->model.get();
  b->neutral=mj_name2id(m,mjOBJ_KEY,"neutral");
  b->control=mj_name2id(m,mjOBJ_JOINT,"control_slide");
  if(b->neutral<0||b->control<0){fail("requires declared neutral pose and control_slide");return nullptr;}
  for(int a=0;a<m->nu;++a){
   const int j=m->actuator_trnid[2*a];
   if(m->actuator_trntype[a]!=mjTRN_JOINT||j==b->control||!m->actuator_ctrllimited[a]||!m->actuator_forcelimited[a]){
    fail("actuators must be bounded joint drives, never control drives");return nullptr;
   }
  }
  b->data.reset(mj_makeData(m));if(!b->data){fail("allocation failed");return nullptr;}
  b->state_size=mj_stateSize(m,mjSTATE_INTEGRATION);
  if(fb_reset(b.get()))return nullptr;
  return b.release();
 }catch(const std::exception& e){last_error=e.what();return nullptr;}
}
void fb_destroy(fb_body* b){delete b;}
size_t fb_controls(const fb_body* b){return b?static_cast<size_t>(b->model->nu):0;}
size_t fb_state_size(const fb_body* b){return b?b->state_size:0;}
int fb_reset(fb_body* b){
 if(!b)return fail("null handle");
 mj_resetDataKeyframe(b->model.get(),b->data.get(),b->neutral);
 mj_forward(b->model.get(),b->data.get());b->healthy=true;
 b->contact_eval_time=b->data->time;b->contact_valid=true;return 0;
}
int fb_advance(fb_body* b,const double* u,size_t n,uint32_t ticks){
 if(!b||!u||n!=fb_controls(b)||ticks==0||ticks>10000)return fail("invalid advance dimensions");
 if(!b->healthy)return fail("body requires explicit reset after solver failure");
 auto m=b->model.get();auto d=b->data.get();
 for(size_t i=0;i<n;++i)if(!std::isfinite(u[i])||u[i]<m->actuator_ctrlrange[2*i]||u[i]>m->actuator_ctrlrange[2*i+1])return fail("command outside declared bounds");
 std::copy(u,u+n,d->ctrl);
 for(uint32_t t=0;t<ticks;++t){
  b->contact_eval_time=d->time;
  mj_step(m,d);
  b->contact_valid=true;
  bool valid=true;
  for(int j=0;j<m->nq;++j)valid&=std::isfinite(d->qpos[j]);
  for(int j=0;j<m->nv;++j)valid&=std::isfinite(d->qvel[j]);
  for(int w=0;w<mjNWARNING;++w)valid&=d->warning[w].number==0;
  if(!valid){b->healthy=false;return fail("nonfinite state or MuJoCo warning");}
 }
 return 0;
}
int fb_state(const fb_body* b,double* out,size_t n){
 if(!b||!out||n!=fb_state_size(b)||!b->healthy)return fail("invalid state request");
 mj_getState(b->model.get(),b->data.get(),out,mjSTATE_INTEGRATION);return 0;
}
int fb_restore(fb_body* b,const double* in,size_t n){
 if(!b||!in||n!=fb_state_size(b)||!b->healthy)return fail("invalid snapshot request");
 for(size_t i=0;i<n;++i)if(!std::isfinite(in[i]))return fail("nonfinite snapshot");
 mj_setState(b->model.get(),b->data.get(),in,mjSTATE_INTEGRATION);
 b->contact_valid=false;return 0;
}
int fb_control_position(const fb_body* b,double* time,double* position){
 if(!b||!time||!position||!b->healthy)return fail("invalid observation request");
 *time=b->data->time;*position=b->data->qpos[b->model->jnt_qposadr[b->control]];return 0;
}
int fb_joint_position(const fb_body* b,const char* name,double* position){
 if(!b||!name||!position||!b->healthy)return fail("invalid joint observation");
 const int j=mj_name2id(b->model.get(),mjOBJ_JOINT,name);
 if(j<0||(b->model->jnt_type[j]!=mjJNT_HINGE&&b->model->jnt_type[j]!=mjJNT_SLIDE))return fail("requires named scalar joint");
 *position=b->data->qpos[b->model->jnt_qposadr[j]];return 0;
}
int fb_contact_normal(const fb_body* b,const char* name,double* evaluation_time,
                      double* normal_force,uint32_t* contact_count){
 if(!b||!name||!evaluation_time||!normal_force||!contact_count||!b->healthy||!b->contact_valid)
  return fail("invalid contact observation");
 const int geom=mj_name2id(b->model.get(),mjOBJ_GEOM,name);
 if(geom<0)return fail("unknown contact geometry");
 double force=0;uint32_t count=0;
 for(int c=0;c<b->data->ncon;++c){
  const auto& contact=b->data->contact[c];
  if(contact.geom[0]!=geom&&contact.geom[1]!=geom)continue;
  mjtNum wrench[6]{};
  mj_contactForce(b->model.get(),b->data.get(),c,wrench);
  if(!std::isfinite(wrench[0])||wrench[0]<0)return fail("invalid contact force");
  force+=wrench[0];++count;
 }
 if(!std::isfinite(force))return fail("contact force overflow");
 *evaluation_time=b->contact_eval_time;*normal_force=force;*contact_count=count;return 0;
}
int fb_contact_points(const fb_body* b,const char* name,double* samples,
                      size_t capacity,uint32_t* count,double* evaluation_time){
 if(!b||!name||!count||!evaluation_time||!b->healthy||!b->contact_valid||
    (capacity&&!samples))return fail("invalid contact point request");
 const int geom=mj_name2id(b->model.get(),mjOBJ_GEOM,name);
 if(geom<0)return fail("unknown contact geometry");
 size_t found=0;
 for(int c=0;c<b->data->ncon;++c){
  const auto& contact=b->data->contact[c];
  if(contact.geom[0]!=geom&&contact.geom[1]!=geom)continue;
  if(++found>capacity)return fail("contact point capacity exceeded");
  mjtNum wrench[6]{};mj_contactForce(b->model.get(),b->data.get(),c,wrench);
  if(!std::isfinite(wrench[0])||wrench[0]<0)return fail("invalid contact force");
  for(int k=0;k<3;++k)if(!std::isfinite(contact.pos[k]))
   return fail("nonfinite contact geometry");
  for(int k=0;k<9;++k)if(!std::isfinite(contact.frame[k]))
   return fail("nonfinite contact frame");
  for(int k=1;k<3;++k)if(!std::isfinite(wrench[k]))return fail("nonfinite contact force");
 }
 if(found>UINT32_MAX)return fail("contact point count overflow");
 size_t j=0;
 for(int c=0;c<b->data->ncon;++c){
  const auto& contact=b->data->contact[c];
  if(contact.geom[0]!=geom&&contact.geom[1]!=geom)continue;
  mjtNum wrench[6]{};mj_contactForce(b->model.get(),b->data.get(),c,wrench);
  const double sign=contact.geom[0]==geom?-1.:1.;
  for(int k=0;k<3;++k)samples[10*j+k]=contact.pos[k];
  for(int k=0;k<3;++k)samples[10*j+3+k]=sign*contact.frame[k];
  for(int k=0;k<3;++k)samples[10*j+6+k]=sign*(wrench[0]*contact.frame[k]+
      wrench[1]*contact.frame[3+k]+wrench[2]*contact.frame[6+k]);
  samples[10*j+9]=wrench[0];++j;
 }
 *count=static_cast<uint32_t>(found);*evaluation_time=b->contact_eval_time;return 0;
}
}
