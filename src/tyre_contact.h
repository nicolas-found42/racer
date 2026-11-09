#pragma once
#include <algorithm>
#include <cmath>
#include <array>
#include <cstddef>
#include <vector>
#include "mesh_asset.h"
#include "vehicle_geometry.h"

namespace racer {
// Furthest reach from the axle (wheel-local Y/Z; meshes are pivot-centred with the
// axle along X) of the rolling sections of one wheel. Zero when the wheel has none.
inline float tyreRadialReach(const MeshAsset &asset, int wheel) {
  float reach = 0;
  for (const auto &section : asset.sections) {
    if (section.wheel != wheel || !section.rolling)
      continue;
    for (std::uint32_t i = 0; i < section.count; ++i) {
      const auto &v = asset.triangles[section.first + i];
      reach = std::max(reach, std::hypot(v.y, v.z));
    }
  }
  return reach;
}
// Outer-rim vertices (within 10% of the reach) of a wheel's rolling sections. The
// lowest point of a spinning pivot-centred tyre is always one of these, because
// the rim ring is far denser than the angle that would let an inner vertex win.
inline std::vector<std::array<float, 3>> tyreRimVertices(const MeshAsset &asset, int wheel,
                                                          float reach) {
  std::vector<std::array<float, 3>> rim;
  for (const auto &section : asset.sections) {
    if (section.wheel != wheel || !section.rolling)
      continue;
    for (std::uint32_t i = 0; i < section.count; ++i) {
      const auto &v = asset.triangles[section.first + i];
      if (std::hypot(v.y, v.z) >= .9f * reach)
        rim.push_back({v.x, v.y, v.z});
    }
  }
  return rim;
}
// Authored wheel centres do not always sit one tyre radius above the road: the
// real mesh reaches radialReach below its centre. Moving the wheel down by this
// amount puts the lowest tyre point exactly on the ground plane (negative lifts
// raise a tyre that would otherwise sink). Zero when the mesh gives no reach.
inline double tyreContactLift(const VehicleGeometry &geometry, std::size_t wheel,
                              float radialReach) {
  return radialReach > 0 ? geometry.wheels[wheel].center.y - double(radialReach) : 0;
}
} // namespace racer
