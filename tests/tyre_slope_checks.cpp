// Tyre-to-road contact on a 12 degree slope, for every library vehicle's real
// tyre meshes, at several headings, using the renderer's own rule: take the
// simulation's dynamic wheel transform and slide it along the contact normal by
// tyreLowestAlongNormal. An independent test then sends EVERY vertex of the
// wheel's rolling meshes through the shifted matrix and measures the distance
// to the analytic slope plane: the lowest tyre point must lie on the road.
#include "simulation.h"
#include "surface_follow.h"
#include "tyre_contact.h"
#include "vehicle_asset.h"
#include "vehicle_tuning.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

int main() {
  using namespace racer;
  const std::filesystem::path library = RACER_VEHICLE_LIBRARY;
  if (!std::filesystem::exists(library)) {
    std::cout << "SKIP: vehicle library not present\n";
    return 77;
  }
  constexpr double pi = 3.14159265358979323846, tolerance = 2e-4; // 0.2 mm
  const double slope = std::tan(12 * pi / 180), norm = std::sqrt(1 + slope * slope);
  const GeometryPoint planeNormal{0, 1 / norm, -slope / norm};
  // One wide inclined plane: y = slope * z.
  MeshAsset plane;
  auto v = [&](double x, double z) { return AssetVertex{float(x), float(slope * z), float(z), 0xffffffff}; };
  plane.triangles = {v(-240, -240), v(-240, 240), v(240, 240), v(-240, -240), v(240, 240), v(240, -240)};
  AssetSection section;
  section.count = 6;
  plane.sections.push_back(section);
  surfaceFollow::SurfaceIndex::Builder builder;
  builder.add(plane, surfaceFollow::identity);
  const auto index = std::make_shared<const surfaceFollow::SurfaceIndex>(builder.finish());

  const auto vehicles = readVehicleLibrary(library);
  if (vehicles.empty()) throw std::runtime_error("empty vehicle library");
  double worst = 0, largestShift = 0;
  int wheelsChecked = 0;
  for (const auto &vehicle : vehicles) {
    const auto asset = loadVehicleAsset(vehicle);
    std::array<std::vector<std::array<float, 3>>, 4> rim;
    for (int w = 0; w < 4; ++w) rim[size_t(w)] = tyreRimVertices(asset, w, tyreRadialReach(asset, w));
    for (const double degrees : {0., 35., -35., 90.}) {
      Simulation sim;
      sim.setRoadSampler(surfaceFollow::makeRoadSampler(index));
      if (!sim.setGeometry(vehicle.geometry) || !sim.setDynamics(dynamicsFor(vehicle.geometry)))
        throw std::runtime_error(vehicle.id + ": geometry rejected");
      sim.car.heading = degrees * pi / 180;
      // Same placement the application uses after a teleport onto a slope.
      const auto pose = surfaceFollow::restingPose(*index, vehicle.geometry, sim.car.heading, 0, 0, 0);
      if (!pose) throw std::runtime_error(vehicle.id + ": no resting pose on the slope");
      sim.car.y = pose->y;
      sim.car.pitch = pose->pitch;
      sim.car.roll = pose->roll;
      sim.tick({}, 0);
      for (int i = 0; i < 600; ++i) sim.tick({0, .6, 0}); // hold on the slope
      for (size_t w = 0; w < 4; ++w) {
        const auto &state = sim.car.wheels[w];
        if (!state.grounded)
          throw std::runtime_error(vehicle.id + " wheel " + std::to_string(w) + " heading " +
                                   std::to_string(int(degrees)) + ": not on the slope (z " +
                                   std::to_string(sim.car.z) + ", y " + std::to_string(sim.car.y) +
                                   ", speed " + std::to_string(sim.groundSpeed()) + ", compression " +
                                   std::to_string(state.compression) + ", roll " + std::to_string(sim.car.roll) +
                                   ", pitch " + std::to_string(sim.car.pitch) + ")");
        auto m = sim.wheelTransform(w, true);
        const double lowestRim = tyreLowestAlongNormal(rim[w], m.data(), state.contactNormal, state.contactPoint);
        m[12] -= float(lowestRim * state.contactNormal.x);
        m[13] -= float(lowestRim * state.contactNormal.y);
        m[14] -= float(lowestRim * state.contactNormal.z);
        double lowest = std::numeric_limits<double>::infinity();
        for (const auto &section : asset.sections) {
          if (section.wheel != int(w) || !section.rolling) continue;
          for (uint32_t i = 0; i < section.count; ++i) {
            const auto &p = asset.triangles[section.first + i];
            const double x = m[0] * p.x + m[4] * p.y + m[8] * p.z + m[12];
            const double y = m[1] * p.x + m[5] * p.y + m[9] * p.z + m[13];
            const double z = m[2] * p.x + m[6] * p.y + m[10] * p.z + m[14];
            lowest = std::min(lowest, planeNormal.x * x + planeNormal.y * y + planeNormal.z * z);
          }
        }
        largestShift = std::max(largestShift, std::abs(lowestRim));
        worst = std::max(worst, std::abs(lowest));
        ++wheelsChecked;
        if (std::abs(lowest) > tolerance)
          throw std::runtime_error(vehicle.id + " wheel " + std::to_string(w) + " heading " +
                                   std::to_string(int(degrees)) + ": lowest tyre point " +
                                   std::to_string(lowest * 1000) + " mm from the slope");
        if (std::abs(lowestRim) > .02)
          throw std::runtime_error(vehicle.id + " wheel " + std::to_string(w) + ": physics and mesh disagree by " +
                                   std::to_string(lowestRim * 1000) + " mm");
      }
    }
  }
  std::cout << "tyre_slope_checks ok: " << vehicles.size() << " vehicles, " << wheelsChecked
            << " wheel placements on a 12 degree slope at 4 headings; worst |lowest tyre point - road| "
            << worst * 1000 << " mm, largest renderer shift " << largestShift * 1000 << " mm\n";
}
