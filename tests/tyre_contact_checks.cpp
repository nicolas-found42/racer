// Independent tyre/ground contact check on every library vehicle. For each wheel and
// each of 64 spin angles, the production lift (lowest rim vertex under the wheel
// matrix) is applied, then EVERY vertex of the wheel's rolling sections is sent through
// the library wheelRenderTransform: the lowest point of the full mesh must sit on y=0
// at every spin (tyre meshes are faceted, so a radial-reach lift is not enough).
#include "tyre_contact.h"
#include "vehicle_asset.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>

int main() {
  const std::filesystem::path library = RACER_VEHICLE_LIBRARY;
  if (!std::filesystem::exists(library)) {
    std::cout << "SKIP: vehicle library not present\n";
    return 77;
  }
  constexpr double tolerance = 1e-5;  // 0.01 mm
  constexpr int spins = 64;
  const auto vehicles = racer::readVehicleLibrary(library);
  if (vehicles.empty())
    throw std::runtime_error("empty vehicle library");
  double worstAbs = 0, largestLift = 0, worstUnlifted = 0;
  for (const auto &vehicle : vehicles) {
    const auto asset = racer::loadVehicleAsset(vehicle);
    for (size_t wheel = 0; wheel < 4; ++wheel) {
      const float reach = racer::tyreRadialReach(asset, int(wheel));
      if (!(reach > 0))
        throw std::runtime_error(vehicle.id + ": wheel without rolling mesh");
      const auto rim = racer::tyreRimVertices(asset, int(wheel), reach);
      if (rim.empty())
        throw std::runtime_error(vehicle.id + ": empty rim set");
      for (int step = 0; step < spins; ++step) {
        float m[16];
        racer::wheelRenderTransform(m, vehicle.geometry, wheel, 0, 0, 0, 0,
                                    2 * 3.14159265358979323846 * step / spins, true);
        const double lift = racer::tyreLowestY(rim, m);
        double lowest = std::numeric_limits<double>::infinity(), unlifted = lowest;
        for (const auto &section : asset.sections) {
          if (section.wheel != int(wheel) || !section.rolling)
            continue;
          for (uint32_t i = 0; i < section.count; ++i) {
            const auto &v = asset.triangles[section.first + i];
            const double y = double(m[1]) * v.x + double(m[5]) * v.y + double(m[9]) * v.z + double(m[13]);
            unlifted = std::min(unlifted, y);
            lowest = std::min(lowest, y - lift);
          }
        }
        largestLift = std::max(largestLift, std::abs(lift));
        worstUnlifted = std::max(worstUnlifted, unlifted);
        worstAbs = std::max(worstAbs, std::abs(lowest));
        if (std::abs(lowest) > tolerance)
          throw std::runtime_error(vehicle.id + " wheel " + std::to_string(wheel) + " spin step " +
                                   std::to_string(step) + ": lowest tyre point off the road by " +
                                   std::to_string(lowest * 1000) + " mm");
      }
    }
  }
  std::cout << "tyre_contact_checks ok: " << vehicles.size() << " vehicles x4 wheels x" << spins
            << " spins; worst |lowest point - road| after lift " << worstAbs * 1000
            << " mm (before lift up to " << worstUnlifted * 1000 << " mm), largest lift "
            << largestLift * 1000 << " mm\n";
}
