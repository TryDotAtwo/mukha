#include "retina.h"
#include <array>
#include <cmath>
#include <limits>
#include <vector>
#include <memory>

namespace {
constexpr double pi=3.1415926535897932384626433832795;
struct Sample { std::array<size_t,4> pixels; std::array<double,4> weights; };
struct Retina { size_t image_count; uint32_t width,height; std::vector<std::array<double,3>> rays; std::vector<Sample> samples; };
Sample make_sample(double x,double y,double z,uint32_t w,uint32_t h) {
    double u=(std::atan2(y,x)/(2*pi)+.5)*w-.5;
    double v=(.5-std::atan2(z,std::hypot(x,y))/pi)*h-.5;
    auto x0=static_cast<int64_t>(std::floor(u));
    double dx=u-x0;
    v=std::fmax(0.,std::fmin(double(h-1),v));
    auto y0=static_cast<uint32_t>(std::floor(v)),y1=y0+1<h?y0+1:y0;
    double dy=v-y0;
    auto left=static_cast<uint32_t>((x0+int64_t(w))%w),right=(left+1)%w;
    return {{{(size_t(y0)*w+left)*3,(size_t(y0)*w+right)*3,
              (size_t(y1)*w+left)*3,(size_t(y1)*w+right)*3}},
            {{(1-dx)*(1-dy),dx*(1-dy),(1-dx)*dy,dx*dy}}};
}
bool valid_rotation(const double* a) {
    if (!a) return false;
    for (size_t i=0;i<9;++i) if (!std::isfinite(a[i])) return false;
    for (size_t i=0;i<3;++i) for (size_t j=0;j<3;++j) {
        double dot=0;
        for (size_t k=0;k<3;++k) dot+=a[k*3+i]*a[k*3+j];
        if (std::abs(dot-(i==j?1.:0.))>1e-8) return false;
    }
    double det=a[0]*(a[4]*a[8]-a[5]*a[7])-a[1]*(a[3]*a[8]-a[5]*a[6])+a[2]*(a[3]*a[7]-a[4]*a[6]);
    return std::abs(det-1.)<=1e-8;
}
bool overlaps(const float* a,size_t an,const float* b,size_t bn) {
    auto aa=reinterpret_cast<uintptr_t>(a),bb=reinterpret_cast<uintptr_t>(b);
    if (an>std::numeric_limits<size_t>::max()/sizeof(float) || bn>std::numeric_limits<size_t>::max()/sizeof(float)) return true;
    auto ab=an*sizeof(float), ba=bn*sizeof(float);
    if (aa>std::numeric_limits<uintptr_t>::max()-ab || bb>std::numeric_limits<uintptr_t>::max()-ba) return true;
    return aa<bb+ba && bb<aa+ab;
}
}
extern "C" {
void* fv_create(const double* rays,size_t n,uint32_t w,uint32_t h) {
    if (!rays || !n || w<2 || h<2 || n>std::numeric_limits<size_t>::max()/3 ||
        size_t(w)>std::numeric_limits<size_t>::max()/h/3) return nullptr;
    try {
        auto r=std::make_unique<Retina>();r->image_count=size_t(w)*h*3;r->width=w;r->height=h;
        r->rays.reserve(n);r->samples.reserve(n);
        for (size_t i=0;i<n;++i) {
            double x=rays[3*i],y=rays[3*i+1],z=rays[3*i+2];
            double norm=x*x+y*y+z*z;
            if (!std::isfinite(norm) || std::abs(norm-1)>1e-10) return nullptr;
            r->rays.push_back({x,y,z});
            r->samples.push_back(make_sample(x,y,z,w,h));
        }
        return r.release();
    } catch (...) {return nullptr;}
}
void fv_destroy(void* p) {delete static_cast<Retina*>(p);}
int fv_sample(const void* p,const float* rgb,size_t count,float* out,size_t out_count) {
    if (!p || !rgb || !out) return 1;
    auto& r=*static_cast<const Retina*>(p);
    if (count!=r.image_count || out_count!=r.samples.size()*3 || overlaps(rgb,count,out,out_count)) return 2;
    for (size_t i=0;i<count;++i) if (!std::isfinite(rgb[i]) || rgb[i]<0) return 3;
    for (size_t i=0;i<r.samples.size();++i) for (size_t c=0;c<3;++c) {
        auto& s=r.samples[i];double value=0;
        for(size_t j=0;j<4;++j) value+=double(rgb[s.pixels[j]+c])*s.weights[j];
        out[3*i+c]=static_cast<float>(value);
    }
    return 0;
}
int fv_sample_oriented(const void* p,const float* rgb,size_t count,const double* rotation,
                       float* out,size_t out_count) {
    if (!p || !rgb || !out) return 1;
    auto& r=*static_cast<const Retina*>(p);
    if (count!=r.image_count || out_count!=r.rays.size()*3 || overlaps(rgb,count,out,out_count)) return 2;
    if (!valid_rotation(rotation)) return 4;
    for (size_t i=0;i<count;++i) if (!std::isfinite(rgb[i]) || rgb[i]<0) return 3;
    for (size_t i=0;i<r.rays.size();++i) {
        auto& ray=r.rays[i];
        double x=rotation[0]*ray[0]+rotation[1]*ray[1]+rotation[2]*ray[2];
        double y=rotation[3]*ray[0]+rotation[4]*ray[1]+rotation[5]*ray[2];
        double z=rotation[6]*ray[0]+rotation[7]*ray[1]+rotation[8]*ray[2];
        auto s=make_sample(x,y,z,r.width,r.height);
        for (size_t c=0;c<3;++c) {
            double value=0;
            for (size_t j=0;j<4;++j) value+=double(rgb[s.pixels[j]+c])*s.weights[j];
            out[3*i+c]=static_cast<float>(value);
        }
    }
    return 0;
}
}
