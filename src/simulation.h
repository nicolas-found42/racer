#pragma once
#include "setup.h"
#include "vehicle_geometry.h"
#include <algorithm>
#include <optional>
namespace racer {
constexpr double step = 1.0 / 120.0;
struct Input {
  double throttle = 0, brake = 0, steer = 0;
};
struct Car {
  double x = 0, z = 0, heading = 0, speed = 0, steering = 0;
  int direction = 1;
  double travel = 0;
};
class Simulation {
public:
  Car car;
  bool boundaryContact = false;
  bool setSetup(const VehicleSetup &setup);
  const VehicleSetup &setup() const { return setup_; }
  bool setGeometry(const VehicleGeometry &geometry);
  double wheelbase() const { return geometry_ ? geometry_->wheelbase() : 2.7; }
  const VehicleGeometry *geometry() const { return geometry_ ? &*geometry_ : nullptr; }
  void tick(Input in, double dt = step);
  void reset();
  void rearm();

private:
  VehicleSetup setup_;
  std::optional<VehicleGeometry> geometry_;
  bool throttleHeld = false, brakeHeld = false;
};
} // namespace racer
