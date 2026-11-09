#include "vehicle_geometry.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <stdexcept>

namespace racer {
namespace {
bool finite(GeometryPoint p) {
  return std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z);
}
void require(bool condition) {
  if (!condition) throw std::invalid_argument("invalid vehicle geometry or pose");
}
}
double VehicleGeometry::wheelbase() const {
  return (wheels[0].center.z + wheels[1].center.z -
          wheels[2].center.z - wheels[3].center.z) / 2;
}
double VehicleGeometry::frontTrack() const { return wheels[1].center.x - wheels[0].center.x; }
double VehicleGeometry::rearTrack() const { return wheels[3].center.x - wheels[2].center.x; }
bool VehicleGeometry::valid(std::string *reason) const {
  auto fail = [&](const char *message) { if (reason) *reason = message; return false; };
  if (!finite(body.minimum) || !finite(body.maximum) ||
      body.minimum.x >= body.maximum.x || body.minimum.y >= body.maximum.y ||
      body.minimum.z >= body.maximum.z || body.minimum.y < 0)
    return fail("body bounds must be finite, ordered and above ground");
  for (const auto &wheel : wheels) {
    if (!finite(wheel.center) || !std::isfinite(wheel.radius) ||
        !std::isfinite(wheel.width) || wheel.radius <= 0 || wheel.width <= 0 ||
        wheel.center.y + 1e-6 < wheel.radius)
      return fail("wheel dimensions must be finite and positive, with tires above ground");
    if (wheel.center.z < body.minimum.z || wheel.center.z > body.maximum.z)
      return fail("axle center must lie within body length");
  }
  for (std::size_t left : {0u, 2u}) {
    const auto &a = wheels[left]; const auto &b = wheels[left + 1];
    if (a.center.x >= 0 || b.center.x <= 0 ||
        std::abs(a.center.z - b.center.z) > 1e-4 ||
        std::abs(a.center.y - b.center.y) > 1e-4 ||
        std::abs(a.radius - b.radius) > 1e-4)
      return fail("wheel order or paired axle alignment is invalid");
  }
  if (!std::isfinite(wheelbase()) || wheelbase() <= 0 ||
      !std::isfinite(frontTrack()) || !std::isfinite(rearTrack()))
    return fail("front axle must be ahead of rear axle");
  const auto envelope = collisionBounds();
  if (!finite(envelope.minimum) || !finite(envelope.maximum))
    return fail("collision envelope overflow");
  if (reason) reason->clear();
  return true;
}
GeometryBounds VehicleGeometry::collisionBounds() const {
  auto result = body;
  for (const auto &wheel : wheels) {
    // A cylinder's horizontal support over every steering angle is bounded by
    // hypot(half-width, radius). Includes rear tires conservatively as well.
    const double sweep = std::hypot(wheel.width / 2, wheel.radius);
    result.minimum.x = std::min(result.minimum.x, wheel.center.x - sweep);
    result.maximum.x = std::max(result.maximum.x, wheel.center.x + sweep);
    result.minimum.z = std::min(result.minimum.z, wheel.center.z - sweep);
    result.maximum.z = std::max(result.maximum.z, wheel.center.z + sweep);
    result.minimum.y = std::min(result.minimum.y, wheel.center.y - wheel.radius);
    result.maximum.y = std::max(result.maximum.y, wheel.center.y + wheel.radius);
  }
  return result;
}
BoundaryClearance orientedBoundaryClearance(const VehicleGeometry &geometry,
                                            double heading, double halfWorld) {
  require(geometry.valid() && std::isfinite(heading) &&
          std::isfinite(halfWorld) && halfWorld > 0);
  const auto bounds = geometry.collisionBounds();
  double minX = std::numeric_limits<double>::infinity(), minZ = minX;
  double maxX = -minX, maxZ = -minX;
  const double c = std::cos(heading), s = std::sin(heading);
  for (double x : {bounds.minimum.x, bounds.maximum.x})
    for (double z : {bounds.minimum.z, bounds.maximum.z}) {
      const double px = c*x + s*z, pz = -s*x + c*z;
      minX = std::min(minX, px); maxX = std::max(maxX, px);
      minZ = std::min(minZ, pz); maxZ = std::max(maxZ, pz);
    }
  BoundaryClearance result{-halfWorld-minX, halfWorld-maxX,
                           -halfWorld-minZ, halfWorld-maxZ};
  require(std::isfinite(result.minX) && std::isfinite(result.maxX) &&
          std::isfinite(result.minZ) && std::isfinite(result.maxZ) &&
          result.minX <= result.maxX && result.minZ <= result.maxZ);
  return result;
}
bool clampVehicleToBoundary(const VehicleGeometry &geometry, double heading,
                            double &x, double &z, double halfWorld) {
  require(std::isfinite(x) && std::isfinite(z));
  const auto range = orientedBoundaryClearance(geometry, heading, halfWorld);
  const double nextX = std::clamp(x, range.minX, range.maxX);
  const double nextZ = std::clamp(z, range.minZ, range.maxZ);
  const bool contact = nextX != x || nextZ != z;
  x = nextX; z = nextZ;
  return contact;
}
double wheelSteeringAngle(const VehicleGeometry &geometry, std::size_t wheel,
                          double centralAngle, double ackermann) {
  require(geometry.valid() && wheel < geometry.wheels.size() &&
          std::isfinite(centralAngle) && std::abs(centralAngle) < std::numbers::pi / 2 &&
          std::isfinite(ackermann) && ackermann >= 0 && ackermann <= 1);
  if (wheel >= 2 || centralAngle == 0 || ackermann == 0)
    return wheel < 2 ? centralAngle : 0;
  const double tangent = std::tan(centralAngle);
  const double midpoint = (geometry.wheels[0].center.x + geometry.wheels[1].center.x) * .5;
  const double offset = geometry.wheels[wheel].center.x - midpoint;
  // atan2 avoids cancellation and a division by zero at very tight lock.
  const double individual = std::atan2(tangent, 1 - tangent * offset / geometry.wheelbase());
  return centralAngle + ackermann * (individual - centralAngle);
}
void wheelRenderTransform(float *m, const VehicleGeometry &geometry, std::size_t wheel,
                          double heading, double x, double z, double steering,
                          double spin, bool rolling) {
  require(m && geometry.valid() && wheel < geometry.wheels.size() &&
          std::isfinite(heading) && std::isfinite(x) && std::isfinite(z) &&
          std::isfinite(steering) && std::isfinite(spin));
  if (!rolling) spin=0;
  const double yaw = heading + wheelSteeringAngle(geometry, wheel, steering);
  require(std::isfinite(yaw));
  const double c = std::cos(yaw), s = std::sin(yaw);
  const double cp = std::cos(spin), sp = std::sin(spin);
  // R_y(heading + steering) * R_x(spin), followed by the unsteered wheel center.
  const auto p = geometry.wheels[wheel].center;
  const double ch = std::cos(heading), sh = std::sin(heading);
  const std::array<double,16> values{{c,0,-s,0, s*sp,cp,c*sp,0,
      s*cp,-sp,c*cp,0, x+ch*p.x+sh*p.z,p.y,z-sh*p.x+ch*p.z,1}};
  for (double value : values)
    require(std::isfinite(value) && std::abs(value) <= std::numeric_limits<float>::max());
  for (std::size_t i = 0; i < values.size(); ++i) m[i] = float(values[i]);
}
double wheelSpinAfterTravel(double angle, double signedDistance, double radius) {
  require(std::isfinite(angle) && std::isfinite(signedDistance) &&
          std::isfinite(radius) && radius > 0);
  const double delta = signedDistance / radius;
  require(std::isfinite(delta));
  constexpr double turn = 2 * std::numbers::pi;
  return std::remainder(std::remainder(angle, turn) + std::remainder(delta, turn), turn);
}
GeometryPoint normalizeVehiclePoint(GeometryPoint point, GeometryPoint pivot,
                                    double metersPerUnit) {
  require(finite(point) && finite(pivot) && std::isfinite(metersPerUnit) && metersPerUnit > 0);
  GeometryPoint result{(point.x-pivot.x)*metersPerUnit,
                       (point.y-pivot.y)*metersPerUnit,
                       (point.z-pivot.z)*metersPerUnit};
  require(finite(result));
  return result;
}
} // namespace racer
