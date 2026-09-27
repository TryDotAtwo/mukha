// Native diagnostic rendering of physical states. No brain, no imposed poses.
#define NOMINMAX
#include <windows.h>
#include <GL/gl.h>
#include <mujoco/mujoco.h>
#include <array>
#include <vector>
#include <cstdio>
#include <cmath>
#include <io.h>
#include <fcntl.h>

struct WindowContext {
 HWND window=nullptr; HDC dc=nullptr; HGLRC gl=nullptr;
 bool open(){
  WNDCLASSA wc={};wc.style=CS_OWNDC;wc.lpfnWndProc=DefWindowProcA;
  wc.hInstance=GetModuleHandleA(nullptr);wc.lpszClassName="FlyDiagnosticOffscreen";
  if(!RegisterClassA(&wc)&&GetLastError()!=ERROR_CLASS_ALREADY_EXISTS)return false;
  window=CreateWindowA(wc.lpszClassName,"Native offscreen render",WS_OVERLAPPEDWINDOW,0,0,64,64,nullptr,nullptr,wc.hInstance,nullptr);
  if(!window)return false;dc=GetDC(window);
  PIXELFORMATDESCRIPTOR p={};p.nSize=sizeof(p);p.nVersion=1;
  p.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL|PFD_DOUBLEBUFFER;p.iPixelType=PFD_TYPE_RGBA;p.cColorBits=24;p.cDepthBits=24;
  int format=ChoosePixelFormat(dc,&p);if(!format||!SetPixelFormat(dc,format,&p))return false;
  gl=wglCreateContext(dc);return gl&&wglMakeCurrent(dc,gl);
 }
 ~WindowContext(){if(gl){wglMakeCurrent(nullptr,nullptr);wglDeleteContext(gl);}if(dc)ReleaseDC(window,dc);if(window)DestroyWindow(window);}
};
struct World {
 mjModel* m=nullptr;mjData* d=nullptr;double maximum=0;int slider=-1,pad=-1;unsigned contacts=0;
 ~World(){if(d)mj_deleteData(d);if(m)mj_deleteModel(m);}
};
int main(int argc,char**argv){
 if(argc!=3)return 2;
 FILE* journal=std::fopen(argv[2],"w");if(!journal)return 1;
 WindowContext window;if(!window.open()){std::fprintf(stderr,"WGL initialization failed\n");return 1;}
 std::array<World,4> worlds;
 for(int i=0;i<4;++i){
  auto& w=worlds[i];char error[2048]={};w.m=mj_loadXML(argv[1],nullptr,error,sizeof(error));
  if(!w.m){std::fprintf(stderr,"%s\n",error);return 1;}
  w.m->vis.global.offwidth=1920;w.m->vis.global.offheight=1080;
  if(i<2)w.m->opt.disableflags|=mjDSBL_CONTACT;
  w.slider=mj_name2id(w.m,mjOBJ_JOINT,"control_slide");w.pad=mj_name2id(w.m,mjOBJ_GEOM,"control_pad");
  int key=mj_name2id(w.m,mjOBJ_KEY,"neutral");if(key<0||w.slider<0||w.pad<0||w.m->nu!=42)return 1;
  w.d=mj_makeData(w.m);if(!w.d)return 1;mj_resetDataKeyframe(w.m,w.d,key);mj_forward(w.m,w.d);
 }
 mjvScene scene;mjv_defaultScene(&scene);mjv_makeScene(worlds[0].m,&scene,2000);
 mjrContext context;mjr_defaultContext(&context);mjr_makeContext(worlds[0].m,&context,mjFONTSCALE_150);
 mjr_setBuffer(mjFB_OFFSCREEN,&context);
 if(context.currentBuffer!=mjFB_OFFSCREEN){std::fprintf(stderr,"No offscreen buffer\n");return 1;}
 mjvCamera camera;mjv_defaultCamera(&camera);camera.type=mjCAMERA_FREE;
 camera.lookat[0]=0.7;camera.lookat[1]=0.2;camera.lookat[2]=0.8;
 camera.distance=5.0;camera.azimuth=120;camera.elevation=-25;
 mjvOption option;mjv_defaultOption(&option);
 std::vector<unsigned char> rgb(1920*1080*3);_setmode(_fileno(stdout),_O_BINARY);
 std::fprintf(stderr,"OpenGL renderer: %s\n",glGetString(GL_RENDERER));
 int tick=0;bool valid=true;
 for(int frame=0;frame<90;++frame){
  int target=(frame+1)*1000/3;
  for(;tick<target;++tick)for(int i=0;i<4;++i){
   auto& w=worlds[i];w.d->ctrl[0]=(i%2==1&&tick>=5000&&tick<15000)?1.:0.;
   mj_step(w.m,w.d);
   double q=w.d->qpos[w.m->jnt_qposadr[w.slider]];w.maximum=std::fmax(w.maximum,std::abs(q));
   for(int j=0;j<w.m->nq;++j)valid&=std::isfinite(w.d->qpos[j]);
   for(int j=0;j<mjNWARNING;++j)valid&=w.d->warning[j].number==0;
   for(int c=0;c<w.d->ncon;++c)if(w.d->contact[c].geom[0]==w.pad||w.d->contact[c].geom[1]==w.pad)++w.contacts;
  }
  if(!valid){std::fprintf(stderr,"Physical state failed validation\n");break;}
  for(int i=0;i<4;++i){
   auto& w=worlds[i];mj_kinematics(w.m,w.d);
   std::fprintf(journal,"{\"frame\":%d,\"panel\":%d,\"tick\":%d,\"time\":%.17g,\"contact_enabled\":%s,\"joint_command\":%.17g,\"qpos\":[",frame,i,tick,w.d->time,i>=2?"true":"false",w.d->ctrl[0]);
   for(int j=0;j<w.m->nq;++j)std::fprintf(journal,"%s%.17g",j?",":"",w.d->qpos[j]);
   std::fprintf(journal,"]}\n");
   mjv_updateScene(w.m,w.d,&option,nullptr,&camera,mjCAT_ALL,&scene);
   mjrRect viewport={(i%2)*960,(1-i/2)*540,960,540};mjr_render(viewport,&scene,&context);
   char title[128],status[160];
   std::snprintf(title,sizeof(title),"DIAGNOSTIC - NO BRAIN\nContact %s | Joint pulse %s",i>=2?"ON":"OFF",i%2?"ON":"OFF");
   std::snprintf(status,sizeof(status),"sim %.4f s | replay 1x\nslider %.6f mm | joint command %.1f",w.d->time,w.d->qpos[w.m->jnt_qposadr[w.slider]],w.d->ctrl[0]);
   mjr_overlay(mjFONT_NORMAL,mjGRID_TOPLEFT,viewport,title,nullptr,&context);
   mjr_overlay(mjFONT_NORMAL,mjGRID_BOTTOMLEFT,viewport,status,nullptr,&context);
  }
  mjr_readPixels(rgb.data(),nullptr,{0,0,1920,1080},&context);
  // OpenGL origin is bottom-left; write top-left packed RGB for the encoder.
  for(int y=1079;y>=0;--y)if(std::fwrite(rgb.data()+y*1920*3,1,1920*3,stdout)!=1920*3){valid=false;break;}
  if(!valid)break;
  if(std::fflush(journal)||std::ferror(journal)){valid=false;break;}
 }
 valid&=worlds[0].maximum==0&&worlds[1].maximum==0&&worlds[2].maximum==0&&worlds[3].maximum>1e-4;
 for(int i=0;i<4;++i)std::fprintf(stderr,"panel %d max_slider_mm %.17g contact_samples %u\n",i,worlds[i].maximum,worlds[i].contacts);
 mjr_freeContext(&context);mjv_freeScene(&scene);
 if(std::fflush(stdout)||std::ferror(stdout))valid=false;
 if(std::fclose(journal))valid=false;
 return valid?0:1;
}
