#pragma once
#include "mesh_asset.h"
#include <bgfx/bgfx.h>
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace racer {
// Base-color mip filtering in linear light. Alpha is coverage, not gamma RGB.
inline AssetImage colorMip(const AssetImage& image) {
  if(!image.width||!image.height||image.width>2048||image.height>2048||
     uint64_t(image.width)*image.height*4!=image.rgba.size()) throw std::invalid_argument("texture_mip_input");
  AssetImage result{std::max(1u,image.width/2),std::max(1u,image.height/2),{}};
  result.rgba.resize(size_t(result.width)*result.height*4);
  for(unsigned y=0;y<result.height;++y)for(unsigned x=0;x<result.width;++x)for(unsigned c=0;c<4;++c) {
    const double left=double(x)*image.width/result.width,right=double(x+1)*image.width/result.width;
    const double top=double(y)*image.height/result.height,bottom=double(y+1)*image.height/result.height;
    double sum=0;
    // Fractional box coverage includes trailing texels when a dimension is odd.
    for(unsigned sy=unsigned(top);sy<unsigned(std::ceil(bottom));++sy)
      for(unsigned sx=unsigned(left);sx<unsigned(std::ceil(right));++sx) {
      const double area=(std::min(right,double(sx+1))-std::max(left,double(sx)))*
        (std::min(bottom,double(sy+1))-std::max(top,double(sy)));
      const auto byte=image.rgba[(sy*image.width+sx)*4+c];
      const double v=byte/255.;sum+=area*(c==3?v:std::pow(v,2.2));
    }
    const double linear=sum/((right-left)*(bottom-top));
    const double mean=c==3?linear:std::pow(linear,1/2.2);
    result.rgba[(y*result.width+x)*4+c]=uint8_t(std::clamp(std::lround(mean*255),0l,255l));
  }
  return result;
}
// Standard glTF tangent-space normal RGB is linear vector data, not color.
inline AssetImage normalMip(const AssetImage& image) {
  if(!image.width||!image.height||image.width>2048||image.height>2048||
     uint64_t(image.width)*image.height*4!=image.rgba.size()) throw std::invalid_argument("texture_mip_input");
  AssetImage result{std::max(1u,image.width/2),std::max(1u,image.height/2),{},ImageRole::Normal};
  result.rgba.resize(size_t(result.width)*result.height*4);
  for(unsigned y=0;y<result.height;++y)for(unsigned x=0;x<result.width;++x) {
    const double left=double(x)*image.width/result.width,right=double(x+1)*image.width/result.width;
    const double top=double(y)*image.height/result.height,bottom=double(y+1)*image.height/result.height;
    double vector[3]{},alpha=0;
    for(unsigned sy=unsigned(top);sy<unsigned(std::ceil(bottom));++sy)
      for(unsigned sx=unsigned(left);sx<unsigned(std::ceil(right));++sx) {
        const double area=(std::min(right,double(sx+1))-std::max(left,double(sx)))*
          (std::min(bottom,double(sy+1))-std::max(top,double(sy)));
        const auto at=(sy*image.width+sx)*4;
        for(unsigned c=0;c<3;++c)vector[c]+=area*(image.rgba[at+c]/127.5-1.);
        alpha+=area*image.rgba[at+3];
      }
    const double length=std::hypot(vector[0],vector[1],vector[2]);
    if(length<1e-12){vector[0]=0;vector[1]=0;vector[2]=1;}
    else for(double& component:vector)component/=length;
    const auto at=(y*result.width+x)*4;
    for(unsigned c=0;c<3;++c)
      result.rgba[at+c]=uint8_t(std::clamp(std::lround((vector[c]+1)*127.5),0l,255l));
    result.rgba[at+3]=uint8_t(std::clamp(std::lround(alpha/((right-left)*(bottom-top))),0l,255l));
  }
  return result;
}
// Authored area-linear packed data mips preserve all four independent lanes.
// Original donor higher mip levels/filtering have not been recovered.
inline AssetImage packedMip(const AssetImage& image) {
  if(!image.width||!image.height||image.width>2048||image.height>2048||
     uint64_t(image.width)*image.height*4!=image.rgba.size())throw std::invalid_argument("texture_mip_input");
  AssetImage result{std::max(1u,image.width/2),std::max(1u,image.height/2),{},ImageRole::PackedHeightSpec};
  result.rgba.resize(size_t(result.width)*result.height*4);
  for(unsigned y=0;y<result.height;++y)for(unsigned x=0;x<result.width;++x)for(unsigned c=0;c<4;++c) {
    const double left=double(x)*image.width/result.width,right=double(x+1)*image.width/result.width;
    const double top=double(y)*image.height/result.height,bottom=double(y+1)*image.height/result.height;
    double sum=0;
    for(unsigned sy=unsigned(top);sy<unsigned(std::ceil(bottom));++sy)
      for(unsigned sx=unsigned(left);sx<unsigned(std::ceil(right));++sx) {
        const double area=(std::min(right,double(sx+1))-std::max(left,double(sx)))*
          (std::min(bottom,double(sy+1))-std::max(top,double(sy)));
        sum+=area*image.rgba[(sy*image.width+sx)*4+c];
      }
    result.rgba[(y*result.width+x)*4+c]=uint8_t(std::clamp(std::lround(sum/((right-left)*(bottom-top))),0l,255l));
  }
  return result;
}
inline bgfx::TextureHandle uploadAssetTexture(const AssetImage& image) {
  if(!validImageRole(image.role))throw std::invalid_argument("texture_upload_role");
  if(!image.width||!image.height||image.width>2048||image.height>2048||
     uint64_t(image.width)*image.height*4!=image.rgba.size()) throw std::invalid_argument("texture_upload_input");
  auto texture=bgfx::createTexture2D(uint16_t(image.width),uint16_t(image.height),true,1,bgfx::TextureFormat::RGBA8,0);
  if(!bgfx::isValid(texture))throw std::runtime_error("asset_texture_gpu_create");
  try {
    AssetImage mip;
    const AssetImage* current=&image;
    for(uint8_t level=0;;++level) {
      bgfx::updateTexture2D(texture,0,level,0,0,uint16_t(current->width),uint16_t(current->height),
        bgfx::copy(current->rgba.data(),uint32_t(current->rgba.size())));
      if(current->width==1&&current->height==1)break;
      mip=current->role==ImageRole::Normal?normalMip(*current):
        current->role==ImageRole::PackedHeightSpec?packedMip(*current):colorMip(*current);current=&mip;
    }
  } catch(...) {bgfx::destroy(texture);throw;}
  return texture;
}
}
