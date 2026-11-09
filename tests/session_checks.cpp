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
    // Force-based model (test revision 2): the default profile measures 7.9165 s and
    // 41.816 m. The benchmark replays the simulation to locate the 100 km/h and
    // 0.01 m/s thresholds, so these are not sample-quantized.
    check(std::abs(baseA.seconds - 7.916461) < .005 &&
              std::abs(baseA.distance - 110.4465) < .1,
          "default acceleration measurement");
    check(std::abs(baseB.distance - 41.816) < .1 && std::abs(baseB.seconds - 2.9182) < .01,
          "baseline braking distance");
    check(baseA.testRevision == 2 && baseB.testRevision == 2, "force-based test revision");
    // Braking begins at the first simulation sample at or above 100 km/h.
    check(baseB.initialSpeed >= 100.0 / 3.6 && baseB.initialSpeed < 100.0 / 3.6 + .1,
          "initial speed is the first sample at or above 100 km/h");
    for (double acceleration : {.8, 1., 1.05, 1.2}) {
      VehicleSetup variant;
      variant.acceleration = acceleration;
      const auto braking = run(TestKind::Braking, variant);
      // The lead-in reaches 100 km/h with the tuned engine, so drivetrain and
      // suspension state at brake-on differ slightly, but not the braking.
      check(braking.initialSpeed >= 100.0 / 3.6 && braking.initialSpeed < 100.0 / 3.6 + .25,
            "acceleration-independent brake initial speed");
      check(std::abs(braking.distance - baseB.distance) < .02 * baseB.distance,
            "acceleration-independent brake distance");
      check(std::abs(braking.seconds - baseB.seconds) < .02 * baseB.seconds,
            "acceleration-independent brake time");
    }
    VehicleSetup fast;
    fast.acceleration = 1.2;
    VehicleSetup strong;
    strong.brake = 1.2;
    const auto faster = run(TestKind::Acceleration, fast);
    // The multiplier scales engine torque, so the time falls roughly in
    // proportion (8/1.2 = 6.667 s under the old kinematic model); gearing,
    // shift timing and slip decide the exact value.
    check(std::abs(faster.seconds - 6.5911) < .01 && faster.seconds < baseA.seconds &&
              faster.seconds > baseA.seconds / 1.35,
          "acceleration multiplier effect");
    const auto stronger = run(TestKind::Braking, strong);
    check(stronger.distance < baseB.distance, "brake improvement");
    // Brake torque is limited by tyre grip: extra torque barely shortens the stop
    // (ABS holds slip), while weaker brakes lengthen it clearly.
    VehicleSetup weak;
    weak.brake = .8;
    const auto weaker = run(TestKind::Braking, weak);
    check(stronger.distance / baseB.distance > .94 && stronger.distance / baseB.distance < .995 &&
              weaker.distance / baseB.distance > 1.08 && weaker.distance / baseB.distance < 1.2,
          "brake strength saturates at the tyre limit");
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
    // There is no artificial road-speed clamp: a tuned car keeps accelerating
    // past the old 160 km/h limit, bounded by gearing, drag and the road.
    Simulation stockCap;
    tunedCap.car.z = stockCap.car.z = -350;
    for (int i = 0; i < 1400; ++i) {
      tunedCap.tick({1, 0, 0});
      stockCap.tick({1, 0, 0});
    }
    check(tunedCap.car.speed > stockCap.car.speed && tunedCap.car.speed * 3.6 > 130 &&
              tunedCap.car.speed * 3.6 < 250,
          "tuning raises uncapped speed");
    tunedCap.reset();
    tunedCap.tick({});
    for (int i = 0; i < 1000; ++i)
      tunedCap.tick({0, 1, 0});
    check(tunedCap.car.gear == -1 && tunedCap.car.speed < -5 / 3.6, "tuned car reverses");
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
