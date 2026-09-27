#include "dallmann_observation.h"
#include <iostream>
#include <iomanip>
int main(){
    std::cout<<std::setprecision(17);
    int mode;std::size_t n;double sr,threshold;
    try{
        while(std::cin>>mode>>n>>sr>>threshold){
            if(mode<0||mode>2||n<2||n>10000)return 2;
            std::vector<double> angle(n);
            for(auto& a:angle)if(!(std::cin>>a))return 2;
            auto p=dallmann_reference::predict(angle,sr,static_cast<dallmann_reference::Motion>(mode),threshold);
            for(auto y:p.calcium)std::cout<<y<<' ';
            std::cout<<'\n';
        }
        if(!std::cin.eof())return 2;
    }catch(const std::exception& e){std::cerr<<e.what();return 3;}
}
