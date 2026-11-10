#pragma once
#include "setup.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
namespace racer {
struct PrototypeRating {
  char className;
  double targetSeconds;
};
// Racer-authored 0–100 km/h bands for the generic force-based vehicle model
// (test revision 2) with its default VehicleDynamics. targetSeconds is the
// measured automatic-test time at each 0.05 acceleration multiplier, linearly
// interpolated between garage steps. It is neither a recovered Juiced2 rating
// formula nor a prediction for a car with different dynamics; re-measure the
// table (tests/performance_class_checks.cpp fails on drift) when the model or
// its defaults change. Re-measured 2026-11-09 after the transmission fix
// (confirmed shift requests, gear hold, re-engagement ramp, road-coupled
// thresholds): full-throttle times shift ~0.03-0.04 s from the earlier
// part-throttle launch fix baseline.
inline PrototypeRating prototypeRating(const VehicleSetup &effective) {
  if (!effective.valid())
    throw std::invalid_argument("rating_invalid_setup");
  constexpr double first = .8, spacing = .05;
  constexpr std::array<double, 9> measured{{10.024454, 9.391823, 8.836819,
                                            8.346687, 7.910369, 7.520503,
                                            7.170671, 6.856074, 6.576538}};
  const double position = std::clamp((effective.acceleration - first) / spacing,
                                     0., double(measured.size() - 1));
  const std::size_t lower = std::min<std::size_t>(
      std::size_t(std::floor(position + 1e-9)), measured.size() - 2);
  const double fraction = position - double(lower);
  const double seconds =
      measured[lower] + (measured[lower + 1] - measured[lower]) * fraction;
  return {seconds <= 6.8   ? 'A'
          : seconds <= 7.3 ? 'B'
          : seconds <= 8.5 ? 'C'
                           : 'D',
          seconds};
}
} // namespace racer
