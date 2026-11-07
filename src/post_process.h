#pragma once
#include <bgfx/bgfx.h>
#include <array>
#include <algorithm>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace racer {
// Authored linear HDR scene/bloom and final display mapping. This is not a
// recovered native pipeline. HUD remains display RGB and renders afterward.
inline std::vector<uint8_t> postShader(bool fragment) {
  constexpr std::string_view vertex=R"MSL(#include <metal_stdlib>
using namespace metal;
struct Input { float2 a_position [[attribute(0)]]; float2 a_texcoord0 [[attribute(1)]]; };
struct Varying { float4 position [[position]]; float2 uv [[user(locn0)]]; };
vertex Varying xlatMtlMain(Input in [[stage_in]]) {
 Varying o; o.position=float4(in.a_position,0,1); o.uv=in.a_texcoord0; return o;
}
)MSL";
  constexpr std::string_view pixel=R"MSL(#include <metal_stdlib>
using namespace metal;
struct Globals { float4 u_post; };
struct Varying { float4 position [[position]]; float2 uv [[user(locn0)]]; };
// Fixed authored exposure1 and the existing Reinhard shoulder; exactly one display conversion.
float hdrDisplay(float radiance) {
 float linear=max(radiance,0.0);return pow(linear/(linear+.72),1.0/2.2);
}
float bloomWeight(float peak) { return smoothstep(1.0,2.0,peak); }
fragment float4 xlatMtlMain(Varying in [[stage_in]], constant Globals& _mtl_u [[buffer(0)]],
 texture2d<float> s_postScene [[texture(0)]], sampler sceneSampler [[sampler(0)]],
 texture2d<float> s_postGlow [[texture(1)]], sampler glowSampler [[sampler(1)]]) {
 float4 config=_mtl_u.u_post;
 float3 scene=s_postScene.sample(sceneSampler,in.uv).rgb;
 if(config.x<.5) {
  float3 linear=max(scene,float3(0));
  return float4(linear*bloomWeight(max(max(linear.r,linear.g),linear.b)),1);
 }
 if(config.x<2.5) {
  float2 step=config.yz;
  float3 sum=scene*.2270270270;
  sum+=(s_postScene.sample(sceneSampler,in.uv+step*1.3846153846).rgb+
        s_postScene.sample(sceneSampler,in.uv-step*1.3846153846).rgb)*.3162162162;
  sum+=(s_postScene.sample(sceneSampler,in.uv+step*3.2307692308).rgb+
        s_postScene.sample(sceneSampler,in.uv-step*3.2307692308).rgb)*.0702702703;
  return float4(sum,1);
 }
 float3 linear=max(scene,float3(0));
 if(config.w<.5) linear+=s_postGlow.sample(glowSampler,in.uv).rgb*.12;
 float3 display=float3(hdrDisplay(linear.r),hdrDisplay(linear.g),hdrDisplay(linear.b));
 if(config.w>.5) return float4(display,1); // Neutral still maps HDR; no bloom/grade.
 float luminance=dot(display,float3(.2126,.7152,.0722));
 display=mix(float3(luminance),display,1.04);
 display=(display-.5)*1.07+.5;
 float shadows=1-smoothstep(.10,.55,luminance),highlights=smoothstep(.55,.95,luminance);
 display+=shadows*float3(-.006,.001,.008)+highlights*float3(.008,.003,-.004);
 float2 p=in.uv-.5;
 display*=1-.08*smoothstep(.10,.50,dot(p,p));
 return float4(clamp(display,float3(0),float3(1)),1);
}
)MSL";
  std::vector<uint8_t> bytes;
  auto u8=[&](uint8_t n){bytes.push_back(n);};
  auto u16=[&](uint16_t n){u8(uint8_t(n));u8(uint8_t(n>>8));};
  auto u32=[&](uint32_t n){u16(uint16_t(n));u16(uint16_t(n>>16));};
  auto uniform=[&](std::string_view name,uint8_t type,uint16_t offset){
    u8(uint8_t(name.size()));bytes.insert(bytes.end(),name.begin(),name.end());
    u8(type|0x10);u8(1);u16(offset);u16(1);u16(0);u16(0);
  };
  constexpr uint32_t interface=0x504f5354;
  u8(fragment?'F':'V');u8('S');u8('H');u8(12);
  u32(fragment?interface:0);u32(fragment?0:interface);u32(0);u32(0);
  u16(fragment?3:0);
  if(fragment) {
    uniform("u_post",bgfx::UniformType::Vec4,0);
    uniform("s_postScene",bgfx::UniformType::Sampler|0x20,0);
    uniform("s_postGlow",bgfx::UniformType::Sampler|0x20,1);
  }
  const auto source=fragment?pixel:vertex;u32(uint32_t(source.size()));
  bytes.insert(bytes.end(),source.begin(),source.end());u8(0);
  u8(fragment?0:2);if(!fragment){u16(0x0001);u16(0x0010);}
  u16(fragment?16:0);return bytes;
}

class PostProcess {
  struct Targets {
    bgfx::TextureHandle scene=BGFX_INVALID_HANDLE,depth=BGFX_INVALID_HANDLE;
    std::array<bgfx::TextureHandle,2> glow{{BGFX_INVALID_HANDLE,BGFX_INVALID_HANDLE}};
    bgfx::FrameBufferHandle sceneFrame=BGFX_INVALID_HANDLE;
    std::array<bgfx::FrameBufferHandle,2> glowFrames{{BGFX_INVALID_HANDLE,BGFX_INVALID_HANDLE}};
    uint16_t width=0,height=0,sceneWidth=0,sceneHeight=0,glowWidth=0,glowHeight=0;
    ~Targets() {
      if(bgfx::isValid(sceneFrame))bgfx::destroy(sceneFrame);
      for(auto h:glowFrames)if(bgfx::isValid(h))bgfx::destroy(h);
      if(bgfx::isValid(scene))bgfx::destroy(scene);
      if(bgfx::isValid(depth))bgfx::destroy(depth);
      for(auto h:glow)if(bgfx::isValid(h))bgfx::destroy(h);
    }
  };
public:
  static constexpr uint16_t uiView=14;
  PostProcess() {
    try {
      bgfx::VertexLayout layout;layout.begin().add(bgfx::Attrib::Position,2,bgfx::AttribType::Float)
        .add(bgfx::Attrib::TexCoord0,2,bgfx::AttribType::Float).end();
      // Metal render targets and samplers both use top-origin texture rows.
      constexpr float vertices[]={-1,-1,0,1, 3,-1,2,1, -1,3,0,-1};
      vertices_=bgfx::createVertexBuffer(bgfx::copy(vertices,sizeof(vertices)),layout);
      const auto vs=postShader(false),fs=postShader(true);
      auto vertex=bgfx::createShader(bgfx::copy(vs.data(),uint32_t(vs.size())));
      if(!bgfx::isValid(vertex))throw std::runtime_error("post_vertex_shader");
      auto pixel=bgfx::createShader(bgfx::copy(fs.data(),uint32_t(fs.size())));
      if(!bgfx::isValid(pixel)){bgfx::destroy(vertex);throw std::runtime_error("post_pixel_shader");}
      program_=bgfx::createProgram(vertex,pixel,false);bgfx::destroy(vertex);bgfx::destroy(pixel);
      sceneSampler_=bgfx::createUniform("s_postScene",bgfx::UniformType::Sampler);
      glowSampler_=bgfx::createUniform("s_postGlow",bgfx::UniformType::Sampler);
      config_=bgfx::createUniform("u_post",bgfx::UniformType::Vec4);
      if(!bgfx::isValid(vertices_)||!bgfx::isValid(program_)||!bgfx::isValid(sceneSampler_)||
         !bgfx::isValid(glowSampler_)||!bgfx::isValid(config_))throw std::runtime_error("post_resources");
    }catch(...){release();throw;}
  }
  ~PostProcess(){release();}
  PostProcess(const PostProcess&)=delete;
  PostProcess& operator=(const PostProcess&)=delete;

  void ensure(uint16_t width,uint16_t height) {
    if(width<1||height<1)throw std::runtime_error("post_size_bounds");
    if(targets_ && targets_->width==width && targets_->height==height)return;
    constexpr uint32_t colorRequired=BGFX_CAPS_FORMAT_TEXTURE_2D | BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER |
      BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4;
    constexpr uint32_t depthRequired=BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER | BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4;
    const auto* caps=bgfx::getCaps();
    if((caps->formats[bgfx::TextureFormat::RGBA16F]&colorRequired)!=colorRequired ||
       (caps->formats[bgfx::TextureFormat::D32F]&depthRequired)!=depthRequired)
      throw std::runtime_error("post_hdr_format_unsupported");
    auto next=std::make_unique<Targets>();next->width=width;next->height=height;
    const double scale=std::min({1.,3840./width,2160./height});
    next->sceneWidth=std::max(uint16_t(1),uint16_t(width*scale));
    next->sceneHeight=std::max(uint16_t(1),uint16_t(height*scale));
    next->glowWidth=uint16_t((next->sceneWidth+3)/4);next->glowHeight=uint16_t((next->sceneHeight+3)/4);
    constexpr uint64_t sampling=BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP;
    next->scene=bgfx::createTexture2D(next->sceneWidth,next->sceneHeight,false,1,bgfx::TextureFormat::RGBA16F,
      BGFX_TEXTURE_RT_MSAA_X4|sampling);
    next->depth=bgfx::createTexture2D(next->sceneWidth,next->sceneHeight,false,1,bgfx::TextureFormat::D32F,
      BGFX_TEXTURE_RT_MSAA_X4|BGFX_TEXTURE_RT_WRITE_ONLY);
    if(!bgfx::isValid(next->scene)||!bgfx::isValid(next->depth))throw std::runtime_error("post_scene_texture");
    bgfx::TextureHandle attachments[]={next->scene,next->depth};
    next->sceneFrame=bgfx::createFrameBuffer(2,attachments,false);
    if(!bgfx::isValid(next->sceneFrame))throw std::runtime_error("post_scene_framebuffer");
    for(size_t i=0;i<2;++i) {
      next->glow[i]=bgfx::createTexture2D(next->glowWidth,next->glowHeight,false,1,bgfx::TextureFormat::RGBA16F,
        BGFX_TEXTURE_RT|sampling);
      if(!bgfx::isValid(next->glow[i]))throw std::runtime_error("post_glow_texture");
      next->glowFrames[i]=bgfx::createFrameBuffer(1,&next->glow[i],false);
      if(!bgfx::isValid(next->glowFrames[i]))throw std::runtime_error("post_glow_framebuffer");
    }
    targets_=std::move(next);
  }
  bgfx::FrameBufferHandle sceneFrame() const {
    if(!targets_)throw std::logic_error("post_not_sized");return targets_->sceneFrame;
  }
  uint16_t sceneWidth() const {if(!targets_)throw std::logic_error("post_not_sized");return targets_->sceneWidth;}
  uint16_t sceneHeight() const {if(!targets_)throw std::logic_error("post_not_sized");return targets_->sceneHeight;}
  void draw(bool neutral) {
    if(!targets_)throw std::logic_error("post_not_sized");
    const auto& t=*targets_;
    // Never bind a writable attachment as either sampled input, even when the
    // selected shader branch would not read it. All views execute in ID order.
    if(!neutral) {
      pass(10,t.glowFrames[0],t.glowWidth,t.glowHeight,t.scene,t.scene,{0,0,0,0});
      pass(11,t.glowFrames[1],t.glowWidth,t.glowHeight,t.glow[0],t.scene,{1,1.f/t.glowWidth,0,0});
      pass(12,t.glowFrames[0],t.glowWidth,t.glowHeight,t.glow[1],t.scene,{2,0,1.f/t.glowHeight,0});
    }
    // Neutral does not read an uninitialized glow texture.
    pass(13,BGFX_INVALID_HANDLE,t.width,t.height,t.scene,neutral?t.scene:t.glow[0],{3,0,0,neutral?1.f:0.f});
  }
private:
  std::unique_ptr<Targets> targets_;
  bgfx::VertexBufferHandle vertices_=BGFX_INVALID_HANDLE;
  bgfx::ProgramHandle program_=BGFX_INVALID_HANDLE;
  bgfx::UniformHandle sceneSampler_=BGFX_INVALID_HANDLE,glowSampler_=BGFX_INVALID_HANDLE,config_=BGFX_INVALID_HANDLE;
  void pass(uint16_t view,bgfx::FrameBufferHandle frame,uint16_t width,uint16_t height,
            bgfx::TextureHandle input,bgfx::TextureHandle glow,const std::array<float,4>& config) {
    bgfx::setViewFrameBuffer(view,frame);bgfx::setViewRect(view,0,0,width,height);
    bgfx::setViewMode(view,bgfx::ViewMode::Sequential);bgfx::setViewClear(view,BGFX_CLEAR_NONE);
    bgfx::setViewTransform(view,nullptr,nullptr);bgfx::setScissor();bgfx::setVertexBuffer(0,vertices_);
    bgfx::setTexture(0,sceneSampler_,input);bgfx::setTexture(1,glowSampler_,glow);
    bgfx::setUniform(config_,config.data());bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_MSAA);
    bgfx::submit(view,program_);
  }
  void release() noexcept {
    targets_.reset();
    if(bgfx::isValid(vertices_))bgfx::destroy(vertices_);vertices_=BGFX_INVALID_HANDLE;
    if(bgfx::isValid(program_))bgfx::destroy(program_);program_=BGFX_INVALID_HANDLE;
    for(auto* h:{&sceneSampler_,&glowSampler_,&config_}) {if(bgfx::isValid(*h))bgfx::destroy(*h);*h=BGFX_INVALID_HANDLE;}
  }
};
}
