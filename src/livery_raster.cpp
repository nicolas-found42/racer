#include "livery_raster.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace racer {
std::vector<uint32_t> rasterLivery(const LiveryState &state,bool transparent) {
  if (!state.valid()) throw std::invalid_argument("livery_raster_state");
  std::vector<uint32_t> pixels(liveryTextureSize*liveryTextureSize,transparent ? 0x00ffffff : 0xffffffff);
  for (const auto &layer:state.layers) {
    if (!layer.visible || !layer.transform.opacity) continue;
    if (layer.decal!="stripe" && layer.decal!="number" && layer.decal!="checker")
      throw std::invalid_argument("livery_raster_decal");
    const auto &t=layer.transform;
    const double angle=t.rotation*3.14159265358979323846/180;
    const double c=std::cos(angle),s=std::sin(angle);
    for (unsigned y=2;y<liveryTextureSize-2;++y)
      for (unsigned x=2;x<liveryTextureSize-2;++x) {
        const double dx=(x+.5)*2/liveryTextureSize-1-t.x;
        const double dy=(y+.5)*2/liveryTextureSize-1-t.y;
        const double u=(c*dx+s*dy)/t.scaleX, v=(-s*dx+c*dy)/t.scaleY;
        if (std::abs(u)>1 || std::abs(v)>1) continue;
        uint32_t paint=0;
        if (layer.decal=="stripe") {
          if (std::abs(u)>.18) continue;
          paint=0xff2828e8;
        } else if (layer.decal=="number") {
          if (!(std::abs(v+.7)<.12 && std::abs(u)<.6) &&
              !(std::abs(u-(.2-.4*v))<.13 && v>-.65 && v<.85)) continue;
          paint=0xff202020;
        } else {
          const int ix=int((u+1)*4),iy=int((v+1)*4);
          paint=(ix+iy)%2 ? 0xff202020 : 0xffffffff;
        }
        auto &pixel=pixels[y*liveryTextureSize+x];
        const double destinationAlpha=double((pixel>>24)&255)/255;
        const double alpha=t.opacity+destinationAlpha*(1-t.opacity);
        uint32_t blended=uint32_t(std::lround(alpha*255))<<24;
        for (unsigned channel=0;channel<3;++channel) {
          const auto shift=channel*8;
          const double source=(paint>>shift)&255, destination=(pixel>>shift)&255;
          blended |= uint32_t(std::lround((source*t.opacity+destination*destinationAlpha*(1-t.opacity))/alpha))<<shift;
        }
        pixel=blended;
      }
  }
  return pixels;
}
}
