#pragma once
#include "setup.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
namespace racer {
struct PrototypeRating { char className;double targetSeconds; };
// Racer-authored 0–100 km/h bands for the generic force-based vehicle model
// (test revision 2) with its default VehicleDynamics. targetSeconds is the
// measured automatic-test time at each 0.05 acceleration multiplier, linearly
// interpolated between garage steps. It is neither a recovered Juiced2 rating
// formula nor a prediction for a car with different dynamics; re-measure the
// table (tests/performance_class_checks.cpp fails on drift) when the model or
// its defaults change.
inline PrototypeRating prototypeRating(const VehicleSetup &effective) {
  if (!effective.valid()) throw std::invalid_argument("rating_invalid_setup");
  constexpr double first=.8,spacing=.05;
  constexpr std::array<double,9> measured{{10.024913,9.393774,8.840427,8.351360,
                                           7.916461,7.528121,7.179740,6.867354,6.591100}};
  const double position=std::clamp((effective.acceleration-first)/spacing,0.,double(measured.size()-1));
  const std::size_t lower=std::min<std::size_t>(std::size_t(std::floor(position+1e-9)),measured.size()-2);
  const double fraction=position-double(lower);
  const double seconds=measured[lower]+(measured[lower+1]-measured[lower])*fraction;
  return {seconds<=6.8 ? 'A' : seconds<=7.3 ? 'B' : seconds<=8.5 ? 'C' : 'D',seconds};
}
}
