// Engineering spike-to-actuator interface; not measured muscle physiology.
#pragma once
#include <vector>
#include <cstdint>
#include <cmath>
#include <algorithm>
#include <stdexcept>
namespace fly_motor {
struct Binding {std::size_t actuator; int sign;};
class Filter {
    std::vector<Binding> map_;
    std::vector<double> activity_,next_,command_;
    double decay_,gain_,limit_;
public:
    Filter(std::vector<Binding> map,std::size_t actuators,double dt,double tau,double gain,double limit)
        :map_(std::move(map)),activity_(map_.size(),0),next_(map_.size(),0),command_(actuators,0),gain_(gain),limit_(limit){
        if(map_.empty()||!actuators||!std::isfinite(dt)||dt<=0||!std::isfinite(tau)||tau<=0||
           !std::isfinite(gain)||gain<0||!std::isfinite(limit)||limit<=0)
            throw std::domain_error("invalid motor filter parameters");
        for(auto b:map_)if(b.actuator>=actuators||(b.sign!=1&&b.sign!=-1))throw std::domain_error("invalid motor binding");
        decay_=std::exp(-dt/tau);
    }
    // Caller supplies this tick's per-channel spike counts, then applies commands
    // to the body step. No heap allocations in this operation. Disconnection
    // suppresses output while retaining the evolving filter state.
    const std::vector<double>& step(const std::vector<std::uint32_t>& spikes,bool enabled){
        if(spikes.size()!=activity_.size())throw std::domain_error("motor spike shape");
        std::fill(command_.begin(),command_.end(),0.);
        for(std::size_t i=0;i<activity_.size();++i){
            next_[i]=activity_[i]*decay_+spikes[i];
            if(!std::isfinite(next_[i]))throw std::overflow_error("motor activity overflow");
            if(enabled)command_[map_[i].actuator]+=gain_*map_[i].sign*next_[i];
        }
        for(auto& u:command_){if(!std::isfinite(u))throw std::overflow_error("motor command overflow");u=std::clamp(u,-limit_,limit_);}
        activity_.swap(next_);return command_;
    }
    const std::vector<double>& activity()const{return activity_;}
    // Snapshot is state only: owner must verify configuration and clock identity.
    void restore_activity(const std::vector<double>& saved){
        if(saved.size()!=activity_.size())throw std::domain_error("motor state shape");
        for(auto x:saved)if(!std::isfinite(x)||x<0)throw std::domain_error("invalid motor state");
        std::copy(saved.begin(),saved.end(),activity_.begin());
    }
};
}
