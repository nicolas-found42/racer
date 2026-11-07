#include "test_session.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace racer;
void check(bool yes, const char *message) {
  if (!yes)
    throw std::runtime_error(message);
}
TestResult run(TestKind kind, VehicleSetup setup = {}, int fps = 60) {
  Simulation sim;
  TestSession session;
  check(session.start(kind, 1, setup, sim), "start");
  double accumulator = 0;
  for (int frame = 0; frame < fps * 65 && session.active(); ++frame) {
    accumulator += 1.0 / fps;
    while (accumulator + 1e-10 >= step && session.active()) {
      // Hostile player input cannot affect automatic schedule.
      session.tick(sim, {0, 1, 1});
      accumulator -= step;
    }
  }
  check(session.result().valid, "automatic result valid");
  return session.result();
}
int main() {
  try {
    const auto baseA = run(TestKind::Acceleration),
               baseB = run(TestKind::Braking);
    check(std::abs(baseA.seconds - 8) < 1e-8,
          "interpolated default acceleration");
    check(std::abs(baseB.distance - 38.8737) < .25,
          "baseline braking distance");
    check(baseB.initialSpeed == 100.0 / 3.6, "exact initial speed");
    for (double acceleration : {.8, 1., 1.05, 1.2}) {
      VehicleSetup variant;
      variant.acceleration = acceleration;
      const auto braking = run(TestKind::Braking, variant);
      check(braking.initialSpeed == 100.0 / 3.6,
            "acceleration-independent brake initial speed");
      check(std::abs(braking.distance - baseB.distance) < 1e-9,
            "acceleration-independent brake distance");
      check(std::abs(braking.seconds - baseB.seconds) < 1e-9,
            "acceleration-independent brake time");
    }
    VehicleSetup fast;
    fast.acceleration = 1.2;
    VehicleSetup strong;
    strong.brake = 1.2;
    const auto faster = run(TestKind::Acceleration, fast);
    check(std::abs(faster.seconds - 8 / 1.2) < step,
          "acceleration multiplier equation");
    const auto stronger = run(TestKind::Braking, strong);
    check(stronger.distance < baseB.distance, "brake improvement");
    // The authored braking term plus unchanged coast drag predicts distance
    // inversely proportional to deceleration, within fixed-step integration
    // error.
    const double expectedRatio =
        (9.645061728 + .25) / (1.2 * 9.645061728 + .25);
    check(std::abs(stronger.distance / baseB.distance - expectedRatio) < .005,
          "brake strength magnitude");
    for (int fps : {30, 60, 144}) {
      check(std::abs(run(TestKind::Acceleration, {}, fps).seconds -
                     baseA.seconds) < step,
            "accel frame independence");
      check(std::abs(run(TestKind::Braking, {}, fps).distance -
                     baseB.distance) < .25,
            "brake frame independence");
    }
    Simulation slowSteer, fastSteer;
    VehicleSetup response;
    response.steering = 1.2;
    fastSteer.setSetup(response);
    slowSteer.tick({0, 0, 1});
    fastSteer.tick({0, 0, 1});
    check(std::abs(fastSteer.car.steering / slowSteer.car.steering - 1.2) <
              1e-9,
          "steering transient equation");
    Simulation tunedCap;
    tunedCap.setSetup(fast);
    // Travel straight from the southern test start so cap is reached before
    // bounds.
    tunedCap.car.z = -350;
    for (int i = 0; i < 1400; ++i)
      tunedCap.tick({1, 0, 0});
    check(std::abs(tunedCap.car.speed - 160 / 3.6) < 1e-9,
          "tuning preserves forward cap");
    tunedCap.reset();
    tunedCap.tick({});
    for (int i = 0; i < 1000; ++i)
      tunedCap.tick({0, 1, 0});
    check(std::abs(tunedCap.car.speed + 30 / 3.6) < 1e-9,
          "tuning preserves reverse cap");
    VehicleSetup bad;
    bad.acceleration = std::numeric_limits<double>::quiet_NaN();
    check(!slowSteer.setSetup(bad), "invalid setup rejected");
    check(slowSteer.setup() == VehicleSetup{},
          "invalid setup preserves applied");
    Simulation sim;
    TestSession session;
    session.start(TestKind::Handling, 2, fast, sim);
    check(session.phase() == TestPhase::Countdown, "countdown");
    auto frozen = sim.car;
    for (int i = 0; i < 120; ++i)
      session.tick(sim, {1, 0, 0});
    check(session.countdownRemaining() > 1.9 && sim.car.z == frozen.z,
          "countdown freezes car");
    const double savedCount = session.countdownRemaining();
    // A paused host supplies no tick: no wall-clock dependency exists.
    check(session.countdownRemaining() == savedCount && session.elapsed() == 0,
          "pause freezes session time");
    for (int i = 0; i < 240; ++i)
      session.tick(sim, {});
    check(session.phase() == TestPhase::Running, "countdown completed");
    Car a, b;
    // Later gate crossed before expected gate cannot advance.
    a.x = 90;
    a.z = 100;
    b.x = 110;
    b.z = 100;
    session.observeMotion(a, b, step);
    check(session.nextGate() == 0, "wrong order");
    a = {};
    b = {};
    a.z = 110;
    b.z = 90;
    session.observeMotion(a, b, step);
    check(session.nextGate() == 0, "reverse crossing");
    a.z = 90;
    b.z = 110;
    a.x = b.x = 20;
    session.observeMotion(a, b, step);
    check(session.nextGate() == 0, "outside gate width");
    for (const auto &g : handlingCourse().gates) {
      a = {};
      b = {};
      a.x = g.x - g.nx * 50;
      a.z = g.z - g.nz * 50;
      b.x = g.x + g.nx * 50;
      b.z = g.z + g.nz * 50;
      session.observeMotion(a, b, step);
    }
    check(session.result().valid && session.phase() == TestPhase::Result,
          "swept gate finish");
    check(session.nextGate() == handlingCourse().gates.size(),
          "ordered course complete");
    check(session.result().slot == 2 && session.result().setup == fast,
          "frozen attribution");
    fast.acceleration = .8;
    check(session.result().setup.acceleration == 1.2,
          "result snapshot immutable from source edits");
    session.start(TestKind::Handling, 0, {}, sim);
    check(session.nextGate() == 0 && session.elapsed() == 0, "retry fresh");
    session.invalidate("Reset");
    check(!session.result().valid && !session.active(), "reset invalidation");
    session.start(TestKind::Acceleration, 0, {}, sim);
    session.cancel();
    check(!session.result().valid && session.phase() == TestPhase::Invalid,
          "cancel invalid");
    session.start(TestKind::Acceleration, 0, {}, sim);
    session.timeout = .001;
    for (int i = 0; i < 362; ++i)
      session.tick(sim, {});
    check(session.phase() == TestPhase::Invalid && !session.result().valid,
          "timeout invalid");
    session.start(TestKind::Handling, 0, {}, sim);
    for (int i = 0; i < 360; ++i)
      session.tick(sim, {});
    session.observeMotion({}, {}, step, true);
    check(session.phase() == TestPhase::Invalid && !session.result().valid,
          "boundary invalid");
    // Drive the actual simulation through the authored route at practice speed.
    // This catches geometrically valid gates that cannot be reached as a
    // course.
    TestSession driven;
    Simulation driver;
    driven.start(TestKind::Handling, 0, {}, driver);
    for (int i = 0; i < 36000 && driven.active(); ++i) {
      const auto &gate = handlingCourse().gates[driven.nextGate()];
      const double x = gate.x + gate.nx * 8 - driver.car.x;
      const double z = gate.z + gate.nz * 8 - driver.car.z;
      const double error = std::remainder(std::atan2(x, z) - driver.car.heading,
                                          2 * 3.141592653589793);
      driven.tick(driver, {driver.car.speed < 7 ? 1. : 0.,
                           driver.car.speed > 8 ? 1. : 0.,
                           std::clamp(error * 2., -1., 1.)});
    }
    check(driven.result().valid, "physical course feasibility");
    std::cout << "Driven course=" << driven.result().seconds << " s / "
              << driven.nextGate() << " gates\n";
    std::cout << "Acceleration=" << baseA.seconds
              << " s braking=" << baseB.distance << " m / " << baseB.seconds
              << " s initial=" << baseB.initialSpeed << " m/s\n";
    std::cout << "PASS: automatic schedules, interpolation, setup effects, "
                 "frame schedules, countdown/pause, directional swept course, "
                 "retry, invalidation and attribution\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
