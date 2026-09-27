// Explicit engineering diagnostic. No neural input or pose animation.
#include <mujoco/mujoco.h>
#include <cmath>
#include <cstdio>
#include <memory>
#include <vector>

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    char error[2048] = {};
    std::unique_ptr<mjModel, decltype(&mj_deleteModel)> m(
        mj_loadXML(argv[1], nullptr, error, sizeof(error)), mj_deleteModel);
    if (!m) { std::fprintf(stderr, "%s\n", error); return 1; }
    int key = mj_name2id(m.get(), mjOBJ_KEY, "neutral");
    if (key < 0 || m->nu < 1) return 1;
    std::unique_ptr<mjData, decltype(&mj_deleteData)> baseline(mj_makeData(m.get()), mj_deleteData);
    std::unique_ptr<mjData, decltype(&mj_deleteData)> driven(mj_makeData(m.get()), mj_deleteData);
    if (!baseline || !driven) return 1;
    for (auto d : {baseline.get(), driven.get()}) {
        mj_resetDataKeyframe(m.get(), d, key);
        mj_forward(m.get(), d);
    }
    std::unique_ptr<FILE, decltype(&std::fclose)> out(std::fopen(argv[2], "w"), std::fclose);
    if (!out) return 1;
    std::fprintf(out.get(), "tick,time,command,force");
    for (int j=0; j<m->nq; ++j) std::fprintf(out.get(), ",baseline_q%d,driven_q%d", j,j);
    std::fprintf(out.get(), "\n");
    double max_diff=0, max_force=0;
    for (int tick=0; tick<10000; ++tick) {
        // Intentionally exceeds the configured bound to test physical saturation.
        const double command = tick>=2000 && tick<4000 ? 2.0 : 0.0;
        driven->ctrl[0] = command;
        mj_step(m.get(), baseline.get());
        mj_step(m.get(), driven.get());
        max_force=std::fmax(max_force,std::abs(driven->actuator_force[0]));
        std::fprintf(out.get(), "%d,%.17g,%.17g,%.17g",tick+1,driven->time,command,driven->actuator_force[0]);
        for (int j=0; j<m->nq; ++j) {
            if (!std::isfinite(driven->qpos[j]) || !std::isfinite(baseline->qpos[j])) return 1;
            max_diff=std::fmax(max_diff,std::abs(driven->qpos[j]-baseline->qpos[j]));
            std::fprintf(out.get(), ",%.17g,%.17g",baseline->qpos[j],driven->qpos[j]);
        }
        std::fprintf(out.get(), "\n");
    }
    int warnings=0;
    for (auto d : {baseline.get(), driven.get()})
        for (int i=0;i<mjNWARNING;++i) warnings+=d->warning[i].number;
    std::printf("{\"actuator\":\"%s\",\"max_q_difference\":%.17g,\"max_force\":%.17g,\"warnings\":%d,\"ticks\":10000}\n",
        mj_id2name(m.get(),mjOBJ_ACTUATOR,0),max_diff,max_force,warnings);
    if (std::fflush(out.get()) || std::ferror(out.get())) return 1;
    return warnings || max_diff<1e-5 || max_force>1.000000001 || max_force<0.99 ? 1:0;
}
