#include "simulation.h"
#include <cmath>
#include <stdexcept>
namespace racer {
bool Simulation::setSetup(const VehicleSetup &setup) {
  if (!setup.valid())
    return false;
  setup_ = setup;
  return true;
}
bool Simulation::setGeometry(const VehicleGeometry &geometry) {
  if (!geometry.valid()) return false;
  try { orientedBoundaryClearance(geometry,0);orientedBoundaryClearance(geometry,.7853981633974483); }
  catch (const std::invalid_argument &) { return false; }
  geometry_=geometry;return true;
}
void Simulation::reset() {
  boundaryContact = false;
  car = {};
  rearm();
}
void Simulation::rearm() {
  throttleHeld = true;
  brakeHeld = true;
}
void Simulation::tick(Input in, double dt) {
  boundaryContact = false;
  in.throttle = std::clamp(in.throttle, 0.0, 1.0);
  in.brake = std::clamp(in.brake, 0.0, 1.0);
  in.steer = std::clamp(in.steer, -1.0, 1.0);
  const bool t = in.throttle > .05, b = in.brake > .05;
  const bool tp = t && !throttleHeld, bp = b && !brakeHeld;
  throttleHeld = t;
  brakeHeld = b;
  if (std::abs(car.speed) < .001) {
    car.speed = 0;
    if (car.direction == 1 && bp && !t)
      car.direction = -1;
    else if (car.direction == -1 && tp && !b)
      car.direction = 1;
  }
  const double drive = car.direction == 1 ? in.throttle : in.brake;
  const double braking = car.direction == 1 ? in.brake : in.throttle;
  double magnitude = std::abs(car.speed);
  // Constant net full-throttle acceleration reaches 100 km/h in eight seconds.
  magnitude = std::max(
      0.0, magnitude +
               (drive * setup_.acceleration * (100.0 / 3.6 / 8.0) -
                braking * setup_.brake * 9.645061728 - (drive == 0 ? .25 : 0)) *
                   dt);
  magnitude = std::min(magnitude, (car.direction == 1 ? 160.0 : 30.0) / 3.6);
  car.speed = magnitude * car.direction;
  car.steering += (in.steer * .55 / (1 + magnitude * .065) - car.steering) *
                  std::min(1.0, dt * 7 * setup_.steering);
  car.heading += car.speed / wheelbase() * std::tan(car.steering) * dt;
  const double priorX=car.x,priorZ=car.z;
  car.x += std::sin(car.heading) * car.speed * dt;
  car.z += std::cos(car.heading) * car.speed * dt;
  // Leave enough clearance for the 4.4 m car, including at oblique angles.
  if (geometry_ ? clampVehicleToBoundary(*geometry_,car.heading,car.x,car.z)
                : std::abs(car.x) > 497.5 || std::abs(car.z) > 497.5) {
    boundaryContact = true;
    if (!geometry_) {
      car.x = std::clamp(car.x, -497.5, 497.5);
      car.z = std::clamp(car.z, -497.5, 497.5);
    }
    car.speed = 0;
  }
  car.travel+=std::hypot(car.x-priorX,car.z-priorZ)*car.direction;
}
} // namespace racer
