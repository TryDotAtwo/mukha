#include "visual_calibration_math.h"
#include <iostream>
#include <iomanip>
#include <vector>
#include <limits>
int main() {
    using namespace fly_calibration;
    std::cout << std::setprecision(17);
    for(double q: {0.,.001,.1,1.,5.,20.,100.})
        std::cout << "capture " << q << ' ' << log_capture(q) << '\n';
    double p[]={1,2,3}, v[]={3,2,1}, w[]={1,2,4};
    std::cout << "weighted " << response_alignment(p,v,w,3) << '\n';
    double extreme[]={1e300,2e300,3e300};
    std::cout << "extreme " << response_alignment(extreme,v,w,3) << '\n';
    double zeros[]={0,0,0};
    int rejected=0;
    try {response_alignment(zeros,v,w,3);} catch(const std::domain_error&) {++rejected;}
    try {response_alignment(p,v,zeros,3);} catch(const std::domain_error&) {++rejected;}
    try {log_capture(-.01);} catch(const std::domain_error&) {++rejected;}
    try {log_capture(std::numeric_limits<double>::infinity());} catch(const std::domain_error&) {++rejected;}
    std::cout << "rejected " << rejected << '\n';
    return rejected==4 ? 0 : 1;
}
