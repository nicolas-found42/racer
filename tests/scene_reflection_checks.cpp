#include "scene_reflection.h"
#include <iostream>
#include <set>
#include <vector>
#include <limits>
namespace mock {
uint32_t missingCapability=0;bool depthSupport=true;
bool mipSupport=true;
int attempts=0,failAt=0;uint16_t texture=10,framebuffer=100;
std::set<uint16_t> textures,framebuffers;
struct Binding {uint16_t cube,side,depth;};
std::vector<Binding> bindings;uint16_t activeFramebuffer=0;
void check(bool value) {if(!value) throw std::runtime_error("mock contract");}
void reset(int failure=0) {missingCapability=0;depthSupport=true;mipSupport=true;attempts=0;failAt=failure;texture=10;framebuffer=100;bindings.clear();textures.clear();framebuffers.clear();}
bool fail() {return ++attempts==failAt;}
}
namespace bgfx {
void Attachment::init(TextureHandle h,Access::Enum a,uint16_t l,uint16_t n,uint16_t m,uint8_t f) {handle=h;access=a;layer=l;numLayers=n;mip=m;flags=f;}
TextureHandle createTextureCube(uint16_t size,bool mips,uint16_t layers,TextureFormat::Enum format,uint64_t flags,const Memory*,uint64_t) {
  mock::check(size==256 && mips && layers==1 && format==TextureFormat::RGBA16F && (flags&BGFX_TEXTURE_RT));
  if(mock::fail())return BGFX_INVALID_HANDLE;
  auto id=mock::texture++;mock::textures.insert(id);return {id};
}
TextureHandle createTexture2D(uint16_t w,uint16_t h,bool mips,uint16_t layers,TextureFormat::Enum format,uint64_t flags,const Memory*,uint64_t) {
  mock::check(w==256 && h==256 && !mips && layers==1 && format==TextureFormat::D32F && (flags&BGFX_TEXTURE_RT));
  if(mock::fail())return BGFX_INVALID_HANDLE;
  auto id=mock::texture++;mock::textures.insert(id);return {id};
}
FrameBufferHandle createFrameBuffer(uint8_t count,const Attachment* attachments,bool own) {
  mock::check(attachments[0].mip==0 && attachments[0].flags==(attachments[0].layer==5?BGFX_ATTACHMENT_AUTO_GEN_MIPS:0) && attachments[1].flags==0);
  mock::check(count==2 && !own && attachments[0].layer<6 && attachments[0].numLayers==1 && attachments[1].handle.idx==12);
  if(mock::fail())return BGFX_INVALID_HANDLE;
  mock::bindings.push_back({attachments[0].handle.idx,attachments[0].layer,attachments[1].handle.idx});
  auto id=mock::framebuffer++;mock::framebuffers.insert(id);return {id};
}
void destroy(FrameBufferHandle h) {mock::check(mock::framebuffers.erase(h.idx)==1);}
void destroy(TextureHandle h) {mock::check(mock::framebuffers.empty() && mock::textures.erase(h.idx)==1);}
const Caps* getCaps() {static Caps caps{};caps.formats[TextureFormat::RGBA16F]=(BGFX_CAPS_FORMAT_TEXTURE_CUBE|BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER|(mock::mipSupport?BGFX_CAPS_FORMAT_TEXTURE_MIP_AUTOGEN:0))&~mock::missingCapability;caps.formats[TextureFormat::D32F]=mock::depthSupport?BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER:0;return &caps;}
void setViewFrameBuffer(ViewId,FrameBufferHandle fb) {mock::activeFramebuffer=fb.idx;}
void setViewRect(ViewId id,int16_t x,int16_t y,uint16_t w,uint16_t h,float,float) {mock::check(id>=3 && id<=8 && x==0 && y==0 && w==256 && h==256);}
void setViewClear(ViewId,uint16_t flags,uint32_t,float depth,uint8_t) {mock::check(flags==(BGFX_CLEAR_COLOR|BGFX_CLEAR_DEPTH) && depth==1);}
void setViewMode(ViewId,ViewMode::Enum mode) {mock::check(mode==ViewMode::Sequential);}
void setViewTransform(ViewId,const void*,const void*) {}
void touch(ViewId) {}
}
int main() try {
  mock::reset();mock::mipSupport=false;bool unsupported=false;
  try{racer::SceneReflection reflection;}catch(const std::runtime_error &e){unsupported=std::string(e.what())=="scene_reflection_hdr_format_unsupported";}
  mock::check(unsupported && mock::attempts==0 && mock::textures.empty() && mock::framebuffers.empty());
  for(uint32_t bit:{BGFX_CAPS_FORMAT_TEXTURE_CUBE,BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER,BGFX_CAPS_FORMAT_TEXTURE_MIP_AUTOGEN}) {
    mock::reset();mock::missingCapability=bit;bool rejected=false;
    try{racer::SceneReflection reflection;}catch(const std::runtime_error&){rejected=true;}
    mock::check(rejected && mock::attempts==0 && mock::textures.empty());
  }
  mock::reset();mock::depthSupport=false;unsupported=false;
  try{racer::SceneReflection reflection;}catch(const std::runtime_error&){unsupported=true;}
  mock::check(unsupported && mock::attempts==0);
  for(int failure=1;failure<=15;++failure) {
    mock::reset(failure);bool rejected=false;
    try {racer::SceneReflection reflection;}catch(const std::runtime_error&){rejected=true;}
    mock::check(rejected && mock::textures.empty() && mock::framebuffers.empty());
  }
  mock::reset();
  {
    racer::SceneReflection reflection;mock::check(!reflection.ready() && reflection.readTexture().idx==10);
    const int directions[6][3]={{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}};
    for(int frame=0;frame<18;++frame) {
      const int side=frame%6;const auto prior=reflection.readTexture();
      auto face=reflection.beginFrame(float(100+frame),float(200+frame));
      mock::check(face.view==3+side && face.eye[0]==100+frame-side && face.eye[2]==200+frame-side && face.eye[1]==1.6f);
      const auto binding=mock::bindings.at(mock::activeFramebuffer-100);
      mock::check(binding.side==side && binding.cube!=prior.idx);
      float forward=0,right=0,up=0;
      for(int axis=0;axis<3;++axis) {forward+=face.viewMatrix[axis*4+2]*directions[side][axis];right+=face.viewMatrix[axis*4]*directions[side][axis];up+=face.viewMatrix[axis*4+1]*directions[side][axis];}
      mock::check(std::abs(forward-1)<1e-5f && std::abs(right)<1e-5f && std::abs(up)<1e-5f);
      mock::check(std::abs(face.projection[0]-1)<1e-5f && std::abs(face.projection[5]-1)<1e-5f);
      reflection.endFrame();
      mock::check(reflection.ready()==(frame>=5));
      mock::check((reflection.readTexture().idx!=prior.idx)==(side==5));
    }
    for(int frame=0;frame<12;++frame){
      auto face=reflection.beginFrame(float(frame),float(-frame),float(frame)*.5f-3);
      mock::check(std::abs(face.eye[1]-(float(frame-frame%6)*.5f-3+1.6f))<1e-6f);
      reflection.endFrame();
    }
    for(float invalid:{std::numeric_limits<float>::infinity(),std::numeric_limits<float>::quiet_NaN()}){
      bool invalidEye=false;try{reflection.beginFrame(0,0,invalid);}catch(const std::runtime_error&){invalidEye=true;}mock::check(invalidEye);
    }
    bool rejected=false;try{reflection.endFrame();}catch(const std::logic_error&){rejected=true;}mock::check(rejected);
    reflection.beginFrame(0,0);rejected=false;try{reflection.beginFrame(0,0);}catch(const std::logic_error&){rejected=true;}mock::check(rejected);reflection.endFrame();
  }
  mock::check(mock::textures.empty() && mock::framebuffers.empty());
  std::cout<<"PASS: 15 partial-allocation failures cleaned, 18 capture faces isolated/frozen/swapped, mip allocation and final-face-only generation, cube camera axes and90degree projection, frame lifecycle\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
