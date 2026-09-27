// Diagnostic only: passive author model, fixed thorax, native time integration.
#include <mujoco/mujoco.h>
#include <cmath>
#include <cstdio>
#include <memory>

int main(int argc, char** argv) {
    if (argc != 2) { std::fprintf(stderr, "usage: body_probe model.xml\n"); return 2; }
    char error[2048] = {};
    std::unique_ptr<mjModel, decltype(&mj_deleteModel)> m(
        mj_loadXML(argv[1], nullptr, error, sizeof(error)), mj_deleteModel);
    if (!m) { std::fprintf(stderr, "%s\n", error); return 1; }
    std::unique_ptr<mjData, decltype(&mj_deleteData)> d(mj_makeData(m.get()), mj_deleteData);
    if (!d) return 1;
    int neutral = mj_name2id(m.get(), mjOBJ_KEY, "neutral");
    if (neutral < 0 || m->nu != 0) { std::fprintf(stderr, "Expected neutral keyframe and passive model\n"); return 1; }
    mj_resetDataKeyframe(m.get(), d.get(), neutral);
    mj_forward(m.get(), d.get());
    double max_speed = 0;
    for (int tick=0; tick<10000; ++tick) {
        mj_step(m.get(), d.get());
        for (int j=0; j<m->nq; ++j) if (!std::isfinite(d->qpos[j])) return 1;
        for (int j=0; j<m->nv; ++j) {
            if (!std::isfinite(d->qvel[j])) return 1;
            max_speed = std::fmax(max_speed, std::abs(d->qvel[j]));
        }
    }
    int warnings = 0;
    for (int i=0; i<mjNWARNING; ++i) warnings += d->warning[i].number;
    std::printf("{\"scope\":\"passive native body diagnostic, no neural control\","
                "\"mujoco\":\"%s\",\"ticks\":10000,\"time\":%.17g,"
                "\"nq\":%lld,\"nv\":%lld,\"max_speed\":%.17g,\"warnings\":%d}\n",
                mj_versionString(), d->time, static_cast<long long>(m->nq),
                static_cast<long long>(m->nv), max_speed, warnings);
    return warnings || std::abs(d->time - 10000*m->opt.timestep) > 1e-9 ? 1 : 0;
}
