// Reference calibration math from Christenson et al. 2024 methods.
// Relative capture is dimensionless; this is NOT photons/s or a neural encoder.
#pragma once
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <algorithm>

namespace fly_calibration {
inline double log_capture(double q) {
    if (!std::isfinite(q) || q < 0) throw std::domain_error("invalid relative capture");
    return std::log((q + .001) / 1.001);
}

// Equation 9's per-cell normalized weighted dot product, without centering.
// Explicit zero weights exclude observations; nonfinite samples are rejected.
inline double response_alignment(const double* prediction, const double* measured,
                                 const double* counts, std::size_t n) {
    if (!prediction || !measured || !counts || !n)
        throw std::invalid_argument("empty calibration observations");
    double max_p=0, max_v=0, max_w=0;
    for(std::size_t i=0;i<n;++i) {
        if(!std::isfinite(prediction[i]) || !std::isfinite(measured[i]) ||
           !std::isfinite(counts[i]) || counts[i]<0)
            throw std::domain_error("invalid calibration observation");
        if(counts[i]>0) {
            max_p=std::max(max_p,std::abs(prediction[i]));
            max_v=std::max(max_v,std::abs(measured[i]));
            max_w=std::max(max_w,counts[i]);
        }
    }
    if(max_p==0 || max_v==0 || max_w==0)
        throw std::domain_error("undefined alignment for zero weighted norm");
    double dot=0, pp=0, vv=0;
    for(std::size_t i=0;i<n;++i) {
        if(counts[i]==0) continue;
        double p=prediction[i]/max_p, v=measured[i]/max_v, w=counts[i]/max_w;
        dot+=w*p*v; pp+=w*p*p; vv+=w*v*v;
    }
    if(pp==0 || vv==0) throw std::domain_error("weighted norm underflow");
    return std::clamp((dot/std::sqrt(pp))/std::sqrt(vv),-1.,1.);
}
}
