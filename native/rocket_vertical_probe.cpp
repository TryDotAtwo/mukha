#include "rocket_vertical.h"
#include <iostream>
#include <iomanip>
int main() {
    using namespace fly_rocket;
    std::cout << std::setprecision(17);
    for(int scenario=0;scenario<5;++scenario) {
        Parameters p{200000.,(scenario==0 || scenario==4)?0.:6.5e10,1000.,20000.,3000.,(scenario==0 || scenario==4)?0.:.3};
        State init{0.,scenario==3?2.:2500.,-20.,scenario==2? .01:100.,0.,false};
        if(scenario==4) {init.altitude=.0001;init.velocity=-.1;}
        VerticalPlant plant(p,init);
        for(int i=0;i<1000 && !plant.state().contact;++i) plant.advance_diagnostic(scenario==3?0.:.6,scenario==4?.1:.01);
        auto s=plant.state();
        std::cout<<scenario<<' '<<s.time<<' '<<s.altitude<<' '<<s.velocity<<' '<<s.fuel<<' '<<s.thrust<<' '<<s.contact<<'\n';
    }
}
