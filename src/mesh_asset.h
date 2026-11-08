#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>
namespace racer {
// Diagnostic-only state: no allocation, source paths or input contents. Empty
// digests mean unavailable; actualMeshSHA256 hashes the complete bounded read.
using AssetDigest = std::array<char,65>;
enum class AssetLoadStage { Definition, Open, Read, Parse, Buffers, Validation,
  Geometry, Images, Identity, Containment, Upload, Physics, Complete };
struct AssetLoadContext {
  AssetLoadStage stage=AssetLoadStage::Open;
  AssetDigest actualMeshSHA256{},expectedMeshSHA256{},descriptorSHA256{},sourceSHA256{};
  size_t inputBytes=0;
};
AssetDigest assetBytesDigest(std::string_view bytes) noexcept;
AssetDigest assetDigestFromHex(std::string_view hex) noexcept;
const char *assetLoadStageName(AssetLoadStage stage) noexcept;
const char *assetInputIdentity(const AssetLoadContext &context) noexcept;
struct AssetVertex { float x,y,z; std::uint32_t color; float u = 0, v = 0; float nx=0,ny=1,nz=0,occlusion=1,opacity=1; float tx=0,ty=0,tz=0,tw=0; };
enum class ImageRole { Color, Normal, PackedHeightSpec };
inline bool validImageRole(ImageRole role) noexcept {
  return role==ImageRole::Color||role==ImageRole::Normal||role==ImageRole::PackedHeightSpec;
}
struct AssetImage { unsigned width=0,height=0;std::vector<uint8_t> rgba;ImageRole role=ImageRole::Color; };
struct AssetSection { uint32_t first=0,count=0;int image=-1;bool blend=false;int wrapU=10497,wrapV=10497;bool mask=false;float alphaCutoff=.5f;int wheel=-1;bool rolling=true; float roughness=1,metallic=0,clearcoat=0,coatRoughness=.1f; int normalImage=-1,normalWrapU=10497,normalWrapV=10497;float normalScale=1; bool sourceBump=false;
  float detailMode() const noexcept { return normalImage<0?0.f:sourceBump?2.f:1.f; }
};
// Carriers (e.g. brake calipers) follow axle steering but do not roll.
struct MeshNodeBinding { uint32_t node=0;int wheel=-1;std::array<float,3> pivot{};bool rolling=true; };
struct MeshAsset {
  std::vector<AssetVertex> triangles;
  std::vector<AssetImage> images;
  std::vector<AssetSection> sections;
  std::array<float,3> minimum{}, maximum{};
  bool texturesPresent = false;
  std::string sourceSHA256;
};
class MeshAssetError : public std::runtime_error {
public:
  using std::runtime_error::runtime_error;
};
// Embedded-buffer glTF/GLB inspection lane. Throws a fixed diagnostic reason
// on invalid/unsupported data; never follows external buffer/image paths.
// Static triangles/transforms/normals/base colors/UVs, scalar finish factors,
// optional _RACER_OCCLUSION, embedded PNG base-color/normal maps and the
// optional RACER_source_bump_spec normal-only custom path. Other texture
// channels, skins and animations remain unsupported.
// Resets read/actual-input state, retaining caller-supplied expected identities.
MeshAsset loadMeshAsset(const std::filesystem::path &path,const std::vector<MeshNodeBinding> &bindings = {},
                        AssetLoadContext *context = nullptr);
}
