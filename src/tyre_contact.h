#pragma once
#include <algorithm>
#include <cmath>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>
#include "mesh_asset.h"
#include "setup.h"
#include "vehicle_geometry.h"

namespace racer {
namespace tyrePhysics {
struct Forces {
  double longitudinal = 0, lateral = 0, aligningMoment = 0, capacity = 0;
};

// A transient, combined-slip brush approximation, NOT a fitted Pacejka tyre.
// Slip ratio = (omega * radius - longitudinal speed) / regularized speed.
// lateralSlip = lateral speed / regularized speed, i.e. tan(slip angle).
// Both denominators use |longitudinal speed|, so reverse motion keeps the
// correct dissipative force signs. See the force-element tyre discussion at
// https://api.projectchrono.org/development/wheeled_tire.html and low-speed
// slip regularization in the PhysX Vehicle SDK. Parameters require tyre data
// before a specific real-world car can be considered calibrated.
inline double frictionCapacity(const TyreParameters &p, double normalLoad,
                               double surfaceGrip) {
  if (!std::isfinite(normalLoad) || !std::isfinite(surfaceGrip) ||
      normalLoad <= 0 || surfaceGrip <= 0 || !p.valid())
    return 0;
  // Grip coefficient falls as normal load rises. Bound the extrapolation
  // outside the measured-load region rather than promising infinite mu at
  // zero load. Clamping load here is only an arithmetic overflow guard.
  const double load = std::min(normalLoad, 1e9);
  const double ratio = std::clamp(load / p.referenceLoad, .05, 20.0);
  return load * p.friction * std::min(surfaceGrip, 4.0) *
         std::pow(ratio, -p.loadSensitivity);
}

inline Forces evaluate(const TyreParameters &p, double normalLoad,
                       double surfaceGrip, double slipRatio, double lateralSlip,
                       double camber = 0) {
  Forces result;
  result.capacity = frictionCapacity(p, normalLoad, surfaceGrip);
  if (!(result.capacity > 0) || !std::isfinite(slipRatio) ||
      !std::isfinite(lateralSlip) || !std::isfinite(camber))
    return result;
  const double loadScale = std::pow(
      std::clamp(normalLoad / p.referenceLoad, .000001, 100.0), .8);
  const double sx = p.longitudinalStiffness * loadScale *
                    std::clamp(slipRatio, -1000.0, 1000.0);
  const double sy = loadScale *
      (-p.corneringStiffness * std::clamp(lateralSlip, -1000.0, 1000.0) +
       p.camberStiffness * std::clamp(camber, -.5, .5));
  const double demand = std::hypot(sx, sy);
  if (demand < 1e-12)
    return result;
  const double q = demand / (3 * result.capacity);
  double magnitude;
  if (q < 1) {
    // The brush saturates smoothly at mu * load; initial slope is the chosen
    // stiffness. Sharing this one budget prevents full braking PLUS full
    // cornering from generating more friction than the contact can provide.
    magnitude = demand * (1 - q + q * q / 3);
  } else {
    // Progressive breakaway toward kinetic friction, with a zero derivative
    // at the adhesion peak. This is a deliberately generic road-tyre shape.
    const double sliding = std::min(q - 1, 100.0);
    magnitude = result.capacity *
                (p.slidingFrictionRatio +
                 (1 - p.slidingFrictionRatio) / (1 + sliding * sliding));
  }
  result.longitudinal = sx * (magnitude / demand);
  result.lateral = sy * (magnitude / demand);
  // The effective pneumatic trail collapses as the contact patch slides.
  // Positive lateral force at the trailing patch makes a negative yaw moment.
  const double trail = p.pneumaticTrail * std::pow(std::max(0.0, 1 - q), 2);
  result.aligningMoment = -result.lateral * trail;
  return result;
}

// Exact exponential update of the first-order relaxation equation. The
// half-metre-per-second transport floor prevents a frozen tyre deformation
// at rest. The wheel solver supplies its own static friction constraint.
inline double relaxSlip(double previous, double target, double transportSpeed,
                        double relaxationLength, double dt) {
  if (!std::isfinite(previous) || !std::isfinite(target) ||
      !std::isfinite(transportSpeed) || !std::isfinite(relaxationLength) ||
      !std::isfinite(dt) || relaxationLength <= 0 || dt <= 0)
    return std::isfinite(previous) ? previous : 0;
  const double rate = std::max(.5, std::abs(transportSpeed)) / relaxationLength;
  return previous + (target - previous) * -std::expm1(-rate * dt);
}
} // namespace tyrePhysics

namespace tyreMeshDetail {
inline void requireRange(std::size_t first, std::size_t count, std::size_t size) {
  if (first > size || count > size - first)
    throw std::invalid_argument("tyre mesh section outside vertex array");
}
}
// Furthest reach from the axle (wheel-local Y/Z; meshes are pivot-centred with the
// axle along X) of the rolling sections of one wheel. Zero when the wheel has none.
inline float tyreRadialReach(const MeshAsset &asset, int wheel) {
  float reach = 0;
  for (const auto &section : asset.sections) {
    if (section.wheel != wheel || !section.rolling)
      continue;
    tyreMeshDetail::requireRange(section.first, section.count, asset.triangles.size());
    for (std::uint32_t i = 0; i < section.count; ++i) {
      const auto &v = asset.triangles[section.first + i];
      if (std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z))
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
  if (!std::isfinite(reach) || reach <= 0)
    return rim;
  for (const auto &section : asset.sections) {
    if (section.wheel != wheel || !section.rolling)
      continue;
    tyreMeshDetail::requireRange(section.first, section.count, asset.triangles.size());
    for (std::uint32_t i = 0; i < section.count; ++i) {
      const auto &v = asset.triangles[section.first + i];
      if (std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z) &&
          std::hypot(v.y, v.z) >= .9f * reach)
        rim.push_back({v.x, v.y, v.z});
    }
  }
  return rim;
}
// Lowest world/local Y of a wheel's rim vertices under a column-major wheel matrix
// (as produced by wheelRenderTransform, optionally with the body frame applied
// first). Tyre meshes are faceted, so this depends on the current spin; using it
// each time a wheel is placed makes the lowest tyre point touch the ground exactly.
// This is a render-only correction: never feed the faceted mesh radius into
// suspension/tyre forces. Empty data returns infinity, i.e. no support point.
inline float tyreLowestY(const std::vector<std::array<float, 3>> &rim, const float *m) {
  float lowest = std::numeric_limits<float>::infinity();
  if (!m)
    return lowest;
  for (const auto &v : rim)
    lowest = std::min(lowest, m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13]);
  return lowest;
}
// Signed distance of the lowest rim vertex (wheel matrix m, column-major) from the
// tangent plane through `point` with unit `normal`; negative means below the road.
// The renderer moves the wheel by -result * normal so the tyre touches the road
// exactly, on slopes as well as on the flat (where it equals tyreLowestY).
inline double tyreLowestAlongNormal(const std::vector<std::array<float, 3>> &rim, const float *m,
                                    const GeometryPoint &normal, const GeometryPoint &point) {
  double lowest = std::numeric_limits<double>::infinity();
  if (!m)
    return lowest;
  for (const auto &v : rim) {
    const double px = m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12];
    const double py = m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13];
    const double pz = m[2] * v[0] + m[6] * v[1] + m[10] * v[2] + m[14];
    lowest = std::min(lowest, normal.x * (px - point.x) + normal.y * (py - point.y) +
                                  normal.z * (pz - point.z));
  }
  return lowest;
}
} // namespace racer
