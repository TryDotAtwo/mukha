#include "motor_filter.h"
#include <iostream>
#include <limits>
int main(){
 using namespace fly_motor;
 std::vector<Binding> map={{0,1},{0,-1},{1,1}};
 Filter a(map,2,.0001,.02,.1,1);
 if(a.step({100,99,100},true)!=std::vector<double>({.1,1})){
  // Floating cancellation is allowed; verify tolerance below.
  auto state=a.activity();if(state!=std::vector<double>({100,99,100}))return 1;
 }
 auto saved=a.activity();Filter b(map,2,.0001,.02,.1,1);b.restore_activity(saved);
 for(int i=0;i<1000;++i){
  std::vector<std::uint32_t> s={std::uint32_t(i%7==0),0,std::uint32_t(i%11==0)};
  auto x=a.step(s,i%13!=0);auto y=b.step(s,i%13!=0);if(x!=y||a.activity()!=b.activity())return 1;
  if(i%13==0&&(x[0]!=0||x[1]!=0))return 1;
  for(auto u:x)if(std::abs(u)>1)return 1;
 }
 saved=a.activity();int rejected=0;
 try{a.restore_activity({0});}catch(const std::domain_error&){++rejected;}
 try{a.restore_activity({0,-1,0});}catch(const std::domain_error&){++rejected;}
 try{a.restore_activity({0,std::numeric_limits<double>::quiet_NaN(),0});}catch(const std::domain_error&){++rejected;}
 try{a.step({1},true);}catch(const std::domain_error&){++rejected;}
 if(rejected!=4||a.activity()!=saved)return 1;
 Filter sum(map,2,.0001,.02,.1,1);auto u=sum.step({100,99,100},true);
 if(std::abs(u[0]-.1)>1e-14||u[1]!=1)return 1;
 std::cout<<"1000 resumed steps exact; clamp after aggregation; disconnect and 4 invalid-state checks pass\n";
}
