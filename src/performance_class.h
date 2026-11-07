#pragma once
#include "setup.h"
#include <stdexcept>
namespace racer {
struct PrototypeRating { char className;double targetSeconds; };
// Racer-authored 0–100 km/h bands for model revision1 only. This is neither a
// recovered Juiced2 rating formula nor a prediction for different car physics.
inline PrototypeRating prototypeRating(const VehicleSetup &effective) {
  if (!effective.valid()) throw std::invalid_argument("rating_invalid_setup");
  const double seconds=8/effective.acceleration;
  return {seconds<=6.8 ? 'A' : seconds<=7.3 ? 'B' : seconds<=8.5 ? 'C' : 'D',seconds};
}
}
