// Recorded full-CNS spikes -> declared engineering filter -> physical actuators.
// Not closed-loop neural control or a validated muscle model.
#include <mujoco/mujoco.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include "motor_filter.h"
int main(int argc,char**argv){
 if(argc!=4)return 2;
 std::ifstream input(argv[2]);int n=0;input>>n;if(n<1||n>100)return 2;
 std::vector<std::string> names(n);std::vector<int> signs(n);
 for(int i=0;i<n;++i){input>>names[i]>>signs[i];if(std::abs(signs[i])!=1)return 2;}
 int count;input>>count;if(!input||count<0||count>100000)return 2;
 std::vector<std::pair<int,int>>events(count);
 for(auto& e:events){input>>e.first>>e.second;if(!input||e.first<0||e.first>=1000||e.second<0||e.second>=n)return 2;}
 if(!std::is_sorted(events.begin(),events.end()))return 2;
 std::ofstream out(argv[3]);if(!out)return 2;
 out<<std::setprecision(17)<<"enabled,tick,actuator,control,position\n";
 for(int enabled=0;enabled<2;++enabled){
  char error[2048]{};auto* m=mj_loadXML(argv[1],nullptr,error,sizeof(error));
  if(!m){std::cerr<<error;return 2;}auto* d=mj_makeData(m);if(!d)return 2;
  auto key=mj_name2id(m,mjOBJ_KEY,"neutral");if(key<0||std::abs(m->opt.timestep-.0001)>1e-15)return 2;
  mj_resetDataKeyframe(m,d,key);std::vector<int> actuators(n);
  for(int i=0;i<n;++i){actuators[i]=mj_name2id(m,mjOBJ_ACTUATOR,names[i].c_str());if(actuators[i]<0)return 2;}
  std::vector<fly_motor::Binding> bindings;
  for(int i=0;i<n;++i)bindings.push_back({std::size_t(actuators[i]),signs[i]});
  fly_motor::Filter filter(bindings,m->nu,.0001,.020,.1,1.);
  std::vector<std::uint32_t> spikes(n,0);std::size_t event=0;
  for(int tick=0;tick<1000;++tick){
   std::fill(spikes.begin(),spikes.end(),0);
   while(event<events.size()&&events[event].first==tick){++spikes[events[event].second];++event;}
   const auto& commands=filter.step(spikes,enabled!=0);
   std::copy(commands.begin(),commands.end(),d->ctrl);
   mj_step(m,d);
   for(int k=0;k<mjNWARNING;++k)if(d->warning[k].number)return 3;
   for(int a=0;a<m->nu;++a){int j=m->actuator_trnid[2*a];if(j<0)return 2;
    double q=d->qpos[m->jnt_qposadr[j]];if(!std::isfinite(q))return 3;
    out<<enabled<<','<<tick<<','<<a<<','<<d->ctrl[a]<<','<<q<<'\n';}
  }
  if(event!=events.size())return 2;mj_deleteData(d);mj_deleteModel(m);
 }
 out.flush();return out?0:3;
}
