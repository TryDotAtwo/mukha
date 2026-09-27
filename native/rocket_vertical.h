// First curriculum plant: radial, airless flight. No pilot or body controller.
#pragma once
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace fly_rocket {
struct Parameters {
    double radius, mu, dry_mass, max_thrust, exhaust_speed, engine_tau;
};
struct State {
    double time, altitude, velocity, fuel, thrust;
    bool contact;
};
class VerticalPlant {
    Parameters p;
    State s;
    double target=0;
    double force(double t) const {
        return p.engine_tau==0 ? target : target+(s.thrust-target)*std::exp(-t/p.engine_tau);
    }
    double impulse(double t) const {
        return p.engine_tau==0 ? target*t : target*t+(s.thrust-target)*p.engine_tau*(-std::expm1(-t/p.engine_tau));
    }
    double acceleration(double t,double z) const {
        const double mass=p.dry_mass+std::max(0.,s.fuel-impulse(t)/p.exhaust_speed);
        return force(t)/mass-p.mu/((p.radius+z)*(p.radius+z));
    }
    State integrate(double h) const {
        double a1=acceleration(0,s.altitude), v1=s.velocity;
        double v2=s.velocity+h*a1/2, a2=acceleration(h/2,s.altitude+h*v1/2);
        double v3=s.velocity+h*a2/2, a3=acceleration(h/2,s.altitude+h*v2/2);
        double v4=s.velocity+h*a3, a4=acceleration(h,s.altitude+h*v3);
        return {s.time+h,s.altitude+h*(v1+2*v2+2*v3+v4)/6,
            s.velocity+h*(a1+2*a2+2*a3+a4)/6,
            std::max(0.,s.fuel-impulse(h)/p.exhaust_speed),force(h),false};
    }
public:
    VerticalPlant(Parameters params,State initial):p(params),s(initial) {
        for(double x:{p.radius,p.mu,p.dry_mass,p.max_thrust,p.exhaust_speed,p.engine_tau,
                      s.time,s.altitude,s.velocity,s.fuel,s.thrust})
            if(!std::isfinite(x)) throw std::invalid_argument("nonfinite plant state");
        if(p.radius<=0 || p.mu<0 || p.dry_mass<=0 || p.max_thrust<0 || p.exhaust_speed<=0 ||
           p.engine_tau<0 || s.time<0 || s.altitude<=0 || s.fuel<0 || s.thrust<0 ||
           s.thrust>p.max_thrust || s.contact) throw std::invalid_argument("invalid plant configuration");
        if(s.fuel==0) s.thrust=0;
    }
    const State& state() const {return s;}
    double gravity_acceleration() const {
        return -p.mu/((p.radius+s.altitude)*(p.radius+s.altitude));
    }
    // Diagnostic fixture input only. Runtime cockpit integration is not supplied.
    void advance_diagnostic(double throttle,double h) {
        if(!std::isfinite(throttle) || throttle<0 || throttle>1 || !std::isfinite(h) || h<=0 || h>.1)
            throw std::invalid_argument("invalid diagnostic input or step");
        if(s.contact) return; // terminal first-contact record, not a settled lander
        double remaining=h;
        while(remaining>0) {
            target=s.fuel>0 ? throttle*p.max_thrust : 0;
            if(s.fuel==0) s.thrust=0;
            double dt=remaining;
            bool depletion=s.fuel>0 && impulse(dt)>=s.fuel*p.exhaust_speed;
            if(depletion) {
                double lo=0,hi=dt;
                for(int i=0;i<60;++i) {double mid=(lo+hi)/2;
                    if(impulse(mid)<s.fuel*p.exhaust_speed) lo=mid; else hi=mid;}
                dt=hi;
            }
            State next=integrate(dt);
            double contact_bracket=dt;
            if(s.velocity<0 && next.velocity>0) {
                double lo=0,hi=dt;
                for(int i=0;i<60;++i) {double mid=(lo+hi)/2;
                    if(integrate(mid).velocity<0) lo=mid; else hi=mid;}
                contact_bracket=hi;
            }
            if(integrate(contact_bracket).altitude<=0) {
                double lo=0,hi=contact_bracket;
                for(int i=0;i<60;++i) {double mid=(lo+hi)/2;
                    if(integrate(mid).altitude>0) lo=mid; else hi=mid;}
                s=integrate(hi);s.altitude=0;s.contact=true;return;
            }
            s=next;
            if(depletion) {s.fuel=0;s.thrust=0;}
            remaining-=dt;
        }
    }
};
}
