// Full native brain -> body diagnostic; no sensory feedback or learned control.
#include "cuda_state64.h"
#include "motor_filter.h"
#include "rocket_vertical.h"
#include <cstring>
#include <mujoco/mujoco.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <memory>
#include <charconv>
template<class T>void read(std::ifstream& f,T* p,std::size_t n){
 if(!f.read(reinterpret_cast<char*>(p),n*sizeof(T)))throw std::runtime_error("truncated graph");
}
int main(int argc,char**argv){try{
 if(argc<6||argc>9)return 2;
 const bool with_rocket=argc>=7,contacts=argc<8||std::strcmp(argv[7],"no-contact")!=0;
 if(argc>=8&&std::strcmp(argv[7],"no-contact")&&std::strcmp(argv[7],"contact"))return 2;
 int ticks=1000;
 if(argc==9){const char* end=argv[8]+std::strlen(argv[8]);auto parsed=std::from_chars(argv[8],end,ticks);
  if(parsed.ec!=std::errc{}||parsed.ptr!=end||ticks<1||ticks>100000)return 2;}
 std::ofstream environment,contact_log;
 if(with_rocket){environment.open(argv[6]);contact_log.open(std::string(argv[6])+".contacts.csv");if(!environment||!contact_log)return 2;
  contact_log<<std::setprecision(17)<<"enabled,tick,geometry_time,foot_x,foot_y,foot_z,pad_x,pad_y,pad_z,pad_contacts,normal_force_model_units\n";
  environment<<std::setprecision(17)<<"enabled,contact,tick,time,q_start_mm,q_end_mm,throttle,altitude_m,velocity_mps,fuel_kg,thrust_n,effective_g_mm_s2\n";}
 std::ifstream file(argv[2],std::ios::binary);uint32_t n,source;uint64_t e;
 read(file,&n,1);read(file,&e,1);read(file,&source,1);
 if(n!=167216||e!=25587572||source>=n)return 2;
 std::vector<uint64_t> row(n+1);std::vector<uint32_t> col(e);std::vector<double>w(e);
 read(file,row.data(),row.size());read(file,col.data(),col.size());read(file,w.data(),w.size());
 if(file.peek()!=EOF)return 2;
 std::ifstream mapfile(argv[3]);int channels;mapfile>>channels;if(channels!=24)return 2;
 std::vector<uint32_t> index(channels);std::vector<std::string>names(channels);std::vector<int>sign(channels);
 for(int i=0;i<channels;++i){mapfile>>index[i]>>names[i]>>sign[i];if(!mapfile||index[i]>=n)return 2;}
 std::ofstream out(argv[4]),events(argv[5]);if(!out||!events)return 2;
 out<<std::setprecision(17)<<"enabled,tick,actuator,control,position\n";events<<"enabled,tick,graph_index\n";
 std::vector<uint8_t>sense(n,0),spikes(n);sense[source]=1;
 std::vector<double>drive(n,0),v(n),g(n);std::vector<uint32_t>motor(channels);
 for(int enabled=0;enabled<2;++enabled){
  std::unique_ptr<ff_cuda64_model,decltype(&ff_cuda64_destroy)>brain(ff_cuda64_create(n,e,row.data(),col.data(),w.data(),sense.data(),{.1,-52,-52,-45,20,5,22,18},1),ff_cuda64_destroy);
  if(!brain)throw std::runtime_error(ff_cuda64_probe_error());
  char error[2048]{};std::unique_ptr<mjModel,decltype(&mj_deleteModel)>m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
  if(!m)throw std::runtime_error(error);
  if(!contacts)m->opt.disableflags|=mjDSBL_CONTACT;
  int slider=-1,foot=-1,pad=-1;
  if(with_rocket){foot=mj_name2id(m.get(),mjOBJ_GEOM,"lf_tarsus5");pad=mj_name2id(m.get(),mjOBJ_GEOM,"control_pad");if(foot<0||pad<0)return 2;}
  if(with_rocket){slider=mj_name2id(m.get(),mjOBJ_JOINT,"control_slide");if(slider<0)return 2;
   for(int a=0;a<m->nu;++a)if(m->actuator_trnid[2*a]==slider)return 2;
   m->opt.gravity[0]=m->opt.gravity[1]=m->opt.gravity[2]=0;}
  std::unique_ptr<mjData,decltype(&mj_deleteData)>d(mj_makeData(m.get()),mj_deleteData);if(!d)return 2;
  int key=mj_name2id(m.get(),mjOBJ_KEY,"neutral");if(key<0||std::abs(m->opt.timestep-.0001)>1e-15)return 2;
  mj_resetDataKeyframe(m.get(),d.get(),key);std::vector<fly_motor::Binding>bindings;
  for(int i=0;i<channels;++i){int a=mj_name2id(m.get(),mjOBJ_ACTUATOR,names[i].c_str());if(a<0)return 2;bindings.push_back({std::size_t(a),sign[i]});}
  fly_motor::Filter filter(bindings,m->nu,.0001,.020,.1,1);
  fly_rocket::VerticalPlant rocket({200000.,6.5e10,1000.,20000.,3000.,.3},{0.,2500.,-20.,100.,0.,false});
  for(int tick=0;tick<ticks;++tick){
   double q=0,throttle=0,effective_g=0;
   if(with_rocket){q=d->qpos[m->jnt_qposadr[slider]];throttle=std::clamp(q/.3,0.,1.);
    auto r=rocket.state();effective_g=-1000*r.thrust/(1000+r.fuel);m->opt.gravity[2]=effective_g;}
   drive[source]=tick%100==0?68.75:0;
   if(ff_cuda64_advance(brain.get(),1,drive.data(),v.data(),g.data(),spikes.data()))throw std::runtime_error(ff_cuda64_probe_error());
   for(uint32_t i=0;i<n;++i){if(!std::isfinite(v[i])||!std::isfinite(g[i]))return 3;if(spikes[i])events<<enabled<<','<<tick<<','<<i<<'\n';}
   for(int i=0;i<channels;++i)motor[i]=spikes[index[i]];
   const auto& command=filter.step(motor,enabled!=0);std::copy(command.begin(),command.end(),d->ctrl);
   mj_step(m.get(),d.get());if(std::abs(d->time-(tick+1)*.0001)>1e-12)return 3;
   // Euler mj_step retains geometry/contact data evaluated before integration.
   // Read only: no extra forward call that could alter solver warm starts.
   if(with_rocket){int count=0;double normal=0;
    for(int c=0;c<d->ncon;++c)if(d->contact[c].geom[0]==pad||d->contact[c].geom[1]==pad){mjtNum force[6]{};mj_contactForce(m.get(),d.get(),c,force);++count;normal+=force[0];}
    contact_log<<enabled<<','<<tick<<','<<tick*.0001;
    for(int geom:{foot,pad})for(int axis=0;axis<3;++axis)contact_log<<','<<d->geom_xpos[3*geom+axis];
    contact_log<<','<<count<<','<<normal<<'\n';}
   if(with_rocket){rocket.advance_diagnostic(throttle,.0001);auto r=rocket.state();
    if(std::abs(r.time-d->time)>1e-12)return 3;
    environment<<enabled<<','<<contacts<<','<<tick<<','<<r.time<<','<<q<<','<<d->qpos[m->jnt_qposadr[slider]]<<','<<throttle<<','<<r.altitude<<','<<r.velocity<<','<<r.fuel<<','<<r.thrust<<','<<effective_g<<'\n';}
   for(int k=0;k<mjNWARNING;++k)if(d->warning[k].number)return 3;
   for(int a=0;a<m->nu;++a){int j=m->actuator_trnid[2*a];if(j<0)return 2;double q=d->qpos[m->jnt_qposadr[j]];if(!std::isfinite(q))return 3;
    out<<enabled<<','<<tick<<','<<a<<','<<d->ctrl[a]<<','<<q<<'\n';}
  }
 }
 out.flush();events.flush();if(with_rocket){environment.flush();contact_log.flush();}return out&&events&&(!with_rocket||(environment&&contact_log))?0:3;
}catch(const std::exception& e){std::cerr<<e.what();return 1;}}
