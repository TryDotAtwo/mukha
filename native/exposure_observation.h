#pragma once
#include "calcium_observation.h"
#include <cstdint>
#include <algorithm>
namespace fly_observation {
struct ExposureResult { std::int64_t reached_ns; bool complete; double mean; };
// Caller supplies consecutive exposure boundaries; no hidden resampling or gaps.
// advance_until stops at the frame boundary. The caller then opens the next frame
// and retries the same held input until its requested time has been reached.
class Exposure {
    double tau_,state_,integral_=0;
    std::int64_t now_,start_,end_;
public:
    Exposure(double tau,double initial,std::int64_t start,std::int64_t end)
        :tau_(tau),state_(initial),now_(start),start_(start),end_(end) {
        if(start<0||end<=start)throw std::domain_error("invalid exposure bounds");
        integrate(initial,0,tau,0);
    }
    ExposureResult advance_until(std::int64_t requested_end,double drive) {
        if(requested_end<=now_||now_==end_)throw std::domain_error("exposure cannot advance");
        const auto reached=std::min(requested_end,end_);
        auto segment=integrate(state_,drive,tau_,double(reached-now_)*1e-9);
        const double accumulated=integral_+segment.integral;
        if(!std::isfinite(accumulated))throw std::overflow_error("exposure overflow");
        const bool complete=reached==end_;
        const double mean=complete?accumulated/(double(end_-start_)*1e-9):0;
        if(!std::isfinite(mean))throw std::overflow_error("exposure mean overflow");
        state_=segment.end_state;integral_=accumulated;now_=reached;
        return {reached,complete,mean};
    }
    void next_frame(std::int64_t end) {
        if(now_!=end_||end<=end_)throw std::domain_error("nonconsecutive exposure");
        start_=now_;end_=end;integral_=0;
    }
    double state()const{return state_;}
    std::int64_t time_ns()const{return now_;}
};
}
