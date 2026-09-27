// Scalar numerical fixture for pinned Neurodriver conductance/aggregation equations.
// No neural graph or biological parameters are enabled by this diagnostic.
#include <algorithm>
#include <cmath>
#include <cstdio>
int main(){
    const double pre[]={-90,-80,-60,-20,-60};
    const double post[]={-50,-50,-50,-50,-90};
    const double expected_g[]={0,0,.016,.032,.016};
    const double expected_i[]={0,0,-.48,-.96,.16};
    for(int i=0;i<5;++i){
        double g=std::min(.0008*40, .00002*40*std::pow(std::max(0.,pre[i]+80),1.));
        double current=g*(-80-post[i]);
        if(std::abs(g-expected_g[i])>1e-14 || std::abs(current-expected_i[i])>1e-14)return 1;
        std::printf("case=%d g=%.17g I=%.17g\n",i,g,current);
    }
    return 0;
}
