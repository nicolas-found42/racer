// Focused transmission regressions. Build with the application's real physics
// headers and geometry implementation (background:
// experiments/2026-11-09-stuck-13mph/TRANSMISSION_FIX.md).
#include "simulation.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <numbers>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>

namespace {
using namespace racer;
void require(bool condition, const std::string &message) {
  if (!condition)
    throw std::runtime_error(message);
}
RoadSampler plane(double grip, double grade = 0) {
  return [=](double, double z, double ceiling,
             double drop) -> std::optional<RoadSample> {
    const double y = grade * z;
    if (y > ceiling || y < ceiling - drop)
      return {};
    const double scale = std::hypot(1.0, grade);
    return RoadSample{y, {0, 1 / scale, -grade / scale}, grip, 1};
  };
}
void finiteState(const Simulation &sim) {
  const auto &c = sim.car;
  for (double value :
       {c.x, c.y, c.z, c.speed, c.velocityX, c.velocityY, c.velocityZ, c.pitch,
        c.roll, c.engineRpm, c.clutchEngagement})
    require(std::isfinite(value), "non-finite vehicle state");
  require(c.clutchEngagement >= 0 && c.clutchEngagement <= 1,
          "clutch engagement outside [0, 1]");
  require(c.gear == -1 || (c.gear >= 1 && c.gear <= 6),
          "gear outside the configured gearbox");
  for (const auto &wheel : c.wheels)
    require(std::isfinite(wheel.angularVelocity) &&
                std::isfinite(wheel.slipRatio) &&
                std::isfinite(wheel.normalLoad),
            "non-finite wheel state");
}
void wheelspinCannotUpshift() {
  // Maintain a wheelspin disturbance on a frictionless but supported surface.
  // Chassis speed stays near the reported 12 mph failure, while shaft RPM is
  // high enough to trigger the old 1->2 schedule. The fixture explicitly
  // injects wheel angular momentum; it is a scheduler regression, not a tyre
  // or energy-conservation benchmark.
  for (double frontSplit : {0.0, .5, 1.0}) {
    Simulation sim;
    auto dynamics = sim.dynamics();
    dynamics.frontDriveFraction = frontSplit;
    require(sim.setDynamics(dynamics), "configure drive split");
    sim.setRoadSampler(plane(0));
    sim.car.speed = 5.5;
    sim.synchronizeState();
    double maximumRpm = 0, minimumClutch = 1;
    for (int i = 0; i < 180; ++i) {
      for (std::size_t j = 0; j < sim.car.wheels.size(); ++j)
        if ((j < 2 ? frontSplit : 1 - frontSplit) > 0)
          sim.car.wheels[j].angularVelocity = 70;
      sim.tick({1, 0, 0});
      finiteState(sim);
      maximumRpm = std::max(maximumRpm, sim.car.engineRpm);
      minimumClutch = std::min(minimumClutch, sim.car.clutchEngagement);
      require(sim.car.gear == 1,
              "wheelspin caused an upshift at low chassis speed (drive split " +
                  std::to_string(frontSplit) + ")");
    }
    require(maximumRpm > dynamics.shiftUpRpm,
            "wheelspin fixture did not cross engine upshift threshold");
    require(sim.car.speed > 5 && sim.car.speed < 6,
            "wheelspin fixture left the low-speed failure range");
    require(minimumClutch > .99,
            "automatic clutch opened in a steady low-speed spin");
  }
}
void noSupportCannotShift() {
  Simulation sim;
  sim.setRoadSampler([](double, double, double,
                        double) -> std::optional<RoadSample> { return {}; });
  sim.car.y = 10;
  sim.car.speed = 20;
  sim.synchronizeState();
  const int initialGear = sim.car.gear;
  double maximumRpm = 0;
  for (int i = 0; i < 240; ++i) {
    sim.tick({1, 0, 0});
    finiteState(sim);
    maximumRpm = std::max(maximumRpm, sim.car.engineRpm);
    require(sim.car.gear == initialGear,
            "airborne wheel speed changed the automatic gear");
    for (const auto &wheel : sim.car.wheels)
      require(!wheel.grounded, "airborne fixture acquired a support");
  }
  require(maximumRpm > sim.dynamics().shiftUpRpm,
          "airborne fixture did not reach upshift RPM");
}
void movingPoseHonorsImmediatePedalDemand() {
  Simulation sim;
  sim.car.speed = 20;
  sim.synchronizeState();
  require(sim.car.gear == 2, "moving-pose fixture selected an unexpected gear");
  // synchronizeState resets the throttle response filter to zero. The actual
  // driver's WOT request must nevertheless select the full-load schedule on
  // this first tick, rather than upshifting at the light-pedal RPM threshold.
  sim.tick({1, 0, 0}, .12);
  require(sim.car.gear == 2,
          "fresh full throttle on a loaded moving pose used idle shift demand");
}
void fullThrottleProgresses() {
  for (double multiplier : {.8, 1.0, 1.2}) {
    Simulation sim;
    VehicleSetup setup;
    setup.acceleration = multiplier;
    require(sim.setSetup(setup), "configure garage multiplier");
    int previousGear = 1, upshifts = 0;
    double openTime = 0, longestOpen = 0, openRun = 0;
    for (int i = 0; i < 120 * 13; ++i) {
      sim.tick({1, 0, 0});
      finiteState(sim);
      if (sim.car.gear != previousGear) {
        require(sim.car.gear > previousGear,
                "full-throttle straight acceleration downshifted");
        ++upshifts;
        previousGear = sim.car.gear;
      }
      if (sim.car.clutchEngagement < .001) {
        openTime += step;
        openRun += step;
        longestOpen = std::max(longestOpen, openRun);
      } else {
        openRun = 0;
      }
      require(!sim.boundaryContact, "acceleration fixture hit world boundary");
    }
    require(sim.car.speed > 28 && sim.car.gear >= 3 && upshifts >= 2,
            "full-throttle gearbox did not accelerate through the ratios");
    require(longestOpen < .4 && openTime < 2,
            "clutch spent excessive time open during acceleration");
    std::cout << "WOT multiplier=" << multiplier
              << " speed=" << sim.car.speed * 3.6
              << " km/h gear=" << sim.car.gear << " clutch_open=" << openTime
              << " s\n";
  }
}
void lowGripAndGradeDoNotHunt() {
  for (double grip : {.2, .45, 1.0}) {
    for (double grade : {0.0, .06}) {
      Simulation sim;
      sim.setRoadSampler(plane(grip, grade));
      sim.car.pitch = std::atan(grade);
      sim.synchronizeState();
      int previousGear = sim.car.gear, reversals = 0, lastShiftDirection = 0;
      double lastShift = -100, longestOpen = 0, openRun = 0;
      for (int i = 0; i < 120 * 20; ++i) {
        sim.tick({1, 0, 0});
        finiteState(sim);
        const double time = (i + 1) * step;
        if (sim.car.gear != previousGear) {
          const int direction = sim.car.gear > previousGear ? 1 : -1;
          if (direction != lastShiftDirection && lastShiftDirection != 0 &&
              time - lastShift < .6)
            ++reversals;
          lastShift = time;
          lastShiftDirection = direction;
          previousGear = sim.car.gear;
        }
        if (sim.car.clutchEngagement < .001) {
          openRun += step;
          longestOpen = std::max(longestOpen, openRun);
        } else {
          openRun = 0;
        }
        // The world has a real boundary; stop the drive fixture before that
        // independent collision can hold the car and legitimately downshift.
        if (sim.car.z > 460)
          break;
      }
      require(reversals == 0,
              "low-grip/grade acceleration rapidly reversed shifts");
      require(longestOpen < .4,
              "low-grip/grade acceleration left clutch continuously open");
      std::cout << "surface grip=" << grip << " grade=" << grade
                << " speed=" << sim.car.speed * 3.6
                << " km/h gear=" << sim.car.gear << '\n';
    }
  }
}
void partialThrottleDoesNotBog() {
  for (double throttle : {.05, .1, .25}) {
    Simulation sim;
    double halfwaySpeed = 0;
    for (int i = 0; i < 120 * 12; ++i) {
      sim.tick({throttle, 0, 0});
      finiteState(sim);
      if (i + 1 == 120 * 6)
        halfwaySpeed = sim.car.speed;
    }
    require(sim.car.speed > halfwaySpeed + .5 && sim.car.speed > 3,
            "part-throttle launch stopped accelerating");
    require(sim.car.engineRpm > 1200,
            "part-throttle engine remained on the idle governor");
  }
}
void clutchOverrideAndReset() {
  Simulation sim;
  sim.car.speed = 12;
  sim.synchronizeState();
  const int initialGear = sim.car.gear;
  for (int i = 0; i < 240; ++i) {
    sim.tick({1, 0, 0, 0, 1});
    finiteState(sim);
    require(sim.car.clutchEngagement == 0,
            "fully pressed clutch pedal did not disconnect drive");
    require(sim.car.gear == initialGear,
            "free-revving engine shifted with clutch pedal pressed");
  }
  sim.reset();
  sim.tick({}, 0);
  require(sim.car.gear == 1 && sim.car.direction == 1 &&
              sim.groundSpeed() == 0 && sim.car.clutchEngagement == 0,
          "reset retained transmission/drive state");
  sim.tick({0, 1, 0});
  require(sim.car.direction == -1 && sim.car.gear == -1,
          "fresh brake press at rest did not select reverse");
  for (int i = 0; i < 120 * 3; ++i)
    sim.tick({0, 1, 0});
  require(sim.car.speed < -1 && sim.car.gear == -1,
          "reverse did not transmit drive torque");
}
template <typename Sim> void requireDriveTorque(const Sim &sim) {
  if constexpr (requires { sim.car.clutchTorque; })
    require(std::abs(sim.car.clutchTorque) > 5,
            "steady throttle-on spin lost clutch torque");
}
void cornerRecovery() {
  // Exact wheel measurements from 58161's wheel_geometry events. Its mesh
  // bounds do NOT establish the physical body envelope, so this fixture keeps
  // the documented default body and dynamics. This is a deterministic corner
  // regression inspired by that drive, not an exact replay of the live run.
  VehicleGeometry geometry;
  geometry.wheels = {{{{-.74676, .2993066608905792, 1.2586160898208618},
                       .299,
                       .24449671804904938},
                      {{.74676, .2993066608905792, 1.2586160898208618},
                       .299,
                       .24449671804904938},
                      {{-.74295, .2993018925189972, -1.364168643951416},
                       .299,
                       .24445891380310059},
                      {{.74295, .2993018925189972, -1.364168643951416},
                       .299,
                       .24445891380310059}}};
  for (double turnSeconds : {2.0, 3.0})
    for (double steering : {-1.0, 1.0}) {
      Simulation sim;
      require(sim.setGeometry(geometry), "configure measured wheel geometry");
      sim.car.speed = 16;
      sim.synchronizeState();
      for (int i = 0; i < int(120 * turnSeconds); ++i)
        sim.tick({1, 0, steering});
      int previousGear = sim.car.gear, shifts = 0;
      double openTime = 0, openRun = 0, longestOpen = 0;
      for (int i = 0; i < 120 * 8; ++i) {
        sim.tick({1, 0, 0});
        finiteState(sim);
        if (sim.car.gear != previousGear) {
          ++shifts;
          previousGear = sim.car.gear;
        }
        if (sim.car.clutchEngagement < .001) {
          openTime += step;
          openRun += step;
          longestOpen = std::max(longestOpen, openRun);
        } else {
          openRun = 0;
        }
        require(!sim.boundaryContact && !sim.chassisContact,
                "corner fixture collided with an unrelated obstacle");
      }
      std::cout << "corner turn_seconds=" << turnSeconds
                << " steer=" << steering
                << " recovery_speed=" << sim.groundSpeed()
                << " m/s gear=" << sim.car.gear << " shifts=" << shifts
                << " clutch_open=" << openTime
                << " s longest_open=" << longestOpen << " s\n";
      // Keeping full power during a spin need not regain traction. Both
      // durations must retain actual drive torque without reopening the clutch
      // repeatedly; recovery with a controlled lift is exercised separately.
      require(shifts <= 6 && openTime < 2 && longestOpen < .4,
              "corner exit triggered repeated shifts with an open clutch");
      require(sim.car.clutchEngagement > .99,
              "steady throttle-on spin retained an open clutch");
      requireDriveTorque(sim);
    }
  for (double steering : {-1.0, 1.0}) {
    Simulation sim;
    require(sim.setGeometry(geometry), "configure recovery wheel geometry");
    sim.car.speed = 16;
    sim.synchronizeState();
    for (int i = 0; i < 120 * 2; ++i)
      sim.tick({1, 0, steering});
    for (int i = 0; i < 120 * 4; ++i)
      sim.tick({1, 0, 0});
    // Lift for one second to let the spinning driven tyres regain grip;
    // then reapply power. No artificial wheel or yaw reset is used.
    for (int i = 0; i < 120; ++i)
      sim.tick({0, 0, 0});
    for (int i = 0; i < 120 * 6; ++i) {
      sim.tick({1, 0, 0});
      finiteState(sim);
      require(!sim.boundaryContact && !sim.chassisContact,
              "lift-recovery fixture collided with an unrelated obstacle");
    }
    std::cout << "corner controlled_lift steer=" << steering
              << " recovery_speed=" << sim.groundSpeed()
              << " m/s gear=" << sim.car.gear << " yaw_rate=" << sim.car.yawRate
              << '\n';
    require(sim.groundSpeed() > 20 && sim.car.gear >= 3 &&
                std::abs(sim.car.yawRate) < .1,
            "vehicle failed to regain traction and accelerate after a lift");
  }
}

void stopAndRelaunch() {
  Simulation sim;
  for (int i = 0; i < 120 * 10; ++i)
    sim.tick({1, 0, 0});
  require(sim.car.gear >= 3, "braking fixture did not reach a higher gear");
  for (int i = 0; i < 120 * 8; ++i)
    sim.tick({0, 1, 0});
  require(sim.groundSpeed() < .01 && sim.car.direction == 1,
          "held brake did not stop without selecting reverse");
  require(sim.car.gear == 1, "automatic gearbox did not select first at rest");
  sim.tick({});
  for (int i = 0; i < 120 * 3; ++i)
    sim.tick({1, 0, 0});
  require(sim.car.speed > 7, "stopped car failed to relaunch in first gear");
}

// A dependent check keeps this source compilable against the uploaded baseline
// for --corner-only / --isolated failure demonstrations; full validation still
// requires the new public diagnostic fields and rejects their absence.
template <typename Sim> void diagnosticsAndValidation() {
  Sim sim;
  auto dynamics = sim.dynamics();
  using Dynamics = std::remove_cvref_t<decltype(dynamics)>;
  if constexpr (requires {
                  sim.car.shiftRemaining;
                  sim.car.shiftCooldown;
                  sim.car.roadCoupledRpm;
                  sim.car.gearboxInputRpm;
                  sim.car.clutchSlipRpm;
                  sim.car.clutchTorque;
                  dynamics.shiftReengagementTime;
                  dynamics.minimumGearHoldTime;
                  dynamics.shiftConfirmTime;
                  dynamics.partThrottleShiftUpRpm;
                }) {
    const auto revision = sim.configurationRevision();
    for (auto member :
         {&Dynamics::shiftReengagementTime, &Dynamics::minimumGearHoldTime,
          &Dynamics::shiftConfirmTime, &Dynamics::partThrottleShiftUpRpm}) {
      for (double invalid : {-1.0, 0.0, std::numeric_limits<double>::infinity(),
                             std::numeric_limits<double>::quiet_NaN()}) {
        auto candidate = dynamics;
        candidate.*member = invalid;
        require(!sim.setDynamics(candidate) &&
                    sim.configurationRevision() == revision &&
                    sim.dynamics() == dynamics,
                "invalid transmission tuning changed configuration");
      }
    }
    bool sawShift = false, sawReengagement = false;
    double previousEngagement = 1;
    for (int i = 0; i < 120 * 8; ++i) {
      sim.tick({1, 0, 0});
      const auto &c = sim.car;
      for (double value : {c.shiftRemaining, c.shiftCooldown, c.roadCoupledRpm,
                           c.gearboxInputRpm, c.clutchSlipRpm, c.clutchTorque})
        require(std::isfinite(value), "non-finite transmission diagnostics");
      require(std::abs(c.clutchSlipRpm - (c.engineRpm - c.gearboxInputRpm)) <
                  1e-7,
              "clutch slip diagnostic does not match engine/shaft speed");
      if (c.shiftRemaining > 0) {
        sawShift = true;
        require(c.clutchEngagement == 0 && c.clutchTorque == 0,
                "open shift clutch transmitted torque");
        const double remaining = c.shiftRemaining, cooldown = c.shiftCooldown;
        sim.tick({}, 0);
        require(c.shiftRemaining == remaining && c.shiftCooldown == cooldown,
                "zero timestep advanced transmission timers");
      } else if (sawShift && c.shifting) {
        sawReengagement = true;
        require(c.clutchEngagement - previousEngagement < .2,
                "shift clutch re-engaged in a discontinuous step");
      }
      previousEngagement = c.clutchEngagement;
      if (sawReengagement && !c.shifting)
        break;
    }
    require(sawShift && sawReengagement,
            "diagnostic fixture did not exercise a complete shift");
    sim.synchronizeState();
    require(!sim.car.shifting && sim.car.shiftRemaining == 0 &&
                sim.car.shiftCooldown == 0 && sim.car.clutchTorque == 0 &&
                sim.car.clutchEngagement == 0,
            "external synchronization retained shift/clutch history");
    sim.reset();
    require(!sim.car.shifting && sim.car.shiftRemaining == 0 &&
                sim.car.shiftCooldown == 0 && sim.car.clutchTorque == 0 &&
                sim.car.clutchEngagement == 0,
            "reset retained shift/clutch history");
  } else {
    require(false, "new transmission diagnostics/tuning unavailable");
  }
}

void dtDoesNotChangeShiftSequence() {
  Simulation fine, coarse;
  int fineGearChanges = 0, coarseGearChanges = 0;
  int fineGear = 1, coarseGear = 1;
  for (int i = 0; i < 120 * 10; ++i) {
    fine.tick({1, 0, 0}, step);
    if (fine.car.gear != fineGear) {
      ++fineGearChanges;
      fineGear = fine.car.gear;
    }
  }
  for (int i = 0; i < 30 * 10; ++i) {
    coarse.tick({1, 0, 0}, 1.0 / 30);
    if (coarse.car.gear != coarseGear) {
      ++coarseGearChanges;
      coarseGear = coarse.car.gear;
    }
  }
  require(fine.car.gear == coarse.car.gear &&
              fineGearChanges == coarseGearChanges &&
              std::abs(fine.car.speed - coarse.car.speed) < 1e-6 &&
              std::abs(fine.car.engineRpm - coarse.car.engineRpm) < 1e-5,
          "same physics interval produced a different shift sequence");
  const auto before = fine.car;
  for (double invalid : {-1.0, 1.01, std::numeric_limits<double>::quiet_NaN()})
    fine.tick({1, 0, 0}, invalid);
  require(fine.car.speed == before.speed && fine.car.gear == before.gear &&
              fine.car.engineRpm == before.engineRpm,
          "invalid timestep advanced the drivetrain");
}
} // namespace
int main(int argc, char **argv) {
  try {
    const std::string_view mode = argc == 2 ? argv[1] : "";
    require(argc <= 2 && (mode.empty() || mode == "--isolated" ||
                          mode == "--corner-only"),
            "usage: transmission_checks [--isolated|--corner-only]");
    if (mode == "--corner-only") {
      cornerRecovery();
      return 0;
    }
    const bool isolated = mode == "--isolated";
    wheelspinCannotUpshift();
    std::cout
        << "PASS: wheelspin cannot upshift at low road speed (RWD/AWD/FWD)\n";
    noSupportCannotShift();
    std::cout << "PASS: airborne wheelspin holds the current gear\n";
    if (!isolated) {
      movingPoseHonorsImmediatePedalDemand();
      fullThrottleProgresses();
      lowGripAndGradeDoNotHunt();
      partialThrottleDoesNotBog();
      clutchOverrideAndReset();
      cornerRecovery();
      stopAndRelaunch();
      diagnosticsAndValidation<Simulation>();
      dtDoesNotChangeShiftSequence();
      std::cout
          << "PASS: full/partial throttle, surfaces/grades, clutch, reverse, "
             "corner recovery, stop/relaunch, tuning validation, reset and "
             "timestep consistency\n";
    }
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
