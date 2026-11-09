// Independent tyre/ground contact check on every library vehicle: all vertices of
// each wheel's rolling sections go through wheelRenderTransform at many spin angles
// and the tyreContactLift, and the lowest world-space point must touch y=0.
#include "tyre_contact.h"
#include "vehicle_asset.h"
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
  constexpr double touchTolerance = 1e-4;  // 0.1 mm: neither sunk nor hovering
  constexpr int spins = 64;
  const auto vehicles = racer::readVehicleLibrary(library);
  if (vehicles.empty())
    throw std::runtime_error("empty vehicle library");
  double worstHover = 0, worstSink = 0, largestLift = 0;
  for (const auto &vehicle : vehicles) {
    const auto asset = racer::loadVehicleAsset(vehicle);
    for (size_t wheel = 0; wheel < 4; ++wheel) {
      const float reach = racer::tyreRadialReach(asset, int(wheel));
      if (!(reach > 0))
        throw std::runtime_error(vehicle.id + ": wheel without rolling mesh");
      const double lift = racer::tyreContactLift(vehicle.geometry, wheel, reach);
      largestLift = std::max(largestLift, std::abs(lift));
      const auto rim = racer::tyreRimVertices(asset, int(wheel), reach);
      if (rim.empty())
        throw std::runtime_error(vehicle.id + ": empty rim set");
      double lowestOverSpins = std::numeric_limits<double>::infinity();
      for (int step = 0; step < spins; ++step) {
        float m[16];
        racer::wheelRenderTransform(m, vehicle.geometry, wheel, 0, 0, 0, 0,
                                    2 * 3.14159265358979323846 * step / spins, true);
        double lowest = std::numeric_limits<double>::infinity();
        for (const auto &section : asset.sections) {
          if (section.wheel != int(wheel) || !section.rolling)
            continue;
          for (uint32_t i = 0; i < section.count; ++i) {
            const auto &v = asset.triangles[section.first + i];
            lowest = std::min(lowest, double(m[1]) * v.x + double(m[5]) * v.y +
                                          double(m[9]) * v.z + double(m[13]) - lift);
          }
        }
        // The showroom plane uses only the rim subset: it must find the same lowest point.
        double lowestRim = std::numeric_limits<double>::infinity();
        for (const auto &v : rim)
          lowestRim = std::min(lowestRim, double(m[1]) * v[0] + double(m[5]) * v[1] +
                                              double(m[9]) * v[2] + double(m[13]) - lift);
        if (std::abs(lowestRim - lowest) > 1e-6)
          throw std::runtime_error(vehicle.id + " wheel " + std::to_string(wheel) +
                                   ": rim subset misses the lowest tyre point by " +
                                   std::to_string((lowestRim - lowest) * 1000) + " mm");
        lowestOverSpins = std::min(lowestOverSpins, lowest);
        worstSink = std::min(worstSink, lowest);  // never below the road at any spin
      }
      // Some spin angle must put a tyre vertex on the road: no hover.
      worstHover = std::max(worstHover, lowestOverSpins);
      if (lowestOverSpins > touchTolerance || lowestOverSpins < -touchTolerance)
        throw std::runtime_error(vehicle.id + " wheel " + std::to_string(wheel) +
                                 ": lowest tyre point off the road by " +
                                 std::to_string(lowestOverSpins * 1000) + " mm");
    }
  }
  if (worstSink < -touchTolerance)
    throw std::runtime_error("a tyre vertex sinks below the road at some spin");
  std::cout << "tyre_contact_checks ok: " << vehicles.size()
            << " vehicles x4 wheels x" << spins << " spins; worst hover " << worstHover * 1000
            << " mm, worst sink " << worstSink * 1000 << " mm, largest lift "
            << largestLift * 1000 << " mm\n";
}
