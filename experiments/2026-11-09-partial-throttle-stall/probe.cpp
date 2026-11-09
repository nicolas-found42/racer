// Reproduces the partial-throttle launch stall on the force-based vehicle
// model (debug/wheel-clip working tree). Headless: no SDL, bgfx or window.
//
// Build and run from the repository root:
//   mkdir -p experiments/2026-11-09-partial-throttle-stall/output
//   clang++ -std=c++20 -O2 -I src -I tests \
//     experiments/2026-11-09-partial-throttle-stall/probe.cpp \
//     src/simulation.cpp src/setup.cpp src/vehicle_geometry.cpp \
//     -o experiments/2026-11-09-partial-throttle-stall/output/probe
//   experiments/2026-11-09-partial-throttle-stall/output/probe
//
// Reads ignored local descriptors under assets/local/vehicles (24 present).
#include "simulation.h"
#include "test_session.h"
#include "vehicle_fixtures.h"
#include "vehicle_tuning.h"
#include <algorithm>
#include <cstdio>

using namespace racer;

namespace {
constexpr double dt = 1.0 / 120.0;

void configure(Simulation &sim, const VehicleGeometry &geometry) {
  VehicleSetup setup;
  sim.setSetup(setup);
  sim.setGeometry(geometry);
  sim.setDynamics(dynamicsFor(geometry)); // application wiring path
  sim.setRoadSampler({});                 // flat Y=0 default world
  sim.reset();
  sim.synchronizeState();
}

// Full throttle: report ground speed after 4 s and validate the built-in
// acceleration test (same PlayFlow wiring: testRevision 2).
void fullThrottle(const NamedGeometry &car) {
  Simulation sim;
  configure(sim, car.geometry);
  for (int i = 0; i < 120 * 4; ++i)
    sim.tick(Input{1, 0, 0}, dt);
  const double v4 = sim.groundSpeed();

  Simulation testSim;
  configure(testSim, car.geometry);
  TestSession session;
  VehicleSetup setup;
  session.start(TestKind::Acceleration, 0, setup, testSim, "probe", 2);
  int guard = 0;
  while (session.active() && guard++ < 120 * 120)
    session.tick(testSim, {});
  std::printf("%-52s full4s=%6.2f m/s  test valid=%d %6.2fs %.1fm %s\n",
              car.name.c_str(), v4, session.result().valid,
              session.result().seconds, session.result().distance,
              session.result().reason.c_str());
}

// 10 % throttle for 12 s: plateau speed, engine rpm and final acceleration.
void partialThrottle(const NamedGeometry &car) {
  Simulation sim;
  configure(sim, car.geometry);
  double v4 = 0, v8 = 0, minRpm = 1e9;
  for (int i = 1; i <= 120 * 12; ++i) {
    sim.tick(Input{.1, 0, 0}, dt);
    if (i == 120 * 4)
      v4 = sim.groundSpeed();
    if (i == 120 * 8)
      v8 = sim.groundSpeed();
    if (i >= 24)
      minRpm = std::min(minRpm, sim.car.engineRpm);
  }
  const double v12 = sim.groundSpeed();
  const bool stalled = v12 < 2.7 && sim.car.accelerationLongitudinal < 0.05;
  std::printf("%-52s 10%% v4=%5.2f v8=%5.2f v12=%5.2f rpm=%4.0f minRpm=%4.0f "
              "a=%6.3f%s\n",
              car.name.c_str(), v4, v8, v12, sim.car.engineRpm, minRpm,
              sim.car.accelerationLongitudinal, stalled ? "  STALL" : "");
}

// Throttle threshold on the default 2.7 m fixture (same engine/drivetrain for
// every car; only suspension and tyre geometry differ).
void threshold() {
  VehicleGeometry geometry;
  std::printf(
      "throttle  v(2s)  v(4s)  v(6s)  v(10s)  rpm(10s) clutch aLong(10s)\n");
  for (double t = 0.18; t <= 0.351; t += 0.01) {
    Simulation sim;
    configure(sim, geometry);
    double v2 = 0, v4 = 0, v6 = 0;
    for (int i = 1; i <= 120 * 10; ++i) {
      sim.tick(Input{t, 0, 0}, dt);
      if (i == 240)
        v2 = sim.groundSpeed();
      if (i == 480)
        v4 = sim.groundSpeed();
      if (i == 720)
        v6 = sim.groundSpeed();
    }
    std::printf("%8.2f %6.2f %6.2f %6.2f %7.2f %8.0f %6.2f %9.2f\n", t, v2, v4,
                v6, sim.groundSpeed(), sim.car.engineRpm,
                sim.car.clutchEngagement, sim.car.accelerationLongitudinal);
  }
}
} // namespace

int main() {
  const auto cars = localCars("assets/local/vehicles");
  std::printf("== full throttle / acceleration test, %zu cars ==\n",
              cars.size());
  for (const auto &car : cars)
    fullThrottle(car);
  std::printf("\n== 10 %% throttle for 12 s ==\n");
  for (const auto &car : cars)
    partialThrottle(car);
  std::printf("\n== partial-throttle threshold (default geometry) ==\n");
  threshold();
}
