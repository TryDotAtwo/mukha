#include "exposure_observation.h"
#include <iostream>
#include <iomanip>
#include <limits>
int main(){
    std::cout<<std::setprecision(17);
    // Rounded absolute 8.01-Hz boundaries avoid accumulated period-rounding drift.
    auto boundary=[](int i){return (std::int64_t(i)*100000000000LL+400)/801;};
    for(bool subdivide:{false,true}){
        fly_observation::Exposure e(.5,0,0,boundary(1));int frame=1;
        for(int epoch=0;epoch<2;++epoch){
            const std::int64_t target=epoch==0?75000000:boundary(8);
            while(e.time_ns()<target){
                const auto stop=subdivide?std::min(target,e.time_ns()+100000):target;
                auto r=e.advance_until(stop,epoch==0?240:0);
                if(r.complete){std::cout<<"frame "<<subdivide<<" "<<frame<<" "<<r.reached_ns<<" "<<r.mean<<"\n";
                    if(frame<8)e.next_frame(boundary(++frame));}
            }
        }
    }
    fly_observation::Exposure e(.5,0,0,100);int rejected=0;
    try{e.next_frame(200);}catch(const std::domain_error&){++rejected;}
    try{e.advance_until(0,1);}catch(const std::domain_error&){++rejected;}
    try{e.advance_until(10,std::numeric_limits<double>::quiet_NaN());}catch(const std::domain_error&){++rejected;}
    if(e.time_ns()!=0||e.state()!=0)return 2;
    e.advance_until(200,1);
    try{e.advance_until(200,1);}catch(const std::domain_error&){++rejected;}
    try{e.next_frame(100);}catch(const std::domain_error&){++rejected;}
    std::cout<<"rejected "<<rejected<<"\n";
}
