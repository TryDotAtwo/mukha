// Observation hypothesis, not identified GCaMP kinetics or a sensory encoder.
#pragma once
#include <cmath>
#include <stdexcept>
namespace fly_observation {
struct Segment { double end_state; double integral; };
// dc/dt=(drive-c)/tau, held drive. Integral permits exact exposure accumulation.
inline Segment integrate(double initial,double drive,double tau,double duration) {
    if(!std::isfinite(initial)||!std::isfinite(drive)||!std::isfinite(tau)||
       !std::isfinite(duration)||tau<=0||duration<0)
        throw std::domain_error("invalid observation segment");
    if(duration==0) return {initial,0};
    const double x=duration/tau;
    const double gain=-std::expm1(-x);
    // Avoid cancellation of duration-tau*gain for small duration/tau.
    const double lag = x<1e-4 ? duration*x*(.5-x/6+x*x/24-x*x*x/120) : duration-tau*gain;
    Segment result{initial+(drive-initial)*gain, initial*duration+(drive-initial)*lag};
    if(!std::isfinite(result.end_state)||!std::isfinite(result.integral))
        throw std::overflow_error("observation overflow");
    return result;
}
}
