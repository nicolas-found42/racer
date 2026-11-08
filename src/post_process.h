#pragma once
#include <algorithm>
#include <array>
#include <bgfx/bgfx.h>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace racer {
// Authored linear HDR scene/bloom and final display mapping. This is not a
// recovered native pipeline. HUD remains display RGB and renders afterward.
inline std::vector<uint8_t> postShader(bool fragment) {
  constexpr std::string_view vertex = R"MSL(#include <metal_stdlib>
using namespace metal;
struct Input { float2 a_position [[attribute(0)]]; float2 a_texcoord0 [[attribute(1)]]; };
struct Varying { float4 position [[position]]; float2 uv [[user(locn0)]]; };
vertex Varying xlatMtlMain(Input in [[stage_in]]) {
 Varying o; o.position=float4(in.a_position,0,1); o.uv=in.a_texcoord0; return o;
}
)MSL";
  constexpr std::string_view pixel = R"MSL(#include <metal_stdlib>
using namespace metal;
struct Globals { float4 u_post; float4 u_sun; float4 u_dof; };
struct Varying { float4 position [[position]]; float2 uv [[user(locn0)]]; };
// Fixed authored exposure1 and the existing Reinhard shoulder; exactly one display conversion.
float hdrDisplay(float radiance) {
 float linear=max(radiance,0.0);return pow(linear/(linear+.72),1.0/2.2);
}
float bloomWeight(float peak) { return smoothstep(1.0,2.0,peak); }
// Depth of field: circle of confusion from eye distance d against the focus distance (u_dof.x, m);
// u_dof.y is the strength (0 disables), u_dof.w the in-focus half-range around it (m), and the radius is
// capped at .010 of the frame height. Authored.
float cocFor(float d,float4 dof) {
 // The sky dome (>80 m) fades back to sharp: a 12-tap gather turns tiny bright stars into flower patterns.
 return clamp(max(abs(d-dof.x)-dof.w,0.0)/max(d,.5)*.012*dof.y,0.0,.010)*(1.0-.9*smoothstep(80.0,200.0,d));
}
float grainHash(float2 p) { return fract(sin(dot(p,float2(12.9898,78.233)))*43758.5453); }
// Authored lens glare: strength comes from the radiance actually visible at the sun
// position, so buildings and cars occlude it. Not a recovered donor lens model.
float3 sunGlare(texture2d<float> scene, sampler smp, float2 uv, float4 sun) {
 if(sun.z<=0) return float3(0);
 float peak=0;
 const float2 taps[5]={float2(0,0),float2(.008,0),float2(-.008,0),float2(0,.012),float2(0,-.012)};
 for(int i=0;i<5;++i) peak+=max(max(scene.sample(smp,sun.xy+taps[i]).r,scene.sample(smp,sun.xy+taps[i]).g),0.0)/5;
 float visible=smoothstep(.9,2.4,peak)*sun.z;
 float2 d=(uv-sun.xy)*float2(sun.w,1); float r=length(d);
 float halo=exp(-r*7.0)*.10+exp(-r*26.0)*.16+exp(-r*90.0)*.30;
 float streak=exp(-abs(d.y)*70.0)*exp(-abs(d.x)*2.6)*.07;
 float ring=exp(-pow((r-.23)*16.0,2.0))*.012;
 // Ghost flares along the sun-to-centre axis (count/size/distance echo the lf_flare_* parameter
 // names REA found in the SLRR engine; values authored).
 float2 axis=float2(.5)-sun.xy;
 const float k[3]={.55,1.15,1.75};
 const float size[3]={.040,.065,.028};
 const float3 tint[3]={float3(1.0,.55,.30),float3(.45,.85,.55),float3(.55,.55,1.0)};
 float3 ghosts=float3(0);
 for(int i=0;i<3;++i) {
  float2 gp=sun.xy+axis*k[i];
  float gd=length((uv-gp)*float2(sun.w,1));
  ghosts+=tint[i]*smoothstep(size[i],size[i]*.1,gd)*.016;
 }
 return float3(1.0,.76,.48)*(halo+streak+ring)*visible+ghosts*visible;
}
fragment float4 xlatMtlMain(Varying in [[stage_in]], constant Globals& _mtl_u [[buffer(0)]],
 texture2d<float> s_postScene [[texture(0)]], sampler sceneSampler [[sampler(0)]],
 texture2d<float> s_postGlow [[texture(1)]], sampler glowSampler [[sampler(1)]],
 texture2d<float> s_postDepth [[texture(2)]]) {
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
 // Speed-driven radial blur with a protected centre, so the car stays sharp while the
 // periphery streaks. Authored; config.z is the 0..1 motion amount.
 float blurWeight=0;float3 blurred=linear;
 if(config.w<.5 && config.z>.001) {
  float2 toCentre=float2(.5)-in.uv;
  blurWeight=smoothstep(.10,.50,length(toCentre*float2(1.7,1.0)))*config.z;
  // Far sky (stars, moon) smeared radially reads as white dashes, not motion: fade the blur out
  // where the eye distance is sky-far (only sampled when the depth target exists, i.e. depth of field is active).
  constexpr sampler speedDepthSampler(filter::nearest,address::clamp_to_edge);
  if(_mtl_u.u_dof.y>.001) blurWeight*=1.0-.9*smoothstep(120.0,260.0,s_postDepth.sample(speedDepthSampler,in.uv).r);
  float3 sum=float3(0);
  for(int i=0;i<8;++i) sum+=s_postScene.sample(sceneSampler,in.uv+toCentre*(float(i)/7.0)*blurWeight*.09).rgb;
  blurred=max(sum/8.0,float3(0));
 }
 if(config.w<.5) {
  // Radial lateral fringing grows toward the frame edge, as in a real lens.
  float2 q=in.uv-.5; float2 shift=q*dot(q,q)*.0075;
  linear.r=max(s_postScene.sample(sceneSampler,in.uv+shift).r,0.0);
  linear.b=max(s_postScene.sample(sceneSampler,in.uv-shift).b,0.0);
  linear=mix(linear,blurred,clamp(blurWeight*6.0,0.0,1.0));
  // Blurred periphery loses saturation (MCLA exposes blurEffectDesatScale / blurEffectTintFade; amounts authored).
  float blurLuma=dot(linear,float3(.2126,.7152,.0722));
  linear=mix(linear,float3(blurLuma),clamp(blurWeight*2.2,0.0,.35));
  if(_mtl_u.u_dof.y>.001) {
   constexpr sampler depthSampler(filter::nearest,address::clamp_to_edge);
   float centreCoc=cocFor(s_postDepth.sample(depthSampler,in.uv).r,_mtl_u.u_dof);
   if(centreCoc>.0004) {
    float3 sum=linear;float weightSum=1.0;
    for(int i=0;i<12;++i) {
     float angle=float(i)*2.39996,radius=sqrt((float(i)+.5)/12.0)*centreCoc;
     float2 offset=float2(cos(angle)/_mtl_u.u_sun.w,sin(angle))*radius;
     float tapCoc=cocFor(s_postDepth.sample(depthSampler,in.uv+offset).r,_mtl_u.u_dof);
     float weight=clamp(tapCoc/max(radius,.0001),0.0,1.0);
     float3 tap=max(s_postScene.sample(sceneSampler,in.uv+offset).rgb,float3(0));
     // Bokeh: bright taps weigh more, so defocused lamps and neon spread into discs (u_dof.z strength).
     float bokeh=1.0+_mtl_u.u_dof.z*clamp(dot(tap,float3(.3,.59,.11))-1.0,0.0,6.0)*2.0;
     sum+=tap*(weight*bokeh);weightSum+=weight*bokeh;
    }
    linear=mix(linear,sum/weightSum,smoothstep(.0004,.0025,centreCoc));
   }
  }
  linear+=s_postGlow.sample(glowSampler,in.uv).rgb*.14;
  // Four-point lens star on very bright highlights (lamps, sun, wet-road glints), read from the
  // blurred bright-pass so it stays cheap. Authored after the cross flares seen in MCLA frames.
  float3 star=float3(0);
  const float2 dirs[4]={float2(1,0),float2(-1,0),float2(0,1),float2(0,-1)};
  for(int d=0;d<4;++d) for(int k=1;k<=7;++k) {
   float t=float(k)/7.0;
   float2 off=dirs[d]*t*.12*float2(.5625,1.0);
   float3 g=max(s_postGlow.sample(glowSampler,in.uv+off).rgb-float3(1.2),float3(0));
   star+=g*(1-t)*(1-t);
  }
  linear+=star*.035;
  linear+=sunGlare(s_postScene,sceneSampler,in.uv,_mtl_u.u_sun);
 }
 float3 display=float3(hdrDisplay(linear.r),hdrDisplay(linear.g),hdrDisplay(linear.b));
 if(config.w>.5) return float4(display,1); // Neutral still maps HDR; no bloom/grade.
 float luminance=dot(display,float3(.2126,.7152,.0722));
 // Daylight colour balance. MCLA's shipped post-processing tune (tune/lighting, REA extract of the retail
 // disc) sets colorcorrect .534/.534/.470 against a .498 neutral: x1.072, x1.072, x.943. Measured frames agree
 // (MCLA day R>G>B; Racer was B>G>R). Applied luminance-normalised and faded out with night amount, because
 // Racer's night is already warmer than MCLA's. The sensor value is carried in config.x - 3 (pass index 3).
 float dayWeight=1.0-clamp(config.x-3.0,0.0,1.0);
 display*=mix(float3(1.0),float3(1.072,1.072,.943)/1.063,dayWeight);
 // Measured trim: Racer day frames still read G>R against the web2 MCLA day references
 // (+.054 G-R vs MCLA -.013), while dusk already matches. Trim green only in full daylight.
 display*=float3(1.0,mix(1.0,.93,smoothstep(.55,.95,dayWeight)),1.0);
 display=mix(float3(luminance),display,1.16);
 // Filmic S-curve, cool shadows and warm highlights, then a restrained edge vignette.
 display=display*display*(3-2*display)*.38+display*.62;
 display=(display-.5)*1.10+.5;
 float shadows=1-smoothstep(.10,.55,luminance),highlights=smoothstep(.45,.95,luminance);
 display+=shadows*float3(-.014,.002,.020)+highlights*float3(.020,.008,-.012);
 float2 p=in.uv-.5;
 display*=1-.17*smoothstep(.06,.46,dot(p,p));
 display+=(grainHash(in.uv*float2(1731.0,947.0)+float2(config.y,config.y*1.7))-.5)*.014;
 return float4(clamp(display,float3(0),float3(1)),1);
}
)MSL";
  std::vector<uint8_t> bytes;
  auto u8 = [&](uint8_t n) { bytes.push_back(n); };
  auto u16 = [&](uint16_t n) {
    u8(uint8_t(n));
    u8(uint8_t(n >> 8));
  };
  auto u32 = [&](uint32_t n) {
    u16(uint16_t(n));
    u16(uint16_t(n >> 16));
  };
  auto uniform = [&](std::string_view name, uint8_t type, uint16_t offset) {
    u8(uint8_t(name.size()));
    bytes.insert(bytes.end(), name.begin(), name.end());
    u8(type | 0x10);
    u8(1);
    u16(offset);
    u16(1);
    u16(0);
    u16(0);
  };
  constexpr uint32_t interface = 0x504f5354;
  u8(fragment ? 'F' : 'V');
  u8('S');
  u8('H');
  u8(12);
  u32(fragment ? interface : 0);
  u32(fragment ? 0 : interface);
  u32(0);
  u32(0);
  u16(fragment ? 6 : 0);
  if (fragment) {
    uniform("u_post", bgfx::UniformType::Vec4, 0);
    uniform("u_sun", bgfx::UniformType::Vec4, 16);
    uniform("s_postScene", bgfx::UniformType::Sampler | 0x20, 0);
    uniform("s_postGlow", bgfx::UniformType::Sampler | 0x20, 1);
    uniform("s_postDepth", bgfx::UniformType::Sampler | 0x20, 2);
    uniform("u_dof", bgfx::UniformType::Vec4, 32);
  }
  const auto source = fragment ? pixel : vertex;
  u32(uint32_t(source.size()));
  bytes.insert(bytes.end(), source.begin(), source.end());
  u8(0);
  u8(fragment ? 0 : 2);
  if (!fragment) {
    u16(0x0001);
    u16(0x0010);
  }
  u16(fragment ? 48 : 0);
  return bytes;
}

class PostProcess {
  struct Targets {
    bgfx::TextureHandle scene = BGFX_INVALID_HANDLE,
                        depth = BGFX_INVALID_HANDLE,
                        depthColor = BGFX_INVALID_HANDLE;
    std::array<bgfx::TextureHandle, 2> glow{
        {BGFX_INVALID_HANDLE, BGFX_INVALID_HANDLE}};
    bgfx::FrameBufferHandle sceneFrame = BGFX_INVALID_HANDLE;
    std::array<bgfx::FrameBufferHandle, 2> glowFrames{
        {BGFX_INVALID_HANDLE, BGFX_INVALID_HANDLE}};
    uint16_t width = 0, height = 0, sceneWidth = 0, sceneHeight = 0,
             glowWidth = 0, glowHeight = 0;
    ~Targets() {
      if (bgfx::isValid(sceneFrame))
        bgfx::destroy(sceneFrame);
      for (auto h : glowFrames)
        if (bgfx::isValid(h))
          bgfx::destroy(h);
      if (bgfx::isValid(scene))
        bgfx::destroy(scene);
      if (bgfx::isValid(depth))
        bgfx::destroy(depth);
      if (bgfx::isValid(depthColor))
        bgfx::destroy(depthColor);
      for (auto h : glow)
        if (bgfx::isValid(h))
          bgfx::destroy(h);
    }
  };

public:
  static constexpr uint16_t uiView = 14;
  PostProcess() {
    try {
      bgfx::VertexLayout layout;
      layout.begin()
          .add(bgfx::Attrib::Position, 2, bgfx::AttribType::Float)
          .add(bgfx::Attrib::TexCoord0, 2, bgfx::AttribType::Float)
          .end();
      // Metal render targets and samplers both use top-origin texture rows.
      constexpr float vertices[] = {-1, -1, 0, 1, 3, -1, 2, 1, -1, 3, 0, -1};
      vertices_ = bgfx::createVertexBuffer(
          bgfx::copy(vertices, sizeof(vertices)), layout);
      const auto vs = postShader(false), fs = postShader(true);
      auto vertex =
          bgfx::createShader(bgfx::copy(vs.data(), uint32_t(vs.size())));
      if (!bgfx::isValid(vertex))
        throw std::runtime_error("post_vertex_shader");
      auto pixel =
          bgfx::createShader(bgfx::copy(fs.data(), uint32_t(fs.size())));
      if (!bgfx::isValid(pixel)) {
        bgfx::destroy(vertex);
        throw std::runtime_error("post_pixel_shader");
      }
      program_ = bgfx::createProgram(vertex, pixel, false);
      bgfx::destroy(vertex);
      bgfx::destroy(pixel);
      sceneSampler_ =
          bgfx::createUniform("s_postScene", bgfx::UniformType::Sampler);
      glowSampler_ =
          bgfx::createUniform("s_postGlow", bgfx::UniformType::Sampler);
      depthSampler_ =
          bgfx::createUniform("s_postDepth", bgfx::UniformType::Sampler);
      dof_ = bgfx::createUniform("u_dof", bgfx::UniformType::Vec4);
      config_ = bgfx::createUniform("u_post", bgfx::UniformType::Vec4);
      sun_ = bgfx::createUniform("u_sun", bgfx::UniformType::Vec4);
      if (!bgfx::isValid(vertices_) || !bgfx::isValid(program_) ||
          !bgfx::isValid(sceneSampler_) || !bgfx::isValid(glowSampler_) ||
          !bgfx::isValid(config_) || !bgfx::isValid(sun_) ||
          !bgfx::isValid(depthSampler_) || !bgfx::isValid(dof_))
        throw std::runtime_error("post_resources");
    } catch (...) {
      release();
      throw;
    }
  }
  ~PostProcess() { release(); }
  PostProcess(const PostProcess &) = delete;
  PostProcess &operator=(const PostProcess &) = delete;

  void ensure(uint16_t width, uint16_t height) {
    if (width < 1 || height < 1)
      throw std::runtime_error("post_size_bounds");
    if (targets_ && targets_->width == width && targets_->height == height)
      return;
    constexpr uint32_t colorRequired =
        BGFX_CAPS_FORMAT_TEXTURE_2D | BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER |
        BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4;
    constexpr uint32_t depthRequired =
        BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER |
        BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4;
    const auto *caps = bgfx::getCaps();
    if ((caps->formats[bgfx::TextureFormat::RGBA16F] & colorRequired) !=
            colorRequired ||
        (caps->formats[bgfx::TextureFormat::D32F] & depthRequired) !=
            depthRequired)
      throw std::runtime_error("post_hdr_format_unsupported");
    auto next = std::make_unique<Targets>();
    next->width = width;
    next->height = height;
    const double scale = std::min({1., 3840. / width, 2160. / height});
    next->sceneWidth = std::max(uint16_t(1), uint16_t(width * scale));
    next->sceneHeight = std::max(uint16_t(1), uint16_t(height * scale));
    next->glowWidth = uint16_t((next->sceneWidth + 3) / 4);
    next->glowHeight = uint16_t((next->sceneHeight + 3) / 4);
    constexpr uint64_t sampling = BGFX_SAMPLER_U_CLAMP | BGFX_SAMPLER_V_CLAMP;
    next->scene = bgfx::createTexture2D(next->sceneWidth, next->sceneHeight,
                                        false, 1, bgfx::TextureFormat::RGBA16F,
                                        BGFX_TEXTURE_RT_MSAA_X4 | sampling);
    next->depth = bgfx::createTexture2D(next->sceneWidth, next->sceneHeight,
                                        false, 1, bgfx::TextureFormat::D32F,
                                        BGFX_TEXTURE_RT_MSAA_X4 |
                                            BGFX_TEXTURE_RT_WRITE_ONLY);
    if (!bgfx::isValid(next->scene) || !bgfx::isValid(next->depth))
      throw std::runtime_error("post_scene_texture");
    // Optional second colour target: eye distance in metres for depth of field.
    // Absent when R32F cannot be a multisampled render target; the post pass
    // then simply skips depth of field.
    constexpr uint32_t depthColorRequired =
        BGFX_CAPS_FORMAT_TEXTURE_2D | BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER |
        BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER_MSAA_X4;
    if ((caps->formats[bgfx::TextureFormat::R32F] & depthColorRequired) ==
        depthColorRequired)
      next->depthColor = bgfx::createTexture2D(
          next->sceneWidth, next->sceneHeight, false, 1,
          bgfx::TextureFormat::R32F, BGFX_TEXTURE_RT_MSAA_X4 | sampling);
    if (bgfx::isValid(next->depthColor)) {
      bgfx::TextureHandle attachments[] = {next->scene, next->depthColor,
                                           next->depth};
      next->sceneFrame = bgfx::createFrameBuffer(3, attachments, false);
    } else {
      bgfx::TextureHandle attachments[] = {next->scene, next->depth};
      next->sceneFrame = bgfx::createFrameBuffer(2, attachments, false);
    }
    if (!bgfx::isValid(next->sceneFrame))
      throw std::runtime_error("post_scene_framebuffer");
    for (size_t i = 0; i < 2; ++i) {
      next->glow[i] = bgfx::createTexture2D(
          next->glowWidth, next->glowHeight, false, 1,
          bgfx::TextureFormat::RGBA16F, BGFX_TEXTURE_RT | sampling);
      if (!bgfx::isValid(next->glow[i]))
        throw std::runtime_error("post_glow_texture");
      next->glowFrames[i] = bgfx::createFrameBuffer(1, &next->glow[i], false);
      if (!bgfx::isValid(next->glowFrames[i]))
        throw std::runtime_error("post_glow_framebuffer");
    }
    targets_ = std::move(next);
  }
  bgfx::FrameBufferHandle sceneFrame() const {
    if (!targets_)
      throw std::logic_error("post_not_sized");
    return targets_->sceneFrame;
  }
  uint16_t sceneWidth() const {
    if (!targets_)
      throw std::logic_error("post_not_sized");
    return targets_->sceneWidth;
  }
  uint16_t sceneHeight() const {
    if (!targets_)
      throw std::logic_error("post_not_sized");
    return targets_->sceneHeight;
  }
  // Screen-space sun anchor: uv.xy (top-origin), visibility weight, aspect.
  // Zero hides glare.
  void setSun(float u, float v, float weight, float aspect) {
    sun_value_ = {u, v, weight, aspect};
  }
  // Focus distance (m) and strength; ignored (no depth of field) when the depth
  // target is unavailable.
  void setFocus(float distance, float strength, float bokeh = 0) {
    focus_value_ = {std::max(distance, .5f), std::clamp(strength, 0.f, 4.f),
                    std::clamp(bokeh, 0.f, 4.f), 2.6f};
  }
  bool depthOfFieldAvailable() const {
    return targets_ && bgfx::isValid(targets_->depthColor);
  }
  // Speed blur amount in [0,1]; ignored by neutral output.
  void setMotion(float amount) { motion_ = std::clamp(amount, 0.f, 1.f); }
  // Night amount 0..1 (day, dusk ~.45, night): fades the daylight colour
  // balance. Rides in u_post.x (3 + night).
  void setNight(float amount) { night_ = std::clamp(amount, 0.f, 1.f); }
  void draw(bool neutral) {
    if (!targets_)
      throw std::logic_error("post_not_sized");
    const auto &t = *targets_;
    // Never bind a writable attachment as either sampled input, even when the
    // selected shader branch would not read it. All views execute in ID order.
    if (!neutral) {
      pass(10, t.glowFrames[0], t.glowWidth, t.glowHeight, t.scene, t.scene,
           {0, 0, 0, 0});
      pass(11, t.glowFrames[1], t.glowWidth, t.glowHeight, t.glow[0], t.scene,
           {1, 1.f / t.glowWidth, 0, 0});
      pass(12, t.glowFrames[0], t.glowWidth, t.glowHeight, t.glow[1], t.scene,
           {2, 0, 1.f / t.glowHeight, 0});
    }
    // Neutral does not read an uninitialized glow texture.
    pass(13, BGFX_INVALID_HANDLE, t.width, t.height, t.scene,
         neutral ? t.scene : t.glow[0],
         {3.f + night_, float(frame_ % 61) * .0137f, motion_,
          neutral ? 1.f : 0.f});
    ++frame_;
  }

private:
  std::unique_ptr<Targets> targets_;
  bgfx::VertexBufferHandle vertices_ = BGFX_INVALID_HANDLE;
  bgfx::ProgramHandle program_ = BGFX_INVALID_HANDLE;
  bgfx::UniformHandle sceneSampler_ = BGFX_INVALID_HANDLE,
                      glowSampler_ = BGFX_INVALID_HANDLE,
                      config_ = BGFX_INVALID_HANDLE, sun_ = BGFX_INVALID_HANDLE,
                      depthSampler_ = BGFX_INVALID_HANDLE,
                      dof_ = BGFX_INVALID_HANDLE;
  std::array<float, 4> sun_value_{{0, 0, 0, 1}}, focus_value_{{8, 0, 0, 0}};
  float motion_ = 0, night_ = 0;
  uint32_t frame_ = 0; // Advances grain only; never affects neutral output.
  void pass(uint16_t view, bgfx::FrameBufferHandle frame, uint16_t width,
            uint16_t height, bgfx::TextureHandle input,
            bgfx::TextureHandle glow, const std::array<float, 4> &config) {
    bgfx::setViewFrameBuffer(view, frame);
    bgfx::setViewRect(view, 0, 0, width, height);
    bgfx::setViewMode(view, bgfx::ViewMode::Sequential);
    bgfx::setViewClear(view, BGFX_CLEAR_NONE);
    bgfx::setViewTransform(view, nullptr, nullptr);
    bgfx::setScissor();
    bgfx::setVertexBuffer(0, vertices_);
    bgfx::setTexture(0, sceneSampler_, input);
    bgfx::setTexture(1, glowSampler_, glow);
    // Stage 2 always holds a texture that is not this pass's render target;
    // without a depth target the scene stands in.
    bgfx::setTexture(2, depthSampler_,
                     targets_ && bgfx::isValid(targets_->depthColor)
                         ? targets_->depthColor
                         : input);
    {
      auto focus = focus_value_;
      if (!targets_ || !bgfx::isValid(targets_->depthColor))
        focus[1] = 0;
      bgfx::setUniform(dof_, focus.data());
    }
    bgfx::setUniform(config_, config.data());
    bgfx::setUniform(sun_, sun_value_.data());
    bgfx::setState(BGFX_STATE_WRITE_RGB | BGFX_STATE_WRITE_A | BGFX_STATE_MSAA);
    bgfx::submit(view, program_);
  }
  void release() noexcept {
    targets_.reset();
    if (bgfx::isValid(vertices_))
      bgfx::destroy(vertices_);
    vertices_ = BGFX_INVALID_HANDLE;
    if (bgfx::isValid(program_))
      bgfx::destroy(program_);
    program_ = BGFX_INVALID_HANDLE;
    for (auto *h : {&sceneSampler_, &glowSampler_, &config_, &sun_,
                    &depthSampler_, &dof_}) {
      if (bgfx::isValid(*h))
        bgfx::destroy(*h);
      *h = BGFX_INVALID_HANDLE;
    }
  }
};
} // namespace racer
