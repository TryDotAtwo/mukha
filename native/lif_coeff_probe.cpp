#include "lif_coeff.h"
#include <cstdlib>
#include <iomanip>
#include <iostream>

int main(int argc,char** argv) {
    if(argc!=4) return 2;
    const double dt=std::strtod(argv[1],nullptr);
    const double tm=std::strtod(argv[2],nullptr);
    const double ts=std::strtod(argv[3],nullptr);
    const auto result=lif_coupling(dt,tm,ts);
    std::cout<<std::setprecision(17)<<result.value<<' '<<result.changed_numerics<<'\n';
}
