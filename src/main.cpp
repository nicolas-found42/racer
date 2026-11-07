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
#include "material_shader.h"
#include <map>
#include <sstream>
#include "vs_debugdraw_fill_texture.bin.h"
#include "fs_debugdraw_fill_texture.bin.h"
struct CarGraphics {
  bgfx::VertexBufferHandle vertices=BGFX_INVALID_HANDLE;
  bgfx::VertexBufferHandle overlay=BGFX_INVALID_HANDLE;
  std::vector<bgfx::TextureHandle> textures;
  std::map<float,bgfx::ProgramHandle> masks;
  std::vector<racer::AssetSection> sections;
  ~CarGraphics() {
    if (bgfx::isValid(vertices)) bgfx::destroy(vertices);
    if (bgfx::isValid(overlay)) bgfx::destroy(overlay);
    for (auto texture:textures) bgfx::destroy(texture);
    for (auto [cutoff,program]:masks) bgfx::destroy(program);
  }
};
using Vertex = racer::AssetVertex;
using Mesh = std::vector<Vertex>;
void box(Mesh &m, float x, float y, float z, float sx, float sy, float sz,
         uint32_t c) {
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
    float shade = f == 3 ? 1.0f : (f < 2 ? .82f : .65f);
    uint32_t col = 0xff000000;
    for (int k = 0; k < 3; k++)
      col |= uint32_t(((c >> (k * 8)) & 255) * shade) << (k * 8);
    for (int i : faces[f])
      m.push_back({p[i][0], p[i][1], p[i][2], col});
  }
}
bgfx::ShaderHandle shader(const char *name, racer::Diagnostics &diagnostics, const std::string &directory) {
  std::ifstream f(directory + "/" + name,
                  std::ios::binary | std::ios::ate);
  if (!f) {
    diagnostics.event("dependency", {{"component", name}, {"success", false}, {"stage", "shader_open"}});
    throw std::runtime_error("Missing pinned bgfx shader");
  }
  diagnostics.event("dependency", {{"component", name}, {"success", true}, {"sha256", racer::Diagnostics::fileHash(directory + "/" + name)}});
  auto n = f.tellg();
  if (n <= 0 || n > 16 * 1024 * 1024) {
    diagnostics.event("dependency", {{"component", name}, {"success", false}, {"stage", "shader_size"}});
    throw std::runtime_error("Pinned shader size invalid");
  }
  f.seekg(0);
  std::vector<char> bytes(static_cast<size_t>(n));
  f.read(bytes.data(), n);
  if (!f) {
    diagnostics.event("dependency", {{"component", name}, {"success", false}, {"stage", "shader_read"}});
    throw std::runtime_error("Pinned shader read failed");
  }
  auto handle = bgfx::createShader(bgfx::copy(bytes.data(), uint32_t(bytes.size())));
  if (!bgfx::isValid(handle)) {
    diagnostics.event("dependency", {{"component", name}, {"success", false}, {"stage", "shader_create"}});
    throw std::runtime_error("Pinned shader creation failed");
  }
  return handle;
}
int run(int argc, char **argv, racer::Diagnostics &diagnostics) {
  double smoke = 0;
  bool courseDriver = false, background = false;
  double autoTurn = .22;
  bool autoDrive = false, benchmark = false, verify = false;
  std::string shot, profilePath, scene, garageMode, captureLoop, reviewPath, previewMesh;
  std::string vehicleLibrary=RACER_VEHICLE_LIBRARY,requestedVehicle;
  std::string cameraView="rear";
  int windowWidth = 1920, windowHeight = 1080;
  std::string shaderDirectory = RACER_SHADER_DIR;
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    if (a == "--diagnostics-dir" && i + 1 < argc)
      ++i;
    else if (a == "--no-diagnostics") {}
    else if (a == "--background") background = true;
    else if (a == "--preview-gltf" && i + 1 < argc) previewMesh = argv[++i];
    else if (a == "--vehicle-library" && i + 1 < argc) vehicleLibrary=argv[++i];
    else if (a == "--vehicle" && i + 1 < argc) requestedVehicle=argv[++i];
    else if (a == "--camera-view" && i + 1 < argc) cameraView=argv[++i];
    else if (a == "--shader-dir" && i + 1 < argc) shaderDirectory = argv[++i];
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
    else {
      std::cerr
          << "Usage: racer [--smoke seconds] [--autodrive] [--benchmark] "
             "[--verify-controls] [--verify-garage keyboard|gamepad] "
             "[--profile path] [--capture-loop directory] [--scene "
             "garage|course|scale] [--camera-view rear|front|left|right|elevated] [--screenshot path.ppm] [--window width height] "
             "[--review-script path] [--course-driver] [--diagnostics-dir path] [--no-diagnostics]\n";
      std::cerr << "Cars: [--vehicle-library catalog.racer] [--vehicle index|id|name] [--preview-gltf local-path]\n";
      return 1;
    }
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
  init.reset = BGFX_RESET_VSYNC;
  init.callback = &callback;
  if (!bgfx::init(init)) {
    diagnostics.event("startup_failure", {{"stage", "bgfx_init"}});
    std::cerr << "Metal initialization failed\n";
    return 1;
  }
  lifetime.ready = true;
  std::cout << "Renderer: " << bgfx::getRendererName(bgfx::getRendererType())
            << " | " << width << 'x' << height << '\n';
  diagnostics.event("renderer_ready", {{"backend", "Metal"}, {"width", width}, {"height", height}});
  bgfx::setDebug(BGFX_DEBUG_TEXT);
  bgfx::VertexLayout layout;
  layout.begin()
      .add(bgfx::Attrib::Position, 3, bgfx::AttribType::Float)
      .add(bgfx::Attrib::Color0, 4, bgfx::AttribType::Uint8, true)
      .add(bgfx::Attrib::TexCoord0, 2, bgfx::AttribType::Float)
      .end();
  auto program =
      bgfx::createProgram(shader("vs_cubes.bin", diagnostics, shaderDirectory), shader("fs_cubes.bin", diagnostics, shaderDirectory), true);
  auto liveryProgram=bgfx::createProgram(
      bgfx::createShader(bgfx::copy(vs_debugdraw_fill_texture_mtl,sizeof(vs_debugdraw_fill_texture_mtl))),
      bgfx::createShader(bgfx::copy(fs_debugdraw_fill_texture_mtl,sizeof(fs_debugdraw_fill_texture_mtl))),true);
  auto liverySampler=bgfx::createUniform("s_texColor",bgfx::UniformType::Sampler);
  auto liveryTexture=bgfx::createTexture2D(racer::liveryTextureSize,racer::liveryTextureSize,false,1,
      bgfx::TextureFormat::RGBA8,BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP);
  const uint32_t whitePixel=0xffffffff;
  auto whiteTexture=bgfx::createTexture2D(1,1,false,1,bgfx::TextureFormat::RGBA8,0,bgfx::copy(&whitePixel,4));
  if (!bgfx::isValid(liveryProgram) || !bgfx::isValid(liverySampler) || !bgfx::isValid(liveryTexture) || !bgfx::isValid(whiteTexture)) {
    diagnostics.event("dependency",{{"component","livery_renderer"},{"success",false},{"stage","gpu_create"}});
    throw std::runtime_error("Livery renderer unavailable");
  }
  diagnostics.event("dependency",{{"component","livery_renderer"},{"success",true},{"source","pinned_bgfx_debugdraw_metal"}});
  Mesh world;
  box(world, 0, -.3, 0, 1000, .5, 1000, 0xff678050);
  for (int n = -500; n <= 500; n += 100) {
    box(world, float(n), -.04, 0, float(racer::worldScale::roadWidth), .08, 1000, 0xff424952);
    box(world, 0, -.04, float(n), 1000, .08, float(racer::worldScale::roadWidth), 0xff424952);
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
  auto worldBuffer = bgfx::createVertexBuffer(
      bgfx::copy(world.data(), uint32_t(world.size() * sizeof(Vertex))),
      layout);
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
      for (const auto &section:asset.sections) if (section.mask && !candidate->masks.contains(section.alphaCutoff)) {
        if (candidate->masks.size()>=16) throw racer::MeshAssetError("asset_alpha_program_budget");
        auto code=racer::alphaMaskShader(fs_debugdraw_fill_texture_mtl,sizeof(fs_debugdraw_fill_texture_mtl),section.alphaCutoff);
        auto handle=bgfx::createProgram(bgfx::createShader(bgfx::copy(vs_debugdraw_fill_texture_mtl,sizeof(vs_debugdraw_fill_texture_mtl))),
            bgfx::createShader(bgfx::copy(code.data(),uint32_t(code.size()))),true);
        if (!bgfx::isValid(handle)) throw racer::MeshAssetError("asset_alpha_program_create");
        candidate->masks.emplace(section.alphaCutoff,handle);
      }
      for (const auto &image:asset.images) {
        auto texture=bgfx::createTexture2D(uint16_t(image.width),uint16_t(image.height),false,1,bgfx::TextureFormat::RGBA8,
            BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP,bgfx::copy(image.rgba.data(),uint32_t(image.rgba.size())));
        if (!bgfx::isValid(texture)) throw racer::MeshAssetError("asset_texture_gpu_create");
        candidate->textures.push_back(texture);
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
  box(eventMarker,-3,1.5,0,.6,3,.6,0xff90e050);
  box(eventMarker,3,1.5,0,.6,3,.6,0xff90e050);
  box(eventMarker,0,3,0,6.6,.5,.6,0xff90e050);
  auto eventBuffer=bgfx::createVertexBuffer(bgfx::copy(eventMarker.data(),uint32_t(eventMarker.size()*sizeof(Vertex))),layout);
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
  auto cameraDistance=[&] {return scene=="scale" ? 8. : vehicles.empty() ? 11. : std::clamp(
      (vehicles[activeVehicle].geometry.body.maximum.z-vehicles[activeVehicle].geometry.body.minimum.z)*1.7,6.,16.);};
  auto cameraHeight=[&] {return scene=="scale" ? 4. : vehicles.empty() ? 6. : std::max(3.6,vehicles[activeVehicle].geometry.body.maximum.y*1.8+1.4);};
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
    double targetX = shown.x - std::sin(shown.heading) * cameraDistance(),
           targetZ = shown.z - std::cos(shown.heading) * cameraDistance();
    if (cameraView!="rear") {
      constexpr double pi=3.14159265358979323846;
      const double angle=shown.heading+(cameraView=="front" ? 0 : cameraView=="left" ? -pi/2 : cameraView=="right" ? pi/2 : pi*.7);
      targetX=shown.x+std::sin(angle)*cameraDistance();
      targetZ=shown.z+std::cos(angle)*cameraDistance();
    }
    cameraY=cameraView=="elevated" ? cameraDistance()*1.3 : cameraHeight();
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
      bgfx::reset(BGFX_RESET_VSYNC, &swap);
      diagnostics.event("resize", {{"width", width}, {"height", height}, {"frame", frameId}});
      std::cout << "Drawable resized: " << width << 'x' << height << '\n';
    }
    float view[16], projection[16], model[16];
    bx::mtxLookAt(view, {float(cameraX), float(cameraY), float(cameraZ)},
                  {float(shown.x + (scene=="scale"?0:std::sin(shown.heading)*2)), float(lookHeight()),
                   float(shown.z + (scene=="scale"?0:std::cos(shown.heading)*2))});
    bx::mtxProj(projection, 65, float(width) / height, .1f, 1600,
                bgfx::getCaps()->homogeneousDepth);
    bgfx::setViewRect(0, 0, 0, uint16_t(width), uint16_t(height));
    bgfx::setViewClear(0, BGFX_CLEAR_COLOR | BGFX_CLEAR_DEPTH, 0xcbddeeff, 1,
                       0);
    bgfx::setViewTransform(0, view, projection);
    bgfx::touch(0);
    bx::mtxIdentity(model);
    bgfx::setTransform(model);
    bgfx::setVertexBuffer(0, worldBuffer);
    bgfx::setState(BGFX_STATE_WRITE_RGB | BGFX_STATE_WRITE_A |
                   BGFX_STATE_WRITE_Z | BGFX_STATE_DEPTH_TEST_LESS |
                   BGFX_STATE_MSAA);
    bgfx::submit(0, program);
    if (!flow.session.active() && scene!="scale") {
      for (const auto &marker:flow.career.markers()) {
        racer::worldTransform(model,0,marker.x,marker.z);
        bgfx::setTransform(model);
        bgfx::setVertexBuffer(0,eventBuffer);
        bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_WRITE_Z|BGFX_STATE_DEPTH_TEST_LESS);
        bgfx::submit(0,program);
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
        bgfx::submit(0, program);
      }
    }
    racer::worldTransform(model, shown.heading, shown.x, shown.z);
    const double orientationError = std::hypot(model[8] - std::sin(shown.heading), model[10] - std::cos(shown.heading));
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
      if (!vehicles.empty()) {
        const auto &g=vehicles[activeVehicle].geometry;float wheel[16];
        const auto spin=racer::wheelSpinAfterTravel(0,shown.travel,g.wheels[0].radius);
        racer::wheelRenderTransform(wheel,g,0,shown.heading,shown.x,shown.z,shown.steering,spin);
        diagnostics.event("wheel_pose",{{"frame",frameId},{"wheel",0},{"spin",spin},{"steering",shown.steering},
          {"x",wheel[12]},{"y",wheel[13]},{"z",wheel[14]},
          {"axle_x",wheel[0]},{"axle_y",wheel[1]},{"axle_z",wheel[2]},
          {"radial_x",wheel[4]},{"radial_y",wheel[5]},{"radial_z",wheel[6]}},flow.attempt);
        if (std::any_of(graphics->sections.begin(),graphics->sections.end(),[](const auto &s){return s.wheel==0 && !s.rolling;})) {
          racer::wheelRenderTransform(wheel,g,0,shown.heading,shown.x,shown.z,shown.steering,spin,false);
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
    // Opaque sections precede blended sections. Transparent depth sorting and
    // additional donor material channels remain outside this inspection lane.
    for (bool transparent:{false,true}) for (const auto &section:graphics->sections) {
      if (section.blend!=transparent) continue;
      float wheelModel[16];
      if (section.wheel>=0 && !vehicles.empty()) {
        const auto &geometry=vehicles[activeVehicle].geometry;
        const auto index=size_t(section.wheel);
        racer::wheelRenderTransform(wheelModel,geometry,index,shown.heading,shown.x,shown.z,shown.steering,
            racer::wheelSpinAfterTravel(0,shown.travel,geometry.wheels[index].radius),section.rolling);
        bgfx::setTransform(wheelModel);
      } else bgfx::setTransform(model);
      bgfx::setVertexBuffer(0,graphics->vertices,section.first,section.count);
      const bool textured=section.image>=0 || section.mask;
      if (textured) {
        uint32_t flags=BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP;
        if (section.image>=0) flags=(section.wrapU==33071 ? BGFX_SAMPLER_U_CLAMP : section.wrapU==33648 ? BGFX_SAMPLER_U_MIRROR : 0) |
            (section.wrapV==33071 ? BGFX_SAMPLER_V_CLAMP : section.wrapV==33648 ? BGFX_SAMPLER_V_MIRROR : 0);
        bgfx::setTexture(0,liverySampler,section.image>=0 ? graphics->textures.at(size_t(section.image)) : whiteTexture,flags);
      }
      bgfx::setState(BGFX_STATE_WRITE_RGB | BGFX_STATE_WRITE_A | BGFX_STATE_DEPTH_TEST_LESS |
          (transparent ? BGFX_STATE_BLEND_ALPHA : BGFX_STATE_WRITE_Z));
      bgfx::submit(0,section.mask ? graphics->masks.at(section.alphaCutoff) : textured ? liveryProgram : program);
    }
    if (!vehicles.empty() && !liveryState.layers.empty()) {
      for (const auto &section:graphics->sections) {
        if (section.wheel>=0 || section.blend || section.mask) continue;
        bgfx::setTransform(model);
        bgfx::setVertexBuffer(0,graphics->overlay,section.first,section.count);
        bgfx::setTexture(0,liverySampler,liveryTexture,BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP);
        bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|BGFX_STATE_DEPTH_TEST_EQUAL|BGFX_STATE_BLEND_ALPHA);
        bgfx::submit(0,liveryProgram);
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
    if (flow.screen == racer::Screen::Drive && !active) {
      bgfx::dbgTextPrintf(3, 2, 0x1e, "RACER / %5.1f MPH / %s",
                          std::abs(sim.car.speed) * 2.236936,
                          sim.car.direction == 1 ? "FORWARD" : "REVERSE");
      bgfx::dbgTextPrintf(
          3, 4, 0x1f, "WASD / Arrows: drive | R: reset | ESC: pause / garage | F8: report");
      bgfx::dbgTextPrintf(3, 5, 0x1f,
                          "PAD: Stick + RT/LT: drive | Y: reset | Menu: pause");
      bgfx::dbgTextPrintf(3, 7, 0x17,
                          "Release and press brake again at rest to reverse.");
      const auto &marker=flow.career.selectedMarker();
      const double dx=marker.x-sim.car.x,dz=marker.z-sim.car.z;
      const double bearing=std::remainder(std::atan2(dx,dz)-sim.car.heading,2*3.14159265358979323846);
      bgfx::dbgTextPrintf(3,9,0x1e,"M: events / destination %s / %.0f m / %s",marker.id.c_str(),std::hypot(dx,dz),
          std::abs(bearing)<.2 ? "AHEAD" : bearing>0 ? "RIGHT" : "LEFT");
      if (!vehicles.empty()) bgfx::dbgTextPrintf(3,11,0x1f,"%s",vehicles[activeVehicle].name.c_str());
    }
    const int columns = width / 8;
    const int rows = height / 16;
    size_t longest = 0;
    for (const auto &line : panel)
      longest = std::max(longest, line.size());
    const int panelWidth = std::min(columns - 6, int(longest) + 2);
    // Active controls stay at the foot of the screen, away from the horizon.
    for (size_t row = 0; row < panel.size(); ++row) {
      int y = 2 + int(row);
      if (active && row >= 6)
        y = rows - int(panel.size() - row) - 1;
      const auto &line = panel[row];
      uint8_t color = row == 0 ? 0x1e : 0x1f;
      if (line.starts_with("> "))
        color = 0x71;
      else if (line.starts_with("INVALID") || line.starts_with("UNSAVED") ||
               line.starts_with("Malformed"))
        color = 0x4f;
      else if (line.starts_with("DRAFT NOT"))
        color = 0x6f;
      else if (line.starts_with("MEASUREMENT:") ||
               line.starts_with("NEXT GATE") || line.starts_with("NEW BEST"))
        color = 0x2f;
      bgfx::dbgTextPrintf(3, uint16_t(y), color, "%*s", panelWidth, "");
      bgfx::dbgTextPrintf(3, uint16_t(y), color, "%s", line.c_str());
    }
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
    if (!shot.empty() && !captured && elapsed > (verify ? 2.5 : 2)) {
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
  bgfx::destroy(program);
  bgfx::destroy(liveryProgram);
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
