#pragma once
#include "mesh_asset.h"
#include <bgfx/bgfx.h>
#include <map>
#include <memory>
#include <set>
#include <tuple>

namespace racer {
struct TextureResource {
  bgfx::TextureHandle handle=BGFX_INVALID_HANDLE;
  ~TextureResource() {if(bgfx::isValid(handle))bgfx::destroy(handle);}
  TextureResource()=default;
  TextureResource(const TextureResource&)=delete;
  TextureResource& operator=(const TextureResource&)=delete;
};
using TextureRef=std::shared_ptr<TextureResource>;
using AssetTextureUpload=bgfx::TextureHandle(*)(const AssetImage&);

inline TextureRef ownedAssetTexture(const AssetImage& image,AssetTextureUpload upload) {
  if(!upload)throw std::invalid_argument("asset_texture_uploader");
  // Allocate the owner first so an allocation failure cannot orphan a GPU handle.
  auto owner=std::make_shared<TextureResource>();owner->handle=upload(image);
  if(!bgfx::isValid(owner->handle))throw MeshAssetError("asset_texture_gpu_create");
  return owner;
}

// Static assets keep their own image indices and sampler addressing. Only the
// uploaded pixels/mip role are shared. No decoded pixel arrays stay in the pool.
class StaticTexturePool {
public:
  struct BudgetError : std::runtime_error {
    size_t used,additional,maximum;
    BudgetError(size_t u,size_t a,size_t m):std::runtime_error("static_image_budget"),used(u),additional(a),maximum(m){}
  };
  explicit StaticTexturePool(AssetTextureUpload upload,size_t maximum=64*1024*1024)
      :upload_(upload),maximum_(maximum) {
    if(!upload_)throw std::invalid_argument("asset_texture_uploader");
  }
  StaticTexturePool(const StaticTexturePool&)=delete;
  StaticTexturePool& operator=(const StaticTexturePool&)=delete;
  size_t decodedBytes() const noexcept {return bytes_;}
  size_t textureCount() const noexcept {return entries_.size();}

  std::vector<TextureRef> acquire(const std::vector<AssetImage>& images) {
    if(images.size()>128)throw std::runtime_error("static_image_count");
    std::vector<Key> keys;keys.reserve(images.size());
    std::set<Key> newKeys;size_t extra=0;
    for(const auto& image:images) {
      const auto key=identity(image);keys.push_back(key);
      if(!entries_.contains(key)&&newKeys.insert(key).second)extra+=image.rgba.size();
    }
    if(extra>maximum_-bytes_)throw BudgetError(bytes_,extra,maximum_);
    std::vector<TextureRef> result;result.reserve(images.size());
    for(size_t i=0;i<images.size();++i) {
      const auto found=entries_.find(keys[i]);
      if(found!=entries_.end()){result.push_back(found->second);continue;}
      auto owner=ownedAssetTexture(images[i],upload_);
      entries_.emplace(keys[i],owner);bytes_+=images[i].rgba.size();
      result.push_back(std::move(owner));
    }
    return result;
  }
private:
  struct Key {
    unsigned width,height;ImageRole role;AssetDigest pixels;
    bool operator<(const Key& b) const noexcept {
      return std::tie(width,height,role,pixels)<std::tie(b.width,b.height,b.role,b.pixels);
    }
  };
  static Key identity(const AssetImage& image) {
    if(!validImageRole(image.role))throw std::runtime_error("static_image_role");
    if(!image.width||!image.height||image.width>2048||image.height>2048||
       image.rgba.size()!=size_t(image.width)*image.height*4)
      throw std::runtime_error("static_image_dimensions");
    return {image.width,image.height,image.role,assetBytesDigest(
      std::string_view(reinterpret_cast<const char*>(image.rgba.data()),image.rgba.size()))};
  }
  AssetTextureUpload upload_;size_t maximum_,bytes_=0;
  std::map<Key,TextureRef> entries_;
};
}
