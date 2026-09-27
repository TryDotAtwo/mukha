// Static geometry diagnostic only: prescribed poses are NOT neural actions.
#include <mujoco/mujoco.h>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <memory>
int main(int argc,char**argv){
 if(argc!=3)return 2;
 char error[2048]{};
 std::unique_ptr<mjModel,decltype(&mj_deleteModel)>m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
 if(!m)return 3;
 std::unique_ptr<mjData,decltype(&mj_deleteData)>d(mj_makeData(m.get()),mj_deleteData);
 int key=mj_name2id(m.get(),mjOBJ_KEY,"neutral"),j=mj_name2id(m.get(),mjOBJ_JOINT,"lf_trochanterfemur-lf_tibia-pitch");
 int foot=mj_name2id(m.get(),mjOBJ_GEOM,"lf_tarsus5"),pad=mj_name2id(m.get(),mjOBJ_GEOM,"control_pad");
 if(!d||key<0||j<0||foot<0||pad<0)return 3;
 std::ofstream out(argv[2]);out<<std::setprecision(17)<<"delta_rad,angle_rad,distance_mm,foot_x,foot_y,foot_z,contacts\n";
 for(int i=-200;i<=200;++i){
  mj_resetDataKeyframe(m.get(),d.get(),key);double delta=i*.001;double& q=d->qpos[m->jnt_qposadr[j]];q+=delta;
  if(m->jnt_limited[j]&&(q<m->jnt_range[2*j]||q>m->jnt_range[2*j+1]))continue;
  mj_forward(m.get(),d.get());mjtNum points[6]{};
  double dist=mj_geomDistance(m.get(),d.get(),foot,pad,10.,points);
  if(!std::isfinite(dist)||dist>=10)return 4;
  int contacts=0;for(int c=0;c<d->ncon;++c)if(d->contact[c].geom[0]==pad||d->contact[c].geom[1]==pad)++contacts;
  out<<delta<<','<<q<<','<<dist;for(int a=0;a<3;++a)out<<','<<d->geom_xpos[3*foot+a];out<<','<<contacts<<'\n';
 }
 out.flush();return out?0:5;
}
