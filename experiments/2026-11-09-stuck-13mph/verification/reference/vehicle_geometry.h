#pragma once
#include <array>
#include <cstddef>
#include <string>
#include "world_scale.h"

namespace racer {
struct GeometryPoint { double x = 0, y = 0, z = 0; };
struct GeometryBounds { GeometryPoint minimum, maximum; };
struct WheelGeometry {
  GeometryPoint center;
  double radius = .4, width = .32;
};

// Converted model coordinates: meters, +X right, +Y up, +Z nose. Wheel meshes
// must be pivot-centered with their axle along X before wheelRenderTransform.
// These dimensions describe geometry, not recovered donor handling parameters.
struct VehicleGeometry {
  GeometryBounds body{{-.925, .3, -2.2}, {.925, 1.525, 2.2}};
  // Front-left, front-right, rear-left, rear-right (left means negative X).
  std::array<WheelGeometry, 4> wheels{{
      {{-1, .4, 1.35}}, {{1, .4, 1.35}},
      {{-1, .4, -1.35}}, {{1, .4, -1.35}}}};
  double wheelbase() const;
  double frontTrack() const;
  double rearTrack() const;
  bool valid(std::string *reason = nullptr) const;
  // Body plus each wheel's full steering sweep; conservative planar contact.
  GeometryBounds collisionBounds() const;
};

struct BoundaryClearance { double minX, maxX, minZ, maxZ; };
// Allowed position of the vehicle origin inside the 1000 m square world.
// Throws invalid_argument for invalid geometry/pose or a vehicle that cannot fit.
BoundaryClearance orientedBoundaryClearance(const VehicleGeometry &, double heading,
                                            double halfWorld = worldScale::halfExtent);
bool clampVehicleToBoundary(const VehicleGeometry &, double heading,
                            double &x, double &z, double halfWorld = worldScale::halfExtent);

// Central/bicycle road-wheel angle -> individual road-wheel angle, radians.
// Positive steer turns right, so the front-right wheel is the inner wheel.
// ackermann=0 is parallel steering, 1 is geometric Ackermann. Rear steer is zero.
// This geometric correction supplies the tyre solver AND wheel rendering;
// it does not prescribe the body's path or remove tyre slip.
double wheelSteeringAngle(const VehicleGeometry &, std::size_t wheel,
                          double centralAngle, double ackermann = 1.0);

// Column-major bgfx-compatible matrix. Positive steering turns the nose toward
// +X; steering is the central angle, corrected per wheel with full Ackermann.
// Rear wheels do not steer. Positive spin rolls forward (+Z at heading 0).
void wheelRenderTransform(float *matrix, const VehicleGeometry &, std::size_t wheel,
                          double heading, double x, double z, double steering,
                          double spin, bool rolling = true);
double wheelSpinAfterTravel(double angle, double signedDistance, double radius);
// Explicit source-space pivot and uniform unit conversion; no inferred scale.
GeometryPoint normalizeVehiclePoint(GeometryPoint point, GeometryPoint pivot,
                                    double metersPerUnit);
} // namespace racer
