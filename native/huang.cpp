// GPL-3.0-or-later. Derived from Luo/Huang/Schnitzer 2024 MATLAB model,
// commit 5d7c08a9a88f923169a0c3008aca68af421e9a7f. Aggregate reference only.
#include "huang.h"
#include <algorithm>
#include <cmath>

extern "C" int hm_simulate(const hm_parameters* p,const hm_event* events,size_t n,double* out,size_t count){
 if(!p||!events||!out||n==0||n>100000||count!=n*6)return -1;
 for(double x:p->weights)if(!std::isfinite(x))return -1;
 for(double x:p->recurrent)if(!std::isfinite(x))return -1;
 for(double x:p->tau)if(!std::isfinite(x)||x<=0)return -1;
 if(!std::isfinite(p->fw0)||!std::isfinite(p->fwdt)||!std::isfinite(p->adaptation_tau)||p->adaptation_tau<=0)return -1;
 size_t last=n;
 for(size_t i=0;i<n;++i){
  const auto& e=events[i];
  if(!std::isfinite(e.duration)||e.duration<0||!std::isfinite(e.punishment)||e.punishment<0||e.training<0||e.training>1)return -1;
  for(double x:e.odor)if(!std::isfinite(x)||x<0)return -1;
  if(e.training)last=i;
 }
 if(last==n)return -1;
 double inverse[6][12]={};
 for(int i=0;i<6;++i)for(int j=0;j<6;++j){inverse[i][j]=(i==j?1.:0.)-p->recurrent[6*i+j];inverse[i][j+6]=i==j?1.:0.;}
 for(int k=0;k<6;++k){
  int pivot=k;for(int i=k+1;i<6;++i)if(std::abs(inverse[i][k])>std::abs(inverse[pivot][k]))pivot=i;
  if(std::abs(inverse[pivot][k])<1e-14)return -1;
  for(int j=0;j<12;++j)std::swap(inverse[k][j],inverse[pivot][j]);
  double v=inverse[k][k];for(int j=0;j<12;++j)inverse[k][j]/=v;
  for(int i=0;i<6;++i)if(i!=k){v=inverse[i][k];for(int j=0;j<12;++j)inverse[i][j]-=v*inverse[k][j];}
 }
 const double punishment[6]={27.85,0,11.38,0,0,0},baseline[6]={0,0,0,35.2,9,11.2},maximum[3]={71.66,17.9,31.16};
 double weights[2][6],delta[2][3]={},odor_start[2]={1,1},elapsed=0;
 for(int o=0;o<2;++o)std::copy(p->weights,p->weights+6,weights[o]);
 for(size_t i=0;i<n;++i){
  const auto& e=events[i];double kc[2],drive[6],activity[6]={};
  for(int o=0;o<2;++o){
   double end=odor_start[o]*std::exp(-0.05*e.duration*e.odor[o]);
   end=1-(1-end)*std::exp(-e.duration/p->adaptation_tau);
   kc[o]=(odor_start[o]+end)*0.5*e.odor[o];odor_start[o]=end;
  }
  for(int j=0;j<6;++j)drive[j]=weights[0][j]*kc[0]+weights[1][j]*kc[1]+punishment[j]*e.punishment;
  for(int j=0;j<6;++j)for(int k=0;k<6;++k)activity[j]+=inverse[j][k+6]*drive[k];
  for(int iteration=0;iteration<10;++iteration){
   double next[6];for(int j=0;j<6;++j){
    double value=drive[j]+baseline[j];
    for(int k=0;k<6;++k)value+=p->recurrent[6*k+j]*activity[k];
    if(j>=3)value=std::clamp(value,0.,maximum[j-3]);
    next[j]=value-baseline[j];
   }
   std::copy(next,next+6,activity);
  }
  for(int j=0;j<3;++j){
   double value=weights[0][j]*kc[0]+weights[1][j]*kc[1];
   for(int k=3;k<6;++k)value+=p->recurrent[6*k+j]*activity[k];
   double induction=p->fw0*e.duration/90*value+p->fwdt*punishment[j]*e.duration/90*e.punishment;
   for(int o=0;o<2;++o)delta[o][j]+=kc[o]*induction;
  }
  if(i>last)elapsed+=e.duration;
  for(int j=0;j<3;++j){
   double early=p->tau[j==0?0:1],late=p->tau[j==0?0:2],decay;
   if(elapsed<=10800)decay=std::exp(-e.duration/early);
   else if(10800>elapsed-e.duration){double first=10800-(elapsed-e.duration);decay=std::exp(-first/early)*std::exp(-(e.duration-first)/late);}
   else decay=std::exp(-e.duration/late);
   for(int o=0;o<2;++o){delta[o][j]*=decay;weights[o][j+3]=p->weights[j+3]+delta[o][j];}
  }
  for(int j=0;j<6;++j){if(!std::isfinite(activity[j]))return -2;out[i*6+j]=activity[j];}
 }
 return 0;
}
