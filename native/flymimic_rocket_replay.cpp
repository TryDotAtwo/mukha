// One-way diagnostic replay of measured FlyMimic passive-slide positions.
#include "rocket_vertical.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>

int main(int argc, char** argv) {
    if (argc != 3 && argc != 4) return 2;
    const int case_count = argc == 4 ? std::atoi(argv[3]) : 4;
    if (case_count < 1 || case_count > 16) return 2;
    FILE* input = std::fopen(argv[1], "r");
    FILE* output = std::fopen(argv[2], "w");
    if (!input || !output) return 2;
    std::fprintf(output, "case_id,tick,time,q_start_mm,throttle,altitude_m,velocity_mps,fuel_kg,thrust_n\n");
    bool ok = true;
    for (int case_id = 0; case_id < case_count && ok; ++case_id) {
        fly_rocket::VerticalPlant rocket({200000., 6.5e10, 1000., 20000., 3000., .3},
                                         {0., 2500., -20., 100., 0., false});
        for (int tick = 0; tick < 1000; ++tick) {
            int parsed_case = -1, parsed_tick = -1;
            double q = 0;
            if (std::fscanf(input, "%d,%d,%lf", &parsed_case, &parsed_tick, &q) != 3 ||
                parsed_case != case_id || parsed_tick != tick || !std::isfinite(q)) {
                ok = false; break;
            }
            const double throttle = std::clamp(q / .3, 0., 1.);
            rocket.advance_diagnostic(throttle, .0001);
            const auto& state = rocket.state();
            ok = std::isfinite(state.altitude) && std::isfinite(state.velocity) &&
                 std::abs(state.time - (tick + 1) * .0001) < 1e-11;
            if (std::fprintf(output, "%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",
                             case_id, tick, state.time, q, throttle, state.altitude,
                             state.velocity, state.fuel, state.thrust) < 0) ok = false;
        }
    }
    int extra = EOF;
    do { extra = std::fgetc(input); } while (extra == '\n' || extra == '\r' || extra == ' ');
    if (extra != EOF) ok = false;
    if (std::fclose(input) || std::fclose(output)) ok = false;
    return ok ? 0 : 1;
}
