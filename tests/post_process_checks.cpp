#include "post_process.h"
#include <cstring>
#include <iostream>
#include <map>
#include <set>

namespace mock {
uint32_t missingColor=0,missingDepth=0;
int attempts=0,failAt=0;uint16_t next=1;
std::map<uint16_t,char> live;
std::map<uint16_t,std::vector<uint16_t>> frames;
std::map<uint16_t,std::array<uint16_t,2>> sizes;
std::map<uint16_t,uint16_t> viewFrames;
std::array<uint16_t,2> sampled{};
std::vector<uint16_t> submitted;
void check(bool value){if(!value)throw std::runtime_error("post mock contract");}
uint16_t allocate(char type){if(++attempts==failAt)return UINT16_MAX;auto id=next++;live[id]=type;return id;}
void remove(uint16_t id,char type){check(live.at(id)==type);live.erase(id);}
void reset(int failure=0){check(live.empty());missingColor=missingDepth=0;attempts=0;failAt=failure;next=1;frames.clear();sizes.clear();viewFrames.clear();submitted.clear();}
}
namespace bgfx {
const Caps* getCaps(){static Caps caps{};caps.formats[TextureFormat::RGBA16F]=(BGFX_CAPS_FORMAT_TEXTURE_2D|BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER|BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4)&~mock::missingColor;caps.formats[TextureFormat::D32F]=(BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER|BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4)&~mock::missingDepth;return &caps;}
VertexLayout::VertexLayout()=default;
VertexLayout& VertexLayout::begin(RendererType::Enum){return *this;}
VertexLayout& VertexLayout::add(Attrib::Enum,uint8_t,AttribType::Enum,bool,bool){return *this;}
void VertexLayout::end(){}
const Memory* copy(const void* data,uint32_t size){static Memory memory;memory.data=const_cast<uint8_t*>(static_cast<const uint8_t*>(data));memory.size=size;return &memory;}
VertexBufferHandle createVertexBuffer(const Memory* data,const VertexLayout&,uint16_t){mock::check(data->size==48);return {mock::allocate('v')};}
ShaderHandle createShader(const Memory* data){mock::check(data->size>100 && data->data[3]==12);return {mock::allocate('s')};}
ProgramHandle createProgram(ShaderHandle v,ShaderHandle f,bool own){mock::check(isValid(v)&&isValid(f)&&!own);return {mock::allocate('p')};}
UniformHandle createUniform(const char*,UniformType::Enum,uint16_t){return {mock::allocate('u')};}
TextureHandle createTexture2D(uint16_t w,uint16_t h,bool mips,uint16_t layers,TextureFormat::Enum format,uint64_t flags,const Memory*,uint64_t){
  mock::check(w&&h&&!mips&&layers==1&&(flags&BGFX_TEXTURE_RT));
  mock::check(format==TextureFormat::RGBA16F||format==TextureFormat::D32F);
  if(format==TextureFormat::D32F)mock::check((flags&BGFX_TEXTURE_RT_MSAA_MASK)==BGFX_TEXTURE_RT_MSAA_X4&&(flags&BGFX_TEXTURE_RT_WRITE_ONLY));
  else mock::check((flags&BGFX_TEXTURE_RT_MSAA_MASK)==BGFX_TEXTURE_RT_MSAA_X4||(flags&BGFX_TEXTURE_RT_MSAA_MASK)==BGFX_TEXTURE_RT);
  auto id=mock::allocate('t');if(id!=UINT16_MAX)mock::sizes[id]={w,h};return {id};
}
FrameBufferHandle createFrameBuffer(uint8_t count,const TextureHandle* textures,bool own){
  mock::check((count==1||count==2)&&!own);std::vector<uint16_t> attachments;
  for(uint8_t i=0;i<count;++i){mock::check(mock::live.at(textures[i].idx)=='t');attachments.push_back(textures[i].idx);}
  auto id=mock::allocate('f');if(id!=UINT16_MAX)mock::frames[id]=attachments;return {id};
}
void destroy(VertexBufferHandle h){mock::remove(h.idx,'v');}
void destroy(ShaderHandle h){mock::remove(h.idx,'s');}
void destroy(ProgramHandle h){mock::remove(h.idx,'p');}
void destroy(UniformHandle h){mock::remove(h.idx,'u');}
void destroy(FrameBufferHandle h){mock::frames.erase(h.idx);mock::remove(h.idx,'f');}
void destroy(TextureHandle h){for(const auto& [id,attachments]:mock::frames)for(auto a:attachments)mock::check(a!=h.idx);mock::sizes.erase(h.idx);mock::remove(h.idx,'t');}
void setViewFrameBuffer(ViewId view,FrameBufferHandle h){mock::viewFrames[view]=h.idx;}
void setViewRect(ViewId,int16_t,int16_t,uint16_t w,uint16_t h,float,float){mock::check(w>0&&h>0);}
void setViewMode(ViewId,ViewMode::Enum){}
void setViewClear(ViewId,uint16_t flags,uint32_t,float,uint8_t){mock::check(flags==BGFX_CLEAR_NONE);}
void setViewTransform(ViewId,const void*,const void*){}
void setScissor(uint16_t){}
void setVertexBuffer(uint8_t,VertexBufferHandle h){mock::check(mock::live.at(h.idx)=='v');}
void setTexture(uint8_t stage,UniformHandle,TextureHandle h,uint32_t){mock::check(stage<2&&mock::live.at(h.idx)=='t');mock::sampled[stage]=h.idx;}
void setUniform(UniformHandle,const void*,uint16_t){}
void setState(uint64_t,uint32_t){}
void submit(ViewId view,ProgramHandle,uint32_t,uint8_t){
  for(auto input:mock::sampled)if(mock::viewFrames[view]!=UINT16_MAX)
    for(auto output:mock::frames.at(mock::viewFrames[view]))mock::check(input!=output);
  mock::submitted.push_back(view);
}
}
int main()try{
  for(uint32_t bit:{BGFX_CAPS_FORMAT_TEXTURE_2D,BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER,BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4}) {
    mock::reset();{racer::PostProcess post;const auto count=mock::attempts;mock::missingColor=bit;bool rejected=false;try{post.ensure(1280,720);}catch(const std::runtime_error&e){rejected=std::string(e.what())=="post_hdr_format_unsupported";}mock::check(rejected&&mock::attempts==count);}
    mock::check(mock::live.empty());
  }
  for(uint32_t bit:{BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER,BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4}) {
    mock::reset();{racer::PostProcess post;mock::missingDepth=bit;bool rejected=false;try{post.ensure(1280,720);}catch(const std::runtime_error&){rejected=true;}mock::check(rejected);}
    mock::check(mock::live.empty());
  }
  for(int failure=1;failure<=15;++failure){
    mock::reset(failure);bool rejected=false;
    try{racer::PostProcess post;post.ensure(1280,720);}catch(const std::runtime_error&){rejected=true;}
    mock::check(rejected&&mock::live.empty());
  }
  mock::reset();
  {
    racer::PostProcess post;bool rejected=false;
    try{post.draw(false);}catch(const std::logic_error&){rejected=true;}mock::check(rejected);
    post.ensure(1281,721);const auto prior=post.sceneFrame();const auto attempts=mock::attempts;
    post.ensure(1281,721);mock::check(mock::attempts==attempts);
    post.setSun(.4f,.3f,1.f,16.f/9.f);post.setMotion(9.f);post.setMotion(-2.f);post.setMotion(.5f); // clamped, never throws
    post.draw(false);mock::check(mock::submitted==std::vector<uint16_t>({10,11,12,13}));
    for(const auto& [frame,attachments]:mock::frames)if(attachments.size()==1)mock::check(mock::sizes.at(attachments[0])==std::array<uint16_t,2>{321,181});
    mock::submitted.clear();post.draw(true);mock::check(mock::submitted==std::vector<uint16_t>({13}));
    // A failed resize must leave the old complete framebuffer usable.
    for(int failure=1;failure<=7;++failure){
      mock::failAt=mock::attempts+failure;rejected=false;
      try{post.ensure(800,600);}catch(const std::runtime_error&){rejected=true;}
      mock::check(rejected&&post.sceneFrame().idx==prior.idx);post.draw(true);
    }
    mock::failAt=0;post.ensure(800,600);mock::check(post.sceneFrame().idx!=prior.idx);post.draw(false);
    post.ensure(6000,3000);mock::check(post.sceneWidth()==3840&&post.sceneHeight()==1920);post.draw(false);
    post.ensure(65535,65535);mock::check(post.sceneWidth()==2160&&post.sceneHeight()==2160);post.draw(true);
    for(const auto& [id,size]:mock::sizes)mock::check(size[0]<=3840&&size[1]<=2160);
    rejected=false;try{post.ensure(0,720);}catch(const std::runtime_error&){rejected=true;}mock::check(rejected);
  }
  mock::check(mock::live.empty());
  std::cout<<"PASS:14 initial allocation failures,7 transactional resize failures, odd quarter sizes, no-feedback pass bindings, neutral-only composite, cleanup\n";
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
