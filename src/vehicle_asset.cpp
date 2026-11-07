#include "vehicle_asset.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <set>
#include <sstream>
#include <CommonCrypto/CommonDigest.h>
#include <cerrno>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
namespace racer {
namespace {
[[noreturn]] void fail(const char *code) { throw MeshAssetError(code); }
std::string read(const std::filesystem::path &path,size_t limit) {
  const int fd=::open(path.c_str(),O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
  if (fd<0) fail("vehicle_descriptor_not_regular");
  struct Close {int fd;~Close(){::close(fd);}} close{fd};
  struct stat before{},after{};
  if (::fstat(fd,&before)!=0 || !S_ISREG(before.st_mode)) fail("vehicle_descriptor_not_regular");
  if (before.st_size<0 || uint64_t(before.st_size)>limit) fail("vehicle_descriptor_budget");
  std::string text(size_t(before.st_size),'\0');size_t offset=0;
  while (offset<text.size()) {
    const auto count=::read(fd,text.data()+offset,text.size()-offset);
    if (count<0 && errno==EINTR) continue;
    if (count<=0) fail("vehicle_descriptor_read");
    offset+=size_t(count);
  }
  char extra;
  if (::read(fd,&extra,1)!=0 || ::fstat(fd,&after)!=0 || before.st_size!=after.st_size ||
      before.st_mtimespec.tv_sec!=after.st_mtimespec.tv_sec || before.st_mtimespec.tv_nsec!=after.st_mtimespec.tv_nsec)
    fail("vehicle_descriptor_read");
  return text;
}
void word(std::istream &in,const char *expected) {
  std::string token;if (!(in>>token) || token!=expected) fail("vehicle_descriptor_schema");
}
bool hash(const std::string &value) {
  return value.size()==64 && std::all_of(value.begin(),value.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');});
}
std::filesystem::path relative(const std::filesystem::path &parent,const std::string &file) {
  const std::filesystem::path path(file);
  if (file.empty() || file.size()>128 || path.has_parent_path() || path.is_absolute() || file.find('\\')!=std::string::npos)
    fail("vehicle_descriptor_path");
  return parent/path;
}
void point(std::istream &in,GeometryPoint &p) {
  if (!(in>>p.x>>p.y>>p.z)) fail("vehicle_descriptor_geometry");
}
}
VehicleDefinition readVehicleDefinition(const std::filesystem::path &path,AssetDigest *descriptorDigest) {
  if (descriptorDigest) *descriptorDigest={};
  const auto bytes=read(path,32768);
  const auto digest=assetBytesDigest(bytes);
  if (descriptorDigest) *descriptorDigest=digest;
  std::istringstream in(bytes);
  word(in,"RACER_VEHICLE");int version=0;
  if (!(in>>version) || (version!=1 && version!=2)) fail("vehicle_descriptor_version");
  VehicleDefinition v;v.descriptorSHA256=digest;std::string file;
  word(in,"id");in>>std::quoted(v.id);word(in,"name");in>>std::quoted(v.name);
  word(in,"mesh");in>>std::quoted(file);v.mesh=relative(path.parent_path(),file);
  word(in,"sha256");in>>v.sha256;word(in,"source_sha256");in>>v.sourceSHA256;
  if (!hash(v.sha256) || !hash(v.sourceSHA256) || v.id!="vehicle-"+v.sha256 ||
      v.name.empty() || v.name.size()>96 || v.name.find_first_of("\r\n\t")!=std::string::npos) fail("vehicle_descriptor_identity");
  word(in,"body");point(in,v.geometry.body.minimum);point(in,v.geometry.body.maximum);
  const char *names[]={"FL","FR","RL","RR"};
  for (size_t i=0;i<4;++i) {
    word(in,"wheel");word(in,names[i]);
    auto &w=v.geometry.wheels[i];point(in,w.center);
    if (!(in>>w.radius>>w.width)) fail("vehicle_descriptor_geometry");
  }
  if (!v.geometry.valid() || v.geometry.wheelbase()<.5 || v.geometry.wheelbase()>20 ||
      v.geometry.body.maximum.x-v.geometry.body.minimum.x>10 ||
      v.geometry.body.maximum.z-v.geometry.body.minimum.z>30 || v.geometry.body.maximum.y>10)
    fail("vehicle_descriptor_geometry");
  word(in,"groups");size_t count=0;
  if (!(in>>count) || !count || count>4096) fail("vehicle_descriptor_groups");
  std::set<uint32_t> nodes;
  for (size_t i=0;i<count;++i) {
    word(in,"group");MeshNodeBinding binding;
    if (!(in>>binding.node)) fail("vehicle_descriptor_group");
    if (version==1) {
      if (!(in>>binding.wheel)) fail("vehicle_descriptor_group");
    } else {
      std::string role;if (!(in>>role)) fail("vehicle_descriptor_group");
      if (role=="body") binding.wheel=-1;
      else if (role=="wheel" || role=="carrier") {
        std::string label;if (!(in>>label)) fail("vehicle_descriptor_group");
        const auto found=std::find(std::begin(names),std::end(names),label);
        if (found==std::end(names)) fail("vehicle_descriptor_group");
        binding.wheel=int(found-std::begin(names));binding.rolling=role=="wheel";
      } else fail("vehicle_descriptor_group");
    }
    if (binding.node>=4096 || binding.wheel< -1 || binding.wheel>3 ||
        !nodes.insert(binding.node).second) fail("vehicle_descriptor_group");
    if (binding.wheel>=0) {
      const auto &p=v.geometry.wheels[size_t(binding.wheel)].center;
      binding.pivot={float(p.x),float(p.y),float(p.z)};
    }
    v.bindings.push_back(binding);
  }
  in>>std::ws;if (!in.eof()) fail("vehicle_descriptor_trailing");
  return v;
}
std::vector<VehicleDefinition> readVehicleLibrary(const std::filesystem::path &path,VehicleLibraryLoadContext *context) {
  VehicleLibraryLoadContext local;
  auto &trace=context ? *context : local;
  trace={};
  const auto bytes=read(path,256*1024);
  trace.librarySHA256=assetBytesDigest(bytes);
  std::istringstream in(bytes);word(in,"RACER_VEHICLES");int version=0;size_t count=0;
  if (!(in>>version>>count) || version!=1 || !count || count>4096) fail("vehicle_library_schema");
  std::vector<VehicleDefinition> result;std::set<std::string> ids;
  for (size_t i=0;i<count;++i) {
    trace.descriptorIndex=int(i);trace.descriptorSHA256={};
    std::string file;if (!(in>>std::quoted(file))) fail("vehicle_library_entry");
    auto v=readVehicleDefinition(relative(path.parent_path(),file),&trace.descriptorSHA256);
    if (!ids.insert(v.id).second) fail("vehicle_library_duplicate");
    result.push_back(std::move(v));
    trace.descriptorIndex=-1;trace.descriptorSHA256={};
  }
  in>>std::ws;if (!in.eof()) fail("vehicle_library_trailing");
  return result;
}
MeshAsset loadVehicleAsset(const VehicleDefinition &v,AssetLoadContext *context) {
  AssetLoadContext local;
  auto &trace=context ? *context : local;
  trace={};trace.stage=AssetLoadStage::Definition;
  trace.expectedMeshSHA256=assetDigestFromHex(v.sha256);
  trace.sourceSHA256=assetDigestFromHex(v.sourceSHA256);
  trace.descriptorSHA256=assetDigestFromHex({v.descriptorSHA256.data(),64});
  if (!v.geometry.valid() || !hash(v.sha256) || v.bindings.empty()) fail("vehicle_definition_invalid");
  auto asset=loadMeshAsset(v.mesh,v.bindings,&trace);
  trace.stage=AssetLoadStage::Identity;
  if (asset.sourceSHA256!=v.sha256) fail("vehicle_mesh_hash");
  trace.stage=AssetLoadStage::Containment;
  std::array<bool,4> wheels{};bool body=false;
  for (const auto &section:asset.sections) {
    if (section.wheel<0) body=true;
    else if (section.rolling) wheels[size_t(section.wheel)]=true;
    for (size_t i=section.first;i<section.first+section.count;++i) {
      const auto &p=asset.triangles[i];
      if (section.wheel<0) {
        const auto &b=v.geometry.body;
        if (p.x<b.minimum.x-.002 || p.x>b.maximum.x+.002 || p.y<b.minimum.y-.002 || p.y>b.maximum.y+.002 ||
            p.z<b.minimum.z-.002 || p.z>b.maximum.z+.002) fail("vehicle_body_containment");
      } else {
        const auto &w=v.geometry.wheels[size_t(section.wheel)];
        if (std::abs(p.x)>w.width/2+.002 || std::hypot(p.y,p.z)>w.radius+.002) fail("vehicle_wheel_containment");
      }
    }
  }
  if (!body || std::find(wheels.begin(),wheels.end(),false)!=wheels.end()) fail("vehicle_incomplete_sections");
  trace.stage=AssetLoadStage::Complete;
  return asset;
}
std::string vehiclePhysicsIdentity(const VehicleDefinition &v) {
  if (!v.geometry.valid() || !hash(v.sha256)) fail("vehicle_definition_invalid");
  std::ostringstream text;text<<std::setprecision(17)<<"racer-vehicle-physics-2 "<<v.sha256;
  const auto point=[&](GeometryPoint p){text<<' '<<p.x<<' '<<p.y<<' '<<p.z;};
  point(v.geometry.body.minimum);point(v.geometry.body.maximum);
  for (const auto &wheel:v.geometry.wheels) {point(wheel.center);text<<' '<<wheel.radius<<' '<<wheel.width;}
  const auto input=text.str();unsigned char digest[CC_SHA256_DIGEST_LENGTH];CC_SHA256(input.data(),CC_LONG(input.size()),digest);
  std::string result="vehicle-";constexpr char hex[]="0123456789abcdef";
  for (auto value:digest) {result+=hex[value>>4];result+=hex[value&15];}
  return result;
}
}
