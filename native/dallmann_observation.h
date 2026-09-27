// Port of hook/club branches of imaging_predict_gcamp.m at e1233f4a.
// Copyright (c) 2024 chrisjdallmann, MIT; full notice retained at
// data/reference/feco_inhibition/LICENSE. Offline replication, not neural output.
#pragma once
#include <vector>
#include <cmath>
#include <stdexcept>
namespace dallmann_reference {
enum class Motion {hook_flex,hook_ext,club,claw,nine_a,web};
struct Prediction {std::vector<double> activation,kernel,calcium;};
inline Prediction predict(const std::vector<double>& angle,double sr,Motion mode,double threshold,
                          const std::vector<double>& behavioral_mask={}){
    const auto n=angle.size();
    if(n<2||!std::isfinite(sr)||sr<=0||!std::isfinite(threshold))
        throw std::domain_error("invalid observation input");
    if(mode!=Motion::hook_flex&&mode!=Motion::hook_ext&&mode!=Motion::club&&
       mode!=Motion::claw&&mode!=Motion::nine_a&&mode!=Motion::web)
        throw std::domain_error("unknown motion model");
    if(mode==Motion::nine_a&&behavioral_mask.size()!=n)
        throw std::domain_error("9A requires explicit behavioral mask");
    if(mode!=Motion::nine_a&&!behavioral_mask.empty())
        throw std::domain_error("unexpected behavioral mask");
    for(auto a:behavioral_mask)if(!std::isfinite(a))throw std::domain_error("nonfinite mask");
    for(auto a:angle)if(!std::isfinite(a))throw std::domain_error("nonfinite angle");
    Prediction p{std::vector<double>(n),std::vector<double>(n),std::vector<double>(n)};
    double sum=0;
    for(std::size_t i=0;i<n;++i){
        const auto j=i?i:1;
        double v=(angle[j]-angle[j-1])*sr;
        if(!std::isfinite(v))throw std::overflow_error("angle derivative overflow");
        if(mode==Motion::nine_a&&behavioral_mask[i]==1)v=0;
        if(mode==Motion::claw){
            const double x=angle[i]-80;
            p.activation[i]=-4.28350195279596e-09*std::pow(x,4)
                -3.08701145496934e-07*std::pow(x,3)
                +.000123726627502515*std::pow(x,2)
                +.000474757347677466*x-.0357758464550021;
        }else if(mode==Motion::web)p.activation[i]=angle[i];
        else p.activation[i]=mode==Motion::hook_flex?v<threshold:
            mode==Motion::hook_ext?v>threshold:(v>threshold||v<-threshold);
        if(!std::isfinite(p.activation[i]))throw std::overflow_error("activation overflow");
        // Preserve author's inclusive linspace endpoint N/sr (not (N-1)/sr).
        const double t=double(i)*(double(n)/sr)/double(n-1);
        p.kernel[i]=std::exp(-t/.30)-std::exp(-t/.03);sum+=p.kernel[i];
    }
    if(!std::isfinite(sum)||sum<=0)throw std::domain_error("degenerate observation kernel");
    for(auto& k:p.kernel)k/=sum;
    for(std::size_t i=0;i<n;++i)
        for(std::size_t j=0;j<=i;++j)p.calcium[i]+=p.activation[j]*p.kernel[i-j];
    return p;
}
}
