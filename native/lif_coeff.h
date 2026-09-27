#pragma once
#include <cmath>

// Exact linear synaptic-current coupling over dt. Keep the historical path
// outside the cancellation region, preserving established source-profile bits.
struct LifCoupling {
    double value;
    bool changed_numerics;
};

inline LifCoupling lif_coupling(double dt, double membrane, double synapse) {
    const double a=std::exp(-dt/membrane);
    if (membrane==synapse) return {a*dt/membrane,false};
    const double delta=(dt/membrane)*((membrane-synapse)/synapse);
    if (std::abs(delta)<1e-4) {
        const double exprel=delta==0.0 ? 1.0 : -std::expm1(-delta)/delta;
        return {a*(dt/membrane)*exprel,true};
    }
    const double b=std::exp(-dt/synapse);
    return {(a-b)*synapse/(membrane-synapse),false};
}
