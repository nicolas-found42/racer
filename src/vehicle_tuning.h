#pragma once
#include "setup.h"
#include "vehicle_geometry.h"
#include <algorithm>
#include <cmath>
namespace racer {
// The generic road-car suspension (VehicleDynamics defaults) allows 12 cm of
// wheel compression. Measured cars sit as low as 8.6 cm above the road, so the
// body would hit the road before the bump stop acts: braking dive and cornering
// load transfer both use up the travel. A lowered car gets less travel (60% of
// its static body clearance) and, as real lowered cars do, proportionally
// stiffer springs and anti-roll bars, so the same load transfer deflects it
// about the same fraction of its travel; damping scales with the square root of
// the spring rate to keep the damping ratio. Still uncalibrated generic data.
inline VehicleDynamics dynamicsFor(const VehicleGeometry &geometry) {
  VehicleDynamics dynamics;
  const double travel = std::max(.02, .6 * geometry.body.minimum.y);
  for (AxleSuspension *axle : {&dynamics.frontSuspension, &dynamics.rearSuspension}) {
    if (travel >= axle->compressionTravel) continue;
    const double stiffer = axle->compressionTravel / travel;
    axle->compressionTravel = travel;
    axle->springRate *= stiffer;
    axle->antiRollRate *= stiffer;
    axle->bumpDamping *= std::sqrt(stiffer);
    axle->reboundDamping *= std::sqrt(stiffer);
  }
  return dynamics;
}
} // namespace racer
