// Isolated source-motivated conductance hypothesis, not a MaleCNS phenotype.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <initializer_list>

struct Result { double baseline, evoked, synaptic_state; };

Result simulate(double dt_ms, double baseline_shift_mv, double gmax) {
    constexpr double rest = -60.0, reversal = 0.0;
    constexpr double membrane_ms = 10.0, synapse_ms = 5.0, release = 0.5;
    double v = rest, g = 0.0;
    const int steps = int(std::lround(100.0 / dt_ms));
    for (int tick = 0; tick < steps; ++tick) {
        // Incoming conductance is held over the membrane substep. Explicit
        // scheduling allows convergence as dt is reduced.
        const double total = 1.0 + g;
        const double steady = (rest + baseline_shift_mv + g * reversal) / total;
        v = steady + (v - steady) * std::exp(-total * dt_ms / membrane_ms);
        g = g * std::exp(-dt_ms / synapse_ms) +
            gmax * release * (-std::expm1(-dt_ms / synapse_ms));
    }
    return {rest + baseline_shift_mv, v, g};
}

int main() {
    for (double dt : {0.2, 0.1, 0.05}) {
        for (double shift : {-5.0, 5.0}) {
            const auto on = simulate(dt, shift, 0.02);
            const auto off = simulate(dt, shift, 0.0);
            if (!std::isfinite(on.evoked) || !std::isfinite(off.evoked)) return 2;
            std::printf("%.8g %.8g %.17g %.17g %.17g\n", dt, shift,
                        on.evoked, off.evoked, on.synaptic_state);
        }
    }
    return 0;
}
