// Every synthetic car and every real local descriptor runs the three benchmarks
// through PlayFlow::configureVehicle, the same path the application takes.
#include "play_flow.h"
#include "vehicle_fixtures.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <string>
#include <unistd.h>
using namespace racer;
namespace {
int failures = 0;
void check(bool ok, const std::string &car, const std::string &why) {
  if (!ok) {
    ++failures;
    std::cerr << "FAIL [" << car << "]: " << why << '\n';
  }
}
std::string identity(int index) {
  std::string digits = std::to_string(index + 1);
  return "vehicle-" + std::string(64 - digits.size(), 'a') + digits;
}
} // namespace
int main(int argc, char **argv) {
  const auto cars = allCars(argc, argv);
  const auto root = std::filesystem::temp_directory_path() / ("racer-bench-" + std::to_string(getpid()));
  std::filesystem::create_directories(root);
  double slowest = 0, fastest = 1e9, shortest = 1e9, longest = 0, handling = 0;
  int index = 0;
  for (const auto &car : cars) {
    const auto &name = car.name;
    PlayFlow flow((root / (std::to_string(index) + ".txt")).string());
    check(flow.configureVehicle(identity(index), "car", car.geometry), name, "configured");
    ++index;
    for (const auto kind : {TestKind::Acceleration, TestKind::Braking}) {
      flow.startTest(kind);
      flow.rearming = false;
      flow.sim.tick({}, 0);
      for (int i = 0; i < 12000 && flow.session.active(); ++i) flow.tick({});
      const auto &result = flow.session.result();
      const std::string test = kind == TestKind::Acceleration ? "acceleration" : "braking";
      check(result.valid, name, test + " valid (" + result.reason + ")");
      if (!result.valid) continue;
      if (kind == TestKind::Acceleration) {
        check(result.seconds > 6 && result.seconds < 9.5, name, "0-100 km/h within a plausible band");
        slowest = std::max(slowest, result.seconds);
        fastest = std::min(fastest, result.seconds);
      } else {
        check(result.distance > 36 && result.distance < 48, name, "100-0 km/h stop within the tyre limit band");
        shortest = std::min(shortest, result.distance);
        longest = std::max(longest, result.distance);
      }
    }
    // Player-run handling course, driven by the same steering law the
    // session checks use (target 8 m past each gate, 7-8 m/s).
    flow.startTest(TestKind::Handling);
    flow.rearming = false;
    flow.sim.tick({}, 0);
    for (int i = 0; i < 40000 && flow.session.active(); ++i) {
      if (flow.session.phase() == TestPhase::Running && flow.session.nextGate() < handlingCourse().gates.size()) {
        const auto &gate = handlingCourse().gates[flow.session.nextGate()];
        const double x = gate.x + gate.nx * 8 - flow.sim.car.x, z = gate.z + gate.nz * 8 - flow.sim.car.z;
        const double error = std::remainder(std::atan2(x, z) - flow.sim.car.heading, 2 * 3.141592653589793);
        flow.tick({flow.sim.car.speed < 7 ? 1. : 0., flow.sim.car.speed > 8 ? 1. : 0.,
                   std::clamp(error * 2., -1., 1.)});
      } else {
        flow.tick({});
      }
    }
    check(flow.session.result().valid, name, "handling course completes (" + flow.session.result().reason + ")");
    handling = std::max(handling, flow.session.result().seconds);
  }
  std::filesystem::remove_all(root);
  std::cout << cars.size() << " cars: 0-100 " << fastest << "-" << slowest << " s, 100-0 " << shortest << "-" << longest
            << " m, slowest handling course " << handling << " s\n";
  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "PASS: acceleration, braking and handling course for every car\n";
}
