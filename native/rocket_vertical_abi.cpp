#include "rocket_vertical.h"
#include <algorithm>
#include <cmath>

struct RocketHandle {
    fly_rocket::VerticalPlant plant;
    RocketHandle() : plant({200000., 6.5e10, 1000., 20000., 3000., .3},
                           {0., 2500., -20., 100., 0., false}) {}
    explicit RocketHandle(fly_rocket::State saved)
        : plant({200000., 6.5e10, 1000., 20000., 3000., .3}, saved) {}
};

extern "C" {
__declspec(dllexport) RocketHandle* rocket_new() {
    try { return new RocketHandle(); } catch (...) { return nullptr; }
}
__declspec(dllexport) void rocket_delete(RocketHandle* handle) { delete handle; }
__declspec(dllexport) int rocket_current_state(const RocketHandle* handle, double* state_out) {
    if (!handle || !state_out) return 0;
    const auto& s = handle->plant.state();
    state_out[0]=s.time;state_out[1]=s.altitude;state_out[2]=s.velocity;
    state_out[3]=s.fuel;state_out[4]=s.thrust;
    return 1;
}
// Six finite FP64 values, with contact encoded as exactly 0 or 1.
// This diagnostic ABI restores airborne states only; terminal landing is not modeled.
__declspec(dllexport) int rocket_snapshot(const RocketHandle* handle, double* state_out) {
    if (!rocket_current_state(handle, state_out)) return 0;
    state_out[5] = handle->plant.state().contact ? 1. : 0.;
    return 1;
}
__declspec(dllexport) RocketHandle* rocket_new_from_snapshot(const double* state_in) {
    if (!state_in) return nullptr;
    for (int i=0;i<6;++i) if (!std::isfinite(state_in[i])) return nullptr;
    if (state_in[5] != 0.) return nullptr;
    try {
        return new RocketHandle({state_in[0],state_in[1],state_in[2],
                                 state_in[3],state_in[4],false});
    } catch (...) { return nullptr; }
}
__declspec(dllexport) double rocket_world_gravity(const RocketHandle* handle) {
    return handle ? handle->plant.gravity_acceleration() : NAN;
}
// Returns thrust-derived effective cabin gravity in MuJoCo mm/s^2.
__declspec(dllexport) double rocket_effective_g(const RocketHandle* handle) {
    if (!handle) return NAN;
    const auto& s = handle->plant.state();
    return -1000. * s.thrust / (1000. + s.fuel);
}
__declspec(dllexport) int rocket_advance(RocketHandle* handle, double q_mm, double dt,
                                         double* state_out) {
    if (!handle || !state_out || !std::isfinite(q_mm)) return 0;
    try {
        handle->plant.advance_diagnostic(std::clamp(q_mm / .3, 0., 1.), dt);
        const auto& s = handle->plant.state();
        state_out[0] = s.time;
        state_out[1] = s.altitude;
        state_out[2] = s.velocity;
        state_out[3] = s.fuel;
        state_out[4] = s.thrust;
        return 1;
    } catch (...) { return 0; }
}
}
