#include "calcium_observation.h"
#include <iostream>
#include <iomanip>
#include <limits>
int main() {
    std::cout<<std::setprecision(17);
    for(double dt:{0.,1e-12,1e-6,.075,1./8.01,2.}) {
        auto s=fly_observation::integrate(.2,3.,.5,dt);
        std::cout<<"segment "<<dt<<" "<<s.end_state<<" "<<s.integral<<"\n";
    }
    // A 75-ms pulse contained in a 125-ms frame. Split boundaries explicitly.
    const double frame=1./8.01;
    auto a=fly_observation::integrate(0,240,.5,.075);
    auto b=fly_observation::integrate(a.end_state,0,.5,frame-.075);
    double c=0,sum=0;
    for(int i=0;i<750;++i) {auto s=fly_observation::integrate(c,240,.5,.0001);c=s.end_state;sum+=s.integral;}
    auto tail=fly_observation::integrate(c,0,.5,frame-.075);sum+=tail.integral;
    std::cout<<"pulse "<<b.end_state<<" "<<(a.integral+b.integral)/frame<<" "<<sum/frame<<"\n";
    int rejected=0;
    for(double tau:{0.,-1.,std::numeric_limits<double>::quiet_NaN()})
        try {fly_observation::integrate(0,1,tau,.1);}catch(const std::domain_error&){++rejected;}
    try{fly_observation::integrate(0,1,.5,-.1);}catch(const std::domain_error&){++rejected;}
    std::cout<<"rejected "<<rejected<<"\n";
}
