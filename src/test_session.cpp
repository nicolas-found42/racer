#include "test_session.h"
#include <algorithm>
#include <cmath>
#include <utility>
namespace racer {
namespace {
constexpr double targetSpeed = 100.0 / 3.6;
// A measured standstill threshold (0.036 km/h), not a guessed braking force.
constexpr double stopSpeed = .01;
double groundSpeed(const Car &car) {
  const double velocity = std::hypot(car.velocityX, car.velocityZ);
  // Preserve observeMotion's use with legacy synthetic Car samples.
  return velocity > 0 ? velocity : std::abs(car.speed);
}
bool finiteMotion(const Car &car) {
  return std::isfinite(car.x) && std::isfinite(car.z) &&
         std::isfinite(car.speed) && std::isfinite(car.heading) &&
         std::isfinite(car.velocityX) && std::isfinite(car.velocityZ) &&
         std::isfinite(car.distance);
}
double traveled(const Car &before, const Car &after) {
  const double arc = after.distance - before.distance;
  // Simulation accumulates substep arc length; manually supplied samples may
  // only carry positions, in which case a segment is the available measurement.
  return arc > 0 ? arc : std::hypot(after.x - before.x, after.z - before.z);
}
// Replay the entire state, including wheel, suspension and drivetrain memory.
// A RoadSampler used in a benchmark must be a pure spatial query.
template <class Reached>
double atEvent(Simulation &sim, const Simulation &before, Input input,
               double interval, Reached reached) {
  double low = 0, high = interval;
  Simulation best = sim;
  for (unsigned i = 0; i < 28; ++i) {
    const double middle = .5 * (low + high);
    Simulation trial = before;
    trial.tick(input, middle);
    if (reached(trial.car)) { high = middle; best = std::move(trial); }
    else low = middle;
  }
  sim = std::move(best);
  return high;
}
} // namespace
const char *testId(TestKind k) {
  switch (k) {
  case TestKind::Acceleration:
    return "acceleration";
  case TestKind::Braking:
    return "braking";
  case TestKind::Handling:
    return "handling";
  }
  return "unknown";
}
const char *testName(TestKind k) {
  switch (k) {
  case TestKind::Acceleration:
    return "Automatic 0-100 km/h (62.14 mph)";
  case TestKind::Braking:
    return "Automatic 100-0 km/h (62.14 mph)";
  case TestKind::Handling:
    return "Player handling course";
  }
  return "Unknown test";
}
const Course &handlingCourse() {
  static const Course course{{0, 0, 0, 0, 0, 1},
                             1,
                             {{0, 100, 0, 1, 18},
                              {100, 100, 1, 0, 18},
                              {100, 200, 0, 1, 18},
                              {0, 200, -1, 0, 18},
                              {0, 300, 0, 1, 18}}};
  return course;
}
std::optional<double> gateCrossing(const Gate &g, const Car &a, const Car &b) {
  const double from = (a.x - g.x) * g.nx + (a.z - g.z) * g.nz;
  const double to = (b.x - g.x) * g.nx + (b.z - g.z) * g.nz;
  if (!(from < 0 && to >= 0))
    return {};
  const double fraction = -from / (to - from);
  const double x = a.x + (b.x - a.x) * fraction - g.x;
  const double z = a.z + (b.z - a.z) * fraction - g.z;
  if (std::abs(x * -g.nz + z * g.nx) > g.width / 2)
    return {};
  return fraction;
}
bool TestSession::start(TestKind kind, int slot, const VehicleSetup &setup,
                        Simulation &sim,const std::string &carId,int modelRevision) {
  if (slot < 0 || slot > 2 || !setup.valid() || modelRevision < 1 ||
      carId.empty() || !std::isfinite(timeout) || timeout <= 0 || timeout > 3600 ||
      (kind != TestKind::Acceleration && kind != TestKind::Braking &&
       kind != TestKind::Handling))
    return false;
  result_ = {};
  result_.kind = kind;
  result_.slot = slot;
  result_.setup = setup;
  result_.carId=carId;result_.handlingRevision=modelRevision;
  sim.setSetup(setup);
  sim.reset();
  sim.car = kind == TestKind::Handling ? handlingCourse().start
                                       : Car{0, -350, 0, 0, 0, 1};
  sim.tick({}, 0); // Automatic schedule starts with released pedals.
  phase_ = TestPhase::Countdown;
  countdown_ = 3;
  total_ = measured_ = distance_ = 0;
  nextGate_ = 0;
  braking_ = false;
  configurationRevision_ = sim.configurationRevision();
  return true;
}
void TestSession::invalidate(std::string reason) {
  if (!active())
    return;
  result_.valid = false;
  result_.seconds = measured_;
  result_.distance = distance_;
  result_.reason = std::move(reason);
  phase_ = TestPhase::Invalid;
}
void TestSession::finish(double seconds, double distance) {
  if (!std::isfinite(seconds) || !std::isfinite(distance) || seconds < 0 || distance < 0) {
    invalidate("Invalid measurement - no record saved");
    return;
  }
  result_.seconds = seconds;
  result_.distance = distance;
  result_.valid = true;
  result_.reason = "Valid finish";
  phase_ = TestPhase::Result;
}
void TestSession::tick(Simulation &sim, Input player, double dt) {
  if (!active() || !(dt > 0) || !std::isfinite(dt) || dt > 1)
    return;
  if (sim.configurationRevision() != configurationRevision_ ||
      sim.setup() != result_.setup) {
    invalidate("Vehicle or road configuration changed - no record saved");
    return;
  }
  if (!std::isfinite(timeout) || timeout <= 0 || timeout > 3600) {
    invalidate("Invalid test timeout - no record saved");
    return;
  }
  if (phase_ == TestPhase::Countdown) {
    const double consumed = std::min(countdown_, dt);
    countdown_ -= consumed;
    dt -= consumed;
    if (countdown_ <= 1e-9) {
      countdown_ = 0;
      phase_ = TestPhase::Running;
    } else return;
  }
  // Bound measurement segments independently of the rendering frame rate.
  while (phase_ == TestPhase::Running && dt > 1e-12) {
    const double interval = std::min(dt, step);
    Input input = player;
    if (result_.kind != TestKind::Handling)
      input = braking_ ? Input{0, 1, 0} : Input{1, 0, 0};
    const Simulation before = sim;
    sim.tick(input, interval);
    if (sim.chassisContact) {
      invalidate("Chassis contact - no record saved");
      return;
    }
    double advanced = interval;
    if (!sim.boundaryContact && finiteMotion(sim.car)) {
      if (result_.kind != TestKind::Handling && !braking_ &&
          groundSpeed(before.car) < targetSpeed &&
          groundSpeed(sim.car) >= targetSpeed) {
        advanced = atEvent(sim, before, input, interval,
                           [](const Car &c) { return groundSpeed(c) >= targetSpeed; });
      } else if (result_.kind == TestKind::Braking && braking_ &&
                 groundSpeed(before.car) > stopSpeed &&
                 groundSpeed(sim.car) <= stopSpeed) {
        advanced = atEvent(sim, before, input, interval,
                           [](const Car &c) { return groundSpeed(c) <= stopSpeed; });
      }
    }
    observeMotion(before.car, sim.car, advanced, sim.boundaryContact);
    dt -= advanced;
  }
}
void TestSession::observeMotion(const Car &before, const Car &after, double dt,
                                bool boundaryContact) {
  if (phase_ != TestPhase::Running || !(dt > 0) || !std::isfinite(dt))
    return;
  if (boundaryContact) {
    invalidate("Boundary contact - no record saved");
    return;
  }
  if (!finiteMotion(before) || !finiteMotion(after)) {
    invalidate("Non-finite vehicle state - no record saved");
    return;
  }
  total_ += dt;
  if (total_ > (result_.kind == TestKind::Handling ? 300 : timeout)) {
    invalidate("Timed out - no record saved");
    return;
  }
  const double movement = traveled(before, after);
  const double initialSpeed = groundSpeed(before), finalSpeed = groundSpeed(after);
  if (!std::isfinite(movement) || !std::isfinite(initialSpeed) || !std::isfinite(finalSpeed)) {
    invalidate("Invalid measurement - no record saved");
    return;
  }
  if (result_.kind == TestKind::Handling) {
    // Only the expected gate may advance. Process subsequent gates in segment
    // order.
    double priorFraction = -1;
    const auto &gates = handlingCourse().gates;
    while (nextGate_ < gates.size()) {
      auto fraction = gateCrossing(gates[nextGate_], before, after);
      if (!fraction || *fraction < priorFraction)
        break;
      priorFraction = *fraction;
      ++nextGate_;
      if (nextGate_ == gates.size()) {
        finish(measured_ + dt * *fraction, distance_ + movement * *fraction);
        return;
      }
    }
    measured_ += dt;
    distance_ += movement;
  } else if (result_.kind == TestKind::Acceleration) {
    if (initialSpeed < targetSpeed && finalSpeed >= targetSpeed) {
      const double fraction =
          (targetSpeed - initialSpeed) / (finalSpeed - initialSpeed);
      finish(measured_ + dt * fraction, distance_ + movement * fraction);
    } else {
      measured_ += dt;
      distance_ += movement;
    }
  } else if (!braking_) {
    if (finalSpeed >= targetSpeed - 1e-10) {
      braking_ = true;
      result_.initialSpeed = finalSpeed;
      // Brake starts at this complete simulated state; lead-in is excluded.
      measured_ = distance_ = 0;
    }
  } else {
    if (finalSpeed <= stopSpeed) {
      // tick() replays to this observed event. For externally supplied samples,
      // interpolate the speed crossing without assuming any deceleration law.
      const double fraction = initialSpeed > stopSpeed && initialSpeed > finalSpeed
          ? std::clamp((initialSpeed - stopSpeed) / (initialSpeed - finalSpeed), 0.0, 1.0)
          : 1.0;
      finish(measured_ + dt * fraction, distance_ + movement * fraction);
    } else {
      measured_ += dt;
      distance_ += movement;
    }
  }
}
} // namespace racer
