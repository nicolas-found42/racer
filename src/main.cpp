#include "gamepad.h"
#include "garage_live_checks.h"
#include "live_checks.h"
#include "play_flow.h"
#include "review_script.h"
#include "simulation.h"
#include "render_transform.h"
#include "diagnostics.h"
#include "workflow_observation.h"
#include <memory>
#include <SDL3/SDL.h>
#include <SDL3/SDL_metal.h>
#include <bgfx/bgfx.h>
#include <bx/math.h>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
#include <string>
#include <vector>

#include "render_capture.h"
// Keeps callbacks alive until bgfx's worker has stopped, including exceptions.
struct RendererLifetime {
  SDL_Window *window;
  SDL_MetalView metal;
  bool ready = false;
  ~RendererLifetime() {
    if (ready) bgfx::shutdown();
    SDL_Metal_DestroyView(metal); SDL_DestroyWindow(window); SDL_Quit();
  }
};
#include "mesh_asset.h"
#include "vehicle_asset.h"
#include "world_scale.h"
#include "livery_raster.h"
#include "visual_shader.h"
#include "world_scene.h"
#include "street_detail.h"
#include "drive_hud.h"
#include "world_surfaces.h"
#include "scene_reflection.h"
#include "post_process.h"
#include "texture_upload.h"
#include "static_texture_pool.h"
#include "surface_follow.h"
#include <map>
#include <sstream>
struct CarGraphics {
  bgfx::VertexBufferHandle vertices=BGFX_INVALID_HANDLE;
  bgfx::VertexBufferHandle overlay=BGFX_INVALID_HANDLE;
  std::vector<racer::TextureRef> textures;
  std::vector<racer::AssetSection> sections;
  ~CarGraphics() {
    if (bgfx::isValid(vertices)) bgfx::destroy(vertices);
    if (bgfx::isValid(overlay)) bgfx::destroy(overlay);
  }
};
using Vertex = racer::AssetVertex;
using Mesh = std::vector<Vertex>;
void box(Mesh &m, float x, float y, float z, float sx, float sy, float sz,
         uint32_t c,float surface=0) {
  float p[8][3] = {{x - sx / 2, y - sy / 2, z - sz / 2},
                   {x + sx / 2, y - sy / 2, z - sz / 2},
                   {x + sx / 2, y + sy / 2, z - sz / 2},
                   {x - sx / 2, y + sy / 2, z - sz / 2},
                   {x - sx / 2, y - sy / 2, z + sz / 2},
                   {x + sx / 2, y - sy / 2, z + sz / 2},
                   {x + sx / 2, y + sy / 2, z + sz / 2},
                   {x - sx / 2, y + sy / 2, z + sz / 2}};
  int faces[6][6] = {{0, 1, 2, 0, 2, 3}, {4, 6, 5, 4, 7, 6},
                     {0, 4, 5, 0, 5, 1}, {3, 2, 6, 3, 6, 7},
                     {1, 5, 6, 1, 6, 2}, {0, 3, 7, 0, 7, 4}};
  for (int f = 0; f < 6; f++) {
    const uint32_t col=c;
    constexpr float normals[6][3]={{0,0,-1},{0,0,1},{0,-1,0},{0,1,0},{1,0,0},{-1,0,0}};
    for (int i : faces[f])
      m.push_back({p[i][0], p[i][1], p[i][2], col,.95f,surface,normals[f][0],normals[f][1],normals[f][2]});
  }
}
int run(int argc, char **argv, racer::Diagnostics &diagnostics) {
  double smoke = 0;
  bool courseDriver = false, background = false;
  double autoTurn = .22;
  bool autoDrive = false, benchmark = false, verify = false;
  double shotDelay = 2;
  bool shotDelayExplicit = false;
  bool wheelBlur = true, skidMarks = true, speedFov = true, tyreSmoke = true;
  float nightAmount = 0, paintHue = 0, paintStrength = 0;
  std::string shot, profilePath, scene, garageMode, captureLoop, reviewPath, previewMesh,skyMesh,sceneryMesh;
  std::vector<std::string> worldMeshes;
  std::string vehicleLibrary=RACER_VEHICLE_LIBRARY,requestedVehicle;
  std::string cameraView="rear";
  float worldOrigin[3]={0,0,0};
  double worldHeading=0;
  double inspectionDistance=0;
  bool postNeutral=false;
  bool hideHud=false,followGround=false;
  int windowWidth = 1920, windowHeight = 1080;
  std::string surfacePath = RACER_WORLD_SURFACES;
  skyMesh=RACER_SKY_MESH;
  if(!std::filesystem::exists(skyMesh))skyMesh.clear();
  sceneryMesh=RACER_CITY_SCENERY;
  if(!std::filesystem::exists(sceneryMesh))sceneryMesh.clear();
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    if (a == "--diagnostics-dir" && i + 1 < argc)
      ++i;
    else if (a == "--no-diagnostics") {}
    else if (a == "--background") background = true;
    else if (a == "--post-neutral") postNeutral = true;
    else if (a == "--no-wheel-blur") wheelBlur = false;
    else if (a == "--no-skid-marks") skidMarks = false;
    else if (a == "--no-speed-fov") speedFov = false;
    else if (a == "--no-tyre-smoke") tyreSmoke = false;
    else if (a == "--paint" && i + 1 < argc) {
      const std::string value = argv[++i];
      struct Entry {const char* name; float hue;};
      const Entry table[] = {{"red",0.f},{"orange",.07f},{"yellow",.15f},{"green",.35f},{"teal",.5f},{"blue",.62f},{"purple",.78f},{"black",-1.f}};
      bool found = false;
      for (const auto& e : table) if (value == e.name) {paintHue = e.hue; paintStrength = value == "black" ? .85f : .9f; found = true;}
      if (!found) {
        std::cerr << "--paint must be red, orange, yellow, green, teal, blue, purple or black\n";
        return 1;
      }
    }
    else if (a == "--time" && i + 1 < argc) {
      const std::string value = argv[++i];
      if (value == "day") nightAmount = 0;
      else if (value == "night") nightAmount = 1;
      else if (value == "dusk") nightAmount = .45f;
      else {
        std::cerr << "--time must be day, dusk or night\n";
        return 1;
      }
    }
    else if (a == "--hide-hud") hideHud = true;
    else if (a == "--follow-ground") followGround = true;
    else if (a == "--preview-gltf" && i + 1 < argc) previewMesh = argv[++i];
    else if (a == "--world-mesh" && i + 1 < argc) {
      if(worldMeshes.size()>=4) {
        diagnostics.event("static_asset_admission",{{"reason","world_mesh_count"},{"maximum",4}});
        throw std::runtime_error("world_mesh_count");
      }
      worldMeshes.push_back(argv[++i]);
    }
    else if (a == "--sky-mesh" && i + 1 < argc) skyMesh = argv[++i];
    else if (a == "--scenery-mesh" && i + 1 < argc) sceneryMesh = argv[++i];
    else if (a == "--world-origin" && i + 3 < argc) {
      for(float &component:worldOrigin) {
        component=std::stof(argv[++i]);
        if(!std::isfinite(component)||std::abs(component)>10000)throw std::runtime_error("world_origin_bounds");
      }
    }
    else if(a=="--world-heading" && i+1<argc) {
      const std::string value=argv[++i];size_t used=0;const double degrees=std::stod(value,&used);
      if(used!=value.size()||!std::isfinite(degrees)||std::abs(degrees)>360)
        throw std::runtime_error("world_heading_bounds");
      // Same clockwise heading convention as the car, expressed in degrees.
      worldHeading=degrees*std::acos(-1.0)/180;
    }
    else if (a == "--camera-distance" && i + 1 < argc) {
      inspectionDistance=std::stod(argv[++i]);
      if(!std::isfinite(inspectionDistance)||inspectionDistance<2||inspectionDistance>1000)
        throw std::runtime_error("camera_distance_bounds");
    }
    else if (a == "--vehicle-library" && i + 1 < argc) vehicleLibrary=argv[++i];
    else if (a == "--vehicle" && i + 1 < argc) requestedVehicle=argv[++i];
    else if (a == "--camera-view" && i + 1 < argc) cameraView=argv[++i];
    // Retained pre-HDR capture argv may still provide external shader files.
    // Current scene/HUD programs are embedded; accept the old option.
    else if (a == "--shader-dir" && i + 1 < argc) ++i;
    else if (a == "--world-surfaces" && i + 1 < argc) surfacePath = argv[++i];
    else if (a == "--autodrive-left") { autoDrive = true; autoTurn = -.22; }
    else if (a == "--course-driver")
      courseDriver = true;
    else if (a == "--review-script" && i + 1 < argc)
      reviewPath = argv[++i];
    else if (a == "--window" && i + 2 < argc) {
      windowWidth = std::stoi(argv[++i]);
      windowHeight = std::stoi(argv[++i]);
    } else if (a == "--capture-loop" && i + 1 < argc)
      captureLoop = argv[++i];
    else if (a == "--profile" && i + 1 < argc)
      profilePath = argv[++i];
    else if (a == "--scene" && i + 1 < argc)
      scene = argv[++i];
    else if (a == "--verify-garage" && i + 1 < argc) {
      garageMode = argv[++i];
      smoke = 28;
      if (garageMode != "keyboard" && garageMode != "gamepad")
        return 1;
    } else if (a == "--smoke" && i + 1 < argc)
      smoke = std::stod(argv[++i]);
    else if (a == "--verify-controls") {
      verify = true;
      smoke = 5;
    } else if (a == "--benchmark")
      benchmark = true;
    else if (a == "--autodrive")
      autoDrive = true;
    else if (a == "--screenshot" && i + 1 < argc)
      shot = argv[++i];
    else if (a == "--screenshot-delay" && i + 1 < argc) {
      shotDelay = std::strtod(argv[++i], nullptr);
      shotDelayExplicit = true;
      if (!std::isfinite(shotDelay) || shotDelay < 2 || shotDelay > 30) {
        std::cerr << "--screenshot-delay must be within [2,30] seconds\n";
        return 1;
      }
    }
    else {
      std::cerr
          << "Usage: racer [--smoke seconds] [--autodrive] [--benchmark] "
             "[--verify-controls] [--verify-garage keyboard|gamepad] "
             "[--profile path] [--capture-loop directory] [--scene "
             "garage|course|scale] [--camera-view rear|front|left|right|elevated] [--screenshot path.ppm [--screenshot-delay 2..30]] [--window width height] "
             "[--review-script path] [--course-driver] [--diagnostics-dir path] [--no-diagnostics]\n";
      std::cerr << "Cars: [--vehicle-library catalog.racer] [--vehicle index|id|name] [--preview-gltf local-path]\n";
      std::cerr << "Visual inspection: [--world-mesh local.glb] [--scenery-mesh local.glb] [--sky-mesh local.glb] [--world-origin x y z] [--world-heading degrees] [--follow-ground] [--camera-distance metres] [--world-surfaces surfaces.rgba]\n";
      std::cerr << "Optical calibration: [--post-neutral]\n";
      std::cerr << "Asset inspection: [--hide-hud]\n";
      return 1;
    }
  }
  if(followGround && (worldMeshes.empty() || !previewMesh.empty()))
    throw std::runtime_error("surface_follow_requires_world_and_vehicle");
  // A requested delayed capture must fit inside a bounded smoke run, or no image would be written.
  if (shotDelayExplicit && smoke > 0 && shotDelay + .25 > smoke) {
    std::cerr << "--screenshot-delay must be shorter than --smoke seconds\n";
    return 1;
  }
  if (cameraView!="rear" && cameraView!="front" && cameraView!="left" && cameraView!="right" && cameraView!="elevated")
    throw std::runtime_error("Unsupported --camera-view");
  if (windowWidth < 320 || windowHeight < 240 || windowWidth > 3840 || windowHeight > 2160) {
    diagnostics.event("configuration_rejected", {{"reason", "window_bounds"}});
    return 1;
  }
  if ((!garageMode.empty() || !reviewPath.empty() || courseDriver) &&
      profilePath.empty()) {
    std::cerr << "Verification drivers require an isolated --profile path\n";
    return 1;
  }
  diagnostics.event("app_start", {{"build", RACER_BUILD_ID}, {"platform", SDL_GetPlatform()},
    {"sdl_version", SDL_GetVersion()}, {"model_revision", previewMesh.empty()?2:1}, {"test_revision", 1}, {"profile_schema_max", 2},
    {"camera_view",cameraView},{"scale_fixture",scene=="scale"},{"world_metres_per_unit",racer::worldScale::metersPerUnit},
    {"background", background}, {"benchmark", benchmark}, {"asset_preview", !previewMesh.empty()}, {"autodrive", autoDrive}, {"autodrive_turn", autoTurn}, {"course_driver", courseDriver},
    {"review_script", !reviewPath.empty()}, {"verify_controls", verify}, {"garage_driver", !garageMode.empty()},
    {"requested_width", windowWidth}, {"requested_height", windowHeight}, {"step_seconds", racer::step}});
  SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
  if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD)) {
    diagnostics.event("startup_failure", {{"stage", "sdl_or_window"}});
    std::cerr << SDL_GetError();
    return 1;
  }
  if (profilePath.empty()) {
    const char *pref = SDL_GetPrefPath("Racer", "Racer");
    if (!pref) {
      std::cerr << "Cannot locate profile directory: " << SDL_GetError();
      SDL_Quit();
      return 1;
    }
    profilePath = std::string(pref) + "profile.txt";
  }
  std::cout << "Profile: " << profilePath << '\n';
  auto window =
      SDL_CreateWindow("Racer | Driving Grid", windowWidth, windowHeight,
                       SDL_WINDOW_METAL | SDL_WINDOW_RESIZABLE | (background ? SDL_WINDOW_HIDDEN : 0));
  if (!window) {
    diagnostics.event("startup_failure", {{"stage", "sdl_or_window"}});
    std::cerr << SDL_GetError();
    SDL_Quit();
    return 1;
  }
  auto metal = SDL_Metal_CreateView(window);
  if (!metal) {
    diagnostics.event("startup_failure", {{"stage", "metal_view"}});
    SDL_DestroyWindow(window); SDL_Quit(); return 1;
  }
  Capture callback(diagnostics);
  RendererLifetime lifetime{window, metal};
  int width, height;
  SDL_GetWindowSizeInPixels(window, &width, &height);
  if (benchmark) {
    width = 1920;
    height = 1080;
  }
  bgfx::Init init;
  init.type = bgfx::RendererType::Metal;
  init.fallback = false;
  init.swapChain.nwh = SDL_Metal_GetLayer(metal);
  init.swapChain.width = width;
  init.swapChain.height = height;
  init.reset = BGFX_RESET_VSYNC | BGFX_RESET_MSAA_X4;
  init.callback = &callback;
  if (!bgfx::init(init)) {
    diagnostics.event("startup_failure", {{"stage", "bgfx_init"}});
    std::cerr << "Metal initialization failed\n";
    return 1;
  }
  lifetime.ready = true;
  racer::DriveHud driveHud;
  std::cout << "Renderer: " << bgfx::getRendererName(bgfx::getRendererType())
            << " | " << width << 'x' << height << '\n';
  diagnostics.event("renderer_ready", {{"backend", "Metal"}, {"width", width}, {"height", height}});
  bgfx::setDebug(hideHud?BGFX_DEBUG_NONE:BGFX_DEBUG_TEXT);
  bgfx::VertexLayout layout;
  layout.begin()
      .add(bgfx::Attrib::Position, 3, bgfx::AttribType::Float)
      .add(bgfx::Attrib::Color0, 4, bgfx::AttribType::Uint8, true)
      .add(bgfx::Attrib::TexCoord0, 2, bgfx::AttribType::Float)
      .add(bgfx::Attrib::Normal, 3, bgfx::AttribType::Float)
      .add(bgfx::Attrib::TexCoord1, 2, bgfx::AttribType::Float)
      .add(bgfx::Attrib::Tangent,4,bgfx::AttribType::Float)
      .end();
  auto liverySampler=bgfx::createUniform("s_texColor",bgfx::UniformType::Sampler);
  auto liveryTexture=bgfx::createTexture2D(racer::liveryTextureSize,racer::liveryTextureSize,false,1,
      bgfx::TextureFormat::RGBA8,BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP);
  const uint32_t whitePixel=0xffffffff;
  auto whiteTexture=bgfx::createTexture2D(1,1,false,1,bgfx::TextureFormat::RGBA8,0,bgfx::copy(&whitePixel,4));
  auto cameraUniform=bgfx::createUniform("u_visualCamera",bgfx::UniformType::Vec4);
  auto materialUniform=bgfx::createUniform("u_visualMaterial",bgfx::UniformType::Vec4);
  auto shadowUniform=bgfx::createUniform("u_shadowMatrix",bgfx::UniformType::Mat4);
  auto shadowSampler=bgfx::createUniform("s_shadow",bgfx::UniformType::Sampler);
  auto surfaceSampler=bgfx::createUniform("s_surfaces",bgfx::UniformType::Sampler);
  auto environmentSampler=bgfx::createUniform("s_environment",bgfx::UniformType::Sampler);
  auto normalSampler=bgfx::createUniform("s_normal",bgfx::UniformType::Sampler);
  auto bindNormal=[&](const CarGraphics* asset=nullptr,const racer::AssetSection* section=nullptr) {
    const int image=section?section->normalImage:-1;
    const auto wrap=[](int u,int v) {
      return (u==33071?BGFX_SAMPLER_U_CLAMP:u==33648?BGFX_SAMPLER_U_MIRROR:0)|
             (v==33071?BGFX_SAMPLER_V_CLAMP:v==33648?BGFX_SAMPLER_V_MIRROR:0);
    };
    bgfx::setTexture(4,normalSampler,image>=0?asset->textures.at(size_t(image))->handle:whiteTexture,
      section?wrap(section->normalWrapU,section->normalWrapV):uint32_t(0));
  };
  auto reflectionUniform=bgfx::createUniform("u_reflectionState",bgfx::UniformType::Vec4);
  auto coatUniform=bgfx::createUniform("u_visualCoat",bgfx::UniformType::Vec4);
  auto headlightUniform=bgfx::createUniform("u_headlight",bgfx::UniformType::Vec4);
  float headlightState[4]={0,0,0,nightAmount}; // car x,z,heading and night amount; refreshed every frame
  racer::SceneReflection sceneReflection;
  racer::PostProcess postProcess;
  bool texturedPalms=false;
  auto surfacePixels=racer::readWorldSurfaces(surfacePath,&texturedPalms);
  const bool sourceSurfaces=!surfacePixels.empty();
  bgfx::TextureHandle surfaceTexture=whiteTexture;
  if(sourceSurfaces) {
    surfaceTexture=bgfx::createTexture2D(256,1024,true,1,bgfx::TextureFormat::RGBA8,0);
    unsigned w=256,h=1024;
    for(uint8_t level=0;;++level) {
      bgfx::updateTexture2D(surfaceTexture,0,level,0,0,uint16_t(w),uint16_t(h),
        bgfx::copy(surfacePixels.data(),uint32_t(surfacePixels.size())));
      if(w==1 && h==1) break;
      const unsigned nw=std::max(1u,w/2),nh=std::max(1u,h/2);
      std::vector<uint8_t> mip(size_t(nw)*nh*4);
      for(unsigned y=0;y<nh;++y) for(unsigned x=0;x<nw;++x) for(unsigned c=0;c<4;++c) {
        unsigned sum=0;
        for(unsigned dy=0;dy<2;++dy) for(unsigned dx=0;dx<2;++dx)
          sum+=surfacePixels[(std::min(h-1,y*2+dy)*w+std::min(w-1,x*2+dx))*4+c];
        mip[(y*nw+x)*4+c]=uint8_t(sum/4);
      }
      surfacePixels=std::move(mip);w=nw;h=nh;
    }
  }
  diagnostics.event("world_surfaces",{{"source_available",sourceSurfaces},{"sha256",sourceSurfaces?racer::Diagnostics::fileHash(surfacePath):"unavailable"}});
  const auto visualVS=racer::visualShader(false),visualFS=racer::visualShader(true);
  auto visualProgram=bgfx::createProgram(
    bgfx::createShader(bgfx::copy(visualVS.data(),uint32_t(visualVS.size()))),
    bgfx::createShader(bgfx::copy(visualFS.data(),uint32_t(visualFS.size()))),true);
  if(!bgfx::isValid(visualProgram)) throw std::runtime_error("Visual shader unavailable");
  const auto shadowFS=racer::visualShader(true,true);
  auto shadowProgram=bgfx::createProgram(
    bgfx::createShader(bgfx::copy(visualVS.data(),uint32_t(visualVS.size()))),
    bgfx::createShader(bgfx::copy(shadowFS.data(),uint32_t(shadowFS.size()))),true);
  constexpr uint64_t shadowFlags=BGFX_TEXTURE_RT|BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP|BGFX_SAMPLER_MIN_POINT|BGFX_SAMPLER_MAG_POINT;
  auto shadowMap=bgfx::createTexture2D(2048,2048,false,1,bgfx::TextureFormat::R32F,shadowFlags);
  auto shadowDepth=bgfx::createTexture2D(2048,2048,false,1,bgfx::TextureFormat::D32F,BGFX_TEXTURE_RT_WRITE_ONLY);
  const bgfx::TextureHandle shadowAttachments[]={shadowMap,shadowDepth};
  auto shadowFramebuffer=bgfx::createFrameBuffer(2,shadowAttachments,true);
  if(!bgfx::isValid(shadowProgram)||!bgfx::isValid(shadowFramebuffer)) throw std::runtime_error("Shadow renderer unavailable");
  bgfx::setViewMode(1,bgfx::ViewMode::Sequential);
  Mesh atmosphere;
  constexpr int rings=20,slices=48;
  auto skyPoint=[](int r,int s) {
    const float phi=float(r)*3.14159265f/rings,theta=float(s)*6.2831853f/slices;
    return Vertex{700*std::sin(phi)*std::cos(theta),700*std::cos(phi),700*std::sin(phi)*std::sin(theta),0xffffffff};
  };
  for(int r=0;r<rings;++r) for(int s=0;s<slices;++s) {
    for(auto [rr,ss]:{std::pair{r,s},std::pair{r+1,s},std::pair{r+1,s+1},std::pair{r,s},std::pair{r+1,s+1},std::pair{r,s+1}})
      atmosphere.push_back(skyPoint(rr,ss));
  }
  auto skyBuffer=bgfx::createVertexBuffer(bgfx::copy(atmosphere.data(),uint32_t(atmosphere.size()*sizeof(Vertex))),layout);
  Mesh contact;
  for(int ring=0;ring<6;++ring) for(int s=0;s<48;++s) {
    auto point=[](int r,int segment) {
      float radius=float(r)/6,angle=segment*6.2831853f/48;
      uint32_t alpha=uint32_t(100*std::pow(1-radius,1.5f));
      return Vertex{std::cos(angle)*radius,.026f,std::sin(angle)*radius,alpha<<24};
    };
    for(auto [r,t]:{std::pair{ring,s},std::pair{ring+1,s},std::pair{ring+1,s+1},std::pair{ring,s},std::pair{ring+1,s+1},std::pair{ring,s+1}}) contact.push_back(point(r,t));
  }
  auto contactBuffer=bgfx::createVertexBuffer(bgfx::copy(contact.data(),uint32_t(contact.size()*sizeof(Vertex))),layout);
  Mesh tireContact=contact;
  for(auto& v:tireContact){v.y=.003f;v.color=std::min(200u,(v.color>>24)*2u)<<24;}
  auto tireContactBuffer=bgfx::createVertexBuffer(bgfx::copy(tireContact.data(),uint32_t(tireContact.size()*sizeof(Vertex))),layout);
  if (!bgfx::isValid(liverySampler) || !bgfx::isValid(liveryTexture) || !bgfx::isValid(whiteTexture)) {
    diagnostics.event("dependency",{{"component","livery_renderer"},{"success",false},{"stage","gpu_create"}});
    throw std::runtime_error("Livery renderer unavailable");
  }
  diagnostics.event("dependency",{{"component","livery_renderer"},{"success",true},{"source","embedded_visual_shader_linear_scene"}});
  Mesh world;
  box(world, 0, -.3, 0, 1800, .5, 1800, 0xff455144);
  for (int n = -500; n <= 500; n += 100) {
    box(world, float(n), -.04, 0, float(racer::worldScale::roadWidth), .08, 1000, 0xff34312e,1);
    box(world, 0, -.04, float(n), 1000, .08, float(racer::worldScale::roadWidth), 0xff34312e,1);
    for (int d = -490; d <= 490; d += 10) {
      if (std::abs(std::remainder(double(d),racer::worldScale::blockSpacing))<7) continue;
      for (float side:{-1.f,1.f}) {
        box(world,float(n)+side*float(racer::worldScale::laneWidth),.012,float(d),.12,.01,3,0xffeeeeee);
        box(world,float(d),.012,float(n)+side*float(racer::worldScale::laneWidth),3,.01,.12,0xffeeeeee);
        box(world,float(n)+side*.12f,.012,float(d),.10,.01,10,0xff44ddee);
        box(world,float(d),.012,float(n)+side*.12f,10,.01,.10,0xff44ddee);
      }
    }
    for (int side : {-1, 1}) {
      box(world, float(n), .8, float(side * 495), 1, 1.6, 1, 0xff66cfff);
      box(world, float(side * 495), .8, float(n), 1, 1.6, 1, 0xff66cfff);
    }
    if (n != 0 && std::abs(n) < 500) {
      box(world, 8, 1, float(n), .35, 2, .35, 0xffeeeeee);
      box(world, float(n), 1, 8, .35, 2, .35, 0xffeeeeee);
    }
  }
  for (int side : {-1, 1}) {
    box(world, side * 500, .3, 0, .5, .6, 1000, 0xff557bf3);
    box(world, 0, .3, side * 500, 1000, .6, .5, 0xff557bf3);
  }
  if (scene=="scale") {
    // Diagnostic references only; these are authored metric fixtures, not
    // collidable city props or dimensions inferred from reference screenshots.
    const auto w=float(racer::worldScale::parkingBayWidth),l=float(racer::worldScale::parkingBayLength);
    for (float side:{-1.f,1.f}) {
      box(world,side*w/2,.018,0,.04,.01,l,0xffeeeeee);
      box(world,0,.018,side*l/2,w,.01,.04,0xffeeeeee);
    }
    const auto h=float(racer::worldScale::referencePersonHeight);
    for (float side:{-1.f,1.f}) box(world,3+side*.09f,.325,0,.12,.65,.18,0xff40caff);
    box(world,3,h*.46f,0,.36f,h*.72f,.22f,0xff40caff);
    box(world,3,h-.11f,0,.22f,.22f,.22f,0xff40caff);
    for (int m=-6;m<=6;++m) box(world,float(m),.018,-3.5,.025,.01,m%5==0?.5f:.22f,0xffeeeeee);
  }
  if(scene=="scale" || !worldMeshes.empty())sceneryMesh.clear();
  if(scene!="scale" && worldMeshes.empty()) {
    auto city=racer::buildCityScene(texturedPalms,sceneryMesh.empty());world.insert(world.end(),city.begin(),city.end());
    auto street=racer::streetDetails::build();world.insert(world.end(),street.begin(),street.end());
  }
  if(!worldMeshes.empty()) {
    world.clear();
  }
  std::vector<std::unique_ptr<CarGraphics>> importedWorlds;
  racer::StaticTexturePool staticTextures(racer::uploadAssetTexture);
  std::optional<racer::surfaceFollow::SurfaceIndex::Builder> groundBuilder;
  if(followGround)groundBuilder.emplace();
  racer::surfaceFollow::Matrix worldMount;
  racer::worldTransform(worldMount.data(),worldHeading,worldOrigin[0],worldOrigin[2]);
  worldMount[13]=worldOrigin[1];
  float importedMinimumY=0;
  auto loadStaticGraphics=[&](const std::string &path,const char* role) {
    const auto asset=racer::loadMeshAsset(path);
    if(std::string_view(role)=="world_mesh")importedMinimumY=std::min(importedMinimumY,asset.minimum[1]+worldOrigin[1]);
    if(groundBuilder && std::string_view(role)=="world_mesh")groundBuilder->add(asset,worldMount);
    auto candidate=std::make_unique<CarGraphics>();candidate->sections=asset.sections;
    try {candidate->textures=staticTextures.acquire(asset.images);}
    catch(const racer::StaticTexturePool::BudgetError& error) {
      diagnostics.event("static_asset_admission",{{"reason","static_image_budget"},{"maximum",error.maximum},
        {"used",error.used},{"candidate",error.additional},{"role",role}});throw;
    }
    candidate->vertices=bgfx::createVertexBuffer(bgfx::copy(asset.triangles.data(),uint32_t(asset.triangles.size()*sizeof(Vertex))),layout);
    if(!bgfx::isValid(candidate->vertices))throw std::runtime_error("world_mesh_gpu");
    diagnostics.event(role,{{"sha256",asset.sourceSHA256},{"triangles",asset.triangles.size()/3},{"images",asset.images.size()},
      {"static_unique_images",staticTextures.textureCount()},{"static_unique_rgba_bytes",staticTextures.decodedBytes()}});
    return candidate;
  };
  for(const auto &path:worldMeshes)importedWorlds.push_back(loadStaticGraphics(path,"world_mesh"));
  std::optional<racer::surfaceFollow::SurfaceIndex> groundIndex;
  if(groundBuilder){
    groundIndex.emplace(groundBuilder->finish());groundBuilder.reset();
    diagnostics.event("surface_index",{{"triangles",groundIndex->triangleCount()},{"cells",groundIndex->cellCount()},
      {"references",groundIndex->referenceCount()},{"peak_cell_references",groundIndex->peakCellReferences()}});
  }
  if(!sceneryMesh.empty())importedWorlds.push_back(loadStaticGraphics(sceneryMesh,"scenery_mesh"));
  std::unique_ptr<CarGraphics> importedSky;
  if(!skyMesh.empty())importedSky=loadStaticGraphics(skyMesh,"sky_mesh");
  if(!worldMeshes.empty())box(world,0,importedMinimumY-.75f,0,1000,.5f,1000,0xff343a40);
  auto worldBuffer=bgfx::createVertexBuffer(
      bgfx::copy(world.data(),uint32_t(world.size()*sizeof(Vertex))),layout);
  racer::PlayFlow flow(profilePath, &diagnostics);
  racer::WorkflowObservation workflowObservation(&diagnostics);
  std::vector<racer::VehicleDefinition> vehicles;
  size_t activeVehicle=0;
  racer::DocumentStore vehicleStore(profilePath+".vehicle",racer::DocumentComponent::Vehicle,256,&diagnostics);
  if (previewMesh.empty()) {
    racer::VehicleLibraryLoadContext libraryContext;
    try {
      vehicles=racer::readVehicleLibrary(vehicleLibrary,&libraryContext);
    } catch (const racer::MeshAssetError &error) {
      try {
        diagnostics.event("vehicle_library_load",{{"success",false},{"reason",error.what()},
          {"library_sha256",libraryContext.librarySHA256.data()},{"descriptor_index",libraryContext.descriptorIndex},
          {"descriptor_sha256",libraryContext.descriptorSHA256.data()}});
      } catch (...) {} // Preserve the original fixed loader error if telemetry cannot allocate.
      throw;
    }
    try {
      diagnostics.event("vehicle_library_load",{{"success",true},
        {"library_sha256",libraryContext.librarySHA256.data()},{"entries",vehicles.size()}});
    } catch (...) {} // A loaded library must remain usable without diagnostics.
    std::string saved;const auto outcome=vehicleStore.load(saved);
    if (outcome.status==racer::DocumentStatus::Loaded) {
      std::istringstream text(saved);std::string id; text>>id; text>>std::ws;
      if (!text.eof() || id.size()!=72 || !id.starts_with("vehicle-") ||
          !std::all_of(id.begin()+8,id.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');})) {
        vehicleStore.disableWrites();flow.vehicleSaveStatus="Malformed car selection preserved; selection saving disabled.";
      } else {
        bool found=false;
        for (size_t i=0;i<vehicles.size();++i) if (vehicles[i].id==id) {activeVehicle=i;found=true;}
        if (!found) {
          flow.vehicleSaveStatus="Saved car unavailable; original preserved. Choose Car to save a replacement.";
          diagnostics.event("vehicle_selection_unavailable",{{"saved_id",id},{"fallback_id",vehicles[0].id}});
        }
      }
    } else if (outcome.status!=racer::DocumentStatus::Missing)
      flow.vehicleSaveStatus="Car selection could not be read; original preserved, saving disabled.";
    if (!requestedVehicle.empty()) {
      bool found=false;
      for (size_t i=0;i<vehicles.size();++i)
        if (vehicles[i].id==requestedVehicle || vehicles[i].name==requestedVehicle || std::to_string(i)==requestedVehicle) {
          activeVehicle=i;found=true;break;
        }
      if (!found) throw racer::MeshAssetError("vehicle_selection_unavailable");
    }
  }
  std::unique_ptr<CarGraphics> graphics;
  auto loadCar=[&](const racer::VehicleDefinition *definition) {
    const auto path=definition ? definition->mesh : std::filesystem::path(previewMesh);
    const auto operation=diagnostics.operation();
    racer::AssetLoadContext context;
    try {
      diagnostics.event("asset_load_begin",{{"asset",racer::Diagnostics::identity(path.string())},
        {"vehicle",definition ? definition->id : "inspection"}},operation);
    } catch (...) {} // Field construction must not affect loading or recovery.
    const auto failed=[&](const char *reason) noexcept {
      try {
        diagnostics.event("asset_load_end",{{"success",false},{"reason",reason},
          {"load_stage",racer::assetLoadStageName(context.stage)},
          {"actual_sha256",context.actualMeshSHA256.data()},{"expected_sha256",context.expectedMeshSHA256.data()},
          {"descriptor_sha256",context.descriptorSHA256.data()},{"source_sha256",context.sourceSHA256.data()},
          {"input_bytes",context.inputBytes},{"input_identity",racer::assetInputIdentity(context)}},operation);
      } catch (...) {}
    };
    try {
      auto asset=definition ? racer::loadVehicleAsset(*definition,&context) : racer::loadMeshAsset(path,{},&context);
      context.stage=racer::AssetLoadStage::Upload;
      auto candidate=std::make_unique<CarGraphics>();candidate->sections=asset.sections;
      for (const auto &image:asset.images) {
        candidate->textures.push_back(racer::ownedAssetTexture(image,racer::uploadAssetTexture));
      }
      candidate->vertices=bgfx::createVertexBuffer(bgfx::copy(asset.triangles.data(),uint32_t(asset.triangles.size()*sizeof(Vertex))),layout);
      if (!bgfx::isValid(candidate->vertices)) throw racer::MeshAssetError("asset_geometry_gpu_create");
      if (definition) {
        auto projected=asset.triangles;
        const auto &bounds=definition->geometry.body;
        for (auto &vertex:projected) {
          vertex.u=float((vertex.x-bounds.minimum.x)/(bounds.maximum.x-bounds.minimum.x));
          vertex.v=float((vertex.z-bounds.minimum.z)/(bounds.maximum.z-bounds.minimum.z));
          vertex.color=0xffffffff;
        }
        candidate->overlay=bgfx::createVertexBuffer(bgfx::copy(projected.data(),uint32_t(projected.size()*sizeof(Vertex))),layout);
        if (!bgfx::isValid(candidate->overlay)) throw racer::MeshAssetError("asset_overlay_gpu_create");
      }
      if (definition) {
        context.stage=racer::AssetLoadStage::Physics;
        if (!flow.configureVehicle(racer::vehiclePhysicsIdentity(*definition),definition->name,definition->geometry))
          throw racer::MeshAssetError("vehicle_physics_configuration");
      }
      graphics=std::move(candidate);
      context.stage=racer::AssetLoadStage::Complete;
      try {
        diagnostics.event("asset_load_end",{{"success",true},{"sha256",asset.sourceSHA256},{"triangles",asset.triangles.size()/3},
          {"load_stage",racer::assetLoadStageName(context.stage)},
          {"actual_sha256",context.actualMeshSHA256.data()},{"expected_sha256",context.expectedMeshSHA256.data()},
          {"descriptor_sha256",context.descriptorSHA256.data()},{"source_sha256",context.sourceSHA256.data()},
          {"input_bytes",context.inputBytes},{"input_identity",racer::assetInputIdentity(context)},
          {"images_loaded",graphics->textures.size()},{"sections",graphics->sections.size()},{"materials_partial",true},
          {"min_x",asset.minimum[0]},{"min_y",asset.minimum[1]},{"min_z",asset.minimum[2]},
          {"max_x",asset.maximum[0]},{"max_y",asset.maximum[1]},{"max_z",asset.maximum[2]},
          {"physics_id",flow.vehicleId},{"wheelbase",flow.sim.wheelbase()}},operation);
        diagnostics.event("asset_motion_roles",{{"rolling_sections",std::count_if(asset.sections.begin(),asset.sections.end(),[](const auto &s){return s.wheel>=0 && s.rolling;})},
          {"carrier_sections",std::count_if(asset.sections.begin(),asset.sections.end(),[](const auto &s){return s.wheel>=0 && !s.rolling;})}},operation);
        if (definition) for (size_t i=0;i<4;++i) {
          const auto &wheel=definition->geometry.wheels[i];
          diagnostics.event("wheel_geometry",{{"wheel",i},{"x",wheel.center.x},{"y",wheel.center.y},{"z",wheel.center.z},
            {"radius",wheel.radius},{"width",wheel.width},{"physics_id",flow.vehicleId}},operation);
        }
      } catch (...) {} // Optional telemetry cannot turn a committed load into failure.
    } catch (const racer::MeshAssetError &error) {
      failed(error.what());throw; // MeshAssetError contains fixed internal reason codes only.
    } catch (...) {
      failed("upload_or_allocation");throw;
    }
  };
  loadCar(vehicles.empty() ? nullptr : &vehicles[activeVehicle]);
  // Static curbside traffic from other catalog vehicles. Visual only: like the city
  // props, parked cars have no collision. Authored layout, not recovered placement.
  struct ParkedCar{size_t vehicle;double x,z,heading;std::unique_ptr<CarGraphics> graphics;};
  std::vector<ParkedCar> parkedCars;
  // Tyre marks on the flat road. SLRR's engine has a skidmark system (REA names skid_PS, skid_SM,
  // WheelSkidmark_Context, skidmark_max); the simulation here has no slip, so marks use an authored
  // rule: hard braking or high lateral acceleration at speed. Visual only.
  struct SkidQuad{float x0,z0,x1,z1,x2,z2,x3,z3,alpha;};
  std::vector<SkidQuad> skidQuads;
  struct SkidTrack{bool valid=false;double x=0,z=0;};
  SkidTrack skidTracks[2];
  // Tyre smoke: soft camera-facing puffs emitted at the rear wheels while marking. Authored; the
  // references (Juiced 2, MCLA, MC3, SLRR) all show smoke but no formula was recovered.
  struct Puff{float x,y,z,vx,vy,vz,age,life,size,seed;};
  std::vector<Puff> puffs;
  double puffCarry[2]={0,0};
  uint32_t puffCounter=0;
  bgfx::TextureHandle puffTexture=BGFX_INVALID_HANDLE;
  {
    constexpr int n=64;std::vector<uint8_t> pixels(n*n*4);
    for(int y=0;y<n;++y)for(int x=0;x<n;++x){
      const float dx=(float(x)+.5f)/n*2-1,dy=(float(y)+.5f)/n*2-1,r=std::sqrt(dx*dx+dy*dy);
      float h=std::sin(float(x)*.91f+float(y)*.37f)*std::sin(float(y)*.83f-float(x)*.29f);
      const float a=std::clamp(1-r,0.f,1.f);const float soft=a*a*(3-2*a)*(.8f+.2f*h);
      const uint8_t v=uint8_t(std::clamp(soft,0.f,1.f)*255);
      pixels[size_t(y*n+x)*4+0]=255;pixels[size_t(y*n+x)*4+1]=255;pixels[size_t(y*n+x)*4+2]=255;pixels[size_t(y*n+x)*4+3]=v;
    }
    puffTexture=bgfx::createTexture2D(n,n,false,1,bgfx::TextureFormat::RGBA8,BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP,
      bgfx::copy(pixels.data(),uint32_t(pixels.size())));
  }
  if(vehicles.size()>1 && previewMesh.empty() && worldMeshes.empty() && scene!="scale") {
    constexpr double pi=3.14159265358979323846;
    const double slots[][3]={{4.7,18,0},{-4.7,31,pi},{4.7,52,0},{-4.7,76,pi},{4.7,110,0},{-4.7,150,pi}};
    size_t pick=0;
    for(const auto& slot:slots) {
      if(pick>=std::min<size_t>(vehicles.size()-1,6))break;
      const size_t index=(activeVehicle+1+pick++)%vehicles.size();
      try {
        racer::AssetLoadContext parkedContext;
        auto asset=racer::loadVehicleAsset(vehicles[index],&parkedContext);
        auto candidate=std::make_unique<CarGraphics>();candidate->sections=asset.sections;
        for(const auto& image:asset.images)candidate->textures.push_back(racer::ownedAssetTexture(image,racer::uploadAssetTexture));
        candidate->vertices=bgfx::createVertexBuffer(bgfx::copy(asset.triangles.data(),uint32_t(asset.triangles.size()*sizeof(Vertex))),layout);
        if(!bgfx::isValid(candidate->vertices))throw racer::MeshAssetError("parked_geometry_gpu_create");
        parkedCars.push_back({index,slot[0],slot[1],slot[2],std::move(candidate)});
      } catch(...) {
        try{diagnostics.event("parked_car_skipped",{{"vehicle",vehicles[index].id}});}catch(...){}
      }
    }
    try{diagnostics.event("parked_cars",{{"count",parkedCars.size()}});}catch(...){}
  }
  std::optional<racer::LiveryState> renderedLivery;
  auto &sim = flow.sim;
  if (scene == "garage")
    flow.garage();
  else if (scene == "course")
    flow.startTest(racer::TestKind::Handling);
  else if (!scene.empty() && scene!="scale") {
    std::cerr << "Unknown scene\n";
    return 1;
  }
  Mesh gateMesh;
  box(gateMesh, -9, 2, 0, .5, 4, .5, 0xff55eaff);
  box(gateMesh, 9, 2, 0, .5, 4, .5, 0xff55eaff);
  box(gateMesh, 0, 4, 0, 18.5, .4, .4, 0xff55eaff);
  // Ground arrow points along the gate's required crossing direction.
  box(gateMesh, 0, .1, 3, .6, .1, 4, 0xff55eaff);
  for (int i = 0; i < 4; ++i)
    box(gateMesh, 0, .1, 5 + i * .4f, 3 - i * .7f, .1, .4f, 0xff55eaff);
  auto gateBuffer = bgfx::createVertexBuffer(
      bgfx::copy(gateMesh.data(), uint32_t(gateMesh.size() * sizeof(Vertex))),
      layout);
  Mesh eventMarker;
  // Low roadside beacons preserve event discoverability without obscuring cars.
  box(eventMarker,-5.5,.5,0,.16,1,.16,0xff90e050);
  box(eventMarker,5.5,.5,0,.16,1,.16,0xff90e050);
  for(float side:{-1.f,1.f}) box(eventMarker,side*4.4f,.024f,0,1.8f,.015f,.14f,0xff90e050);
  auto eventBuffer=bgfx::createVertexBuffer(bgfx::copy(eventMarker.data(),uint32_t(eventMarker.size()*sizeof(Vertex))),layout);
  if(followGround && vehicles.empty())throw std::runtime_error("surface_follow_requires_vehicle");
  double groundReference=0;
  unsigned poseRevision = flow.poseRevision;
  racer::Car previous = sim.car;
  SDL_Gamepad *pad = nullptr;
  bool padActive = false, running = true;
  auto &paused = flow.paused;
  auto &rearming = flow.rearming;
  auto &focus = flow.focus;
  auto openPad = [&]() {
    if (pad)
      return;
    int count = 0;
    auto ids = SDL_GetGamepads(&count);
    if (count) {
      pad = SDL_OpenGamepad(ids[0]);
      diagnostics.event("device_open", {{"available", count}, {"success", pad != nullptr}});
    }
    SDL_free(ids);
  };
  openPad();
  std::cout << "Gamepad at launch: " << (pad ? SDL_GetGamepadName(pad) : "none")
            << '\n';
  diagnostics.event("device", {{"connected", pad != nullptr}});
  auto cameraDistance=[&] {return inspectionDistance>0?inspectionDistance:scene=="scale" ? 8. : vehicles.empty() ? 11. : std::clamp(
      (vehicles[activeVehicle].geometry.body.maximum.z-vehicles[activeVehicle].geometry.body.minimum.z)*1.15,4.8,11.)+std::min(1.5,std::abs(sim.car.speed)*.03);};
  auto cameraHeight=[&] {return scene=="scale" ? 4. : vehicles.empty() ? 3.8 : std::max(1.7,vehicles[activeVehicle].geometry.body.maximum.y+.55);};
  auto lookHeight=[&] {return scene=="scale" ? .9 : vehicles.empty() ? .8 : vehicles[activeVehicle].geometry.body.maximum.y*.6;};
  double cameraX = 0, cameraZ = -cameraDistance(), cameraY = cameraHeight();
  auto last = std::chrono::steady_clock::now(), start = last;
  double accumulator = 0, elapsed = 0, measured = 0;
  uint64_t frames = 0;
  double longestFrame = 0;
  uint64_t overBudgetFrames = 0;
  bool captured = false;
  std::set<racer::Screen> capturedScreens;
  if (!captureLoop.empty())
    std::filesystem::create_directories(captureLoop);
  auto pause = [&]() { flow.suspend(); };
  GarageLiveChecks garageChecks(garageMode == "gamepad", &diagnostics);
  LiveChecks liveChecks(&diagnostics);
  ReviewScript review(reviewPath);
  bool timedOut = false;
  uint64_t frameId = 0;
  double nextSample = 0, nextTiming = 0, maxInterval = 0, clampedSeconds = 0;
  size_t timingFrames = 0, timingSlow = 0, diagnosticShots = 0;
  bool orientationReported = false, manualShot = false;
  const char *captureCause = "user_marker";
  auto requestCapture = [&](const std::string &path, const char *cause = "explicit_request") {
    try {
      diagnostics.event("capture_request", {{"capture", racer::Diagnostics::identity(path)}, {"frame", frameId}, {"cause", cause}}, flow.attempt);
    } catch (...) {
      // Optional diagnostic field allocation must not prevent the capture.
    }
    bgfx::requestScreenShot(BGFX_INVALID_HANDLE, path.c_str());
  };
  while (running) {
    ++frameId;
    auto now = std::chrono::steady_clock::now();
    double rawdt = std::chrono::duration<double>(now - last).count();
    last = now;
    double dt = std::min(rawdt, .1);
    elapsed = std::chrono::duration<double>(now - start).count();
    if (verify)
      liveChecks.update(elapsed, sim.car, paused);
    if (!garageMode.empty())
      garageChecks.update(elapsed, flow, pad);
    try {
      review.update(elapsed, flow);
      if(review.windowSize) {
        const auto size=*review.windowSize;review.windowSize.reset();
        if(!SDL_SetWindowSize(window,size[0],size[1]))throw std::runtime_error("review_window_resize_failed");
      }
    } catch (const ReviewScript::InvalidKey &) {
      try {
        diagnostics.event("review_script_error", {{"reason", "unknown_key"},
                           {"command_index", review.cursor}}, flow.attempt);
      } catch (...) {
        // Preserve the original script failure if optional telemetry fails.
      }
      throw;
    }
    SDL_Event e;
    while (SDL_PollEvent(&e)) {
      if (e.type == SDL_EVENT_WINDOW_FOCUS_LOST || e.type == SDL_EVENT_WINDOW_FOCUS_GAINED ||
          e.type == SDL_EVENT_GAMEPAD_ADDED || e.type == SDL_EVENT_GAMEPAD_REMOVED || e.type == SDL_EVENT_QUIT)
        diagnostics.event("sdl_event", {{"type", e.type}, {"frame", frameId}}, flow.attempt);
      if (e.type == SDL_EVENT_QUIT)
        running = false;
      if (e.type == SDL_EVENT_WINDOW_FOCUS_LOST) {
        focus = false;
        pause();
      }
      if (e.type == SDL_EVENT_WINDOW_FOCUS_GAINED)
        focus = true;
      if (e.type == SDL_EVENT_GAMEPAD_ADDED)
        openPad();
      if (e.type == SDL_EVENT_GAMEPAD_REMOVED && pad &&
          e.gdevice.which == SDL_GetGamepadID(pad)) {
        SDL_CloseGamepad(pad);
        pad = nullptr;
        if (padActive)
          pause();
        padActive = false;
        openPad();
      }
      if (e.type == SDL_EVENT_KEY_DOWN && !e.key.repeat) {
        using racer::Action;
        switch (e.key.key) {
        case SDLK_F8:
          manualShot = true; captureCause = "user_marker";
          diagnostics.event("user_marker", {{"frame", frameId}}, flow.attempt);
          break;
        case SDLK_ESCAPE:
          flow.action(Action::Back);
          break;
        case SDLK_UP:
          flow.action(Action::Up);
          break;
        case SDLK_DOWN:
          flow.action(Action::Down);
          break;
        case SDLK_LEFT:
          flow.action(Action::Left);
          break;
        case SDLK_RIGHT:
          flow.action(Action::Right);
          break;
        case SDLK_RETURN:
          flow.action(Action::Accept);
          break;
        case SDLK_R:
          flow.action(Action::Reset);
          break;
        case SDLK_M:
          flow.action(Action::Map);
          break;
        default:
          break;
        }
      }
      if (e.type == SDL_EVENT_GAMEPAD_BUTTON_DOWN && pad &&
          e.gbutton.which == SDL_GetGamepadID(pad)) {
        padActive = true;
        using racer::Action;
        switch (e.gbutton.button) {
        case SDL_GAMEPAD_BUTTON_START:
          flow.action(Action::Pause);
          break;
        case SDL_GAMEPAD_BUTTON_EAST:
          flow.action(Action::Back);
          break;
        case SDL_GAMEPAD_BUTTON_DPAD_UP:
          flow.action(Action::Up);
          break;
        case SDL_GAMEPAD_BUTTON_DPAD_DOWN:
          flow.action(Action::Down);
          break;
        case SDL_GAMEPAD_BUTTON_DPAD_LEFT:
          flow.action(Action::Left);
          break;
        case SDL_GAMEPAD_BUTTON_DPAD_RIGHT:
          flow.action(Action::Right);
          break;
        case SDL_GAMEPAD_BUTTON_SOUTH:
          flow.action(Action::Accept);
          break;
        case SDL_GAMEPAD_BUTTON_NORTH:
          flow.action(Action::Reset);
          break;
        default:
          break;
        }
      }
    }
    if (flow.quit)
      running = false;
    if (!vehicles.empty() && flow.vehicleSaveRetryRequest) {
      flow.vehicleSaveRetryRequest=false;
      vehicleStore.context(flow.attempt);
      const auto saved=vehicleStore.save(vehicles[activeVehicle].id+"\n");
      flow.vehicleSaveStatus=saved ? "Car selection saved." : "UNSAVED car selection; active for this run.";
    }
    if (!vehicles.empty() && flow.screen==racer::Screen::Garage && std::abs(flow.vehicleCycleRequest)==1) {
      const auto next=(activeVehicle+vehicles.size()+flow.vehicleCycleRequest)%vehicles.size();
      flow.vehicleCycleRequest=0;
      try {
        loadCar(&vehicles[next]);activeVehicle=next;
        vehicleStore.context(flow.attempt);
        const auto saved=vehicleStore.save(vehicles[next].id+"\n");
        flow.vehicleSaveStatus=saved ? "Car selection saved." : "UNSAVED car selection; active for this run.";
      } catch (const racer::MeshAssetError &) {
        flow.vehicleSaveStatus="Car could not load; previous car retained.";
      }
    }
    if (poseRevision != flow.poseRevision) {
      poseRevision = flow.poseRevision;
      groundReference=0;
      previous = sim.car;
      cameraX = sim.car.x - std::sin(sim.car.heading) * cameraDistance();
      cameraZ = sim.car.z - std::cos(sim.car.heading) * cameraDistance();
      cameraY = cameraHeight();
      accumulator = 0;
    }
    auto keys = SDL_GetKeyboardState(nullptr);
    racer::Input input{
        double(keys[SDL_SCANCODE_W] || keys[SDL_SCANCODE_UP]),
        double(keys[SDL_SCANCODE_S] || keys[SDL_SCANCODE_DOWN]),
        double(keys[SDL_SCANCODE_D] || keys[SDL_SCANCODE_RIGHT]) -
            double(keys[SDL_SCANCODE_A] || keys[SDL_SCANCODE_LEFT])};
    if (input.throttle || input.brake || input.steer)
      padActive = false;
    if (pad) {
      auto p = racer::gamepadInput(pad);
      if (p.throttle > .05 || p.brake > .05 || p.steer != 0) {
        input = p;
        padActive = true;
      }
    }
    const auto requestedInput = input;
    if (autoDrive && !paused && !flow.session.active())
      input = elapsed<.75 ? racer::Input{} : racer::Input{elapsed < 10 ? 1.0 : 0, elapsed >= 10 ? 1.0 : 0,
               elapsed > 4 && elapsed < 8 ? autoTurn : 0};
    if (review.vehicleInput && !paused && !flow.session.active()) input=*review.vehicleInput;
    if ((courseDriver || review.driveCourse) && !rearming && !paused &&
        flow.session.active() &&
        flow.session.result().kind == racer::TestKind::Handling) {
      const auto &g = racer::handlingCourse().gates[flow.session.nextGate()];
      const double error = std::remainder(
          std::atan2(g.x + g.nx * 8 - sim.car.x, g.z + g.nz * 8 - sim.car.z) -
              sim.car.heading,
          2 * 3.141592653589793);
      input = {sim.car.speed < 7 ? 1. : 0., sim.car.speed > 8 ? 1. : 0.,
               std::clamp(error * 2., -1., 1.)};
    }
    const auto selectedInput = input;
    const char *inputSource = (courseDriver || review.driveCourse) ? "synthetic_course" : review.vehicleInput ? "synthetic_vehicle" : autoDrive ? "autodrive" : padActive ? "gamepad" : "keyboard";
    if (rearming) {
      if (input.throttle < .05 && input.brake < .05 &&
          std::abs(input.steer) < .05 && !keys[SDL_SCANCODE_RETURN] &&
          !keys[SDL_SCANCODE_ESCAPE] &&
          (!pad || (!SDL_GetGamepadButton(pad, SDL_GAMEPAD_BUTTON_SOUTH) &&
                    !SDL_GetGamepadButton(pad, SDL_GAMEPAD_BUTTON_EAST) &&
                    !SDL_GetGamepadButton(pad, SDL_GAMEPAD_BUTTON_START) &&
                    !SDL_GetGamepadButton(pad, SDL_GAMEPAD_BUTTON_NORTH)))) {
        rearming = false;
        sim.tick({}, 0);
      }
      input = {};
    }
    if (!paused) {
      accumulator += dt;
      while (accumulator >= racer::step) {
        previous = sim.car;
        flow.tick(input);
        accumulator -= racer::step;
        if (paused) {
          accumulator = 0;
          previous = sim.car;
          break;
        }
      }
    } else {
      accumulator = 0;
      previous = sim.car;
    }
    const double alpha = accumulator / racer::step;
    auto shown = sim.car;
    shown.x = previous.x + (shown.x - previous.x) * alpha;
    shown.z = previous.z + (shown.z - previous.z) * alpha;
    shown.heading =
        previous.heading + (shown.heading - previous.heading) * alpha;
    shown.steering=previous.steering+(shown.steering-previous.steering)*alpha;
    shown.travel=previous.travel+(shown.travel-previous.travel)*alpha;
    if(skidMarks && !vehicles.empty() && !paused) {
      const auto& geometry=vehicles[activeVehicle].geometry;
      size_t rear[2]={0,1};
      for(size_t i=0;i<4;++i) { // two wheels with the lowest z are the rear pair (nose is +Z)
        if(geometry.wheels[i].center.z<geometry.wheels[rear[0]].center.z){rear[1]=rear[0];rear[0]=i;}
        else if(i!=rear[0] && geometry.wheels[i].center.z<geometry.wheels[rear[1]].center.z)rear[1]=i;
      }
      const double speedNow=std::abs(shown.speed);
      const double lateral=speedNow*speedNow*std::abs(std::tan(shown.steering))/std::max(.5,sim.wheelbase());
      const bool marking=speedNow>7 && (selectedInput.brake>.7 || lateral>9);
      // Launch smoke: hard throttle from near standstill (wheelspin is not simulated; authored trigger).
      const bool launching=!marking && selectedInput.throttle>.85 && speedNow<8;
      const double c=std::cos(shown.heading),sn=std::sin(shown.heading);
      for(int k=0;k<2;++k) {
        const auto& wheel=geometry.wheels[rear[size_t(k)]];
        const double wx=shown.x+c*wheel.center.x+sn*wheel.center.z,wz=shown.z-sn*wheel.center.x+c*wheel.center.z;
        auto& track=skidTracks[k];
        if(marking && track.valid) {
          const double dx=wx-track.x,dz=wz-track.z,len=std::hypot(dx,dz);
          if(len>.05 && len<1.5) {
            const float hw=float(wheel.width*.45),px=float(-dz/len)*hw,pz=float(dx/len)*hw;
            skidQuads.push_back({float(track.x)-px,float(track.z)-pz,float(track.x)+px,float(track.z)+pz,
              float(wx)+px,float(wz)+pz,float(wx)-px,float(wz)-pz,.55f});
          }
          if(len>.05){track.x=wx;track.z=wz;}
        } else {track.valid=marking;track.x=wx;track.z=wz;}
        if(marking)track.valid=true;
        if((marking||launching) && tyreSmoke && puffs.size()<900) {
          puffCarry[k]+=dt*(launching?26.0:110.0);
          while(puffCarry[k]>=1.0) {
            puffCarry[k]-=1.0;++puffCounter;
            auto rnd=[&](unsigned salt){uint32_t h=(puffCounter*2654435761u)^(salt*40503u);h^=h>>13;h*=1274126177u;h^=h>>16;return float(h&0xffff)/65535.f-.5f;};
            const float back=-float(std::copysign(1.0,shown.speed));
            puffs.push_back({float(wx),.15f,float(wz),
              float(sn)*back*.6f+rnd(1)*.9f,.5f+rnd(2)*.4f,float(c)*back*.6f+rnd(3)*.9f,0,1.6f+rnd(4)*.6f,(launching?.45f:.75f)+rnd(5)*.2f,rnd(6)+(launching?2.f:0.f)});
          }
        }
      }
      for(auto& puff:puffs){puff.age+=float(dt);puff.x+=puff.vx*float(dt);puff.y+=puff.vy*float(dt);puff.z+=puff.vz*float(dt);
        puff.vx*=1-float(dt)*.9f;puff.vz*=1-float(dt)*.9f;puff.vy*=1-float(dt)*.6f;}
      puffs.erase(std::remove_if(puffs.begin(),puffs.end(),[](const Puff& p){return p.age>=p.life;}),puffs.end());
      if(skidQuads.size()>1400)skidQuads.erase(skidQuads.begin(),skidQuads.begin()+400);
    }
    std::optional<racer::surfaceFollow::GroundFrame> groundFrame;
    if(groundIndex){
      groundFrame=racer::surfaceFollow::fit(*groundIndex,vehicles[activeVehicle].geometry,
        shown.heading,shown.x,shown.z,groundReference);
      if(!groundFrame){
        diagnostics.event("surface_follow_uncovered",{{"frame",frameId},{"x",shown.x},{"z",shown.z},{"reference_y",groundReference}});
        throw std::runtime_error("surface_follow_uncovered");
      }
      groundReference=groundFrame->groundElevation;
    }
    const double bodyElevation=groundFrame?groundFrame->elevation:0;
    auto bodyMatrix=[&](float* output){
      if(groundFrame)std::copy(groundFrame->body.begin(),groundFrame->body.end(),output);
      else racer::worldTransform(output,shown.heading,shown.x,shown.z);
    };
    auto wheelMatrix=[&](float* output,size_t index,bool rolling=true,double extraSpin=0){
      const auto& g=vehicles[activeVehicle].geometry;
      const auto spin=racer::wheelSpinAfterTravel(0,shown.travel,g.wheels[index].radius)+extraSpin;
      if(groundFrame)racer::surfaceFollow::wheelMatrix(output,*groundFrame,g,index,shown.steering,spin,rolling);
      else racer::wheelRenderTransform(output,g,index,shown.heading,shown.x,shown.z,shown.steering,spin,rolling);
    };
    double targetX = shown.x - std::sin(shown.heading) * cameraDistance(),
           targetZ = shown.z - std::cos(shown.heading) * cameraDistance();
    if (cameraView!="rear") {
      constexpr double pi=3.14159265358979323846;
      const double angle=shown.heading+(cameraView=="front" ? 0 : cameraView=="left" ? -pi/2 : cameraView=="right" ? pi/2 : pi*.7);
      targetX=shown.x+std::sin(angle)*cameraDistance();
      targetZ=shown.z+std::cos(angle)*cameraDistance();
    }
    cameraY=bodyElevation+(cameraView=="elevated" ? cameraDistance()*1.3 : cameraHeight());
    double blend = 1 - std::exp(-8 * dt);
    cameraX += (targetX - cameraX) * blend;
    cameraZ += (targetZ - cameraZ) * blend;
    int w, h;
    SDL_GetWindowSizeInPixels(window, &w, &h);
    if (!benchmark && w > 0 && h > 0 && (w != width || h != height)) {
      width = w;
      height = h;
      bgfx::SwapChain swap;
      swap.width = w;
      swap.height = h;
      bgfx::reset(BGFX_RESET_VSYNC | BGFX_RESET_MSAA_X4, &swap);
      diagnostics.event("resize", {{"width", width}, {"height", height}, {"frame", frameId}});
      std::cout << "Drawable resized: " << width << 'x' << height << '\n';
    }
    float view[16], projection[16], model[16],lightView[16],lightProjection[16],lightMatrix[16];
    const bx::Vec3 lightTarget{float(shown.x),float(bodyElevation),float(shown.z)};
    bx::mtxLookAt(lightView,{lightTarget.x-110,lightTarget.y+68,lightTarget.z+140},lightTarget);
    bx::mtxOrtho(lightProjection,-65,65,-65,65,1,400,0,bgfx::getCaps()->homogeneousDepth);
    bx::mtxMul(lightMatrix,lightView,lightProjection);
    auto drawImportedWorld=[&](uint16_t target,bool shadow,const float* eye,bool reflections) {
      // The prepared residential scenery spans +-182 m. Repeat it at 400 m multiples of the
      // 100 m street grid in the main view only, so the horizon is not a bare plain. Authored
      // repetition, not source placement; shadows and reflection probes use the original tile.
      std::vector<std::array<float,2>> tiles{{0.f,0.f}};
      if(target==1 && !shadow && worldMeshes.empty() && !sceneryMesh.empty())
        for(float dx:{-400.f,0.f,400.f})for(float dz:{-400.f,0.f,400.f})if(dx!=0||dz!=0)tiles.push_back({dx,dz});
      for(bool transparent:{false,true}) for(const auto &importedWorld:importedWorlds) for(const auto &tile:tiles)
        for(const auto &section:importedWorld->sections) {
        if(section.blend!=transparent || (shadow&&transparent))continue;
        racer::worldTransform(model,worldHeading,worldOrigin[0],worldOrigin[2]);
        model[12]+=tile[0];model[14]+=tile[1];
        model[13]=worldOrigin[1];bgfx::setTransform(model);
        bgfx::setVertexBuffer(0,importedWorld->vertices,section.first,section.count);
        const float camera[4]={eye[0],eye[1],eye[2],section.mask?section.alphaCutoff:0};
        const float material[4]={section.roughness,section.metallic,section.image>=0?1.f:0.f,-1};
        const float coat[4]={section.clearcoat,section.coatRoughness,section.detailMode(),section.normalScale},reflection[4]={reflections?1.f:0.f,0,0,0};
        bgfx::setUniform(cameraUniform,camera);bgfx::setUniform(materialUniform,material);
        bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,coat);bgfx::setUniform(reflectionUniform,reflection);
        bgfx::setUniform(shadowUniform,lightMatrix);
        const uint32_t flags=(section.wrapU==33071?BGFX_SAMPLER_U_CLAMP:section.wrapU==33648?BGFX_SAMPLER_U_MIRROR:0)|
          (section.wrapV==33071?BGFX_SAMPLER_V_CLAMP:section.wrapV==33648?BGFX_SAMPLER_V_MIRROR:0);
        bgfx::setTexture(0,liverySampler,section.image>=0?importedWorld->textures.at(size_t(section.image))->handle:whiteTexture,flags);
        bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
        bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
        bindNormal(importedWorld.get(),&section);
        bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_LESS|
          (shadow?0:BGFX_STATE_MSAA)|(transparent?BGFX_STATE_BLEND_ALPHA:BGFX_STATE_WRITE_Z));
        bgfx::submit(target,shadow?shadowProgram:visualProgram);
      }
    };
    // Snap the orthographic projection to shadow texels to reduce crawling
    // edges as the chase camera and car travel through the district.
    lightProjection[12]+=(std::round(lightMatrix[12]*1024)-lightMatrix[12]*1024)/1024;
    lightProjection[13]+=(std::round(lightMatrix[13]*1024)-lightMatrix[13]*1024)/1024;
    bx::mtxMul(lightMatrix,lightView,lightProjection);
    bgfx::setViewFrameBuffer(0,shadowFramebuffer);
    bgfx::setViewRect(0,0,0,2048,2048);
    bgfx::setViewClear(0,BGFX_CLEAR_COLOR|BGFX_CLEAR_DEPTH,0xffffffff,1,0);
    bgfx::setViewTransform(0,lightView,lightProjection);
    bx::mtxIdentity(model);bgfx::setTransform(model);
    bgfx::setVertexBuffer(0,worldBuffer);
    const float shadowEye[4]={0,0,0,0},shadowMaterial[4]={1,0,sourceSurfaces?2.f:0.f,1};
    bgfx::setUniform(cameraUniform,shadowEye);bgfx::setUniform(materialUniform,shadowMaterial);
    bgfx::setTexture(0,liverySampler,whiteTexture);
    bgfx::setTexture(2,surfaceSampler,surfaceTexture);
    bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_Z|BGFX_STATE_DEPTH_TEST_LESS);
    bgfx::submit(0,shadowProgram);
    drawImportedWorld(0,true,shadowEye,false);
    for(const auto &section:graphics->sections) {
      if(section.blend) continue;
      if(section.wheel>=0 && !vehicles.empty()) {
        const auto index=size_t(section.wheel);
        wheelMatrix(model,index,section.rolling);
      } else bodyMatrix(model);
      bgfx::setTransform(model);bgfx::setVertexBuffer(0,graphics->vertices,section.first,section.count);
      const float cut[4]={0,0,0,section.mask?section.alphaCutoff:0},mat[4]={1,0,section.image>=0?1.f:0.f,0};
      bgfx::setUniform(cameraUniform,cut);bgfx::setUniform(materialUniform,mat);
      uint32_t flags=(section.wrapU==33071?BGFX_SAMPLER_U_CLAMP:section.wrapU==33648?BGFX_SAMPLER_U_MIRROR:0)|
        (section.wrapV==33071?BGFX_SAMPLER_V_CLAMP:section.wrapV==33648?BGFX_SAMPLER_V_MIRROR:0);
      bgfx::setTexture(0,liverySampler,section.image>=0?graphics->textures.at(size_t(section.image))->handle:whiteTexture,flags);
      bgfx::setTexture(2,surfaceSampler,surfaceTexture);
      bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_Z|BGFX_STATE_DEPTH_TEST_LESS);
      bgfx::submit(0,shadowProgram);
    }
    for(const auto& parked:parkedCars) for(const auto &section:parked.graphics->sections) {
      if(section.blend) continue;
      if(section.wheel>=0)
        racer::wheelRenderTransform(model,vehicles[parked.vehicle].geometry,size_t(section.wheel),parked.heading,parked.x,parked.z,0,0,section.rolling);
      else racer::worldTransform(model,parked.heading,parked.x,parked.z);
      bgfx::setTransform(model);bgfx::setVertexBuffer(0,parked.graphics->vertices,section.first,section.count);
      const float cut[4]={0,0,0,section.mask?section.alphaCutoff:0},mat[4]={1,0,section.image>=0?1.f:0.f,0};
      bgfx::setUniform(cameraUniform,cut);bgfx::setUniform(materialUniform,mat);
      uint32_t flags=(section.wrapU==33071?BGFX_SAMPLER_U_CLAMP:section.wrapU==33648?BGFX_SAMPLER_U_MIRROR:0)|
        (section.wrapV==33071?BGFX_SAMPLER_V_CLAMP:section.wrapV==33648?BGFX_SAMPLER_V_MIRROR:0);
      bgfx::setTexture(0,liverySampler,section.image>=0?parked.graphics->textures.at(size_t(section.image))->handle:whiteTexture,flags);
      bgfx::setTexture(2,surfaceSampler,surfaceTexture);
      bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_Z|BGFX_STATE_DEPTH_TEST_LESS);
      bgfx::submit(0,shadowProgram);
    }
    const float lookAhead=scene=="scale"?0.f:cameraView=="rear"||inspectionDistance>0?2.f:0.f;
    bx::mtxLookAt(view, {float(cameraX), float(cameraY), float(cameraZ)},
                  {float(shown.x + std::sin(shown.heading)*lookAhead), float(bodyElevation+lookHeight()),
                   float(shown.z + std::cos(shown.heading)*lookAhead)});
    // Chase-camera field of view widens with speed (up to +12 degrees by ~48 m/s), smoothed so it
    // never jumps; inspection and scale cameras keep their fixed lens.
    static float fovKick=0;
    const float fovTarget=(speedFov && inspectionDistance<=0 && scene!="scale")?
      std::clamp((float(std::abs(shown.speed))-8.f)/40.f,0.f,1.f)*12.f:0.f;
    fovKick+=(fovTarget-fovKick)*float(1-std::exp(-3*dt));
    bx::mtxProj(projection, (inspectionDistance>0 || scene=="scale" ? 65 : 55)+fovKick, float(width) / height, .1f, 1600,
                bgfx::getCaps()->homogeneousDepth);
    // Car pose and time of day for the lamp/headlight terms of the surface shader (sticky uniform).
    headlightState[0]=float(shown.x);headlightState[1]=float(shown.z);headlightState[2]=float(shown.heading);
    postProcess.ensure(uint16_t(width),uint16_t(height));
    bgfx::setViewFrameBuffer(1,postProcess.sceneFrame());
    bgfx::setViewRect(1, 0, 0, postProcess.sceneWidth(), postProcess.sceneHeight());
    bgfx::setViewClear(1, BGFX_CLEAR_COLOR | BGFX_CLEAR_DEPTH, 0x000000ffu, 1,
                       0);
    bgfx::setViewTransform(1, view, projection);
    bgfx::touch(1);
    const float eyeUniform[4]={float(cameraX),float(cameraY),float(cameraZ),0};
    const float reflectionState[4]={sceneReflection.ready()?1.f:0.f,0,paintHue,paintStrength};
    const float noCoat[4]={0,.1f,0,0};
    const float skyMaterial[4]={1,0,0,2},worldMaterial[4]={.95f,0,sourceSurfaces?2.f:0.f,1};
    // Scene attachments are linear HDR. Unlit source colors and livery still
    // originate in display RGB and require the explicit shader conversion modes.
    auto bindUnlit=[&](float mode,bgfx::TextureHandle texture) {
      const float material[4]={1,0,1,mode};
      bgfx::setUniform(cameraUniform,eyeUniform);bgfx::setUniform(materialUniform,material);
      bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setUniform(reflectionUniform,reflectionState);
      bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,noCoat);
      bgfx::setTexture(0,liverySampler,texture,BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP);
      bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
      bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());bindNormal();
    };
    auto drawSourceSky=[&](uint16_t target,const float* eye) {
      if(!importedSky)return;
      bx::mtxScale(model,.15f,.15f,.15f);
      model[12]=eye[0];model[13]=eye[1];model[14]=eye[2];
      for(const auto &section:importedSky->sections) {
        bgfx::setTransform(model);bgfx::setVertexBuffer(0,importedSky->vertices,section.first,section.count);
        const float material[4]={1,0,1,4};
        bgfx::setUniform(cameraUniform,eye);bgfx::setUniform(materialUniform,material);
        bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setUniform(reflectionUniform,reflectionState);
        bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,noCoat);
        bgfx::setTexture(0,liverySampler,section.image>=0?importedSky->textures.at(size_t(section.image))->handle:whiteTexture,
          BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP);
        bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
        bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
        bindNormal();
        bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_MSAA);
        bgfx::submit(target,visualProgram);
      }
    };
    bx::mtxTranslate(model,float(cameraX),float(cameraY),float(cameraZ));
    bgfx::setTransform(model);bgfx::setVertexBuffer(0,skyBuffer);
    bgfx::setUniform(cameraUniform,eyeUniform);bgfx::setUniform(materialUniform,skyMaterial);
    bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
    bgfx::setUniform(reflectionUniform,reflectionState);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
    bindNormal();
    bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,noCoat);
    bgfx::setTexture(0,liverySampler,whiteTexture);
    bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_MSAA);
    bgfx::submit(1,visualProgram);
    drawSourceSky(1,eyeUniform);
    bx::mtxIdentity(model);
    bgfx::setTransform(model);
    bgfx::setVertexBuffer(0, worldBuffer);
    bgfx::setState(BGFX_STATE_WRITE_RGB | BGFX_STATE_WRITE_A |
                   BGFX_STATE_WRITE_Z | BGFX_STATE_DEPTH_TEST_LESS |
                   BGFX_STATE_MSAA);
    bgfx::setUniform(cameraUniform,eyeUniform);bgfx::setUniform(materialUniform,worldMaterial);
    bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
    bgfx::setUniform(reflectionUniform,reflectionState);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
    bindNormal();
    bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,noCoat);
    bgfx::setTexture(0,liverySampler,whiteTexture);
    bgfx::submit(1, visualProgram);
    drawImportedWorld(1,false,eyeUniform,sceneReflection.ready());
    if (!flow.session.active() && scene!="scale") {
      for (const auto &marker:flow.career.markers()) {
        racer::worldTransform(model,0,marker.x,marker.z);
        bgfx::setTransform(model);
        bgfx::setVertexBuffer(0,eventBuffer);
        bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_WRITE_Z|BGFX_STATE_DEPTH_TEST_LESS);
        bindUnlit(3,whiteTexture);bgfx::submit(1,visualProgram);
      }
    }
    if (flow.session.active() &&
        flow.session.result().kind == racer::TestKind::Handling) {
      const auto &gates = racer::handlingCourse().gates;
      for (size_t i = flow.session.nextGate(); i < gates.size(); ++i) {
        const auto &g = gates[i];
        const float scale = i == flow.session.nextGate() ? 1.f : .6f;
        racer::worldTransform(model, std::atan2(g.nx, g.nz), g.x, g.z,
                              float(g.width / 18), scale);
        bgfx::setTransform(model);
        bgfx::setVertexBuffer(0, gateBuffer);
        bgfx::setState(BGFX_STATE_WRITE_RGB | BGFX_STATE_WRITE_A |
                       BGFX_STATE_WRITE_Z | BGFX_STATE_DEPTH_TEST_LESS);
        bindUnlit(3,whiteTexture);bgfx::submit(1, visualProgram);
      }
    }
    bodyMatrix(model);
    const double horizontalForward=std::hypot(model[8],model[10]);
    const double orientationError = std::hypot(model[8]/horizontalForward - std::sin(shown.heading), model[10]/horizontalForward - std::cos(shown.heading));
    if (orientationError > .001 && !orientationReported) {
      diagnostics.event("orientation_mismatch", {{"error", orientationError}, {"heading", shown.heading}, {"model_x", model[8]}, {"model_z", model[10]}, {"frame", frameId}}, flow.attempt);
      orientationReported = true; manualShot = true; captureCause = "orientation_mismatch";
    }
    flow.observe("frame");
    if (elapsed >= nextSample) {
      nextSample = elapsed + .1;
      diagnostics.event("motion", {{"frame", frameId}, {"source", inputSource},
        {"requested_throttle", requestedInput.throttle}, {"requested_brake", requestedInput.brake}, {"requested_steer", requestedInput.steer},
        {"selected_throttle", selectedInput.throttle}, {"selected_brake", selectedInput.brake}, {"selected_steer", selectedInput.steer},
        {"effective_throttle", input.throttle}, {"effective_brake", input.brake}, {"effective_steer", input.steer},
        {"automatic_test", flow.session.active() && flow.session.result().kind != racer::TestKind::Handling},
        {"x", sim.car.x}, {"z", sim.car.z}, {"heading", sim.car.heading}, {"speed", sim.car.speed}, {"steering", sim.car.steering},
        {"vehicle_id",flow.vehicleId},{"wheelbase",sim.wheelbase()},{"travel",sim.car.travel},{"shown_steering",shown.steering},
        {"shown_x", shown.x}, {"shown_z", shown.z}, {"shown_heading", shown.heading}, {"alpha", alpha},
        {"model_x", model[8]}, {"model_z", model[10]}, {"camera_x", cameraX}, {"camera_z", cameraZ},
        {"target_x", targetX}, {"target_z", targetZ}, {"orientation_error", orientationError},
        {"phase", int(flow.session.phase())}, {"gate", flow.session.nextGate()}, {"paused", paused}, {"rearming", rearming},
        {"boundary", sim.boundaryContact}}, flow.attempt);
      if(groundFrame){
        diagnostics.event("surface_pose",{{"frame",frameId},{"elevation",bodyElevation},{"ground_y",groundReference},{"max_fit_error",groundFrame->maxFitError}},flow.attempt);
        for(size_t i=0;i<4;++i){const auto& c=groundFrame->contacts[i];
          diagnostics.event("surface_contact",{{"frame",frameId},{"wheel",i},{"x",c.rendered.x},{"y",c.rendered.y},{"z",c.rendered.z},{"ground_y",c.ground.y},{"error",c.error},{"triangle",c.hit.triangle}},flow.attempt);
        }
      }
      if (!vehicles.empty()) {
        const auto &g=vehicles[activeVehicle].geometry;float wheel[16];
        const auto spin=racer::wheelSpinAfterTravel(0,shown.travel,g.wheels[0].radius);
        wheelMatrix(wheel,0);
        diagnostics.event("wheel_pose",{{"frame",frameId},{"wheel",0},{"spin",spin},{"steering",shown.steering},
          {"x",wheel[12]},{"y",wheel[13]},{"z",wheel[14]},
          {"axle_x",wheel[0]},{"axle_y",wheel[1]},{"axle_z",wheel[2]},
          {"radial_x",wheel[4]},{"radial_y",wheel[5]},{"radial_z",wheel[6]}},flow.attempt);
        if (std::any_of(graphics->sections.begin(),graphics->sections.end(),[](const auto &s){return s.wheel==0 && !s.rolling;})) {
          wheelMatrix(wheel,0,false);
          diagnostics.event("carrier_pose",{{"frame",frameId},{"wheel",0},{"steering",shown.steering},
            {"x",wheel[12]},{"y",wheel[13]},{"z",wheel[14]},
            {"axle_x",wheel[0]},{"axle_y",wheel[1]},{"axle_z",wheel[2]},
            {"radial_x",wheel[4]},{"radial_y",wheel[5]},{"radial_z",wheel[6]}},flow.attempt);
        }
      }
    }
    maxInterval = std::max(maxInterval, rawdt); clampedSeconds += std::max(0., rawdt - dt); ++timingFrames;
    if (rawdt > 1.0/60) ++timingSlow;
    if (elapsed >= nextTiming) {
      diagnostics.event("timing", {{"frame", frameId}, {"frames", timingFrames}, {"over_budget", timingSlow},
        {"max_ms", maxInterval * 1000}, {"clamped_seconds", clampedSeconds}});
      nextTiming = elapsed + 1; maxInterval = clampedSeconds = 0; timingFrames = timingSlow = 0;
    }
    if (manualShot) {
      manualShot = false;
      if (diagnostics.enabled() && diagnosticShots++ < 8) {
        auto dir = diagnostics.directory() / "captures";
        std::error_code ec; std::filesystem::create_directories(dir, ec);
        uint64_t bytes = 0;
        for (std::filesystem::directory_iterator it(dir, ec), end; !ec && it != end; it.increment(ec))
          if (it->is_regular_file(ec)) bytes += it->file_size(ec);
        if (!ec && bytes + uint64_t(width) * height * 3 < 64 * 1024 * 1024)
          requestCapture((dir / (diagnostics.runId() + "-" + std::to_string(frameId) + ".ppm")).string(), captureCause);
        else diagnostics.event("capture_rejected", {{"reason", "quota_or_access"}});
      } else diagnostics.event("capture_rejected", {{"reason", "disabled_or_run_quota"}});
    }
    workflowObservation.observe(flow,frameId);
    bgfx::setTransform(model);
    bgfx::setVertexBuffer(0, graphics->vertices);
    const auto &liveryState=flow.screen==racer::Screen::Livery ? flow.features.livery().draft()
                                                            : flow.features.livery().applied();
    if (!renderedLivery || *renderedLivery!=liveryState) {
      auto began=std::chrono::steady_clock::now();
      auto pixels=racer::rasterLivery(liveryState,!vehicles.empty());
      bgfx::updateTexture2D(liveryTexture,0,0,0,0,racer::liveryTextureSize,racer::liveryTextureSize,
          bgfx::copy(pixels.data(),uint32_t(pixels.size()*sizeof(uint32_t))));
      renderedLivery=liveryState;
      diagnostics.event("livery_render",{{"frame",frameId},{"draft",flow.screen==racer::Screen::Livery},{"layers",liveryState.layers.size()},
        {"state",racer::Diagnostics::identity(racer::encodeLivery(liveryState))},{"size",racer::liveryTextureSize},
        {"raster_ms",std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count()},
        {"applied_revision",flow.features.liveryRevision()},{"draft_revision",flow.features.draftRevision()},
        {"vehicle_id",flow.vehicleId}},flow.attempt);
    }
    if(!skidQuads.empty() && bgfx::getAvailTransientVertexBuffer(uint32_t(skidQuads.size()*6),layout)>=skidQuads.size()*6) {
      bgfx::TransientVertexBuffer skidBuffer;
      bgfx::allocTransientVertexBuffer(&skidBuffer,uint32_t(skidQuads.size()*6),layout);
      auto* out=reinterpret_cast<Vertex*>(skidBuffer.data);
      size_t n=0;
      for(size_t i=0;i<skidQuads.size();++i) {
        const auto& q=skidQuads[i];
        const uint32_t a=uint32_t(255*q.alpha*(.2+.8*double(i)/double(skidQuads.size())));
        const uint32_t color=(a<<24);
        const float xs[4]={q.x0,q.x1,q.x2,q.x3},zs[4]={q.z0,q.z1,q.z2,q.z3};
        for(int idx:{0,1,2,0,2,3}) {Vertex v{xs[idx],.006f,zs[idx],color};out[n++]=v;}
      }
      bgfx::setTransform(nullptr);bgfx::setVertexBuffer(0,&skidBuffer,0,uint32_t(n));
      const float skidMaterial[4]={1,0,0,3};
      bgfx::setUniform(cameraUniform,eyeUniform);bgfx::setUniform(materialUniform,skidMaterial);
      bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
      bgfx::setUniform(reflectionUniform,reflectionState);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
      bindNormal();bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,noCoat);bgfx::setTexture(0,liverySampler,whiteTexture);
      bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_LESS|BGFX_STATE_BLEND_ALPHA|BGFX_STATE_MSAA);
      bgfx::submit(1,visualProgram);
    }
    for(const auto& parked:parkedCars) {
      const auto& geometry=vehicles[parked.vehicle].geometry;const auto& body=geometry.body;
      float footprint[16];
      bx::mtxSRT(footprint,float((body.maximum.x-body.minimum.x)*.74),1,float((body.maximum.z-body.minimum.z)*.64),
        0,float(-parked.heading),0,float(parked.x),0,float(parked.z));
      bgfx::setTransform(footprint);bgfx::setVertexBuffer(0,contactBuffer);
      const float contactMaterial[4]={1,0,0,3};
      bgfx::setUniform(cameraUniform,eyeUniform);bgfx::setUniform(materialUniform,contactMaterial);
      bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
      bgfx::setUniform(reflectionUniform,reflectionState);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
      bindNormal();bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,noCoat);bgfx::setTexture(0,liverySampler,whiteTexture);
      bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_LESS|BGFX_STATE_BLEND_ALPHA|BGFX_STATE_MSAA);
      bgfx::submit(1,visualProgram);
      for(bool transparent:{false,true}) for(const auto& section:parked.graphics->sections) {
        if(section.blend!=transparent)continue;
        float placed[16];
        if(section.wheel>=0)racer::wheelRenderTransform(placed,geometry,size_t(section.wheel),parked.heading,parked.x,parked.z,0,0,section.rolling);
        else racer::worldTransform(placed,parked.heading,parked.x,parked.z);
        bgfx::setTransform(placed);bgfx::setVertexBuffer(0,parked.graphics->vertices,section.first,section.count);
        uint32_t flags=BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP;
        if(section.image>=0)flags=(section.wrapU==33071?BGFX_SAMPLER_U_CLAMP:section.wrapU==33648?BGFX_SAMPLER_U_MIRROR:0)|
          (section.wrapV==33071?BGFX_SAMPLER_V_CLAMP:section.wrapV==33648?BGFX_SAMPLER_V_MIRROR:0);
        bgfx::setTexture(0,liverySampler,section.image>=0?parked.graphics->textures.at(size_t(section.image))->handle:whiteTexture,flags);
        bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_LESS|BGFX_STATE_MSAA|
          (transparent?BGFX_STATE_BLEND_ALPHA:BGFX_STATE_WRITE_Z));
        const float carEye[4]={eyeUniform[0],eyeUniform[1],eyeUniform[2],section.mask?section.alphaCutoff:0};
        const float carMaterial[4]={section.roughness,section.metallic,section.image>=0?1.f:0.f,0};
        const float carCoat[4]={section.clearcoat,section.coatRoughness,section.detailMode(),section.normalScale};
        bgfx::setUniform(cameraUniform,carEye);bgfx::setUniform(materialUniform,carMaterial);
        bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
        bgfx::setUniform(reflectionUniform,reflectionState);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
        bindNormal(parked.graphics.get(),&section);bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,carCoat);
        bgfx::submit(1,visualProgram);
      }
    }
    // Opaque sections precede blended sections. Transparent depth sorting and
    // additional donor material channels remain outside this inspection lane.
    if(!vehicles.empty()) {
      const auto &body=vehicles[activeVehicle].geometry.body;
      float shadow[16];
      bx::mtxSRT(shadow,float((body.maximum.x-body.minimum.x)*.74),1,
        float((body.maximum.z-body.minimum.z)*.64),0,float(-shown.heading),0,float(shown.x),0,float(shown.z));
      if(groundFrame){
        std::copy(groundFrame->body.begin(),groundFrame->body.end(),shadow);
        shadow[13]=float(groundFrame->groundElevation);
        const float scales[3]={float((body.maximum.x-body.minimum.x)*.74),1,float((body.maximum.z-body.minimum.z)*.64)};
        for(size_t c=0;c<3;++c)for(size_t r=0;r<3;++r)shadow[c*4+r]*=scales[c];
      }
      bgfx::setTransform(shadow);bgfx::setVertexBuffer(0,contactBuffer);
      const float contactMaterial[4]={1,0,0,3};
      bgfx::setUniform(cameraUniform,eyeUniform);bgfx::setUniform(materialUniform,contactMaterial);
      bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
    bgfx::setUniform(reflectionUniform,reflectionState);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
    bindNormal();
    bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,noCoat);
      bgfx::setTexture(0,liverySampler,whiteTexture);
      bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_LESS|BGFX_STATE_BLEND_ALPHA|BGFX_STATE_MSAA);
      bgfx::submit(1,visualProgram);
      const auto& geometry=vehicles[activeVehicle].geometry;
      for(size_t i=0;i<4;++i){
        const auto& wheel=geometry.wheels[i];
        racer::GeometryPoint ground,normal{0,1,0};
        if(groundFrame){ground=groundFrame->contacts[i].ground;normal=groundFrame->contacts[i].hit.normal;}
        else{
          const double c=std::cos(shown.heading),s=std::sin(shown.heading);
          // The receiver is the authored flat roadY0, independent of model clearance.
          ground={shown.x+c*wheel.center.x+s*wheel.center.z,0,shown.z-s*wheel.center.x+c*wheel.center.z};
        }
        float unrolled[16];wheelMatrix(unrolled,i,false);
        const double tireHeading=std::atan2(unrolled[8],unrolled[10]);
        const auto footprint=racer::surfaceFollow::footprintMatrix(ground,normal,tireHeading,wheel.width*.8,wheel.radius*.5);
        bgfx::setTransform(footprint.data());bgfx::setVertexBuffer(0,tireContactBuffer);
        bindUnlit(3,whiteTexture);
        bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_LESS|BGFX_STATE_BLEND_ALPHA|BGFX_STATE_MSAA);
        bgfx::submit(1,visualProgram);
      }
    }
    for (bool transparent:{false,true}) for (const auto &section:graphics->sections) {
      if (section.blend!=transparent) continue;
      float wheelModel[16];
      if (section.wheel>=0 && !vehicles.empty()) {
        wheelMatrix(wheelModel,size_t(section.wheel),section.rolling);
        bgfx::setTransform(wheelModel);
      } else bgfx::setTransform(model);
      bgfx::setVertexBuffer(0,graphics->vertices,section.first,section.count);
      const bool textured=section.image>=0;
      {
        uint32_t flags=BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP;
        if (section.image>=0) flags=(section.wrapU==33071 ? BGFX_SAMPLER_U_CLAMP : section.wrapU==33648 ? BGFX_SAMPLER_U_MIRROR : 0) |
            (section.wrapV==33071 ? BGFX_SAMPLER_V_CLAMP : section.wrapV==33648 ? BGFX_SAMPLER_V_MIRROR : 0);
        bgfx::setTexture(0,liverySampler,section.image>=0 ? graphics->textures.at(size_t(section.image))->handle : whiteTexture,flags);
      }
      bgfx::setState(BGFX_STATE_WRITE_RGB | BGFX_STATE_WRITE_A | BGFX_STATE_DEPTH_TEST_LESS |
          BGFX_STATE_MSAA | (transparent ? BGFX_STATE_BLEND_ALPHA : BGFX_STATE_WRITE_Z));
      float carEye[4]={eyeUniform[0],eyeUniform[1],eyeUniform[2],section.mask?section.alphaCutoff:0};
      const float carMaterial[4]={section.roughness,section.metallic,textured?1.f:0.f,0};
      const float carCoat[4]={section.clearcoat,section.coatRoughness,section.detailMode(),section.normalScale};
      bgfx::setUniform(cameraUniform,carEye);bgfx::setUniform(materialUniform,carMaterial);
      bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
      bgfx::setUniform(reflectionUniform,reflectionState);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
      bindNormal(graphics.get(),&section);
      bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,carCoat);
      bgfx::submit(1,visualProgram);
    }
    // Rotational blur: translucent ghosts of each rolling wheel across the angle it sweeps during a
    // ~1/40 s exposure, so spokes smear at speed as in the reference frames. Authored.
    if(wheelBlur && !vehicles.empty() && std::abs(shown.speed)>6) {
      const auto& wheels=vehicles[activeVehicle].geometry.wheels;
      for(const auto &section:graphics->sections) {
        if(section.wheel<0 || !section.rolling || section.blend)continue;
        const double arc=std::min(1.7,std::abs(shown.speed)/wheels[size_t(section.wheel)].radius/40.0);
        for(int k=-3;k<=3;++k) {
          if(k==0)continue;
          float ghost[16];wheelMatrix(ghost,size_t(section.wheel),true,arc*k/6.0);
          bgfx::setTransform(ghost);bgfx::setVertexBuffer(0,graphics->vertices,section.first,section.count);
          uint32_t flags=BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP;
          if(section.image>=0)flags=(section.wrapU==33071?BGFX_SAMPLER_U_CLAMP:section.wrapU==33648?BGFX_SAMPLER_U_MIRROR:0)|
            (section.wrapV==33071?BGFX_SAMPLER_V_CLAMP:section.wrapV==33648?BGFX_SAMPLER_V_MIRROR:0);
          bgfx::setTexture(0,liverySampler,section.image>=0?graphics->textures.at(size_t(section.image))->handle:whiteTexture,flags);
          bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_LESS|BGFX_STATE_MSAA|BGFX_STATE_BLEND_ALPHA);
          const float carEye[4]={eyeUniform[0],eyeUniform[1],eyeUniform[2],section.mask?section.alphaCutoff:0};
          const float carMaterial[4]={section.roughness,section.metallic,section.image>=0?1.f:0.f,0};
          const float carCoat[4]={section.clearcoat,section.coatRoughness,section.detailMode(),section.normalScale};
          const float ghostState[4]={sceneReflection.ready()?1.f:0.f,.22f,0,0};
          bgfx::setUniform(cameraUniform,carEye);bgfx::setUniform(materialUniform,carMaterial);
          bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setTexture(1,shadowSampler,shadowMap);bgfx::setTexture(2,surfaceSampler,surfaceTexture);
          bgfx::setUniform(reflectionUniform,ghostState);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
          bindNormal(graphics.get(),&section);bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,carCoat);
          bgfx::submit(1,visualProgram);
        }
      }
    }
    if(!puffs.empty() && bgfx::isValid(puffTexture) &&
       bgfx::getAvailTransientVertexBuffer(uint32_t(puffs.size()*6),layout)>=puffs.size()*6) {
      std::vector<const Puff*> order;order.reserve(puffs.size());
      for(const auto& p:puffs)order.push_back(&p);
      auto dist2=[&](const Puff* p){const double dx=p->x-cameraX,dy=p->y-cameraY,dz=p->z-cameraZ;return dx*dx+dy*dy+dz*dz;};
      std::sort(order.begin(),order.end(),[&](const Puff* a,const Puff* b){return dist2(a)>dist2(b);});
      bgfx::TransientVertexBuffer puffBuffer;
      bgfx::allocTransientVertexBuffer(&puffBuffer,uint32_t(order.size()*6),layout);
      auto* out=reinterpret_cast<Vertex*>(puffBuffer.data);
      const float rx=view[0],ry=view[4],rz=view[8],ux=view[1],uy=view[5],uz=view[9];
      size_t n=0;
      for(const Puff* p:order) {
        const float t=p->age/p->life;
        const float size=p->size*(1+3.2f*t);
        const float fade=std::min(1.f,t*8.f)*(1-t)*(1-t);
        const uint32_t a=uint32_t(255*std::clamp((p->seed>1.f?.42f:.95f)*fade,0.f,1.f)); // launch puffs (seed>1) are thinner
        // Start-to-end colour ramp (MCLA exposes smokeStartColor/smokeEndColor; values authored).
        const float ramp=std::clamp(t*1.6f,0.f,1.f);
        auto lerp8=[&](float from,float to){return uint32_t(from+(to-from)*ramp);};
        const uint32_t color=nightAmount>.5f?((a<<24)|(lerp8(120,80)<<16)|(lerp8(95,64)<<8)|lerp8(86,60))
                                           :((a<<24)|(lerp8(232,150)<<16)|(lerp8(228,148)<<8)|lerp8(226,146));
        const float cx[4]={-1,1,1,-1},cy[4]={-1,-1,1,1};
        Vertex v[4];
        for(int i=0;i<4;++i){
          const float lift=size*.9f; // keep the quad above the road so it is not cut by the ground plane
          v[i]=Vertex{p->x+(rx*cx[i]+ux*cy[i])*size,p->y+lift+(ry*cx[i]+uy*cy[i])*size,p->z+(rz*cx[i]+uz*cy[i])*size,color};
          v[i].u=cx[i]*.5f+.5f;v[i].v=.5f-cy[i]*.5f;
        }
        for(int idx:{0,1,2,0,2,3})out[n++]=v[idx];
      }
      bgfx::setTransform(nullptr);bgfx::setVertexBuffer(0,&puffBuffer,0,uint32_t(n));
      bindUnlit(5,puffTexture);
      bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_LESS|BGFX_STATE_BLEND_ALPHA|BGFX_STATE_MSAA);
      bgfx::submit(1,visualProgram);
    }
    if (!vehicles.empty() && !liveryState.layers.empty()) {
      for (const auto &section:graphics->sections) {
        if (section.wheel>=0 || section.blend || section.mask) continue;
        bgfx::setTransform(model);
        bgfx::setVertexBuffer(0,graphics->overlay,section.first,section.count);
        bindUnlit(5,liveryTexture);
        bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_EQUAL|BGFX_STATE_BLEND_ALPHA);
        bgfx::submit(1,visualProgram);
      }
    }
    bgfx::dbgTextClear();
    if (scene=="scale") bgfx::dbgTextPrintf(3,uint16_t(height/16-3),0x1f,
      "SCALE / 1 unit = 1 m / bay %.1f x %.1f m / figure %.2f m / ticks 1 m / lanes %.1f m",
      racer::worldScale::parkingBayWidth,racer::worldScale::parkingBayLength,
      racer::worldScale::referencePersonHeight,racer::worldScale::laneWidth);
    if (!previewMesh.empty()) bgfx::dbgTextPrintf(3, uint16_t(height/16-2), 0x6f,
      "ASSET INSPECTION / partial materials / prototype physics / livery disabled");
    auto panel = flow.lines();
    const bool active =
        flow.screen == racer::Screen::Drive && flow.session.active();
    if (!hideHud && flow.screen == racer::Screen::Drive && !active) {
      const auto &marker=flow.career.selectedMarker();
      const double dx=marker.x-sim.car.x,dz=marker.z-sim.car.z;
      const double bearing=std::remainder(std::atan2(dx,dz)-sim.car.heading,2*3.14159265358979323846);
      driveHud.draw(uint16_t(width),uint16_t(height),std::abs(sim.car.speed)*2.236936,sim.car.direction!=1,
        vehicles.empty()?"Prototype":vehicles[activeVehicle].name,marker.id,std::hypot(dx,dz),
        std::abs(bearing)<.2 ? "AHEAD" : bearing>0 ? "RIGHT" : "LEFT");
    }
    const int columns = width / 8;
    const int rows = height / 16;
    if (!hideHud && (flow.screen != racer::Screen::Drive || active))
      driveHud.drawPanel(uint16_t(width),uint16_t(height),panel,active);
    if (active && flow.session.result().kind == racer::TestKind::Handling) {
      const auto &gates = racer::handlingCourse().gates;
      {
        const size_t i = flow.session.nextGate();
        const auto &g = gates[i];
        float p[4] = {float(g.x), 5.5f, float(g.z), 1}, eye[4]{}, clip[4]{};
        for (int r = 0; r < 4; ++r)
          for (int c = 0; c < 4; ++c)
            eye[r] += view[c * 4 + r] * p[c];
        for (int r = 0; r < 4; ++r)
          for (int c = 0; c < 4; ++c)
            clip[r] += projection[c * 4 + r] * eye[c];
        if (clip[3] > 0) {
          int x = int((clip[0] / clip[3] + 1) * width / 16);
          // Keep the active tag below the compact HUD when perspective
          // places a distant gate on the horizon, including at 720p.
          int y = std::max(9, int((1 - clip[1] / clip[3]) * height / 32));
          if (x >= 2 && x < columns - 16 && y >= 9 && y < rows - 5)
            bgfx::dbgTextPrintf(uint16_t(x), uint16_t(y), 0x2f,
                                "[NEXT GATE] %zu", i + 1);
        }
      }
    }
    if (!review.capture.empty()) {
      requestCapture(review.capture);
      review.capture.clear();
    }
    if (!shot.empty() && !captured && elapsed > (verify ? 2.5 : shotDelay)) {
      requestCapture(shot);
      captured = true;
    }
    if (!captureLoop.empty() && flow.screen != racer::Screen::Pause &&
        flow.screen != racer::Screen::Pending &&
        (flow.screen != racer::Screen::Drive || flow.session.active()) &&
        capturedScreens.insert(flow.screen).second) {
      auto path = std::filesystem::path(captureLoop) /
                  ("screen-" + std::to_string(int(flow.screen)) + ".ppm");
      requestCapture(path.string());
    }
    const auto probe=sceneReflection.beginFrame(float(shown.x),float(shown.z),float(bodyElevation));
    const float probeEye[4]={probe.eye[0],probe.eye[1],probe.eye[2],0},noReflection[4]={0,0,0,0};
    auto probeBindings=[&](const float* material) {
      bgfx::setUniform(cameraUniform,probeEye);bgfx::setUniform(materialUniform,material);
      bgfx::setUniform(shadowUniform,lightMatrix);bgfx::setUniform(reflectionUniform,noReflection);
      bgfx::setUniform(headlightUniform,headlightState);bgfx::setUniform(coatUniform,noCoat);
      bgfx::setTexture(0,liverySampler,whiteTexture);bgfx::setTexture(1,shadowSampler,shadowMap);
      bgfx::setTexture(2,surfaceSampler,surfaceTexture);bgfx::setTexture(3,environmentSampler,sceneReflection.readTexture());
      bindNormal();
    };
    bx::mtxTranslate(model,probe.eye[0],probe.eye[1],probe.eye[2]);
    bgfx::setTransform(model);bgfx::setVertexBuffer(0,skyBuffer);probeBindings(skyMaterial);
    bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A);bgfx::submit(probe.view,visualProgram);
    drawSourceSky(probe.view,probeEye);
    bx::mtxIdentity(model);bgfx::setTransform(model);bgfx::setVertexBuffer(0,worldBuffer);probeBindings(worldMaterial);
    bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_WRITE_Z|BGFX_STATE_DEPTH_TEST_LESS);
    bgfx::submit(probe.view,visualProgram);
    drawImportedWorld(probe.view,false,probeEye,false);
    sceneReflection.endFrame();
    {
      // Anchor lens glare to the authored sun direction used by the sky and shadow light.
      const float sunLength=std::sqrt(110.f*110.f+68.f*68.f+140.f*140.f);
      const float far[4]={float(cameraX)-110.f/sunLength*1000.f,float(cameraY)+68.f/sunLength*1000.f,
                          float(cameraZ)+140.f/sunLength*1000.f,1};
      float eyeSpace[4]{},clip[4]{};
      for(int r=0;r<4;++r)for(int c=0;c<4;++c)eyeSpace[r]+=view[c*4+r]*far[c];
      for(int r=0;r<4;++r)for(int c=0;c<4;++c)clip[r]+=projection[c*4+r]*eyeSpace[c];
      if(clip[3]>0) {
        const float x=clip[0]/clip[3],y=clip[1]/clip[3];
        const float edge=std::max(std::abs(x),std::abs(y));
        // Glare needs the disc on screen: the glare shader reads scene radiance at the sun
        // position, which is edge-clamped once the sun is outside the frame.
        const float weight=std::clamp((1.12f-edge)/.12f,0.f,1.f);
        postProcess.setSun(x*.5f+.5f,.5f-y*.5f,weight,float(width)/height);
      } else postProcess.setSun(0,0,0,1);
    }
    postProcess.setMotion(std::clamp((float(std::abs(shown.speed))-15.f)/35.f,0.f,1.f)*.85f);
    postProcess.draw(postNeutral);
    bgfx::frame();
    if (elapsed > 1) {
      measured += rawdt;
      frames++;
      longestFrame = std::max(longestFrame, rawdt);
      if (rawdt > 1.0 / 60)
        overBudgetFrames++;
    }
    if (smoke > 0 && elapsed >= smoke && running) {
      timedOut = true;
      running = false;
    }
  }
  std::cout << "Measured frames=" << frames << " seconds=" << measured
            << " FPS=" << (measured ? frames / measured : 0)
            << " final_mph=" << sim.car.speed * 2.236936 << " x=" << sim.car.x
            << " z=" << sim.car.z << '\n';
  std::cout << "Frame intervals: longest_ms=" << longestFrame * 1000
            << " over_16.67ms=" << overBudgetFrames << '/' << frames << '\n';
  if (courseDriver || review.driveCourse)
    std::cout << "Synthetic course: gates=" << flow.session.nextGate()
              << " valid=" << flow.session.result().valid
              << " seconds=" << flow.session.result().seconds << '\n';
  diagnostics.event("app_exit", {{"reason", timedOut ? "smoke_limit" : flow.quit ? "menu_quit" : "window_quit"}, {"frames", frameId}, {"review_cursor", review.cursor}, {"review_commands", review.commands.size()}});
  garageChecks.close();
  if (pad)
    SDL_CloseGamepad(pad);
  bgfx::destroy(gateBuffer);
  bgfx::destroy(eventBuffer);
  bgfx::destroy(worldBuffer);
  bgfx::destroy(skyBuffer);bgfx::destroy(contactBuffer);bgfx::destroy(tireContactBuffer);
  bgfx::destroy(visualProgram);bgfx::destroy(cameraUniform);bgfx::destroy(materialUniform);
  bgfx::destroy(shadowProgram);bgfx::destroy(shadowFramebuffer);
  bgfx::destroy(shadowUniform);bgfx::destroy(shadowSampler);bgfx::destroy(surfaceSampler);
  bgfx::destroy(environmentSampler);bgfx::destroy(reflectionUniform);
  bgfx::destroy(normalSampler);
  bgfx::destroy(coatUniform);
  if(sourceSurfaces) bgfx::destroy(surfaceTexture);
  bgfx::destroy(liverySampler);
  bgfx::destroy(liveryTexture);
  bgfx::destroy(whiteTexture);
  if (!reviewPath.empty() &&
      (review.cursor != review.commands.size() || timedOut)) {
    std::cerr << "FAIL: review script incomplete at " << review.cursor << '\n';
    return 1;
  }
  if (!garageMode.empty() && (!garageChecks.complete() || timedOut)) {
    std::cerr << "FAIL: garage verification incomplete\n";
    return 1;
  }
  if (verify && (!liveChecks.complete() || timedOut)) {
    std::cerr << "FAIL: live verification ended before confirmed Quit\n";
    return 1;
  }
  return 0;
}

int main(int argc, char **argv) {
  std::filesystem::path directory;
  if (auto pref = SDL_GetPrefPath("Racer", "Racer")) directory = std::filesystem::path(pref) / "diagnostics";
  for (int i = 1; i < argc; ++i) {
    if (std::string(argv[i]) == "--diagnostics-dir" && i + 1 < argc) directory = argv[++i];
    else if (std::string(argv[i]) == "--no-diagnostics") directory.clear();
  }
  racer::Diagnostics diagnostics(directory);
  diagnostics.event("executable", {{"sha256", racer::Diagnostics::fileHash(argv[0])}});
  try {
    int result = run(argc, argv, diagnostics);
    diagnostics.event("process_outcome", {{"exit_code", result}});
    return result;
  }
  catch (const std::exception &) {
    diagnostics.event("unhandled_exception", {{"reason", "std_exception_details_omitted"}});
    diagnostics.event("process_outcome", {{"exit_code", 1}});
    diagnostics.flush();
    std::cerr << "Racer failed; inspect retained diagnostics for the last completed boundary.\n";
    return 1;
  }
}
