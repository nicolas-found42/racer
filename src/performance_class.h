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
// its defaults change. Re-measured 2026-11-09 after the part-throttle launch
// fix (rpm-scaled engine braking, sqrt pedal map): times shift ~0.05 s from
// the launch-ramp transient; full-throttle steady state is unchanged.
inline PrototypeRating prototypeRating(const VehicleSetup &effective) {
  if (!effective.valid())
    throw std::invalid_argument("rating_invalid_setup");
  constexpr double first = .8, spacing = .05;
  constexpr std::array<double, 9> measured{{9.981110, 9.349068, 8.794632,
                                            8.305135, 7.869522, 7.480605,
                                            7.132100, 6.819413, 6.542811}};
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
