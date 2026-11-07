// Technical shared-PostProcess probe. These constant panels are not game PBR.
#include "post_process.h"
#include <SDL3/SDL.h>
#include <SDL3/SDL_metal.h>
#include <atomic>
#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>

#ifndef RACER_HDR_PROBE_SOURCE_SHA256
#error Define RACER_HDR_PROBE_SOURCE_SHA256 from this source at CMake configure time.
#endif
#ifndef RACER_HDR_POST_SOURCE_SHA256
#error Define RACER_HDR_POST_SOURCE_SHA256 from src/post_process.h at configure time.
#endif

namespace {
struct Screenshot final : bgfx::CallbackI {
  std::atomic<bool> complete{false},failed{false};
  std::atomic<unsigned> traces{0};
  void fatal(const char*,uint16_t,bgfx::Fatal::Enum,const char* message) override {
    std::cerr<<"HDR probe renderer fatal: "<<message<<'\n';std::abort();
  }
  void traceVargs(const char*,uint16_t,const char* format,va_list args) override {if(traces.fetch_add(1)<10)vfprintf(stderr,format,args);}
  void profilerBegin(const char*,uint32_t,const char*,uint16_t) override {}
  void profilerBeginLiteral(const char*,uint32_t,const char*,uint16_t) override {}
  void profilerEnd() override {}
  uint32_t cacheReadSize(uint64_t) override {return 0;}
  bool cacheRead(uint64_t,void*,uint32_t) override {return false;}
  void cacheWrite(uint64_t,const void*,uint32_t) override {}
  void screenShot(const char* path,uint32_t w,uint32_t h,uint32_t pitch,bgfx::TextureFormat::Enum format,
                  const void* data,uint32_t size,bool flip) noexcept override {
    try {
      if(complete.load()||w!=640||h!=360||pitch<w*4||uint64_t(pitch)*h>size||
         (format!=bgfx::TextureFormat::BGRA8&&format!=bgfx::TextureFormat::RGBA8))
        throw std::runtime_error("probe_capture_format");
      std::ofstream out(path,std::ios::binary);out<<"P6\n"<<w<<' '<<h<<"\n255\n";
      const auto* bytes=static_cast<const unsigned char*>(data);
      for(uint32_t y=0;y<h;++y)for(uint32_t x=0;x<w;++x){
        const auto* p=bytes+(flip?h-1-y:y)*pitch+x*4;
        const char rgb[]={char(p[format==bgfx::TextureFormat::BGRA8?2:0]),char(p[1]),
                          char(p[format==bgfx::TextureFormat::BGRA8?0:2])};out.write(rgb,3);
      }
      out.close();if(!out)throw std::runtime_error("probe_capture_write");complete.store(true);
    }catch(...){failed.store(true);}
  }
  void captureBegin(uint32_t,uint32_t,uint32_t,bgfx::TextureFormat::Enum,bool) override {}
  void captureEnd() override {}
  void captureFrame(const void*,uint32_t) override {}
};
struct NativeLifetime {
  SDL_Window* window=nullptr;SDL_MetalView metal=nullptr;bool renderer=false;
  ~NativeLifetime(){if(renderer)bgfx::shutdown();if(metal)SDL_Metal_DestroyView(metal);if(window)SDL_DestroyWindow(window);SDL_Quit();}
};
std::vector<uint8_t> panelPixelShader(){
  constexpr std::string_view source=R"MSL(#include <metal_stdlib>
using namespace metal;
struct Varying {float4 position [[position]];float2 uv [[user(locn0)]];};
fragment float4 xlatMtlMain(Varying in [[stage_in]]) {
 float radiance=in.uv.x<.25?1.0:in.uv.x<.5?4.0:in.uv.x<.75?8.0:4.0;
 float alpha=in.uv.x<.75?1.0:.25;
 return float4(float3(radiance),alpha);
}
)MSL";
  std::vector<uint8_t> bytes;
  auto u8=[&](uint8_t n){bytes.push_back(n);};
  auto u16=[&](uint16_t n){u8(uint8_t(n));u8(uint8_t(n>>8));};
  auto u32=[&](uint32_t n){u16(uint16_t(n));u16(uint16_t(n>>16));};
  for(uint8_t n:{uint8_t('F'),uint8_t('S'),uint8_t('H'),uint8_t(12)})u8(n);
  u32(0x504f5354);u32(0);u32(0);u32(0);u16(0);
  u32(uint32_t(source.size()));bytes.insert(bytes.end(),source.begin(),source.end());u8(0);u8(0);u16(0);
  return bytes;
}
struct Panels {
  bgfx::VertexBufferHandle vertices=BGFX_INVALID_HANDLE;
  bgfx::ProgramHandle program=BGFX_INVALID_HANDLE;
  Panels(){
    try{
      bgfx::VertexLayout layout;layout.begin().add(bgfx::Attrib::Position,2,bgfx::AttribType::Float)
        .add(bgfx::Attrib::TexCoord0,2,bgfx::AttribType::Float).end();
      constexpr float triangle[]={-1,-1,0,1, 3,-1,2,1, -1,3,0,-1};
      vertices=bgfx::createVertexBuffer(bgfx::copy(triangle,sizeof(triangle)),layout);
      const auto vs=racer::postShader(false),fs=panelPixelShader();
      auto vertex=bgfx::createShader(bgfx::copy(vs.data(),uint32_t(vs.size())));
      if(!bgfx::isValid(vertex))throw std::runtime_error("probe_vertex_shader");
      auto pixel=bgfx::createShader(bgfx::copy(fs.data(),uint32_t(fs.size())));
      if(!bgfx::isValid(pixel)){bgfx::destroy(vertex);throw std::runtime_error("probe_pixel_shader");}
      program=bgfx::createProgram(vertex,pixel,false);bgfx::destroy(vertex);bgfx::destroy(pixel);
      if(!bgfx::isValid(vertices)||!bgfx::isValid(program))throw std::runtime_error("probe_resources");
    }catch(...){release();throw;}
  }
  ~Panels(){release();}
  Panels(const Panels&)=delete;Panels& operator=(const Panels&)=delete;
  void release(){if(bgfx::isValid(program))bgfx::destroy(program);program=BGFX_INVALID_HANDLE;
    if(bgfx::isValid(vertices))bgfx::destroy(vertices);vertices=BGFX_INVALID_HANDLE;}
};
}
int main(int argc,char** argv)try{
  if(argc!=2||!std::filesystem::path(argv[1]).is_absolute())throw std::runtime_error("usage: native_hdr_probe ABSOLUTE_NEW_PPM_PATH");
  if(std::filesystem::exists(argv[1])||std::filesystem::is_symlink(argv[1]))throw std::runtime_error("probe_capture_conflict");
  Screenshot capture;NativeLifetime lifetime;
  if(!SDL_Init(SDL_INIT_VIDEO))throw std::runtime_error(SDL_GetError());
  lifetime.window=SDL_CreateWindow("Racer HDR technical probe",640,360,SDL_WINDOW_METAL|SDL_WINDOW_HIDDEN);
  if(!lifetime.window)throw std::runtime_error(SDL_GetError());
  lifetime.metal=SDL_Metal_CreateView(lifetime.window);if(!lifetime.metal)throw std::runtime_error(SDL_GetError());
  int width=0,height=0;SDL_GetWindowSizeInPixels(lifetime.window,&width,&height);
  if(width!=640||height!=360)throw std::runtime_error("probe_drawable_size");
  bgfx::Init init;init.type=bgfx::RendererType::Metal;init.fallback=false;
  init.swapChain.nwh=SDL_Metal_GetLayer(lifetime.metal);init.swapChain.width=640;init.swapChain.height=360;
  init.reset=BGFX_RESET_VSYNC|BGFX_RESET_MSAA_X4;init.callback=&capture;
  if(!bgfx::init(init))throw std::runtime_error("probe_metal_init");lifetime.renderer=true;
  std::cout<<"probe_source_sha256="<<RACER_HDR_PROBE_SOURCE_SHA256<<"\npost_source_sha256="<<RACER_HDR_POST_SOURCE_SHA256<<'\n';
  std::cout<<"renderer="<<bgfx::getRendererName(bgfx::getRendererType())<<" size=640x360 shared_PostProcess neutral\n";
  racer::PostProcess post;post.ensure(640,360);Panels panels;
  const auto began=std::chrono::steady_clock::now();bool requested=false;
  while(true){
    const auto elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count();
    if(elapsed>=3)break;
    SDL_Event event;while(SDL_PollEvent(&event))if(event.type==SDL_EVENT_QUIT)throw std::runtime_error("probe_interrupted");
    bgfx::setViewFrameBuffer(1,post.sceneFrame());bgfx::setViewRect(1,0,0,640,360);
    bgfx::setViewMode(1,bgfx::ViewMode::Sequential);
    bgfx::setViewClear(1,BGFX_CLEAR_COLOR|BGFX_CLEAR_DEPTH,0x000000ffu,1,0);
    bgfx::setViewTransform(1,nullptr,nullptr);bgfx::setVertexBuffer(0,panels.vertices);
    bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_BLEND_ALPHA|BGFX_STATE_MSAA);
    bgfx::submit(1,panels.program);post.draw(true);
    if(elapsed>2&&!requested){bgfx::requestScreenShot(BGFX_INVALID_HANDLE,argv[1]);requested=true;}
    bgfx::frame();SDL_Delay(1);
  }
  if(capture.failed.load()||!capture.complete.load())throw std::runtime_error("probe_capture_incomplete");
  std::cout<<"PASS: captured shared HDR post panels; analytic pixel acceptance belongs to native_hdr_checks.py\n";
}catch(const std::exception& error){std::cerr<<"HDR technical probe failed: "<<error.what()<<'\n';return 1;}
