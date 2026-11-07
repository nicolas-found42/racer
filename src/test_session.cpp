#include "test_session.h"
#include <algorithm>
#include <cmath>
namespace racer {
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
  if (slot < 0 || slot > 2 || !setup.valid() ||
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
  result_.seconds = seconds;
  result_.distance = distance;
  result_.valid = true;
  result_.reason = "Valid finish";
  phase_ = TestPhase::Result;
}
void TestSession::tick(Simulation &sim, Input player, double dt) {
  if (!active() || !(dt > 0) || !std::isfinite(dt))
    return;
  if (phase_ == TestPhase::Countdown) {
    countdown_ = std::max(0.0, countdown_ - dt);
    if (countdown_ < 1e-9) {
      countdown_ = 0;
      phase_ = TestPhase::Running;
    }
    return;
  }
  Input input = player;
  if (result_.kind != TestKind::Handling) {
    input = braking_ ? Input{0, 1, 0} : Input{1, 0, 0};
  }
  auto before = sim.car;
  sim.tick(input, dt);
  constexpr double target = 100.0 / 3.6;
  if (result_.kind == TestKind::Braking && !braking_ &&
      sim.car.speed >= target - 1e-10) {
    // End the lead-in at the threshold, then begin braking on the next tick.
    // A stronger acceleration setup must not change the measured initial speed.
    const double fraction = std::clamp(
        (target - before.speed) / (sim.car.speed - before.speed), 0.0, 1.0);
    sim.car.x = before.x + (sim.car.x - before.x) * fraction;
    sim.car.z = before.z + (sim.car.z - before.z) * fraction;
    sim.car.speed = target;
  }
  observeMotion(before, sim.car, dt, sim.boundaryContact);
}
void TestSession::observeMotion(const Car &before, const Car &after, double dt,
                                bool boundaryContact) {
  if (phase_ != TestPhase::Running || !(dt > 0) || !std::isfinite(dt))
    return;
  if (boundaryContact) {
    invalidate("Boundary contact - no record saved");
    return;
  }
  total_ += dt;
  if (total_ > (result_.kind == TestKind::Handling ? 300 : timeout)) {
    invalidate("Timed out - no record saved");
    return;
  }
  const double movement = std::hypot(after.x - before.x, after.z - before.z);
  constexpr double target = 100.0 / 3.6;
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
    if (before.speed < target && after.speed >= target) {
      const double fraction =
          (target - before.speed) / (after.speed - before.speed);
      finish(measured_ + dt * fraction, distance_ + movement * fraction);
    } else {
      measured_ += dt;
      distance_ += movement;
    }
  } else if (!braking_) {
    if (after.speed >= target - 1e-10) {
      braking_ = true;
      result_.initialSpeed = after.speed;
      // Brake begins at the next exact tick boundary; lead-in is excluded.
      measured_ = distance_ = 0;
    }
  } else {
    if (after.speed <= 0) {
      // Last braking interval may reach zero before the tick ends.
      const double deceleration = result_.setup.brake * 9.645061728 + .25;
      const double fraction =
          std::clamp(before.speed / (deceleration * dt), 0.0, 1.0);
      // Simulation uses semi-implicit position integration; retain that
      // measurement.
      finish(measured_ + dt * fraction, distance_ + movement);
    } else {
      measured_ += dt;
      distance_ += movement;
    }
  }
}
} // namespace racer
