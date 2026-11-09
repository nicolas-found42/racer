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
// Lowest world/local Y of a wheel's rim vertices under a column-major wheel matrix
// (as produced by wheelRenderTransform, optionally with the body frame applied
// first). Tyre meshes are faceted, so this depends on the current spin; using it
// each time a wheel is placed makes the lowest tyre point touch the ground exactly.
inline float tyreLowestY(const std::vector<std::array<float, 3>> &rim, const float *m) {
  float lowest = 1e9f;
  for (const auto &v : rim)
    lowest = std::min(lowest, m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13]);
  return lowest;
}
} // namespace racer
