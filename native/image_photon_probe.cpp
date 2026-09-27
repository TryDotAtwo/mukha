#include "retina.h"
#include "photon.h"
#include <vector>
#include <fstream>
#include <iostream>
#include <cmath>
#include <stdexcept>
#include <cstdint>
// Diagnostic monochrome image stimulus. Scale is explicit, not calibrated.
int main(int argc,char**argv){
 try{
  if(argc!=4)throw std::runtime_error("usage: probe rays.bin output.bin image|closed");
  const bool closed=std::string(argv[3])=="closed";
  if(!closed && std::string(argv[3])!="image")throw std::runtime_error("invalid mode");
  std::ifstream in(argv[1],std::ios::binary);uint32_t n=0;in.read((char*)&n,4);
  if(!in||n==0||n>100000)throw std::runtime_error("invalid ray count");
  std::vector<double> rays(3*n);in.read((char*)rays.data(),rays.size()*8);
  if(!in||in.peek()!=EOF)throw std::runtime_error("invalid ray data");
  constexpr unsigned w=512,h=256,frames=100,ticks_per_frame=10;
  constexpr double pi=3.14159265358979323846,full_scale_rate=100000.;
  void* retina=fv_create(rays.data(),n,w,h);if(!retina)throw std::runtime_error("retina create");
  void* photo=fp_create(n,30000,19641,128);if(!photo)throw std::runtime_error(fp_last_error());
  std::vector<float> rgb(w*h*3),samples(n*3);std::vector<double> rates(n),state(9*n);
  std::ofstream out(argv[2],std::ios::binary);if(!out)throw std::runtime_error("output open");
  for(unsigned f=0;f<frames;++f){
   // A translating sinusoidal grating is a declared experimental stimulus.
   // Ten initial dark frames precede illumination. No rocket data is read.
   for(unsigned y=0;y<h;++y)for(unsigned x=0;x<w;++x){
    const double longitude=2*pi*((x+.5)/w-.5);
    float intensity=closed||f<10?0.f:float(.5+.5*std::cos(4*longitude-2*pi*(f-10)/90.));
    for(unsigned c=0;c<3;++c)rgb[(size_t(y)*w+x)*3+c]=intensity;
   }
   if(fv_sample(retina,rgb.data(),rgb.size(),samples.data(),samples.size()))throw std::runtime_error("image sample");
   for(unsigned i=0;i<n;++i)rates[i]=full_scale_rate*double(samples[3*i]);
   if(fp_advance(photo,rates.data(),n,ticks_per_frame))throw std::runtime_error(fp_last_error());
   uint64_t tick=0;if(fp_observe(photo,state.data(),state.size(),&tick))throw std::runtime_error(fp_last_error());
   if(tick!=(f+1)*ticks_per_frame)throw std::runtime_error("time mismatch");
   for(double v:state)if(!std::isfinite(v))throw std::runtime_error("nonfinite state");
   out.write((char*)&tick,8);out.write((char*)rates.data(),n*8);out.write((char*)state.data(),n*8);
   if(!out)throw std::runtime_error("output write");
  }
  fp_destroy(photo);fv_destroy(retina);std::cout<<"frames="<<frames<<" cells="<<n<<" full_scale_photons_per_second="<<full_scale_rate<<"\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
