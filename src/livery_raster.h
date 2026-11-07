#pragma once
#include "livery.h"
#include <vector>
namespace racer {
inline constexpr unsigned liveryTextureSize = 512;
// Authored stripe/7/checker artwork. White preserves the body's vertex color.
// Pixel (0,0) is reserved white for unpainted mesh sections. No donor artwork.
std::vector<uint32_t> rasterLivery(const LiveryState &state,bool transparent = false);
}
