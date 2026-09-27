#include "photon.h"
#include <cstdio>
#include <cmath>
#include <stdexcept>
#include <vector>
#include <limits>
void check(int status) { if(status) throw std::runtime_error(fp_last_error()); }
int main() { try {
    // Non-warp-multiple populations and microvillus counts exercise tail ownership.
    for(unsigned n : {1u,3u,33u}) {
        void* p=fp_create(n,1001,19303,16);
        if(!p) throw std::runtime_error(fp_last_error());
        std::vector<double> rates(n,100000.),state(9*n),first(9*n);
        uint64_t tick=99;
        check(fp_observe(p,first.data(),first.size(),&tick));
        if(tick!=0) return 2;
        check(fp_advance(p,rates.data(),n,20));
        check(fp_observe(p,state.data(),state.size(),&tick));
        if(tick!=20) return 3;
        for(double x:state) if(!std::isfinite(x)) return 4;
        auto expected=state;
        rates[0]=std::numeric_limits<double>::quiet_NaN();
        if(fp_advance(p,rates.data(),n,1)==0) return 5;
        check(fp_observe(p,state.data(),state.size(),&tick));
        if(state!=expected || tick!=20) return 6;
        std::vector<double> feedback(n,-0.5);feedback[0]=0.5;
        check(fp_set_neural_feedback(p,feedback.data(),n));
        const size_t bytes=fp_checkpoint_size(p);
        if(!bytes) return 8;
        std::vector<unsigned char> saved(bytes),restored(bytes),terminal(bytes);
        check(fp_save(p,saved.data(),bytes));
        rates[0]=50000.;
        check(fp_advance(p,rates.data(),n,10));
        check(fp_save(p,terminal.data(),bytes));
        check(fp_load(p,saved.data(),bytes));
        check(fp_save(p,restored.data(),bytes));
        if(saved!=restored) return 9;
        check(fp_advance(p,rates.data(),n,10));
        check(fp_save(p,restored.data(),bytes));
        if(terminal!=restored) return 10;
        saved[64]^=1;
        if(fp_load(p,saved.data(),bytes)==0) return 11;
        check(fp_save(p,restored.data(),bytes));
        if(terminal!=restored) return 12;
        feedback[n-1]=std::numeric_limits<double>::quiet_NaN();
        if(fp_set_neural_feedback(p,feedback.data(),n)==0) return 13;
        check(fp_save(p,restored.data(),bytes));
        if(terminal!=restored) return 14;
        check(fp_reset(p,19303));
        check(fp_observe(p,state.data(),state.size(),&tick));
        if(state!=first || tick!=0) return 7;
        fp_destroy(p);
        std::printf("PASS n=%u microvilli=1001 checkpoint=20 final=30 restore/replay/reset\n",n);
    }
    return 0;
} catch(const std::exception& e) { std::fprintf(stderr,"%s\n",e.what()); return 1; } }
